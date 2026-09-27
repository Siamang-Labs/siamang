"""The rules of a version 2 codeframe: words, negation, clauses and terms.

A codeframe of version 2 codes an answer three ways, in this order: a coder's
own decision for that answer (kept by its fingerprint), else the rules, else
nothing — the answer stays uncoded for a coder to read. This module is the
second step. It is deliberately small and literal, because a rule a researcher
cannot predict is a rule nobody can defend:

* An answer is **normalised** as :func:`siamang.data.text_coding.normalise`
  does (Unicode NFKC, case-folded, whitespace collapsed), its apostrophes made
  one (``’`` → ``'``), then the codeframe's **replacements** applied — whole
  words or phrases, for synonyms and typos.
* It is split into **words**: runs of letters, digits and combining marks in
  any script, with an apostrophe inside a word kept (``wasn't``). Diacritics
  stay (``café`` is not ``cafe``). Every other character separates words, and
  ``. , ; : ! ? ( ) [ ] { } – — …`` (and their CJK, Arabic and Devanagari
  forms) also end a **clause**, as do the words *but, however, although,
  though, whereas, except* and *plus*.
* A **negation** — *not, no, never, cannot, without, nothing, none, nobody,
  neither, nor, hardly, barely* and every *n't* form (``wasn't``, and
  ``wasnt`` typed without its apostrophe) — marks the next three words as
  negated, stopping early at a clause's end and at *and, or, yet*. The packs
  are English; an answer in another language keeps its words and matches terms
  in them, but no negation is found in it.

A **term** is a word or phrase in the same normal form, and what it may say is
short: ``delay*`` (``*`` for any letters: *delay, delays, delayed*),
``slow|late`` (either word at that place), ``not_late`` (only a negated
mention: *wasn't late*, *never late*), ``staff ~3 rude`` (the two within three
words of each other, in either order). A term matches only mentions that are
**not** negated — ``late`` does not match *wasn't late* — unless the negation
is part of the term itself (``not late``, ``don't know``). There are no
regular expressions: a pattern language is a way to write a rule nobody can
read back, and a server that runs them runs whatever it is sent.

Everything here is a pure function of the codeframe and the text: no model,
no network, no state that outlives a call except caches of the compiled rules.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

__all__ = [
    "ANSWER",
    "CLAUSE",
    "Analysis",
    "Fired",
    "RuleSet",
    "RuleTheme",
    "Term",
    "TermError",
    "analyse",
    "is_negator",
    "normalise_replacement",
    "normalise_term",
    "parse_term",
    "resolve",
    "rule_text",
    "suggest_terms",
]

CLAUSE = "clause"
ANSWER = "answer"
SCOPES = (CLAUSE, ANSWER)

# ─── The English packs ────────────────────────────────────────────────────────

#: Words that negate the ones after them (with every word ending in n't).
NEGATORS = frozenset(
    "not no never cannot without nothing none nobody neither nor hardly barely".split()
)
#: The n't forms as respondents type them without the apostrophe.
BARE_NT = frozenset(
    "dont doesnt didnt isnt wasnt arent werent cant couldnt wont wouldnt shouldnt "
    "havent hasnt hadnt aint mustnt neednt".split()
)
#: How many words after a negation it reaches.
NEGATION_WINDOW = 3
#: Words that end a negation's reach (as a clause's end does).
NEGATION_STOPS = frozenset("but however although though whereas except plus and or yet".split())
#: Words that end a clause (as punctuation does).
CLAUSE_WORDS = frozenset("but however although though whereas except plus".split())
#: Characters that end a clause: sentence and list punctuation, brackets, dashes.
BOUNDARIES = ".,;:!?()[]{}–—…¡¿。，、；：！？؟،؛।॥"
#: Words too common to suggest as a term.
STOP_WORDS = frozenset(
    """
