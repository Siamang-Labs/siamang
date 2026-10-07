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

/* Render one media attachment as <img>/<video>/<audio>, or a YouTube or
   Vimeo video (kind "embed") as a play button (EmbedMedia). Authors should
   keep media URLs trusted; the runtime does not sanitize a file's. `name` is
   what a video's play button is called after when the media has no alt text
   or caption (the question's title). */
function MediaItem({ media, name }) {
  if (!media) return null;
  if (media.kind === "embed") return <EmbedMedia media={media} name={name} />;
  if (!media.url) return null;
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

function MediaGallery({ media, name }) {
  if (!media) return null;
  const items = Array.isArray(media) ? media : [media];
  if (!items.length) return null;
  return (
    <div className="siamang-media-gallery">
      {items.map((m, i) => <MediaItem key={i} media={m} name={name} />)}
    </div>
  );
}

/* ─── YouTube and Vimeo videos ────────────────────────────────────────────
   A video of kind "embed" names its provider and its id. The player's
   address is built here from them, checked again — never from the media's
   url, which is the video's page for a person to read — and nothing is
   requested from the provider until the respondent presses play: no
   thumbnail, no preconnect. The press loads the player on YouTube's
   privacy-enhanced host or Vimeo's player with Do Not Track, with the
   provider's own `allow` list and the referrer policy its player needs. */
const _EMBED_START_MAX = 86400;
const EMBED = Object.freeze({
  youtube: Object.freeze({
    label: "YouTube",
    origin: "https://www.youtube-nocookie.com",
    id: /^[A-Za-z0-9_-]{11}$/,
    allow: "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; "
      + "picture-in-picture; web-share; fullscreen",
    src: (m) => "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(m.id)
      + "?autoplay=1&rel=0&playsinline=1" + (m.start ? "&start=" + m.start : ""),
    watch: (m) => "https://www.youtube.com/watch?v=" + encodeURIComponent(m.id)
      + (m.start ? "&t=" + m.start : ""),
  }),
  vimeo: Object.freeze({
    label: "Vimeo",
    origin: "https://player.vimeo.com",
    id: /^[0-9]{1,20}$/,
    key: /^[0-9a-f]{6,64}$/,
    allow: "autoplay; fullscreen; picture-in-picture; clipboard-write; encrypted-media; web-share",
    src: (m) => "https://player.vimeo.com/video/" + encodeURIComponent(m.id) + "?"
      + (m.key ? "h=" + encodeURIComponent(m.key) + "&" : "") + "dnt=1&autoplay=1"
      + (m.start ? "#t=" + m.start + "s" : ""),
    watch: (m) => "https://vimeo.com/" + encodeURIComponent(m.id)
      + (m.key ? "/" + encodeURIComponent(m.key) : "") + (m.start ? "#t=" + m.start + "s" : ""),
  }),
});
const _EMBED_SHAPES = { "16:9": "wide", "9:16": "portrait", "4:3": "classic", "1:1": "square" };

/* The video a media of kind "embed" plays — its provider's entry, the
   player's address, the video's page and the box's shape — or null (with a
   warning) when the provider is unknown or the id is not one of its ids. */
function embedOf(media) {
  if (!media || media.kind !== "embed") return null;
  const provider = media.provider;
  const p = typeof provider === "string" && Object.prototype.hasOwnProperty.call(EMBED, provider)
    ? EMBED[provider] : null;
  const id = typeof media.id === "string" ? media.id : "";
  const key = provider === "vimeo" && typeof media.key === "string" ? media.key : "";
  if (!p || !p.id.test(id) || (key && !p.key.test(key))) {
    try { console.warn("siamang: not a YouTube or Vimeo video, nothing shown:", provider, media.id); } catch (e) { /* no console */ }
    return null;
  }
  const start = Number.isInteger(media.start) && media.start > 0 && media.start <= _EMBED_START_MAX
    ? media.start : 0;
  const video = { id, key, start };
  return {
    provider, label: p.label, allow: p.allow,
    src: p.src(video), watch: p.watch(video),
    shape: _EMBED_SHAPES[media.aspect] || "wide",
  };
}

/* What a press of play does where the page is. In a design preview (a
   host's editor, `window.SIAMANG_DESIGN`) a player cannot play — it gets no
   referrer from the preview's page, and YouTube and Vimeo refuse it — so the
   box says so and the host is told. In a sandboxed page (an opaque origin,
   such as a page served in a sandboxed iframe or under a CSP `sandbox`) the
   same holds, and the video opens on the provider's site instead. */
function embedPlace() {
  if (typeof window === "undefined") return "play";
  if (window.SIAMANG_DESIGN) return "design";
  if (window.origin === "null") return "away";
  return "play";
}
/* The video's page in a new tab, with no way back to this one; false when the
   browser refused the tab. */
function openVideoPage(url) {
  let tab = null;
  try { tab = window.open(url, "_blank"); } catch (e) { tab = null; }
  if (!tab) return false;
  try { tab.opener = null; } catch (e) { /* cross-origin already */ }
  return true;
}
/* What a press does: "play" (show the player), or "blocked" (say this
   preview cannot), or nothing ("away": the video opened in a tab). */
function pressPlay(provider, page) {
  const place = embedPlace();
  if (place === "design") {
    postToDesignHost({ type: "siamang:embed-blocked", provider: provider });
    return "blocked";
  }
  if (place === "away") return openVideoPage(page) ? "away" : "blocked";
  return "play";
}

/* The player: the provider's frame, from the address embedOf built. */
function playerFrame(src, allow, title) {
  const frame = document.createElement("iframe");
  frame.setAttribute("src", src);
  frame.setAttribute("title", title);
  frame.setAttribute("allow", allow);
  frame.setAttribute("allowfullscreen", "");
  frame.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");
  return frame;
}

const _PLAY_GLYPH = "M8 5.14v13.72a1 1 0 0 0 1.52.85l11.03-6.86a1 1 0 0 0 0-1.7L9.52 4.29A1 1 0 0 0 8 5.14z";
function PlayGlyph() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d={_PLAY_GLYPH} /></svg>
  );
}

