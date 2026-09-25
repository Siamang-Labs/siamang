/* Question components — one per survey question type.
   Markup uses sd-* class names for consistent styling with siamang's CSS rules. */

const { useState, useRef, useEffect } = React;

/* Per-option visibility gate. Uses the global isVisibleGated defined in
   app.jsx (both files share window scope). Falls back to "always visible"
   if the helper isn't loaded yet (defensive). */
function gateOption(opt, answers) {
  if (typeof isVisibleGated === "function") {
    return isVisibleGated(opt.showIf, opt.hideIf, answers);
  }
  return true;
}

function visibleOptions(q, answers) {
  // Honour script- or author-randomized option order stored in
  // answers.__options__ (see Script.randomize_options / Question.randomize).
  let opts = q.options;
  const stored = answers && answers.__options__ && answers.__options__[q.id];
  if (Array.isArray(stored) && stored.length) opts = stored;
  if (!opts) return [];
  return opts.filter((opt) => gateOption(opt, answers));
}

/* Render one media attachment as <img>/<video>/<audio>. Authors should keep
   media URLs trusted; the runtime does not sanitise them. */
function MediaItem({ media }) {
  if (!media || !media.url) return null;
  const caption = media.caption ? <figcaption className="siamang-media__caption">{media.caption}</figcaption> : null;
  const wrap = (el) => (
    <figure className={"siamang-media siamang-media--" + media.kind}>
      {el}
      {caption}
    </figure>
  );
  if (media.kind === "image") {
    return wrap(<img src={media.url} alt={media.alt || ""} loading="lazy" />);
  }
  if (media.kind === "video") {
    return wrap(
      <video
        src={media.url}
        controls={media.controls !== false}
        autoPlay={!!media.autoplay}
        loop={!!media.loop}
        muted={!!media.autoplay}
        playsInline
      />
    );
  }
  if (media.kind === "audio") {
    return wrap(
      <audio
        src={media.url}
        controls={media.controls !== false}
        autoPlay={!!media.autoplay}
        loop={!!media.loop}
      />
    );
  }
  return null;
}

function MediaGallery({ media }) {
  if (!media) return null;
  const items = Array.isArray(media) ? media : [media];
  if (!items.length) return null;
  return (
    <div className="siamang-media-gallery">
      {items.map((m, i) => <MediaItem key={i} media={m} />)}
    </div>
  );
}

/* Piping: {answer:x} / {var:x} insert the raw answer to variable x,
   {label:x} the label of the chosen option(s) (falls back to the raw
   value for questions without options). Unanswered → the placeholder
   stays, so an author sees at once what is missing. */
let _pipeLabelIndex = null;
const _pipeOtherIndex = {};
function pipeLabelIndex() {
  if (_pipeLabelIndex) return _pipeLabelIndex;
  const index = {};
  // The pages are window.PAGES; SURVEY carries the study's metadata only, so
  // an index built from SURVEY.pages was always empty and {label:x} piped the
  // raw code.
  const pages = (typeof window !== "undefined" && window.PAGES) || [];
  const visit = (items) => {
    for (const q of items || []) {
      if (!q) continue;
      if (Array.isArray(q.options) && q.id) {
        const map = {};
        for (const o of q.options) if (o && o.code !== undefined) map[String(o.code)] = o.label;
        if (q.otherSpecify && q.otherKey) {
          // {label:x} of Other is what the respondent typed, else its label.
          const code = String(otherCodeOf(q));
          if (map[code] === undefined) map[code] = q.otherLabel || runtimeTexts().other;
          if (!q.wide) _pipeOtherIndex[q.id] = { code, key: q.otherKey };
        }
        index[q.id] = map;
        // A MaxDiff's best and worst variables hold item codes too.
        if (q.kind === "maxdiff") for (const pair of q.taskVars || []) for (const v of pair) index[v] = map;
      }
      if (Array.isArray(q.columns) && Array.isArray(q.rows)) {
        // Matrix: each row is its own variable; the columns are its labels,
        // keyed by the code each one stores.
        for (const r of q.rows) {
          if (!r || !r.id) continue;
          index[r.id] = Object.fromEntries((q.columns || []).map((c, i) => [String(matrixColumnCode(q, i)), String(c)]));
          if (q.naOption) index[r.id][String(rowNaCode(r))] = q.naOption;
        }
      }
      if (q.kind === "likert" && q.naOption && q.id) {
        index[q.id] = { [String(q.naCode !== undefined ? q.naCode : "na")]: q.naOption };
      }
    }
  };
  for (const p of pages) {
    visit(p.items);
    for (const b of p.blocks || []) visit(b.items);
  }
  _pipeLabelIndex = index;
  return index;
}
function pipeValue(type, key, answers) {
  let val = answers[key];
  if (val && typeof val === "object" && !Array.isArray(val) && "code" in val) val = val.text && val.code === "__other__" ? val.text : val.code;
  if (val === null || val === undefined || val === "") return null;
  if (type === "label") {
    const labels = pipeLabelIndex()[key];
    const other = _pipeOtherIndex[key];
    const one = (v) => {
      if (other && String(v) === other.code && answers[other.key]) return String(answers[other.key]);
      return labels && labels[String(v)] !== undefined ? String(labels[String(v)]) : String(v);
    };
    return Array.isArray(val) ? val.map(one).join(", ") : one(val);
  }
  return Array.isArray(val) ? val.join(", ") : String(val);
}
function processPipedText(text, answers) {
  if (!text || typeof text !== 'string' || !answers) return text;
  return text.replace(/\{(answer|label|var):([a-zA-Z0-9_]+)\}/g, (match, type, key) => {
    const piped = pipeValue(type, key, answers);
    return piped === null ? match : piped;
  });
}
/* Redirect URL templates: ``{url:NAME}`` is the query parameter the
   respondent arrived with (a panel's respondent id), ``{answer:x}`` etc.
   pipe answers; every value is URL-encoded. An unknown placeholder is
   removed rather than sent to a third party as literal braces. */