a about above after again against all am an and any are as at be because been before being below
between both by can could did do does doing down during each few for from further had has have
having he her here hers herself him himself his how i if in into is it its itself just me more
most my myself of off on once only other our ours ourselves out over own same she should so some
such than that the their theirs them themselves then there these they this those through to too
under until up very was we were what when where which while who whom why will with would you your
yours yourself yourselves im i'm it's that's there's they're we're you're i've i'd i'll get got
also really much maybe please us one lot bit make like think
""".split()
)

_APOSTROPHES = str.maketrans(dict.fromkeys("‘’ʼ`´′＇", "'"))
#: As the rules read an answer: one apostrophe, and no underscore (which
#: ``\w`` counts as a letter, and a word here does not).
_READ = str.maketrans({**dict.fromkeys("‘’ʼ`´′＇", "'"), "_": " "})
#: The longest a term may be, and the widest a proximity (``~N``).
MAX_TERM_LENGTH = 200
MAX_GAP = 20


@lru_cache(maxsize=1)
def _word_class() -> str:
    """The inside of a character class of the letters, digits and combining
    marks of every script: ``\\w`` (whose underscore the text the rules read
    no longer has) and the marks ``\\w`` leaves out (Devanagari's vowel signs,
    Arabic's harakat), so a word in those scripts is one word rather than its
    pieces. Built once, from ``unicodedata``; one class, so words split fast."""

    ranges: list[tuple[int, int]] = []
    start = previous = -2
    for code in (*range(0x300, 0x30000), *range(0xE0100, 0xE01F0)):
        if unicodedata.category(chr(code))[0] != "M":
            continue
        if code != previous + 1:
            if start >= 0:
                ranges.append((start, previous))
            start = code
        previous = code
    ranges.append((start, previous))
    marks = "".join(
        re.escape(chr(low)) if low == high else f"{re.escape(chr(low))}-{re.escape(chr(high))}"
        for low, high in ranges
    )
    return f"\\w{marks}"


@lru_cache(maxsize=1)
def _patterns() -> tuple[re.Pattern[str], re.Pattern[str]]:
    char = f"[{_word_class()}]"
    word = f"{char}+(?:'{char}+)*"
    tokens = re.compile(f"(?P<w>{word})|(?P<b>[{re.escape(BOUNDARIES)}]+)")
    return tokens, re.compile(word)


def rule_text(normalised: str) -> str:
    """An answer's normalised text (``text_coding.normalise``) as the rules
    read it before replacements: one apostrophe, no underscore."""
    return normalised.translate(_READ)


def is_negator(word: str) -> bool:
    return word in NEGATORS or word.endswith("n't") or word in BARE_NT


# ─── An answer, read ──────────────────────────────────────────────────────────


@dataclass(slots=True)
class Analysis:
    """An answer as the rules see it: its words, which are negated and by what,
    and where its clauses and sentences end."""

    text: str
    words: list[str]
    #: The index of the word that negates each word, or -1.
    negated_by: list[int]
    #: The clause of each word; -1 for a word that ends a clause (*but*).
    clause: list[int]
    #: Which stretch between two punctuation marks each word is in: a term
    #: never reaches across one, in either scope.
    segment: list[int]
    #: Filled by :class:`RuleSet`: the word patterns each word matches.
    matched: list[frozenset[int]] = field(default_factory=list)

    def clause_texts(self) -> list[str]:
        clauses: dict[int, list[str]] = {}
        for word, number in zip(self.words, self.clause, strict=True):
            if number >= 0:
                clauses.setdefault(number, []).append(word)
        return [" ".join(words) for _, words in sorted(clauses.items())]

    def fragment(self, positions: Iterable[int]) -> str:
        spots = list(positions)
        return " ".join(self.words[min(spots) : max(spots) + 1])


_PLAIN, _ENDS_CLAUSE, _ENDS_NEGATION, _NEGATES = 0, 1, 2, 3
_KINDS: dict[str, int] = {}


def _kind(word: str) -> int:
    kind = _KINDS.get(word)
    if kind is None:
        if word in CLAUSE_WORDS:
            kind = _ENDS_CLAUSE
        elif word in NEGATION_STOPS:
            kind = _ENDS_NEGATION
        elif is_negator(word):
            kind = _NEGATES
        else:
            kind = _PLAIN
        if len(_KINDS) < 200_000:
            _KINDS[word] = kind
    return kind


def analyse(text: str) -> Analysis:
    """Split ``text`` — already normalised and replaced — into words, and mark
    the clauses and the negated words."""

    tokens, _ = _patterns()
    words: list[str] = []
    negated_by: list[int] = []
    clause: list[int] = []
    segment: list[int] = []
    current_clause, current_segment = 0, 0
    clause_open = False
    reach, source = 0, -1
    for word, _ in tokens.findall(text):
        if not word:  # punctuation: the clause and any negation end here
            if clause_open:
                current_clause += 1
                clause_open = False
            if words and segment[-1] == current_segment:
                current_segment += 1
            reach = 0
            continue
        kind = _KINDS.get(word)
        if kind is None:
            kind = _kind(word)
        index = len(words)
        words.append(word)
        segment.append(current_segment)
        if kind == _ENDS_CLAUSE:  # it ends a negation too
            if clause_open:
                current_clause += 1
                clause_open = False
            clause.append(-1)
            reach = 0
            negated_by.append(-1)
            continue
        clause.append(current_clause)
        clause_open = True
        if kind == _ENDS_NEGATION:
            reach = 0
            negated_by.append(-1)
        elif kind == _NEGATES:
            reach, source = NEGATION_WINDOW, index
            negated_by.append(-1)
        elif reach:
            reach -= 1
            negated_by.append(source)
        else:
            negated_by.append(-1)
    return Analysis(text, words, negated_by, clause, segment)


# ─── Terms ────────────────────────────────────────────────────────────────────


class TermError(ValueError):
    """A term that cannot be read."""


@dataclass(frozen=True, slots=True)
class Atom:
    """One way a word of a term can be matched: a form (``delay*``) and
    whether the mention must be negated (``not_``) or not."""

    core: str
    negated: bool


@dataclass(frozen=True, slots=True)
class Term:
    """A term, read: a phrase — each word a set of alternatives — and, for a
    proximity term, a second phrase and how many words may lie between."""

    text: str
    first: tuple[tuple[Atom, ...], ...]
    second: tuple[tuple[Atom, ...], ...] = ()
    gap: int = 0

    @property
    def words(self) -> tuple[tuple[Atom, ...], ...]:
        return self.first + self.second


def normalise_term(term: str) -> str:
    """A term in the answers' normal form (NFKC, case-folded, one apostrophe,
    single spaces)."""
    text = unicodedata.normalize("NFKC", str(term)).casefold().translate(_APOSTROPHES)
    return " ".join(text.split())


def normalise_replacement(text: str) -> str:
    """A replacement's words in the form the rules read an answer in."""
    return " ".join(unicodedata.normalize("NFKC", str(text)).casefold().translate(_READ).split())