/* A question's video: the play button, the player once it is pressed. */
function EmbedMedia({ media, name }) {
  const embed = embedOf(media);
  const [state, setState] = useState("idle");
  const frameRef = useRef(null);
  const fromId = React.useId();
  useEffect(() => {
    if (state === "play" && frameRef.current) frameRef.current.focus();
  }, [state]);
  if (!embed) return null;
  const texts = runtimeTexts();
  const own = media.alt || media.caption || "";
  const press = () => {
    const next = pressPlay(embed.provider, embed.watch);
    if (next !== "away") setState(next);
  };
  return (
    <figure className="siamang-media siamang-media--embed">
      <div className={"siamang-embed siamang-embed--" + embed.shape}>
        {state === "play" ? (
          <iframe
            ref={frameRef}
            src={embed.src}
            title={own || embed.label + " video"}
            allow={embed.allow}
            allowFullScreen
            referrerPolicy="strict-origin-when-cross-origin"
          />
        ) : (
          <button
            type="button"
            className="siamang-embed__facade"
            aria-label={texts.mediaPlay + ": " + (own || name || embed.label)}
            aria-describedby={fromId}
            onClick={press}
          >
            <span className="siamang-embed__glyph"><PlayGlyph /></span>
            {own ? <span className="siamang-embed__title">{own}</span> : null}
            <span className="siamang-embed__from" id={fromId}>
              {fillText(texts.mediaLoadsFrom, { service: embed.label })}
            </span>
          </button>
        )}
        <span className="siamang-embed__note" role="status">
          {state === "blocked" ? texts.mediaPreviewBlocked : ""}
        </span>
      </div>
      {media.caption ? <figcaption className="siamang-media__caption">{media.caption}</figcaption> : null}
    </figure>
  );
}

/* An answer option's video: a Play button beside the option, outside its
   label — so the choice keeps the option's name and pressing play never
   chooses it — that opens the player in a window over the page. One player
   at a time: opening one closes the last; closing it removes the player,
   which stops it, and gives the focus back to the button. */
let __playerDialog = null;
function closePlayerDialog() {
  if (__playerDialog && __playerDialog.open) __playerDialog.close();
}
function openPlayerDialog(embed, title, opener, blocked) {
  closePlayerDialog();
  const texts = runtimeTexts();
  const dialog = document.createElement("dialog");
  dialog.className = "siamang-player-dialog";
  // Named as the button that opened it ("Play video: Acme"), so a screen
  // reader says it holds a video, not just the option's label.
  dialog.setAttribute("aria-label", texts.mediaPlay + ": " + title);
  const bar = document.createElement("div");
  bar.className = "siamang-player-dialog__bar";
  const close = document.createElement("button");
  close.type = "button";
  close.className = "siamang-player-dialog__close";
  close.textContent = texts.mediaClose;
  close.addEventListener("click", () => dialog.close());
  bar.appendChild(close);
  const box = document.createElement("div");
  box.className = "siamang-embed siamang-embed--" + embed.shape;
  if (blocked) {
    const note = document.createElement("p");
    note.className = "siamang-embed__note is-shown";
    note.setAttribute("role", "status");
    note.textContent = texts.mediaPreviewBlocked;
    box.appendChild(note);
  } else {
    box.appendChild(playerFrame(embed.src, embed.allow, title));
  }
  dialog.appendChild(bar);
  dialog.appendChild(box);
  // Its keys are its own: Escape closes it (and does not go back a page),
  // Enter and the digits do nothing to the survey under it.
  dialog.addEventListener("keydown", (e) => e.stopPropagation());
  // A press outside the window (on its backdrop) closes it too.
  dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); });
  dialog.addEventListener("close", () => {
    dialog.remove();
    if (__playerDialog === dialog) __playerDialog = null;
    if (opener && opener.isConnected) opener.focus();
  });
  document.body.appendChild(dialog);
  __playerDialog = dialog;
  dialog.showModal();
  return dialog;
}

function OptionPlay({ media, name }) {
  const embed = embedOf(media);
  if (!embed) return null;
  const texts = runtimeTexts();
  const label = texts.mediaPlay + ": " + (name || media.alt || embed.label);
  const press = (e) => {
    const opener = e.currentTarget;
    const next = pressPlay(embed.provider, embed.watch);
    if (next === "away") return;
    const title = media.alt || media.caption || name || embed.label + " video";
    openPlayerDialog(embed, title, opener, next === "blocked");
  };
  return (
    <button type="button" className="sd-choice-play" aria-label={label} title={label} onClick={press}>
      <PlayGlyph />
    </button>
  );
}

/* An option's row (its <label>) as it was, or — the option has a video —
   the row and the video's Play button side by side. */
function withPlay(row, opt, pipe) {
  if (!opt.media || opt.media.kind !== "embed") return row;
  return (
    <div className="sd-choice-row" key={row.key}>
      {row}
      <OptionPlay media={pipedMedia(opt.media, pipe)} name={pipe(opt.label)} />
    </div>
  );
}
/* The media an option shows inside its label: a file's (a video's is a Play
   button beside it). */
function rowMedia(opt, pipe) {
  if (!opt.media || opt.media.kind === "embed") return null;
  return <MediaItem media={pipedMedia(opt.media, pipe)} />;
}

/* Piping: {answer:x} / {var:x} insert the raw answer to variable x,
   {label:x} the label of the chosen option(s) (falls back to the raw
   value for questions without options). Unanswered → the placeholder
   stays, so an author sees at once what is missing. */
const PIPE_TOKENS = /\{(answer|label|var):([a-zA-Z0-9_]+)\}/g;
const PIPE_TOKEN = /\{(answer|label|var):[a-zA-Z0-9_]+\}/;
function hasPipe(text) {
  return typeof text === "string" && text.indexOf("{") !== -1 && PIPE_TOKEN.test(text);
}

/* The keys a question stores its own answer under: its id, its Other text,
   a wide question's variables, a matrix's rows. An answer option never pipes
   one of them — "{label:q}" among q's own options would change under the
   respondent's hand as they answer — so such a placeholder stays as typed. */