function redirectTemplate(url, answers) {
  if (!url || typeof url !== "string") return url || null;
  let params = null;
  try { params = new URLSearchParams(window.location.search); } catch (e) { params = null; }
  return url.replace(/\{(url|answer|label|var):([a-zA-Z0-9_]+)\}/g, (match, type, key) => {
    if (type === "url") return encodeURIComponent((params && params.get(key)) || "");
    const piped = pipeValue(type, key, answers || {});
    return piped === null ? "" : encodeURIComponent(piped);
  });
}
/* The same for HTML bodies: piped values are escaped so an answer can never
   inject markup into the page. */
function processPipedHtml(html, answers) {
  if (!html || typeof html !== 'string' || !answers) return html;
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  return html.replace(/\{(answer|label|var):([a-zA-Z0-9_]+)\}/g, (match, type, key) => {
    const piped = pipeValue(type, key, answers);
    return piped === null ? match : esc(piped);
  });
}

function QuestionShell({ num, title, required, description, error, children, onBlur, answers, media }) {
  const processedTitle = processPipedText(title, answers);
  const processedDescription = processPipedText(description, answers);
  return (
    <div className={"sd-question" + (error ? " has-error" : "")} onBlur={onBlur}>
      <div className="sd-question__header">
        <h3 className="sd-question__title">
          {num ? <span className="sd-question__num">{num}</span> : null}
          <span>{processedTitle}</span>
          {required ? <span className="sd-question__required-text" aria-hidden="true">*</span> : null}
        </h3>
        {processedDescription ? <p className="sd-question__description">{processedDescription}</p> : null}
        <MediaGallery media={media} />
      </div>
      {children}
      {error ? <div className="sd-question__error" role="alert">{error}</div> : null}
    </div>
  );
}

/* "Other (please specify)": the code the choice stores (a code of the
   question's variable — q.otherCode), and whether one of the question's own
   options is it, in which case no extra option is added. A payload compiled
   before the code existed falls back to the old "__other__". */
function otherCodeOf(q) {
  return q.otherCode !== undefined ? q.otherCode : "__other__";
}
function otherIsAnOption(q) {
  return !!q.otherSpecify && (q.options || []).some((o) => sameCode(o.code, otherCodeOf(q)));
}

/* Focus the Other box once it has rendered — unless the respondent has moved
   on to another question meanwhile, whose field must keep the focus. */
function focusOtherSoon(ref) {
  setTimeout(() => {
    const el = ref.current;
    if (!el) return;
    const active = document.activeElement;
    const question = el.closest(".sd-question");
    if (!active || active === document.body || (question && question.contains(active))) el.focus();
  }, 50);
}

function OtherInput({ q, text, onText, inputRef }) {
  return (
    <div className="sd-other-input">
      <input
        ref={inputRef}
        type="text"
        className="sd-input sd-other-input__field"
        placeholder={q.otherPlaceholder || runtimeTexts().otherPlaceholder}
        value={text}
        onChange={(e) => onText(e.target.value)}
      />
    </div>
  );
}

function SingleChoice({ q, value, onChange, num, error, onBlur, answers, onAutoAdvance }) {
  const isButtons = q.display === "buttons";
  // With Other the answer arrives as { code, text } while Other is chosen.
  const OTHER = otherCodeOf(q);
  const isObject = q.otherSpecify && value && typeof value === "object";
  const currentCode = isObject ? value.code : value;
  const otherText = isObject ? value.text || "" : "";
  const isOtherSelected = !!q.otherSpecify && sameCode(currentCode, OTHER);
  const otherInputRef = useRef(null);

  const handleChange = (code) => {
    if (q.otherSpecify && sameCode(code, OTHER)) {
      onChange({ code, text: otherText || "" });
      focusOtherSoon(otherInputRef);
    } else {
      onChange(code);
      if (q.autoAdvance && onAutoAdvance) {
        setTimeout(() => onAutoAdvance(), 400);
      }
    }
  };

  const handleOtherText = (text) => {
    onChange({ code: currentCode, text });
  };

  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} onBlur={onBlur} answers={answers} media={q.media}>
      <div className={"sd-choices" + (isButtons ? " sd-choices--buttons" : "")} role="radiogroup" aria-label={q.title}>
        {visibleOptions(q, answers).map((opt) => {
          const checked = currentCode === opt.code;
          return (
            <label key={String(opt.code)} className={"sd-radio" + (checked ? " sd-item--checked" : "")}>
              <input
                type="radio"
                name={q.id}
                value={String(opt.code)}
                checked={checked}
                onChange={() => handleChange(opt.code)}
              />
              <span className="sd-radio__decorator" aria-hidden="true"></span>
              <span className="sd-choice-label">{opt.label}</span>
              {opt.media ? <MediaItem media={opt.media} /> : null}
            </label>
          );
        })}
        {q.otherSpecify && !otherIsAnOption(q) && (
          <label className={"sd-radio" + (isOtherSelected ? " sd-item--checked" : "")}>
            <input
              type="radio"
              name={q.id}
              value={String(OTHER)}
              checked={isOtherSelected}
              onChange={() => handleChange(OTHER)}
            />
            <span className="sd-radio__decorator" aria-hidden="true"></span>
            <span className="sd-choice-label">{q.otherLabel || runtimeTexts().other}</span>
          </label>
        )}
        {isOtherSelected && (
          <OtherInput q={q} text={otherText} onText={handleOtherText} inputRef={otherInputRef} />
        )}
      </div>
    </QuestionShell>
  );
}