def parse_term(term: Any) -> tuple[Term, list[str]]:
    """Read a term; return it with warnings about the parts of it that can
    never match an answer. A term that cannot be read raises
    :class:`TermError` with the reason."""

    if not isinstance(term, str):
        raise TermError("a term is text")
    text = normalise_term(term)
    if not text:
        raise TermError("the term is empty")
    if len(text) > MAX_TERM_LENGTH:
        raise TermError(f"the term is longer than {MAX_TERM_LENGTH} characters")
    if text.startswith("re:"):
        raise TermError(
            "regular expressions are not supported: write the words, with * for word "
            "forms (delay*), | for alternatives (slow|late) and ~N for words near each "
            "other (staff ~3 rude)"
        )
    parts = text.split(" ")
    operators = [i for i, part in enumerate(parts) if "~" in part]
    if len(operators) > 1:
        raise TermError("a term takes one ~N at most")
    warnings: list[str] = []
    if operators:
        at = operators[0]
        found = re.fullmatch(r"~(\d+)", parts[at])
        if found is None:
            raise TermError(
                "~ takes the number of words that may lie between two words, "
                "with spaces around it: staff ~3 rude"
            )
        if at == 0 or at == len(parts) - 1:
            raise TermError("~N needs words on both sides: staff ~3 rude")
        gap = int(found.group(1))
        if gap > MAX_GAP:
            raise TermError(f"~{gap} is too far apart: at most ~{MAX_GAP}")
        first = _phrase(parts[:at], warnings, text)
        second = _phrase(parts[at + 1 :], warnings, text)
        return Term(str(term).strip(), first, second, gap), warnings
    return Term(str(term).strip(), _phrase(parts, warnings, text)), warnings