function ownAnswerKeys(q) {
  const keys = new Set();
  if (q.id) keys.add(q.id);
  if (q.otherKey) keys.add(q.otherKey);
  for (const o of Array.isArray(q.options) ? q.options : []) if (o && o.var) keys.add(o.var);
  for (const r of Array.isArray(q.rows) ? q.rows : []) if (r && r.id) keys.add(r.id);
  return keys;
}

/* What a respondent reads as a question's answers, where the runtime pipes
   as it does in its title: the options' labels (and an option image's alt
   text and caption), Other's label, a scale's end labels and N/A, a matrix's
   statements and column headers, a slider's labels. A MaxDiff's items and a
   Conjoint's levels are its design — every respondent is shown the same
   items, so that their choices can be compared — and are shown as written. */
function answerTexts(q) {
  if (q.kind === "maxdiff" || q.kind === "conjoint") return [];
  const texts = [q.otherLabel, q.leftLabel, q.rightLabel, q.naOption, q.minLabel, q.maxLabel];
  for (const o of Array.isArray(q.options) ? q.options : []) {
    if (!o) continue;
    texts.push(o.label);
    if (o.media) texts.push(o.media.alt, o.media.caption);
  }
  for (const c of Array.isArray(q.columns) ? q.columns : []) texts.push(c);
  for (const r of Array.isArray(q.rows) ? q.rows : []) if (r) texts.push(r.label);
  if (q.labels && typeof q.labels === "object") texts.push(...Object.values(q.labels));
  return texts;
}

/* What piping a question needs, worked out once per question object (the
   page's items do not change while it is shown): whether its title or hint
   pipes, whether any of its answers does (most do not — their labels are
   then shown with no scan at all), whose answers they may not pipe, and
   whether an option has a condition. */
const _piping = new WeakMap();
function pipingOf(q) {
  let info = _piping.get(q);
  if (info) return info;
  info = {
    text: hasPipe(q.title) || hasPipe(q.description),
    options: answerTexts(q).some(hasPipe),
    own: ownAnswerKeys(q),
    gated: Array.isArray(q.options) && q.options.some((o) => o && (o.showIf !== undefined || o.hideIf !== undefined)),
  };
  _piping.set(q, info);
  return info;
}

const keepText = (text) => text;
/* The function a question shows its answers' texts through: the text as it
   is when none of them pipes, else the text piped from `answers` — but never
   from the question's own answer. It returns text, which React renders as
   text: a piped answer cannot add markup. */
function optionPiper(q, answers) {
  const info = pipingOf(q);
  if (!info.options || !answers) return keepText;
  return (text) => pipeText(text, answers, info.own, 0);
}
/* An option's image with its alt text and caption piped. */
function pipedMedia(media, pipe) {
  if (!media || pipe === keepText) return media;
  return { ...media, alt: pipe(media.alt), caption: pipe(media.caption) };
}
/* The question's title as its controls' accessible name: piped, as the
   title the respondent reads is. */
function questionName(q, answers) {
  return pipingOf(q).text ? processPipedText(q.title, answers) : q.title;
}

/* What a screen reader is told of a question's answer field or group, beside
   its name: that it is required, and while its error shows, that it is
   invalid and why (the error, by its id — QuestionShell's errorId). */
function answerAria(q, error, { required = true } = {}) {
  return {
    "aria-required": required && q.required ? true : undefined,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": error ? q.id + "__err" : undefined,
  };
}