function MultiChoice({ q, value, onChange, num, error, onBlur, answers }) {
  // value is [code1, code2, …], or { selected: [...], otherText } with Other.
  const hasOther = !!q.otherSpecify;
  const OTHER = otherCodeOf(q);
  const v = hasOther && value && typeof value === "object" && !Array.isArray(value)
    ? (Array.isArray(value.selected) ? value.selected : [])
    : (Array.isArray(value) ? value : []);
  const otherText = hasOther && value && typeof value === "object" && !Array.isArray(value)
    ? (value.otherText || "") : "";
  const isOtherSelected = hasOther && v.some((c) => sameCode(c, OTHER));
  const otherInputRef = useRef(null);

  const emitValue = (selected, text) => {
    if (hasOther) {
      onChange({ selected, otherText: text });
    } else {
      onChange(selected);
    }
  };

  const exclusiveCodes = Array.isArray(q.exclusive) ? q.exclusive : [];
  const isExclusive = (code) => exclusiveCodes.includes(code);

  const toggle = (code) => {
    if (v.includes(code)) {
      emitValue(v.filter((x) => x !== code), otherText);
    } else if (isExclusive(code)) {
      // Picking an exclusive code (e.g. "None of the above") clears the rest.
      emitValue([code], "");
    } else if (!q.max || v.length < q.max) {
      // Picking a regular code clears any selected exclusive codes.
      emitValue([...v.filter((x) => !isExclusive(x)), code], otherText);
      if (hasOther && sameCode(code, OTHER)) {
        focusOtherSoon(otherInputRef);
      }
    }
  };

  const toggleOther = () => {
    if (isOtherSelected) {
      emitValue(v.filter((x) => !sameCode(x, OTHER)), "");
    } else if (!q.max || v.length < q.max) {
      emitValue([...v.filter((x) => !isExclusive(x)), OTHER], otherText);
      focusOtherSoon(otherInputRef);
    }
  };

  const handleOtherText = (text) => {
    emitValue(v, text);
  };

  const effectiveCount = v.length;
  // An exclusive answer is whole by itself: the minimum asks for no more.
  const exclusiveChosen = v.some(isExclusive);

  return (
    <QuestionShell
      num={num}
      title={q.title}
      required={q.required}
      description={q.description}
      error={error}
      onBlur={onBlur}
      answers={answers}
      media={q.media}
    >
      <div className="sd-choices" role="group" aria-label={q.title}>
        {visibleOptions(q, answers).map((opt) => {
          const checked = v.includes(opt.code);
          const disabled = !checked && q.max && v.length >= q.max;
          return (
            <label
              key={String(opt.code)}
              className={"sd-checkbox" + (checked ? " sd-item--checked" : "")}
              style={disabled ? { opacity: 0.45, cursor: "not-allowed" } : null}
            >
              <input
                type="checkbox"
                checked={checked}
                disabled={disabled}
                onChange={() => toggle(opt.code)}
              />
              <span className="sd-checkbox__decorator" aria-hidden="true"></span>
              <span className="sd-choice-label">{opt.label}</span>
              {opt.media ? <MediaItem media={opt.media} /> : null}
            </label>
          );
        })}
        {hasOther && !otherIsAnOption(q) && (
          <label className={"sd-checkbox" + (isOtherSelected ? " sd-item--checked" : "")}
            style={(!isOtherSelected && q.max && v.length >= q.max) ? { opacity: 0.45, cursor: "not-allowed" } : null}
          >
            <input
              type="checkbox"
              checked={isOtherSelected}
              disabled={!isOtherSelected && q.max && v.length >= q.max}
              onChange={toggleOther}
            />
            <span className="sd-checkbox__decorator" aria-hidden="true"></span>
            <span className="sd-choice-label">{q.otherLabel || runtimeTexts().other}</span>
          </label>
        )}
        {isOtherSelected && (
          <OtherInput q={q} text={otherText} onText={handleOtherText} inputRef={otherInputRef} />
        )}
      </div>
      {/* The count against Max, and how many more Min needs — which Next
          enforces once the question is answered (answerLimitError). */}
      {(q.max || q.min > 1) ? (
        <div className="siamang-multi-counter" role="status" aria-live="polite">
          {q.max ? <span className="siamang-multi-counter__count">{`${effectiveCount} ${runtimeTexts().of} ${q.max} ${runtimeTexts().selected}`}</span> : null}
          {q.min && effectiveCount < q.min && !exclusiveChosen && (effectiveCount > 0 || q.required) ? (
            <span className="siamang-multi-counter__hint">{fillText(runtimeTexts().minChoices, { n: q.min - effectiveCount, min: q.min })}</span>
          ) : q.max && effectiveCount >= q.max ? (
            <span className="siamang-multi-counter__hint is-max">{runtimeTexts().maxReached}</span>
          ) : null}
        </div>
      ) : null}
    </QuestionShell>
  );
}

function Likert({ q, value, onChange, num, error, onBlur, answers }) {
  // N/A stores the codebook's not_applicable code, or "na" without one.
  const NA = q.naCode !== undefined ? q.naCode : "na";
  const isNA = sameCode(value, NA);
  const start = q.start === 0 ? 0 : 1;
  const stars = q.display === "stars";
  const [hover, setHover] = useState(null);
  const points = Array.from({ length: q.points }, (_, i) => i + start);
  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} onBlur={onBlur} answers={answers} media={q.media}>
      <div className={"sd-rating" + (stars ? " sd-rating--stars" : "")}>
        <div className="sd-rating__scale" role="radiogroup" aria-label={q.title} onMouseLeave={() => setHover(null)}>
          {points.map((n) => {
            // Stars fill up to the chosen (or hovered) one; numbers select one point.
            const lit = stars && typeof value === "number" && n <= (hover ?? value);
            const hot = stars && hover !== null && n <= hover;
            return (
              <button
                type="button"
                key={n}
                className={"sd-rating__item" + (value === n ? " is-selected" : "") + (lit || hot ? " is-lit" : "")}
                onClick={() => onChange(n)}
                onMouseEnter={stars ? () => setHover(n) : undefined}
                aria-pressed={value === n}
                aria-label={stars ? `${n - start + 1} ${runtimeTexts().of} ${q.points}` : undefined}
              >
                {stars ? <span className="sd-rating__star" aria-hidden="true">{lit || hot ? "\u2605" : "\u2606"}</span> : <span className="sd-rating__num">{n}</span>}
              </button>
            );
          })}
        </div>
        <div className="sd-rating__labels">
          <span>{q.leftLabel}</span>
          <span>{q.rightLabel}</span>
        </div>
        {q.naOption ? (
          <div className="sd-rating__na">
            <label className={"sd-radio" + (isNA ? " sd-item--checked" : "")}>
              <input
                type="radio"
                name={q.id + "_na"}
                checked={isNA}
                onChange={() => onChange(NA)}
              />
              <span className="sd-radio__decorator" aria-hidden="true"></span>
              <span className="sd-choice-label">{q.naOption}</span>
            </label>
          </div>
        ) : null}
      </div>
    </QuestionShell>
  );
}

/* The code a matrix column stores: the codebook code the compiler read for it
   (Matrix.columns), or — for a payload without codes — its position + 1. */
function matrixColumnCode(q, colIdx) {
  const codes = q.columnCodes;
  if (Array.isArray(codes) && codes.length === (q.columns || []).length) return codes[colIdx];
  return colIdx + 1;
}