def _phrase(parts: list[str], warnings: list[str], whole: str) -> tuple[tuple[Atom, ...], ...]:
    words = []
    for part in parts:
        alternatives = part.split("|")
        if any(not alternative for alternative in alternatives):
            raise TermError(f"'{part}' has an empty alternative: write slow|late")
        atoms = []
        for alternative in alternatives:
            negated = alternative.startswith("not_")
            core = alternative[4:] if negated else alternative
            if not core:
                raise TermError("not_ needs a word after it: not_late")
            if not core.replace("*", ""):
                raise TermError("* stands for letters of a word and needs some of its own: delay*")
            problem = _never_a_word(core)
            if problem:
                warnings.append(
                    f"can never match: {problem}"
                    if alternative == whole
                    else f"has a part that can never match, '{alternative}': {problem}"
                )
                continue
            atoms.append(Atom(core, negated))
        words.append(tuple(atoms))
    return tuple(words)


def _never_a_word(core: str) -> str | None:
    """Why ``core`` (``*`` standing for letters) can never be a word of an
    answer, or None."""
    _, word = _patterns()
    probe = core.replace("*", "x")
    if "_" not in probe and word.fullmatch(probe):
        return None
    for char in probe:
        if char != "'" and (char == "_" or not word.fullmatch(char)):
            return (
                f"'{char}' is not part of a word — the answers are split into words there, "
                "so write the parts as separate words"
            )
    return "a word of an answer neither begins nor ends with an apostrophe, nor has two in a row"


# ─── Themes and their rules, compiled ─────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class RuleTheme:
    """What the rule set needs of a theme."""

    code: int
    label: str
    order: int
    exclusive: bool = False
    priority: float = 0.0
    scope: str = CLAUSE
    include: tuple[str, ...] = ()
    require: tuple[tuple[str, ...], ...] = ()
    exclude: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Fired:
    """A theme whose rule matched: the include term, the words it matched and
    the clause (its number and its words; -1 and "" for the whole answer)."""

    theme: RuleTheme
    term: str
    fragment: str
    clause: int
    where: str = ""


@dataclass(slots=True)
class _Compiled:
    term: Term
    #: Each word of the term: its alternatives as (pattern id, negated).
    first: tuple[tuple[tuple[int, bool], ...], ...]
    second: tuple[tuple[tuple[int, bool], ...], ...]
    gap: int
    dead: bool