let _pipeLabelIndex = null;
const _pipeOtherIndex = {};
// The own answer keys of the question each piped variable belongs to, for a
// question whose labels pipe: {label:x} inserts the label as the respondent
// read it, piped too.
const _pipeOwnIndex = {};
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
      if (pipingOf(q).options) {
        const own = pipingOf(q).own;
        for (const key of own) _pipeOwnIndex[key] = own;
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
/* `own`: the keys the text being piped may not show (see pipeText); a label
   piped into it carries them on, so that an option cannot show its own
   question's answer by way of another question's label either. */
function pipeValue(type, key, answers, depth = 0, own = null) {
  let val = answers[key];
  if (val && typeof val === "object" && !Array.isArray(val) && "code" in val) val = val.text && val.code === "__other__" ? val.text : val.code;
  if (val === null || val === undefined || val === "") return null;
  if (type === "label") {
    const labels = pipeLabelIndex()[key];
    const other = _pipeOtherIndex[key];
    const one = (v) => {
      if (other && String(v) === other.code && answers[other.key]) return String(answers[other.key]);
      if (!labels || labels[String(v)] === undefined) return String(v);
      const label = String(labels[String(v)]);
      // A label that pipes was read piped ("Acme Pro" for "{label:brand}
      // Pro"), and is inserted so. A respondent's own text never is: only
      // an author's label is scanned, and a few levels deep at most. It
      // shows neither its own question's answers nor those the text it goes
      // into may not.
      if (!(depth < 3 && _pipeOwnIndex[key] && hasPipe(label))) return label;
      const inner = own ? new Set([...own, ..._pipeOwnIndex[key]]) : _pipeOwnIndex[key];
      return pipeText(label, answers, inner, depth + 1);
    };
    return Array.isArray(val) ? val.map(one).join(", ") : one(val);
  }
  return Array.isArray(val) ? val.join(", ") : String(val);
}
/* `own`: keys never piped here (a question's own answers, for its options);
   their placeholders stay as typed. */
function pipeText(text, answers, own, depth) {
  if (!text || typeof text !== 'string' || !answers) return text;
  return text.replace(PIPE_TOKENS, (match, type, key) => {
    if (own && own.has(key)) return match;
    const piped = pipeValue(type, key, answers, depth, own);
    return piped === null ? match : piped;
  });
}
function processPipedText(text, answers) {
  return pipeText(text, answers, null, 0);
}
/* An address the respondent is sent to or opens, as a browser reads it
   (spaces and control characters at either end and tabs and line breaks
   inside dropped), when it is an http(s) one; else null. The compiler sends
   no other (siamang.core.safe_url): this is the last check before
   location.href, where a javascript: address would run as the survey. */
function safeNavigationUrl(url) {
  if (!url || typeof url !== "string") return null;
  const value = url.replace(/^[\u0000-\u0020]+|[\u0000-\u0020]+$/g, "").replace(/[\t\n\r]/g, "");
  return /^https?:\/\/[^\/\\\s]/i.test(value) ? value : null;
}
/* Redirect URL templates: ``{url:NAME}`` is the query parameter the
   respondent arrived with (a panel's respondent id), ``{answer:x}`` etc.
   pipe answers; every value is URL-encoded. An unknown placeholder is
   removed rather than sent to a third party as literal braces. What comes
   out is an http(s) address or null (safeNavigationUrl). */
function redirectTemplate(url, answers) {
  if (!url || typeof url !== "string") return null;
  let params = null;
  try { params = new URLSearchParams(window.location.search); } catch (e) { params = null; }
  return safeNavigationUrl(url.replace(/\{(url|answer|label|var):([a-zA-Z0-9_]+)\}/g, (match, type, key) => {
    if (type === "url") return encodeURIComponent((params && params.get(key)) || "");
    const piped = pipeValue(type, key, answers || {});
    return piped === null ? "" : encodeURIComponent(piped);
  }));
}
/* The same for HTML bodies: piped values are escaped so an answer can never
   inject markup into the page. The body itself is the compiler's sanitized
   HTML (siamang.core.safe_html); SafeHtml puts it in the page. */
/* The last line before a body's HTML becomes part of the page. The compiler
   sends it sanitized; this reads it as the browser does — in an inert
   <template>, where nothing loads or runs — and takes out what could run a
   script once it is in the page: script-capable and form elements, frames
   other than the YouTube and Vimeo players the compiler writes, foreign
   content (svg, math), on… handlers and srcdoc, and javascript:, vbscript:
   and data: addresses (a data: picture aside). The browser's own URL parser
   reads each address, so no spelling of a scheme gets past it. On the
   compiler's output it changes nothing. */
const _BODY_DROPPED = new Set(["SCRIPT", "STYLE", "LINK", "META", "BASE", "OBJECT", "EMBED",
  "APPLET", "FRAME", "FRAMESET", "TEMPLATE", "NOSCRIPT", "FORM", "INPUT", "BUTTON", "SELECT",
  "TEXTAREA", "PORTAL"]);
const _BODY_PLAYER = /^https:\/\/(www\.youtube-nocookie\.com\/embed\/|player\.vimeo\.com\/video\/)/;
const _BODY_URLS = new Set(["href", "src", "poster", "action", "formaction", "cite", "background",
  "data", "xlink:href"]);
const _BODY_PICTURE = /^data:image\/(png|jpe?g|pjpeg|gif|webp|avif|bmp|x-icon|vnd\.microsoft\.icon)[;,]/i;
function cleanBodyFragment(html) {
  const template = document.createElement("template");
  template.innerHTML = html || "";
  for (const el of Array.from(template.content.querySelectorAll("*"))) {
    const tag = el.tagName.toUpperCase();
    if (el.namespaceURI !== "http://www.w3.org/1999/xhtml" || _BODY_DROPPED.has(tag)
        || (tag === "IFRAME" && !_BODY_PLAYER.test(el.getAttribute("src") || ""))) {
      el.remove();
      continue;
    }
    for (const attr of Array.from(el.attributes)) {
      const name = attr.name.toLowerCase();
      if (name.startsWith("on") || name === "srcdoc") {
        el.removeAttribute(attr.name);
      } else if (_BODY_URLS.has(name)) {
        let protocol = "";
        try { protocol = new URL(attr.value, document.baseURI).protocol; } catch (e) { protocol = ""; }
        const picture = (tag === "IMG" || name === "poster") && _BODY_PICTURE.test(attr.value.trim());
        if (protocol === "javascript:" || protocol === "vbscript:" || (protocol === "data:" && !picture)) {
          el.removeAttribute(attr.name);
        }
      }
    }
  }
  if ((window.SURVEY || {}).clickToPlay) bodyPlayersWaitForPress(template.content);
  return template.content;
}

/* With the host's clickToPlay (SURVEY.clickToPlay), a body's YouTube and
   Vimeo players wait for the respondent as a question's video does: each
   kept player becomes the same play button, in a box of the frame's shape
   (its width and height, 16:9 without them; 200 px at the least), its
   address kept on the box (data-src) and checked again when it is pressed
   (onBodyPress). The <template>'s content is inert: nothing has loaded the
   frame meanwhile. Without the flag a body's players are frames, as the
   compiler wrote them. */
const _BODY_FACADES = new WeakSet();
/* The title the compiler's sanitizer writes on a player that had none
   (siamang.core.safe_html _PLAYER_TITLES). */
const _BODY_PLAYER_TITLES = Object.freeze({ youtube: "YouTube video player", vimeo: "Vimeo video player" });
const _PIXELS = /^\s*\d+(?:\.\d+)?\s*(?:px)?\s*$/;
let _bodyFacades = 0;
function bodyPlayerProvider(src) {
  if (typeof src !== "string" || !_BODY_PLAYER.test(src)) return null;
  let url = null;
  try { url = new URL(src); } catch (e) { return null; }
  const parts = url.pathname.split("/").filter(Boolean);
  if (url.host === "www.youtube-nocookie.com" && parts[0] === "embed"
      && /^[A-Za-z0-9_-]{1,64}$/.test(parts[1] || "")) return "youtube";
  if (url.host === "player.vimeo.com" && parts[0] === "video" && EMBED.vimeo.id.test(parts[1] || "")) return "vimeo";
  return null;
}
/* The video's own page, for a page that cannot play it. */
function bodyVideoPage(src, provider) {
  const url = new URL(src);
  const id = url.pathname.split("/").filter(Boolean)[1];
  if (provider === "youtube") {
    const list = url.searchParams.get("list");
    if (id === "videoseries" && list) return "https://www.youtube.com/playlist?list=" + encodeURIComponent(list);
    const start = parseInt(url.searchParams.get("start") || "", 10);
    return EMBED.youtube.watch({ id, start: start > 0 && start <= _EMBED_START_MAX ? start : 0 });
  }
  const key = url.searchParams.get("h") || "";
  return "https://vimeo.com/" + encodeURIComponent(id)
    + (EMBED.vimeo.key.test(key) ? "/" + key : "") + (/^#t=[0-9hms.]+$/.test(url.hash) ? url.hash : "");
}
/* `src` with name=value in its query, its fragment kept. A name already there
   keeps its place and takes this value, and any repeat of it goes: a
   player written with dnt=0&dnt=0 loads with dnt=1 alone, not dnt=1&dnt=0. */
function withParam(src, name, value) {
  let url = null;
  try { url = new URL(src); } catch (e) { return src; }
  url.searchParams.set(name, value);
  return url.toString();
}
function facadeButton(doc, label, title, from) {
  const button = doc.createElement("button");
  button.type = "button";
  button.className = "siamang-embed__facade";
  button.setAttribute("aria-label", label);
  const fromId = "siamang-embed-from-" + (++_bodyFacades);
  button.setAttribute("aria-describedby", fromId);
  const glyph = doc.createElement("span");
  glyph.className = "siamang-embed__glyph";
  const svg = doc.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const path = doc.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", _PLAY_GLYPH);
  svg.appendChild(path);
  glyph.appendChild(svg);
  button.appendChild(glyph);
  if (title) {
    const name = doc.createElement("span");
    name.className = "siamang-embed__title";
    name.textContent = title;
    button.appendChild(name);
  }
  const line = doc.createElement("span");
  line.className = "siamang-embed__from";
  line.id = fromId;
  line.textContent = from;
  button.appendChild(line);
  return button;
}
function bodyPlayersWaitForPress(root) {
  const texts = runtimeTexts();
  for (const frame of Array.from(root.querySelectorAll("iframe"))) {
    const src = frame.getAttribute("src") || "";
    const provider = bodyPlayerProvider(src);
    if (!provider) { frame.remove(); continue; }
    const doc = frame.ownerDocument;
    const box = doc.createElement("div");
    box.className = "siamang-embed siamang-embed--body";
    box.setAttribute("data-src", src);
    const width = frame.getAttribute("width") || "";
    const height = frame.getAttribute("height") || "";
    if (_PIXELS.test(width) && _PIXELS.test(height) && parseFloat(width) > 0 && parseFloat(height) > 0) {
      box.style.aspectRatio = parseFloat(width) + " / " + parseFloat(height);
      box.style.maxWidth = Math.max(200, parseFloat(width)) + "px";
    }
    // The title the sanitizer gives an untitled player ("Vimeo video
    // player") is not the author's: such a player shows no title, and is
    // named as a question's video is.
    const given = (frame.getAttribute("title") || "").trim();
    const own = given === _BODY_PLAYER_TITLES[provider] ? "" : given;
    const title = own || EMBED[provider].label + " video";
    box.setAttribute("data-title", title);
    box.appendChild(facadeButton(doc, texts.mediaPlay + ": " + title, own,
      fillText(texts.mediaLoadsFrom, { service: EMBED[provider].label })));
    const note = doc.createElement("span");
    note.className = "siamang-embed__note";
    note.setAttribute("role", "status");
    box.appendChild(note);
    frame.replaceWith(box);
    _BODY_FACADES.add(box);
  }
}
/* A press in a body: on one of the play buttons bodyPlayersWaitForPress
   made (an author's look-alike is not one), its address checked again. */
function onBodyPress(e) {
  const button = e.target && e.target.closest ? e.target.closest(".siamang-embed__facade") : null;
  const box = button ? button.closest(".siamang-embed") : null;
  if (!box || !_BODY_FACADES.has(box)) return;
  const src = box.getAttribute("data-src") || "";
  const provider = bodyPlayerProvider(src);
  if (!provider) return;
  e.preventDefault();
  const place = pressPlay(provider, bodyVideoPage(src, provider));
  if (place === "away") return;
  if (place === "blocked") {
    const note = box.querySelector(".siamang-embed__note");
    if (note) note.textContent = runtimeTexts().mediaPreviewBlocked;
    return;
  }
  let play = withParam(src, "autoplay", "1");
  if (provider === "vimeo") play = withParam(play, "dnt", "1");
  const frame = playerFrame(play, EMBED[provider].allow, box.getAttribute("data-title") || "");
  button.replaceWith(frame);
  frame.focus();
}
function processPipedHtml(html, answers) {
  if (!html || typeof html !== 'string' || !answers) return html;
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  return html.replace(/\{(answer|label|var):([a-zA-Z0-9_]+)\}/g, (match, type, key) => {
    const piped = pipeValue(type, key, answers);
    return piped === null ? match : esc(piped);
  });
}

/* `errorId`: the id the error is given, for a field or a group that names
   it in aria-describedby, so a screen reader on the field hears why it is
   invalid after the alert has been read out once. */
function QuestionShell({ num, title, required, description, error, errorId, children, onBlur, answers, media }) {
  const processedTitle = processPipedText(title, answers);
  const processedDescription = processPipedText(description, answers);
  // A question is checked when the focus leaves it, not when it moves
  // between its own controls: the dropdown's button to its search box as
  // the list opens (which said "requires an answer" before anything could be
  // chosen), one checkbox to the next, a choice to its Other box.
  const handleBlur = onBlur
    ? (e) => {
      if (e.relatedTarget && e.currentTarget.contains(e.relatedTarget)) return;
      onBlur(e);
    }
    : undefined;
  return (
    <div className={"sd-question" + (error ? " has-error" : "")} onBlur={handleBlur}>
      <div className="sd-question__header">
        <h3 className="sd-question__title">
          {num ? <span className="sd-question__num">{num}</span> : null}
          <span>{processedTitle}</span>
          {required ? <span className="sd-question__required-text" aria-hidden="true">*</span> : null}
        </h3>
        {processedDescription ? <p className="sd-question__description">{processedDescription}</p> : null}
        <MediaGallery media={media} name={processedTitle} />
      </div>
      {children}
      {error ? <div className="sd-question__error" id={errorId} role="alert">{error}</div> : null}
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
  // What an option shows is piped; what it stores (`value`) is its code.
  const pipe = optionPiper(q, answers);

  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} errorId={q.id + "__err"} onBlur={onBlur} answers={answers} media={q.media}>
      <div className={"sd-choices" + (isButtons ? " sd-choices--buttons" : "")} role="radiogroup" aria-label={questionName(q, answers)} {...answerAria(q, error)}>
        {visibleOptions(q, answers).map((opt) => {
          const checked = currentCode === opt.code;
          return withPlay(
            <label key={String(opt.code)} className={"sd-radio" + (checked ? " sd-item--checked" : "")}>
              <input
                type="radio"
                name={q.id}
                value={String(opt.code)}
                checked={checked}
                onChange={() => handleChange(opt.code)}
              />
              <span className="sd-radio__decorator" aria-hidden="true"></span>
              <span className="sd-choice-label">{pipe(opt.label)}</span>
              {rowMedia(opt, pipe)}
            </label>,
            opt, pipe
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
            <span className="sd-choice-label">{pipe(q.otherLabel) || runtimeTexts().other}</span>
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
  const pipe = optionPiper(q, answers);

  return (
    <QuestionShell
      num={num}
      title={q.title}
      required={q.required}
      description={q.description}
      error={error}
      errorId={q.id + "__err"}
      onBlur={onBlur}
      answers={answers}
      media={q.media}
    >
      {/* A group of boxes is not required as a whole for a screen reader
          (aria-required is not a group's), only invalid while its error shows. */}
      <div className="sd-choices" role="group" aria-label={questionName(q, answers)} {...answerAria(q, error, { required: false })}>
        {visibleOptions(q, answers).map((opt) => {
          const checked = v.includes(opt.code);
          const disabled = !checked && q.max && v.length >= q.max;
          return withPlay(
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
              <span className="sd-choice-label">{pipe(opt.label)}</span>
              {rowMedia(opt, pipe)}
            </label>,
            opt, pipe
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
            <span className="sd-choice-label">{pipe(q.otherLabel) || runtimeTexts().other}</span>
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
  const pipe = optionPiper(q, answers);
  // A radio group, as a screen reader and the keyboard expect one: one tab
  // stop (the chosen point, else the first), the arrows and Home/End move the
  // choice. Every point was a button of its own, announced as a toggle
  // button with no place on the scale.
  const tabIdx = Math.max(0, points.indexOf(value));
  const ends = [pipe(q.leftLabel), pipe(q.rightLabel)];
  const endId = (i) => (i === 0 && ends[0] ? q.id + "__lo" : i === points.length - 1 && ends[1] ? q.id + "__hi" : undefined);
  const move = (e, i) => {
    // With Alt, Ctrl or Cmd an arrow is the browser's (Alt+Left goes back).
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    const to = { ArrowRight: i + 1, ArrowDown: i + 1, ArrowLeft: i - 1, ArrowUp: i - 1, Home: 0, End: points.length - 1 }[e.key];
    if (to === undefined) return;
    e.preventDefault();
    const j = Math.min(points.length - 1, Math.max(0, to));
    // At an end the choice stays: nothing to save again.
    if (points[j] !== value) onChange(points[j]);
    const items = e.currentTarget.parentElement.querySelectorAll(".sd-rating__item");
    if (items[j]) items[j].focus();
  };
  // How many points a row of numbers holds: all of them where each still
  // has its least width (the stylesheet's --sd-rating-min) and the gaps fit,
  // else half of them, in two even rows (0-5, 6-10), and fewer only if those
  // are still too narrow. Measured on the scale itself, so a narrow theme or
  // embed wraps and a wide phone does not; the count goes in as a custom
  // property through the CSSOM, which a strict CSP allows, as a matrix's
  // --sd-matrix-cols does.
  const scaleRef = useRef(null);
  React.useLayoutEffect(() => {
    const el = scaleRef.current;
    if (stars || !el || typeof ResizeObserver !== "function") return undefined;
    const fit = () => {
      const width = el.clientWidth;
      if (!(width > 0)) return;
      const cs = getComputedStyle(el);
      const gap = parseFloat(cs.columnGap) || 0;
      const least = parseFloat(cs.getPropertyValue("--sd-rating-min")) || 44;
      let cols = q.points;
      for (let rows = 1; rows <= q.points; rows++) {
        cols = Math.ceil(q.points / rows);
        if (cols === 1 || (width - gap * (cols - 1)) / cols >= least) break;
      }
      el.style.setProperty("--sd-rating-cols", String(cols));
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(el);
    return () => observer.disconnect();
  }, [stars, q.points]);
  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} errorId={q.id + "__err"} onBlur={onBlur} answers={answers} media={q.media}>
      <div className={"sd-rating" + (stars ? " sd-rating--stars" : "")}>
        <div
          ref={scaleRef}
          className="sd-rating__scale"
          role="radiogroup"
          aria-label={questionName(q, answers)}
          {...answerAria(q, error)}
          onMouseLeave={() => setHover(null)}
          style={stars ? undefined : { "--sd-rating-points": q.points }}
        >
          {points.map((n, i) => {
            // Stars fill up to the chosen (or hovered) one; numbers select one point.
            const lit = stars && typeof value === "number" && n <= (hover ?? value);
            const hot = stars && hover !== null && n <= hover;
            // A star is named by its count, and the radio says where it is
            // ("3, radio button, 3 of 5"): "3 of 5" said its place twice.
            return (
              <button
                type="button"
                key={n}
                className={"sd-rating__item" + (value === n ? " is-selected" : "") + (lit || hot ? " is-lit" : "")}
                onClick={() => onChange(n)}
                onKeyDown={(e) => move(e, i)}
                onMouseEnter={stars ? () => setHover(n) : undefined}
                role="radio"
                aria-checked={value === n}
                tabIndex={i === tabIdx ? 0 : -1}
                aria-label={stars ? String(n - start + 1) : undefined}
                aria-describedby={endId(i)}
              >
                {stars ? <span className="sd-rating__star" aria-hidden="true">{lit || hot ? "\u2605" : "\u2606"}</span> : <span className="sd-rating__num">{n}</span>}
              </button>
            );
          })}
        </div>
        <div className="sd-rating__labels">
          <span id={ends[0] ? q.id + "__lo" : undefined}>{ends[0]}</span>
          <span id={ends[1] ? q.id + "__hi" : undefined}>{ends[1]}</span>
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
              <span className="sd-choice-label">{pipe(q.naOption)}</span>
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
  // The headers, statements and N/A as the respondent reads them — piped,
  // in the visible text and in each cell's accessible name alike.
  const pipe = optionPiper(q, answers);
  const columns = pipe === keepText ? q.columns : q.columns.map((c) => pipe(c));
  const naOption = pipe(q.naOption);

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
        {/* --sd-matrix-cols: on a narrow screen each row is a card of this
            many answers, each under its column's label (style.css). */}
        <table className="sd-matrix" role="radiogroup" aria-label={questionName(q, answers)} style={{ "--sd-matrix-cols": width }}>
          <thead>
            <tr>
              <th></th>
              {columns.map((c, i) => <th key={i}>{c}</th>)}
              {q.naOption ? <th className="sd-matrix__na-header">{naOption}</th> : null}
            </tr>
          </thead>
          <tbody>
            {q.rows.map((row, rowIdx) => {
              const statement = pipe(row.label);
              return (
                <tr key={row.id} className={missing && missing.has(row.id) ? "is-missing" : undefined}>
                  <td>{statement}</td>
                  {q.columns.map((_, colIdx) => {
                    const code = matrixColumnCode(q, colIdx);
                    const selected = v[row.id] === code;
                    return (
                      <td key={colIdx}>
                        <button
                          type="button"
                          className={"sd-matrix__cell" + (selected ? " is-selected" : "")}
                          aria-label={`${statement}: ${columns[colIdx]}`}
                          aria-pressed={selected}
                          {...cellProps(row, rowIdx, colIdx)}
                          onClick={() => onChange({ ...v, [row.id]: code })}
                        />
                        <span className="sd-matrix__col-label" aria-hidden="true" onClick={() => onChange({ ...v, [row.id]: code })}>{columns[colIdx]}</span>
                      </td>
                    );
                  })}
                  {q.naOption ? (
                    <td>
                      <button
                        type="button"
                        className={"sd-matrix__cell" + (sameCode(v[row.id], rowNaCode(row)) ? " is-selected" : "")}
                        aria-label={`${statement}: ${naOption}`}
                        aria-pressed={sameCode(v[row.id], rowNaCode(row))}
                        {...cellProps(row, rowIdx, q.columns.length)}
                        onClick={() => onChange({ ...v, [row.id]: rowNaCode(row) })}
                      />
                      <span className="sd-matrix__col-label" aria-hidden="true" onClick={() => onChange({ ...v, [row.id]: rowNaCode(row) })}>{naOption}</span>
                    </td>
                  ) : null}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </QuestionShell>
  );
}

/* What is typed into a text or number field goes into the answers when the
   field is left, or 600 ms after the last key. commitPendingInputs puts what
   is still waiting there at once, as the page is hidden or left
   (useAutosave), so the save written then holds it. A field marks its commit
   as waiting with each key (usePendingInput's mark) and every commit clears
   it. */
const pendingInputs = new Set();
function commitPendingInputs() {
  for (const ref of Array.from(pendingInputs)) {
    pendingInputs.delete(ref);
    if (ref.current) ref.current();
  }
}
function usePendingInput(commit) {
  const ref = useRef(null);
  ref.current = commit;
  useEffect(() => () => { pendingInputs.delete(ref); }, []);
  return {
    mark: () => { pendingInputs.add(ref); },
    clear: () => { pendingInputs.delete(ref); },
  };
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
    // Nothing is stored until the respondent moves the slider, so an untouched
    // one must not look answered: the thumb waits (faded) where it starts, the
    // default or the middle, and the value reads "—". Showing the middle as the
    // answer let someone who agreed with it go on with a blank.
    const touched = value !== null && value !== undefined;
    const v = touched ? value : (q.defaultValue !== undefined ? q.defaultValue : Math.round((min + max) / 2));
    const labels = q.labels || {};
    // Only show tick marks if the range is small enough (≤20 steps)
    const totalSteps = Math.round((max - min) / step);
    const showTicks = totalSteps <= 20;
    // A click on the thumb where it waits changes nothing, so no change event
    // comes: letting go of the pointer answers the value it shows.
    const settle = (e) => { if (!touched) onChange(Number(e.currentTarget.value)); };
    const pipe = optionPiper(q, answers);
    return (
      <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} onBlur={onBlur} answers={answers} media={q.media}>
        <div className={"siamang-slider" + (touched ? "" : " is-untouched")}>
          <input
            type="range"
            min={min}
            max={max}
            step={step}
            value={v}
            onChange={(e) => onChange(Number(e.target.value))}
            onPointerUp={settle}
            className="siamang-slider__input"
            aria-valuemin={min}
            aria-valuemax={max}
            aria-valuenow={touched ? v : undefined}
            aria-valuetext={touched ? undefined : "Not answered"}
            aria-label={questionName(q, answers)}
          />
          <div className="siamang-slider__value" style={{
            color: touched ? "var(--siamang-accent)" : "var(--siamang-muted)",
            fontWeight: 600,
            fontSize: "1.1rem",
          }}>{touched ? v : "—"}</div>
          {showTicks ? (
            <div className="siamang-slider__labels">
              {Array.from({ length: totalSteps + 1 }, (_, i) => min + i * step).map((n) => (
                <span key={n} className={"siamang-slider__tick" + (touched && v === n ? " is-active" : "")}>
                  {labels[n] !== undefined ? pipe(labels[n]) : n}
                </span>
              ))}
            </div>
          ) : (
            <div className="siamang-slider__end-labels">
              <span>{labels[min] !== undefined ? pipe(labels[min]) : (pipe(q.minLabel) || `${min}`)}</span>
              <span>{labels[max] !== undefined ? pipe(labels[max]) : (pipe(q.maxLabel) || `${max}`)}</span>
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
    pending.clear();
    if (debounceRef.current) { clearTimeout(debounceRef.current); debounceRef.current = null; }
    if (!inputRef.current) return;
    const raw = inputRef.current.value;
    onChange(raw === "" ? null : Number(raw));
  };
  const pending = usePendingInput(commit);
  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} errorId={q.id + "__err"} onBlur={onBlur} answers={answers} media={q.media}>
      <div className="sd-numeric">
        <input
          ref={inputRef}
          type="number"
          className="sd-input"
          aria-label={questionName(q, answers)}
          {...answerAria(q, error)}
          defaultValue={value ?? ""}
          min={q.min}
          max={q.max}
          step={q.step || 1}
          onInput={() => {
            if (debounceRef.current) clearTimeout(debounceRef.current);
            debounceRef.current = setTimeout(commit, 600);
            pending.mark();
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
    pending.clear();
    if (debounceRef.current) { clearTimeout(debounceRef.current); debounceRef.current = null; }
    if (inputRef.current) onChange(inputRef.current.value);
  };
  const pending = usePendingInput(commit);
  const handleInput = (e) => {
    setChars(e.target.value.length);   // local-only state for the counter
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(commit, 600);
    pending.mark();
  };
  const handleBlur = () => {
    commit();
    if (onBlur) onBlur();
  };

  const InputTag = q.multiline ? "textarea" : "input";
  const extraProps = q.multiline ? { rows: 4 } : { type: TEXT_INPUT_TYPES[q.format] || "text", inputMode: TEXT_INPUT_MODES[q.format] };

  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} errorId={q.id + "__err"} onBlur={null} answers={answers} media={q.media}>
      <InputTag
        ref={inputRef}
        className="sd-input"
        aria-label={questionName(q, answers)}
        {...answerAria(q, error)}
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

  // The options as the respondent reads them: the button, the list and the
  // search all go by the piped label.
  const pipe = optionPiper(q, answers);
  const name = questionName(q, answers);
  const visible = pipe === keepText
    ? visibleOptions(q, answers)
    : visibleOptions(q, answers).map((o) => ({ ...o, label: pipe(o.label) }));
  const offered = q.otherSpecify && !otherIsAnOption(q)
    ? [...visible, { code: OTHER, label: pipe(q.otherLabel) || runtimeTexts().other }]
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
  // and puts the keys on its first entry. The keys are read on the whole
  // menu, so they work wherever in it the focus is (a click on the list's
  // scroll bar puts it on the list), and Esc there never reaches the page,
  // where it would go back a page.
  const handleMenuKey = (e) => {
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
      e.stopPropagation();
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
          <div className="siamang-search-dropdown__menu" onKeyDown={handleMenuKey}>
            <input
              type="text"
              className="sd-input siamang-search-dropdown__search"
              placeholder={runtimeTexts().searchPlaceholder}
              value={search}
              onChange={(e) => { setSearch(e.target.value); setActive(e.target.value ? 0 : -1); }}
              role="combobox"
              aria-expanded={true}
              aria-controls={listId}
              aria-autocomplete="list"
              aria-activedescendant={filtered[active] ? optionId(active) : undefined}
              aria-label={name}
              autoFocus
            />
            {/* The options are reached from the search box
                (aria-activedescendant), not by Tab: without tabIndex -1 a
                list long enough to scroll is a stop of its own (Chromium
                130+), inside the menu, so Tab left the menu open with the
                focus on it. */}
            <div className="siamang-search-dropdown__options" role="listbox" id={listId} aria-label={name} tabIndex={-1}>
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
  const pipe = optionPiper(q, answers);
  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} errorId={q.id + "__err"} onBlur={onBlur} answers={answers} media={q.media}>
      <div className="sd-image-choices" role="radiogroup" aria-label={questionName(q, answers)} {...answerAria(q, error)}>
        {visibleOptions(q, answers).map((opt) => {
          const checked = value === opt.code;
          const imageUrl = opt.imageUrl || (opt.media && opt.media.kind === "image" ? opt.media.url : null);
          const label = pipe(opt.label);
          return (
            <button
              key={String(opt.code)}
              type="button"
              className={"sd-image-choice" + (checked ? " is-selected" : "")}
              onClick={() => onChange(opt.code)}
              aria-pressed={checked}
            >
              {imageUrl && (
                <img className="sd-image-choice__img" src={imageUrl} alt={label} loading="lazy" />
              )}
              <span className="sd-image-choice__label">{label}</span>
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
  const pipe = optionPiper(q, answers);

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
              <span className="sd-ranking__label">{pipe(opt.label)}</span>
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
                  <span className="sd-ranking__label">{pipe(opt.label)}</span>
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
   text from another answer ({answer:x} / {var:x} / {label:x}) into its
   title, hint or answer options, or gates an option on one; for the
   common case where it doesn't, we ignore answers changes. */
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
  if (prev.answers === next.answers) return true;
  // A title, a hint or an answer option that pipes another answer, and an
  // option's show_if/hide_if, read the other answers: such a question is
  // drawn again when they change — an option's label as soon as the answer
  // it pipes is given, on the same page. Whether it does is worked out once
  // per question (pipingOf), not at every change.
  const piping = pipingOf(next.q);
  if (piping.text || piping.options || piping.gated) return false;
  // Option order can be changed through answers.__options__ (randomize
  // scripts / author-declared randomization) — re-render when it does.
  const optOrder = (a) => (a && a.__options__ ? a.__options__[next.qId] : undefined);
  if (optOrder(prev.answers) !== optOrder(next.answers)) return false;
  return true;
});

Object.assign(window, { Question, QuestionShell, processPipedText, processPipedHtml, safeNavigationUrl });