/* A matrix row's N/A: its variable's not_applicable code, or "na". */
function rowNaCode(row) {
  return row && row.naCode !== undefined ? row.naCode : "na";
}

function Matrix({ q, value, onChange, num, error, held, onBlur, answers }) {
  const v = value || {};
  // One cell is in the tab order (a roving tabindex) and the arrow keys move
  // the focus itself between the cells, the N/A column included: Left and
  // Right answer the row with the cell they move to, Up and Down go to the
  // same column of the row above or below. Space and Enter choose the cell
  // the focus is on, as a button's own keys (useKeyboardShortcuts leaves a
  // button's Enter and Space to it).
  const [focusRow, setFocusRow] = useState(0);
  const [focusCol, setFocusCol] = useState(0);
  const cells = useRef({});
  const width = q.columns.length + (q.naOption ? 1 : 0);
  // Once Next has held the required matrix (`held`), the rows still without
  // an answer are marked — to the eye and, on their cells, with
  // aria-invalid — each until it is answered. The message goes with the next
  // click, as every question's does.
  const missing = held ? new Set(unansweredRows(q, v)) : null;

  const handleKeyDown = (e, rowIdx, colIdx) => {
    let row = rowIdx;
    let col = colIdx;
    if (e.key === "ArrowRight") col = Math.min(colIdx + 1, width - 1);
    else if (e.key === "ArrowLeft") col = Math.max(colIdx - 1, 0);
    else if (e.key === "ArrowDown" && rowIdx < q.rows.length - 1) row = rowIdx + 1;
    else if (e.key === "ArrowUp" && rowIdx > 0) row = rowIdx - 1;
    else return;
    e.preventDefault();
    const cell = cells.current[row + ":" + col];
    if (cell) cell.focus();
    if (row === rowIdx) {
      const target = q.rows[rowIdx];
      onChange({ ...v, [target.id]: col < q.columns.length ? matrixColumnCode(q, col) : rowNaCode(target) });
    }
  };

  // What every cell shares: its place in the keyboard's grid, and whether its
  // row is marked.
  const cellProps = (row, rowIdx, colIdx) => ({
    ref: (el) => { cells.current[rowIdx + ":" + colIdx] = el; },
    tabIndex: rowIdx === focusRow && colIdx === focusCol ? 0 : -1,
    onFocus: () => { setFocusRow(rowIdx); setFocusCol(colIdx); },
    onKeyDown: (e) => handleKeyDown(e, rowIdx, colIdx),
    "aria-invalid": missing && missing.has(row.id) ? "true" : undefined,
  });

  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} onBlur={onBlur} answers={answers} media={q.media}>
      <div className="sd-matrix-wrapper">
        <table className="sd-matrix" role="radiogroup" aria-label={q.title}>
          <thead>
            <tr>
              <th></th>
              {q.columns.map((c, i) => <th key={i}>{c}</th>)}
              {q.naOption ? <th className="sd-matrix__na-header">{q.naOption}</th> : null}
            </tr>
          </thead>
          <tbody>
            {q.rows.map((row, rowIdx) => (
              <tr key={row.id} className={missing && missing.has(row.id) ? "is-missing" : undefined}>
                <td>{row.label}</td>
                {q.columns.map((_, colIdx) => {
                  const code = matrixColumnCode(q, colIdx);
                  const selected = v[row.id] === code;
                  return (
                    <td key={colIdx}>
                      <button
                        type="button"
                        className={"sd-matrix__cell" + (selected ? " is-selected" : "")}
                        aria-label={`${row.label}: ${q.columns[colIdx]}`}
                        aria-pressed={selected}
                        {...cellProps(row, rowIdx, colIdx)}
                        onClick={() => onChange({ ...v, [row.id]: code })}
                      />
                    </td>
                  );
                })}
                {q.naOption ? (
                  <td>
                    <button
                      type="button"
                      className={"sd-matrix__cell" + (sameCode(v[row.id], rowNaCode(row)) ? " is-selected" : "")}
                      aria-label={`${row.label}: ${q.naOption}`}
                      aria-pressed={sameCode(v[row.id], rowNaCode(row))}
                      {...cellProps(row, rowIdx, q.columns.length)}
                      onClick={() => onChange({ ...v, [row.id]: rowNaCode(row) })}
                    />
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </QuestionShell>
  );
}

/* Its valid range is checked by the survey, not here: when the field is left
   and on Next ("Minimum value is …" / "Maximum value is …", answerLimitError),
   the same way as a required answer — a message of the component's own was
   never shown, the survey's blur handler taking its place. */
function NumericInput({ q, value, onChange, num, error, onBlur, answers }) {
  if (q.display === "slider") {
    const min = q.min ?? 0;
    const max = q.max ?? 10;
    const step = q.step || 1;
    const v = value ?? (q.defaultValue !== undefined ? q.defaultValue : Math.round((min + max) / 2));
    const labels = q.labels || {};
    // Only show tick marks if the range is small enough (≤20 steps)
    const totalSteps = Math.round((max - min) / step);
    const showTicks = totalSteps <= 20;
    return (
      <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} onBlur={onBlur} answers={answers} media={q.media}>
        <div className="siamang-slider">
          <input
            type="range"
            min={min}
            max={max}
            step={step}
            value={v}
            onChange={(e) => onChange(Number(e.target.value))}
            className="siamang-slider__input"
            aria-valuemin={min}
            aria-valuemax={max}
            aria-valuenow={v}
            aria-label={q.title}
          />
          <div className="siamang-slider__value" style={{
            color: v !== null ? "var(--siamang-accent)" : "var(--siamang-muted)",
            fontWeight: 600,
            fontSize: "1.1rem",
          }}>{v !== null && v !== undefined ? v : "—"}</div>
          {showTicks ? (
            <div className="siamang-slider__labels">
              {Array.from({ length: totalSteps + 1 }, (_, i) => min + i * step).map((n) => (
                <span key={n} className={"siamang-slider__tick" + (v === n ? " is-active" : "")}>
                  {labels[n] !== undefined ? labels[n] : n}
                </span>
              ))}
            </div>
          ) : (
            <div className="siamang-slider__end-labels">
              <span>{labels[min] !== undefined ? labels[min] : (q.minLabel || `${min}`)}</span>
              <span>{labels[max] !== undefined ? labels[max] : (q.maxLabel || `${max}`)}</span>
            </div>
          )}
        </div>
      </QuestionShell>
    );
  }
  // Uncontrolled-style input: the DOM owns the live value while typing,
  // we only push it into React state on blur (plus a 600 ms debounce so
  // autosave still catches the latest value). This stops every keystroke
  // from re-rendering the whole App + every other question on the page.
  const inputRef = useRef(null);
  const debounceRef = useRef(null);
  useEffect(() => {
    // Sync external value into the DOM when it changes from outside
    // (e.g. restored from localStorage). Skip while the input is focused
    // so we don't fight live typing.
    if (inputRef.current && document.activeElement !== inputRef.current) {
      inputRef.current.value = value ?? "";
    }
  }, [value]);
  const commit = () => {
    if (debounceRef.current) { clearTimeout(debounceRef.current); debounceRef.current = null; }
    if (!inputRef.current) return;
    const raw = inputRef.current.value;
    onChange(raw === "" ? null : Number(raw));
  };
  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} onBlur={onBlur} answers={answers} media={q.media}>
      <div className="sd-numeric">
        <input
          ref={inputRef}
          type="number"
          className="sd-input"
          defaultValue={value ?? ""}
          min={q.min}
          max={q.max}
          step={q.step || 1}
          onInput={() => {
            if (debounceRef.current) clearTimeout(debounceRef.current);
            debounceRef.current = setTimeout(commit, 600);
          }}
          onBlur={() => {
            commit();
            if (onBlur) onBlur();
          }}
        />
        {q.unit ? <span className="sd-numeric__unit">{q.unit}</span> : null}
      </div>
    </QuestionShell>
  );
}