class RuleSet:
    """The rules of one codeframe, compiled once: every distinct word form of
    every term becomes one pattern, every term is filed under the patterns
    its first word may take, and an answer's words are looked up once each
    (and remembered), so coding an answer costs what its words match rather
    than what the codeframe holds."""

    def __init__(self, themes: Sequence[RuleTheme], replace: Sequence[tuple[str, str]] = ()):
        self.themes = tuple(themes)
        self._replacements = {
            normalise_replacement(a): normalise_replacement(b) for a, b in replace
        }
        self._replace_re = _replacer(self._replacements)
        self._patterns: list[str] = []
        self._pattern_ids: dict[str, int] = {}
        self._terms: list[_Compiled] = []
        self._term_ids: dict[str, int] = {}
        #: pattern id -> the terms whose first word may take it
        self._anchored: dict[int, list[int]] = {}
        self._exact: dict[str, list[int]] = {}
        self._prefix: dict[str, list[int]] = {}
        self._suffix: dict[str, list[int]] = {}
        self._other: list[tuple[int, tuple[str, ...]]] = []
        self._seen: dict[str, frozenset[int]] = {}
        #: term id -> the rules (by index) it is an include term of
        self._including: dict[int, list[int]] = {}
        self.rules: list[
            tuple[RuleTheme, tuple[int, ...], tuple[tuple[int, ...], ...], tuple[int, ...]]
        ] = []
        for theme in self.themes:
            if not theme.include:
                continue
            include = tuple(self._term(text) for text in theme.include)
            require = tuple(tuple(self._term(text) for text in group) for group in theme.require)
            exclude = tuple(self._term(text) for text in theme.exclude)
            for number in include:
                self._including.setdefault(number, []).append(len(self.rules))
            self.rules.append((theme, include, require, exclude))

    # ── compiling ──

    def _term(self, text: str) -> int:
        key = normalise_term(text)
        if key in self._term_ids:
            return self._term_ids[key]
        try:
            term, _ = parse_term(text)
        except TermError:
            term = Term(text, ())
        first = tuple(self._word(atoms) for atoms in term.first)
        second = tuple(self._word(atoms) for atoms in term.second)
        dead = not first or any(not atoms for atoms in (*first, *second))
        number = len(self._terms)
        self._terms.append(_Compiled(term, first, second, term.gap, dead))
        self._term_ids[key] = number
        if not dead:
            for pattern in {pattern for pattern, _ in first[0]}:
                self._anchored.setdefault(pattern, []).append(number)
        return number

    def _word(self, atoms: tuple[Atom, ...]) -> tuple[tuple[int, bool], ...]:
        return tuple((self._pattern(atom.core), atom.negated) for atom in atoms)

    def _pattern(self, core: str) -> int:
        if core in self._pattern_ids:
            return self._pattern_ids[core]
        number = len(self._patterns)
        self._patterns.append(core)
        self._pattern_ids[core] = number
        stars = core.count("*")
        if not stars:
            self._exact.setdefault(core, []).append(number)
        elif stars == 1 and core.endswith("*"):
            self._prefix.setdefault(core[:-1], []).append(number)
        elif stars == 1 and core.startswith("*"):
            self._suffix.setdefault(core[1:], []).append(number)
        else:
            self._other.append((number, tuple(core.split("*"))))
        return number

    # ── reading an answer ──

    def prepare(self, normalised: str) -> Analysis:
        """An answer's normalised text, read: replacements made, words split
        and marked, and each word's patterns looked up."""
        analysis = analyse(self.replaced(normalised))
        analysis.matched = [self._patterns_of(word) for word in analysis.words]
        return analysis

    def _patterns_of(self, word: str) -> frozenset[int]:
        known = self._seen.get(word)
        if known is not None:
            return known
        found: set[int] = set(self._exact.get(word, ()))
        if self._prefix:
            for end in range(len(word) + 1):
                found.update(self._prefix.get(word[:end], ()))
        if self._suffix:
            for start in range(len(word) + 1):
                found.update(self._suffix.get(word[start:], ()))
        for number, pieces in self._other:
            if _glob(pieces, word):
                found.add(number)
        result = frozenset(found)
        if len(self._seen) < 500_000:
            self._seen[word] = result
        return result

    def replaced(self, normalised: str) -> str:
        """An answer's normalised text with one apostrophe and the replacements
        made: the text the rules read."""
        text = rule_text(normalised)
        if self._replace_re is not None:
            text = self._replace_re.sub(lambda m: self._replacements[m.group(0)], text)
            text = " ".join(text.split())
        return text

    def matches(
        self, analysis: Analysis, *, ignore_negation: bool = False
    ) -> dict[int, dict[int, str]]:
        """Every term that matches ``analysis``: term id -> {clause: the words
        it matched there} (clause -1 for a match that reaches across clauses,
        which only a rule over the whole answer takes)."""

        found: dict[int, dict[int, str]] = {}
        tried: set[tuple[int, int]] = set()
        for position, patterns in enumerate(analysis.matched):
            for pattern in patterns:
                for number in self._anchored.get(pattern, ()):
                    if (number, position) in tried:
                        continue
                    tried.add((number, position))
                    self._match_at(number, position, analysis, found, ignore_negation)
        return found

    def _match_at(
        self,
        number: int,
        start: int,
        analysis: Analysis,
        found: dict[int, dict[int, str]],
        ignore_negation: bool,
    ) -> None:
        term = self._terms[number]
        first = _phrase_at(term.first, start, analysis)
        if first is None:
            return
        spans: list[tuple[list[int], list[tuple[tuple[int, bool], ...]]]] = []
        if not term.second:
            spans.append(first)
        else:
            width = len(term.second)
            end = start + len(term.first)
            starts = [*range(end, end + term.gap + 1)]
            starts += [*range(start - term.gap - width, start - width + 1)]
            for other in starts:
                if other < 0:
                    continue
                second = _phrase_at(term.second, other, analysis)
                if second is not None and analysis.segment[other] == analysis.segment[start]:
                    spans.append((first[0] + second[0], first[1] + second[1]))
        for positions, atoms in spans:
            if not ignore_negation and not _negation_fits(positions, atoms, analysis):
                continue
            clauses = {analysis.clause[p] for p in positions}
            where = clauses.pop() if len(clauses) == 1 else -1
            hits = found.setdefault(number, {})
            hits.setdefault(where, analysis.fragment(positions))
            if where != -1:
                hits.setdefault(-1, analysis.fragment(positions))

    # ── themes ──

    def fire(
        self, analysis: Analysis, found: dict[int, dict[int, str]] | None = None
    ) -> list[Fired]:
        """The themes whose rules match ``analysis``, in the codeframe's order."""
        found = self.matches(analysis) if found is None else found
        fired: list[Fired] = []
        if not found:
            return fired
        texts: list[str] | None = None
        candidates = sorted({r for n in found for r in self._including.get(n, ())})
        for theme, include, require, exclude in (self.rules[r] for r in candidates):
            if theme.scope == ANSWER:
                if all(any(n in found for n in group) for group in require) and not any(
                    n in found for n in exclude
                ):
                    number = next(n for n in include if n in found)
                    fired.append(Fired(theme, self.term_text(number), found[number][-1], -1))
                continue
            clauses = sorted({c for n in include if n in found for c in found[n] if c >= 0})
            for clause in clauses:
                if all(
                    any(clause in found.get(n, ()) for n in group) for group in require
                ) and not any(clause in found.get(n, ()) for n in exclude):
                    number = next(n for n in include if clause in found.get(n, ()))
                    texts = analysis.clause_texts() if texts is None else texts
                    fired.append(
                        Fired(
                            theme,
                            self.term_text(number),
                            found[number][clause],
                            clause,
                            texts[clause],
                        )
                    )
                    break
        return fired

    def term_text(self, number: int) -> str:
        return self._terms[number].term.text

    def term_id(self, text: str) -> int:
        return self._term_ids[normalise_term(text)]

    def explain(self, analysis: Analysis) -> list[dict[str, Any]]:
        """Every rule that matched, or would have: fired, vetoed (a require
        missing, an exclude present) or blocked by a negation — with the
        clause and the words. For a person reading why an answer got a theme."""

        found = self.matches(analysis)
        loose = self.matches(analysis, ignore_negation=True)
        clauses = analysis.clause_texts()
        rows: list[dict[str, Any]] = []
        for theme, include, require, exclude in self.rules:
            units = (
                [-1]
                if theme.scope == ANSWER
                else sorted({c for n in include for c in loose.get(n, ()) if c >= 0})
            )
            for unit in units:
                base = {
                    "code": theme.code,
                    "label": theme.label,
                    "scope": theme.scope,
                    "clause": "" if unit == -1 else clauses[unit],
                }
                hit = next((n for n in include if unit in found.get(n, ())), None)
                if hit is None:
                    blocked = next((n for n in include if unit in loose.get(n, ())), None)
                    if blocked is not None:
                        rows.append(
                            {
                                **base,
                                "status": "negation",
                                "term": self.term_text(blocked),
                                "fragment": loose[blocked][unit],
                                "reason": self._negation_reason(blocked),
                            }
                        )
                    continue
                reason = ""
                where = "the answer" if unit == -1 else "this clause"
                for group in require:
                    if not any(unit in found.get(n, ()) for n in group):
                        needed = ", ".join(f"'{self.term_text(n)}'" for n in group)
                        reason = (
                            f"it requires {needed}, which is not in {where}"
                            if len(group) == 1
                            else f"it requires one of {needed}, and none is in {where}"
                        )
                        break
                if not reason:
                    veto = next((n for n in exclude if unit in found.get(n, ())), None)
                    if veto is not None:
                        reason = (
                            f"it excludes '{self.term_text(veto)}', which is there "
                            f"('{found[veto][unit]}')"
                        )
                status = "vetoed" if reason else "fired"
                rows.append(
                    {
                        **base,
                        "status": status,
                        "term": self.term_text(hit),
                        "fragment": found[hit][unit],
                        "reason": reason,
                    }
                )
        return rows

    def _negation_reason(self, number: int) -> str:
        """Why a term whose words are there does not match: the negation."""
        asks = {atom.negated for atoms in self._terms[number].term.words for atom in atoms}
        if asks == {False}:
            return (
                "the words are negated here, and the term takes a mention that is not "
                "(not_… takes a negated one)"
            )
        if asks == {True}:
            return "the term takes a negated mention (not_…), and the words are not negated here"
        return "the words are not negated as the term asks"


def resolve(
    fired: list[Fired], *, multiple: bool, max_codes: int
) -> tuple[list[Fired], list[tuple[Fired, str]]]:
    """Which of the fired themes an answer keeps, and why each other is
    dropped: an exclusive theme stands alone and gives way to any other;
    then the highest priority first (ties by the codeframe's order), cut to
    ``max_codes``, and to one when the codeframe gives one theme an answer.
    The kept themes come back in the codeframe's order."""

    if not fired:
        return [], []
    dropped: list[tuple[Fired, str]] = []
    ordinary = [f for f in fired if not f.theme.exclusive]
    if ordinary:
        dropped += [(f, "exclusive, and another theme matched") for f in fired if f.theme.exclusive]
        kept = ordinary
    else:
        ranked = sorted(fired, key=_rank)
        kept = ranked[:1]
        dropped += [(f, "exclusive, and one ranked higher matched") for f in ranked[1:]]
    kept = sorted(kept, key=_rank)
    cap = 1 if not multiple else (max_codes if max_codes > 0 else len(kept))
    if len(kept) > cap:
        why = (
            "the codeframe gives one theme an answer, and one ranked higher matched"
            if not multiple
            else f"max_codes keeps {cap}, and they ranked higher"
        )
        dropped += [(f, why) for f in kept[cap:]]
        kept = kept[:cap]
    return sorted(kept, key=lambda f: f.theme.order), dropped