function OpenText({ q, value, onChange, num, error, onBlur, answers }) {
  // Uncontrolled-style: the DOM owns the live value while typing. We
  // commit to React state on blur and on a 600 ms idle. This is the
  // single biggest win for typing performance — every keystroke no
  // longer re-renders the entire App.
  const inputRef = useRef(null);
  const debounceRef = useRef(null);
  const [chars, setChars] = useState((value ?? "").length);

  useEffect(() => {
    if (inputRef.current && document.activeElement !== inputRef.current) {
      inputRef.current.value = value ?? "";
      setChars((value ?? "").length);
    }
  }, [value]);

  const commit = () => {
    if (debounceRef.current) { clearTimeout(debounceRef.current); debounceRef.current = null; }
    if (inputRef.current) onChange(inputRef.current.value);
  };
  const handleInput = (e) => {
    setChars(e.target.value.length);   // local-only state for the counter
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(commit, 600);
  };
  const handleBlur = () => {
    commit();
    if (onBlur) onBlur();
  };

  const InputTag = q.multiline ? "textarea" : "input";
  const extraProps = q.multiline ? { rows: 4 } : { type: TEXT_INPUT_TYPES[q.format] || "text", inputMode: TEXT_INPUT_MODES[q.format] };

  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} onBlur={null} answers={answers} media={q.media}>
      <InputTag
        ref={inputRef}
        className="sd-input"
        defaultValue={value ?? ""}
        placeholder={q.placeholder}
        maxLength={q.maxChars}
        onInput={handleInput}
        onBlur={handleBlur}
        {...extraProps}
      />
      {q.maxChars ? (
        <div className="sd-char-counter">{chars} / {q.maxChars}</div>
      ) : null}
      {q.maxChars && chars > q.maxChars * 0.8 && chars <= q.maxChars && (
        <div className="siamang-char-warning" role="alert">{fillText(runtimeTexts().charsRemaining, { n: q.maxChars - chars })}</div>
      )}
    </QuestionShell>
  );
}

/* An OpenText's format picks the browser input (a date picker, the phone
   keypad) — and the runtime's own check on "Next" (see textFormatError). */
const TEXT_INPUT_TYPES = { email: "email", phone: "tel", url: "url", date: "date", time: "time" };
const TEXT_INPUT_MODES = { email: "email", phone: "tel", url: "url" };