def _rank(fired: Fired) -> tuple[float, int]:
    return (-fired.theme.priority, fired.theme.order)


def _glob(pieces: tuple[str, ...], word: str) -> bool:
    """Whether ``word`` is the pieces of a form with ``*`` between them: the
    first piece begins it, the last ends it, the others come in order. Taking
    each at its first place is always right for ``*``, so this is linear —
    where a regular expression of many ``*`` can take exponential time."""
    first, last = pieces[0], pieces[-1]
    if len(word) < len(first) + len(last) or not word.startswith(first):
        return False
    if not word.endswith(last):
        return False
    position, end = len(first), len(word) - len(last)
    for piece in pieces[1:-1]:
        found = word.find(piece, position, end)
        if found < 0:
            return False
        position = found + len(piece)
    return True


def _phrase_at(
    words: tuple[tuple[tuple[int, bool], ...], ...], start: int, analysis: Analysis
) -> tuple[list[int], list[tuple[tuple[int, bool], ...]]] | None:
    """Where the phrase's words match from ``start`` on (by form only), with
    the alternatives that matched each, or None."""
    end = start + len(words)
    if end > len(analysis.words) or analysis.segment[end - 1] != analysis.segment[start]:
        return None
    atoms = []
    for offset, alternatives in enumerate(words):
        have = analysis.matched[start + offset]
        fits = tuple(alt for alt in alternatives if alt[0] in have)
        if not fits:
            return None
        atoms.append(fits)
    return list(range(start, end)), atoms