function SearchableDropdown({ q, value, onChange, num, error, onBlur, answers }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  // The option the arrow keys are on (an index into `filtered`; -1: none).
  const [active, setActive] = useState(-1);
  const ref = useRef(null);
  const triggerRef = useRef(null);
  const optionRefs = useRef([]);
  const otherInputRef = useRef(null);
  const listId = React.useId();

  // "Other (please specify)" is offered here as in the radio list: an extra
  // entry at the end (unless one of the options is it), with its text box
  // below the dropdown while it is chosen.
  const OTHER = otherCodeOf(q);
  const isObject = q.otherSpecify && value && typeof value === "object";
  const currentCode = isObject ? value.code : value;
  const otherText = isObject ? value.text || "" : "";
  const isOtherSelected = !!q.otherSpecify && sameCode(currentCode, OTHER);

  const visible = visibleOptions(q, answers);
  const offered = q.otherSpecify && !otherIsAnOption(q)
    ? [...visible, { code: OTHER, label: q.otherLabel || runtimeTexts().other }]
    : visible;
  const filtered = search
    ? offered.filter((o) => String(o.label).toLowerCase().includes(search.toLowerCase()))
    : offered;

  const selected = currentCode === undefined ? undefined : offered.find((o) => sameCode(o.code, currentCode));

  const choose = (code) => {
    if (q.otherSpecify && sameCode(code, OTHER)) {
      onChange({ code, text: otherText || "" });
      focusOtherSoon(otherInputRef);
    } else {
      onChange(code);
    }
    setOpen(false);
  };

  // Opened, the arrow keys start from the chosen option.
  const toggle = () => {
    if (!open) setActive(offered.findIndex((o) => sameCode(o.code, currentCode)));
    setOpen(!open);
    setSearch("");
  };
  // Closed from the keyboard, the focus goes back to the button.
  const close = () => {
    setOpen(false);
    if (triggerRef.current) triggerRef.current.focus();
  };

  // The search box is a combobox over the options: ↓ ↑ move along them,
  // Enter chooses the one they are on, Esc closes. Typing narrows the list
  // and puts the keys on its first entry.
  const handleSearchKey = (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!filtered.length) return;
      const step = e.key === "ArrowDown" ? 1 : -1;
      setActive((i) => (i < 0 ? (step > 0 ? 0 : filtered.length - 1)
        : Math.min(Math.max(i + step, 0), filtered.length - 1)));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const option = filtered[active];
      if (!option) return;
      // Chosen before the focus leaves the box, so the question it leaves
      // is already answered.
      choose(option.code);
      if (triggerRef.current) triggerRef.current.focus();
    } else if (e.key === "Escape") {
      e.preventDefault();
      close();
    }
  };

  // On the button, ↓ opens the menu and Esc closes it (rather than going
  // back a page).
  const handleTriggerKey = (e) => {
    if (e.key === "ArrowDown" && !open) {
      e.preventDefault();
      toggle();
    } else if (e.key === "Escape" && open) {
      e.preventDefault();
      e.stopPropagation();
      setOpen(false);
    }
  };

  useEffect(() => {
    const el = optionRefs.current[active];
    if (open && el && el.scrollIntoView) el.scrollIntoView({ block: "nearest" });
  }, [open, active]);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Tab away from the menu closes it, as a press of the mouse outside it does.
  const handleFocusOut = (e) => {
    if (e.relatedTarget && ref.current && !ref.current.contains(e.relatedTarget)) setOpen(false);
  };

  const optionId = (i) => `${listId}-${i}`;
  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} onBlur={onBlur} answers={answers} media={q.media}>
      <div className="siamang-search-dropdown" ref={ref} onBlur={handleFocusOut}>
        <button
          type="button"
          ref={triggerRef}
          className="sd-input siamang-search-dropdown__trigger"
          onClick={toggle}
          onKeyDown={handleTriggerKey}
          aria-haspopup="listbox"
          aria-expanded={open}
        >
          <span>{selected ? selected.label : runtimeTexts().selectPlaceholder}</span>
          <span className="siamang-search-dropdown__arrow" aria-hidden="true"></span>
        </button>
        {open && (
          <div className="siamang-search-dropdown__menu">
            <input
              type="text"
              className="sd-input siamang-search-dropdown__search"
              placeholder={runtimeTexts().searchPlaceholder}
              value={search}
              onChange={(e) => { setSearch(e.target.value); setActive(e.target.value ? 0 : -1); }}
              onKeyDown={handleSearchKey}
              role="combobox"
              aria-expanded={true}
              aria-controls={listId}
              aria-autocomplete="list"
              aria-activedescendant={filtered[active] ? optionId(active) : undefined}
              aria-label={q.title}
              autoFocus
            />
            <div className="siamang-search-dropdown__options" role="listbox" id={listId} aria-label={q.title}>
              {filtered.map((opt, i) => (
                <div
                  key={String(opt.code)}
                  id={optionId(i)}
                  ref={(el) => { optionRefs.current[i] = el; }}
                  className={"siamang-search-dropdown__option"
                    + (sameCode(currentCode, opt.code) ? " is-selected" : "")
                    + (i === active ? " is-active" : "")}
                  role="option"
                  aria-selected={sameCode(currentCode, opt.code)}
                  onClick={() => choose(opt.code)}
                >
                  {opt.label}
                </div>
              ))}
              {filtered.length === 0 && (
                <div className="siamang-search-dropdown__empty">{runtimeTexts().noOptions}</div>
              )}
            </div>
          </div>
        )}
      </div>
      {isOtherSelected && (
        <OtherInput q={q} text={otherText} onText={(text) => onChange({ code: currentCode, text })} inputRef={otherInputRef} />
      )}
    </QuestionShell>
  );
}

function ImageChoice({ q, value, onChange, num, error, onBlur, answers }) {
  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} onBlur={onBlur} answers={answers} media={q.media}>
      <div className="sd-image-choices" role="radiogroup" aria-label={q.title}>
        {visibleOptions(q, answers).map((opt) => {
          const checked = value === opt.code;
          const imageUrl = opt.imageUrl || (opt.media && opt.media.kind === "image" ? opt.media.url : null);
          return (
            <button
              key={String(opt.code)}
              type="button"
              className={"sd-image-choice" + (checked ? " is-selected" : "")}
              onClick={() => onChange(opt.code)}
              aria-pressed={checked}
            >
              {imageUrl && (
                <img className="sd-image-choice__img" src={imageUrl} alt={opt.label} loading="lazy" />
              )}
              <span className="sd-image-choice__label">{opt.label}</span>
            </button>
          );
        })}
      </div>
    </QuestionShell>
  );
}

function Ranking({ q, value, onChange, num, error, onBlur, answers }) {
  const ranked = Array.isArray(value) ? value : [];
  const visible = visibleOptions(q, answers);
  const unranked = visible.filter((o) => !ranked.includes(o.code));
  const [dragIdx, setDragIdx] = useState(null);
  const [dragOverIdx, setDragOverIdx] = useState(null);
  // Touch support
  const [touchIdx, setTouchIdx] = useState(null);

  const add = (code) => {
    if (q.max && ranked.length >= q.max) return;
    onChange([...ranked, code]);
  };
  const remove = (code) => onChange(ranked.filter((c) => c !== code));

  const handleDragStart = (idx) => { setDragIdx(idx); };
  const handleDragOver = (e, idx) => { e.preventDefault(); setDragOverIdx(idx); };
  const handleDragEnd = () => {
    if (dragIdx !== null && dragOverIdx !== null && dragIdx !== dragOverIdx) {
      const next = [...ranked];
      const [moved] = next.splice(dragIdx, 1);
      next.splice(dragOverIdx, 0, moved);
      onChange(next);
    }
    setDragIdx(null);
    setDragOverIdx(null);
  };

  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} onBlur={onBlur} answers={answers} media={q.media}>
      <div className="sd-ranking">
        {ranked.map((code, idx) => {
          const opt = visible.find((o) => o.code === code);
          if (!opt) return null;
          const isOver = dragOverIdx === idx;
          return (
            <div
              key={code}
              className={"sd-ranking__item is-ranked" + (isOver ? " is-drag-over" : "") + (dragIdx === idx ? " is-dragging" : "")}
              draggable
              onDragStart={() => handleDragStart(idx)}
              onDragOver={(e) => handleDragOver(e, idx)}
              onDragEnd={handleDragEnd}
            >
              <span className="sd-ranking__handle" aria-hidden="true">⋮⋮</span>
              <span className="sd-ranking__rank">{idx + 1}</span>
              <span className="sd-ranking__label">{opt.label}</span>
              <span className="sd-ranking__actions">
                <button type="button" className="sd-ranking__btn" aria-label="Remove" onClick={() => remove(code)}>✕</button>
              </span>
            </div>
          );
        })}
        {unranked.length > 0 && (!q.max || ranked.length < q.max) ? (
          <>
            <div className="sd-ranking__section-label">
              {ranked.length > 0 ? runtimeTexts().rankingRemaining : runtimeTexts().rankingHint}
            </div>
            {unranked.map((opt) => {
              const atMax = q.max && ranked.length >= q.max;
              return (
                <div
                  key={opt.code}
                  className="sd-ranking__item is-unranked"
                  onClick={() => !atMax && add(opt.code)}
                  style={atMax ? { opacity: 0.5, cursor: "not-allowed" } : null}
                >
                  <span className="sd-ranking__handle" aria-hidden="true">+</span>
                  <span className="sd-ranking__rank">—</span>
                  <span className="sd-ranking__label">{opt.label}</span>
                </div>
              );
            })}
          </>
        ) : null}
      </div>
    </QuestionShell>
  );
}

/* MaxDiff — a few items at a time, best and worst of them.

   All tasks are on one screen rather than one per page: the runtime has no
   concept of a question spanning pages, and a respondent scrolling a short
   list of tasks can also go back and change an earlier one, which a paged
   version would have to reimplement.

   The version of the design is chosen from the respondent id with the same
   seeded hash Script.assign_condition uses, so a respondent who resumes gets
   the tasks they already started, and it is written into the answer as an
   ordinary variable — without it nobody can read the picks, because knowing
   somebody chose item 7 says nothing until you know what 7 was up against. */
function maxDiffVersion(q, answers) {
  const total = (q.versions || []).length || 1;
  /* The same respondent key Script.assign_condition draws arms from
     (answers.__respondent__, which the runtime always sets — see
     interviewRespondentId), and the same FNV-1a hash, so one respondent lands
     in one version however many things are assigned to them, and a reload
     lands in it again. A store without the key falls back to a random draw. */
  const id = String((answers && (answers.__respondent__ || answers.respondent_id)) || "");
  if (!id) return Math.floor(Math.random() * total);
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) { h ^= id.charCodeAt(i); h = Math.imul(h, 16777619); }
  return Math.abs(h) % total;
}

function MaxDiff({ q, value, onChange, num, error, onBlur, answers }) {
  const v = value || {};
  const labels = {};
  for (const opt of q.options || []) labels[String(opt.code)] = opt.label;
  const versions = q.versions || [];
  const versionRef = useRef(null);
  if (versionRef.current === null) {
    const stored = v[q.versionVar];
    versionRef.current = stored === undefined ? maxDiffVersion(q, answers) : stored;
  }
  const version = versionRef.current;
  const tasks = versions.length ? versions[version % versions.length] : [];

  const pick = (taskIdx, code, side) => {
    const [bestVar, worstVar] = q.taskVars[taskIdx];
    const mine = side === "best" ? bestVar : worstVar;
    const other = side === "best" ? worstVar : bestVar;
    const next = { ...v, [q.versionVar]: version };
    // One item cannot be both the best and the worst of the same task; picking
    // it on one side releases it from the other rather than silently keeping a
    // contradiction the analysis would have to resolve.
    if (next[other] === code) delete next[other];
    next[mine] = next[mine] === code ? undefined : code;
    if (next[mine] === undefined) delete next[mine];
    onChange(next);
  };

  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} onBlur={onBlur} answers={answers} media={q.media}>
      <div className="sd-maxdiff">
        {tasks.map((task, taskIdx) => {
          const [bestVar, worstVar] = q.taskVars[taskIdx];
          return (
            <table className="sd-maxdiff__task" key={taskIdx} aria-label={`Task ${taskIdx + 1} ${runtimeTexts().of} ${tasks.length}`}>
              <thead>
                <tr>
                  <th className="sd-maxdiff__side">{q.bestLabel}</th>
                  <th className="sd-maxdiff__item"></th>
                  <th className="sd-maxdiff__side">{q.worstLabel}</th>
                </tr>
              </thead>
              <tbody>
                {task.map((code) => {
                  const isBest = v[bestVar] === code;
                  const isWorst = v[worstVar] === code;
                  const label = labels[String(code)] !== undefined ? labels[String(code)] : String(code);
                  return (
                    <tr key={String(code)}>
                      <td>
                        <button type="button"
                          className={"sd-maxdiff__pick" + (isBest ? " is-selected" : "")}
                          aria-pressed={isBest}
                          aria-label={`${q.bestLabel}: ${label}`}
                          onClick={() => pick(taskIdx, code, "best")} />
                      </td>
                      <td className="sd-maxdiff__item">{label}</td>
                      <td>
                        <button type="button"
                          className={"sd-maxdiff__pick" + (isWorst ? " is-selected" : "")}
                          aria-pressed={isWorst}
                          aria-label={`${q.worstLabel}: ${label}`}
                          onClick={() => pick(taskIdx, code, "worst")} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          );
        })}
      </div>
    </QuestionShell>
  );
}


/* Conjoint — whole products side by side, pick one.

   The grid is attributes down the side and alternatives across, because that
   is the comparison being asked for: a respondent reads across a row to see
   what differs. On a narrow screen the same table scrolls sideways rather than
   becoming a list of products, which would be a different question.

   Like MaxDiff, the version of the design is drawn from the respondent key and
   written as an ordinary variable — the choice is meaningless without knowing
   which products it was between. */
function Conjoint({ q, value, onChange, num, error, onBlur, answers }) {
  const v = value || {};
  const versions = q.versions || [];
  const versionRef = useRef(null);
  if (versionRef.current === null) {
    const stored = v[q.versionVar];
    versionRef.current = stored === undefined ? maxDiffVersion(q, answers) : stored;
  }
  const version = versionRef.current;
  const tasks = versions.length ? versions[version % versions.length] : [];
  const attributes = q.attributes || [];

  const pick = (taskIdx, alt) => {
    const name = q.taskVars[taskIdx];
    const next = { ...v, [q.versionVar]: version };
    if (next[name] === alt) delete next[name];
    else next[name] = alt;
    onChange(next);
  };

  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} onBlur={onBlur} answers={answers} media={q.media}>
      <div className="sd-conjoint">
        {tasks.map((profiles, taskIdx) => {
          const chosen = v[q.taskVars[taskIdx]];
          return (
            <div className="sd-conjoint__task" key={taskIdx}>
              <div className="sd-conjoint__count">{`${taskIdx + 1} / ${tasks.length}`}</div>
              <div className="sd-conjoint__scroll">
                <table className="sd-conjoint__grid" aria-label={`Choice ${taskIdx + 1} ${runtimeTexts().of} ${tasks.length}`}>
                  <tbody>
                    {attributes.map((attribute, row) => (
                      <tr key={attribute.name}>
                        <th scope="row">{attribute.label}</th>
                        {profiles.map((profile, col) => {
                          const code = String(profile[row]);
                          const label = attribute.levels && attribute.levels[code] !== undefined ? attribute.levels[code] : code;
                          return <td key={col} className={chosen === col + 1 ? "is-chosen" : undefined}>{label}</td>;
                        })}
                      </tr>
                    ))}
                    <tr className="sd-conjoint__picks">
                      <th scope="row" />
                      {profiles.map((_profile, col) => (
                        <td key={col}>
                          <button type="button"
                            className={"sd-conjoint__pick" + (chosen === col + 1 ? " is-selected" : "")}
                            aria-pressed={chosen === col + 1}
                            aria-label={`Choice ${taskIdx + 1}, option ${col + 1}`}
                            onClick={() => pick(taskIdx, col + 1)}>
                            {chosen === col + 1 ? "\u2713" : ""}
                          </button>
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
              {q.noneLabel ? (
                <label className="sd-conjoint__none">
                  <input type="radio" checked={chosen === profiles.length + 1}
                    onChange={() => pick(taskIdx, profiles.length + 1)} />
                  {q.noneLabel}
                </label>
              ) : null}
            </div>
          );
        })}
      </div>
    </QuestionShell>
  );
}


/* Internal dispatcher. SurveyPage passes a stable `setAnswer` plus the
   question's id; we build the per-question `onChange`/`onBlur` closures
   here so that they only get recreated when this dispatcher actually
   re-renders (which the memo below blocks unless props matter). */
function _QuestionDispatcher({ q, qId, value, setAnswer, num, error, held, handleBlur, answers, onAutoAdvance }) {
  const onChange = (v) => setAnswer(qId, v);
  const onBlur = handleBlur ? () => handleBlur(qId) : undefined;
  switch (q.kind) {
    case "single":   return <SingleChoice q={q} value={value} onChange={onChange} num={num} error={error} onBlur={onBlur} answers={answers} onAutoAdvance={onAutoAdvance} />;
    case "multi":    return <MultiChoice  q={q} value={value} onChange={onChange} num={num} error={error} onBlur={onBlur} answers={answers} />;
    case "likert":   return <Likert       q={q} value={value} onChange={onChange} num={num} error={error} onBlur={onBlur} answers={answers} />;
    case "matrix":   return <Matrix       q={q} value={value} onChange={onChange} num={num} error={error} held={held} onBlur={onBlur} answers={answers} />;
    case "numeric":  return <NumericInput q={q} value={value} onChange={onChange} num={num} error={error} onBlur={onBlur} answers={answers} />;
    case "text":     return <OpenText     q={q} value={value} onChange={onChange} num={num} error={error} onBlur={onBlur} answers={answers} />;
    case "dropdown": return <SearchableDropdown q={q} value={value} onChange={onChange} num={num} error={error} onBlur={onBlur} answers={answers} />;
    case "searchable": return <SearchableDropdown q={q} value={value} onChange={onChange} num={num} error={error} onBlur={onBlur} answers={answers} />;
    case "image":    return <ImageChoice  q={q} value={value} onChange={onChange} num={num} error={error} onBlur={onBlur} answers={answers} />;
    case "ranking":  return <Ranking      q={q} value={value} onChange={onChange} num={num} error={error} onBlur={onBlur} answers={answers} />;
    case "maxdiff":  return <MaxDiff      q={q} value={value} onChange={onChange} num={num} error={error} onBlur={onBlur} answers={answers} />;
    case "conjoint": return <Conjoint     q={q} value={value} onChange={onChange} num={num} error={error} onBlur={onBlur} answers={answers} />;
    default:         return null;
  }
}

/* Memoised wrapper. The expensive miss is "typing into one OpenText
   causes every other question on the page to re-render". The memo
   skips this work for questions whose value, error, and identity
   didn't change. `answers` is only relevant when the question pipes
   text from another answer ({answer:x} / {var:x} / {label:x}); for
   the common case where it doesn't, we ignore answers changes. */
const Question = React.memo(_QuestionDispatcher, (prev, next) => {
  if (prev.q !== next.q) return false;
  if (prev.qId !== next.qId) return false;
  if (prev.value !== next.value) return false;
  if (prev.error !== next.error) return false;
  if (prev.held !== next.held) return false;
  if (prev.num !== next.num) return false;
  if (prev.setAnswer !== next.setAnswer) return false;
  if (prev.handleBlur !== next.handleBlur) return false;
  if (prev.onAutoAdvance !== next.onAutoAdvance) return false;
  const pipes = (s) => typeof s === "string" && /\{(answer|var|label):/.test(s);
  if (pipes(next.q.title) || pipes(next.q.description)) {
    if (prev.answers !== next.answers) return false;
  }
  // Option order can be changed through answers.__options__ (randomize
  // scripts / author-declared randomization) — re-render when it does.
  const optOrder = (a) => (a && a.__options__ ? a.__options__[next.qId] : undefined);
  if (optOrder(prev.answers) !== optOrder(next.answers)) return false;
  // Per-option show_if/hide_if gates read other answers.
  const hasGatedOptions =
    Array.isArray(next.q.options) &&
    next.q.options.some((o) => o && (o.showIf !== undefined || o.hideIf !== undefined));
  if (hasGatedOptions && prev.answers !== next.answers) return false;
  return true;
});

Object.assign(window, { Question, QuestionShell, processPipedText, processPipedHtml });