def _negation_fits(
    positions: list[int], atoms: list[tuple[tuple[int, bool], ...]], analysis: Analysis
) -> bool:
    """Whether each word is mentioned as its term asks: negated for a not_
    form, else not negated — or negated by a word of the term itself, as
    *not late* and *don't know* are."""
    inside = set(positions)
    for position, alternatives in zip(positions, atoms, strict=True):
        source = analysis.negated_by[position]
        if not any(
            (source >= 0) if negated else (source < 0 or source in inside)
            for _, negated in alternatives
        ):
            return False
    return True


def _replacer(replacements: dict[str, str]) -> re.Pattern[str] | None:
    if not replacements:
        return None
    edge = f"[{_word_class()}']"  # a replacement starts and ends a word
    alternatives = sorted(replacements, key=len, reverse=True)
    body = "|".join(re.escape(item).replace(r"\ ", " ") for item in alternatives)
    return re.compile(f"(?<!{edge})(?:{body})(?!{edge})")


# ─── Suggestions ──────────────────────────────────────────────────────────────


def suggest_terms(
    answers: Iterable[tuple[str, str, int]], *, n: int = 30, min_count: int = 2
) -> dict[str, list[dict[str, Any]]]:
    """Frequent words and two-word phrases of ``answers`` — (text as written,
    text as the rules read it, count) — with how many answers hold each and
    one of them as an example. Stop words are left out; a negated word comes
    as ``not_word``, a term that finds it."""

    words: Counter[str] = Counter()
    pairs: Counter[str] = Counter()
    example: dict[str, str] = {}
    for written, text, count in answers:
        analysis = analyse(text)
        seen_words: set[str] = set()
        seen_pairs: set[str] = set()
        for position, word in enumerate(analysis.words):
            if _worth_suggesting(word):
                seen_words.add(("not_" if analysis.negated_by[position] >= 0 else "") + word)
            if position and analysis.clause[position] >= 0:
                before = analysis.words[position - 1]
                same = analysis.clause[position - 1] == analysis.clause[position]
                if same and _worth_pairing(before) and _worth_pairing(word):
                    seen_pairs.add(f"{before} {word}")
        for term in seen_words:
            words[term] += count
            example.setdefault(term, written)
        for term in seen_pairs:
            pairs[term] += count
            example.setdefault(term, written)

    def top(counter: Counter[str]) -> list[dict[str, Any]]:
        ranked = sorted(
            ((term, total) for term, total in counter.items() if total >= min_count),
            key=lambda item: (-item[1], item[0]),
        )
        return [{"term": t, "count": c, "example": example[t]} for t, c in ranked[:n]]

    return {"words": top(words), "phrases": top(pairs)}


def _worth_pairing(word: str) -> bool:
    """A word a suggested phrase may hold: not a stop word (a negation is
    fine — *not fast*, *no problems*)."""
    if word in STOP_WORDS or word in NEGATION_STOPS:
        return False
    return not (len(word) == 1 and word.isascii())


def _worth_suggesting(word: str) -> bool:
    """A word worth suggesting as a term: not a stop word, not a word that
    ends a clause or a negation, not *not* or an n't form (the words after
    them are suggested as not_word)."""
    if word == "not" or word.endswith("n't") or word in BARE_NT:
        return False
    return _worth_pairing(word)
