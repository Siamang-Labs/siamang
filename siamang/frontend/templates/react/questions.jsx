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
function pipeLabelIndex() {
  if (_pipeLabelIndex) return _pipeLabelIndex;
  const index = {};
  const survey = (typeof window !== "undefined" && window.SURVEY) || {};
  const visit = (items) => {
    for (const q of items || []) {
      if (!q) continue;
      if (Array.isArray(q.options) && q.id) {
        const map = {};
        for (const o of q.options) if (o && o.code !== undefined) map[String(o.code)] = o.label;
        index[q.id] = map;
        // A MaxDiff's best and worst variables hold item codes too.
        if (q.kind === "maxdiff") for (const pair of q.taskVars || []) for (const v of pair) index[v] = map;
      }
      if (Array.isArray(q.columns) && Array.isArray(q.rows)) {
        // Matrix: each row is its own variable; the columns are its labels,
        // keyed by the code each one stores.
        for (const r of q.rows) if (r && r.id) index[r.id] = Object.fromEntries((q.columns || []).map((c, i) => [String(matrixColumnCode(q, i)), String(c)]));
      }
    }
  };
  for (const p of survey.pages || []) {
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
    const one = (v) => (labels && labels[String(v)] !== undefined ? String(labels[String(v)]) : String(v));
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

function SingleChoice({ q, value, onChange, num, error, onBlur, answers, onAutoAdvance }) {
  const isButtons = q.display === "buttons";
  // For other_specify: value is stored as { code, text } or just code
  const currentCode = q.otherSpecify && value && typeof value === "object" ? value.code : value;
  const otherText = q.otherSpecify && value && typeof value === "object" ? value.text : "";
  const isOtherSelected = currentCode === "__other__";
  const otherInputRef = useRef(null);

  const handleChange = (code) => {
    if (code === "__other__") {
      onChange({ code: "__other__", text: otherText || "" });
      setTimeout(() => otherInputRef.current && otherInputRef.current.focus(), 50);
    } else {
      onChange(code);
      if (q.autoAdvance && onAutoAdvance) {
        setTimeout(() => onAutoAdvance(), 400);
      }
    }
  };

  const handleOtherText = (e) => {
    onChange({ code: "__other__", text: e.target.value });
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
        {q.otherSpecify && (
          <label className={"sd-radio" + (isOtherSelected ? " sd-item--checked" : "")}>
            <input
              type="radio"
              name={q.id}
              value="__other__"
              checked={isOtherSelected}
              onChange={() => handleChange("__other__")}
            />
            <span className="sd-radio__decorator" aria-hidden="true"></span>
            <span className="sd-choice-label">{q.otherLabel || "Other"}</span>
          </label>
        )}
        {q.otherSpecify && isOtherSelected && (
          <div className="sd-other-input">
            <input
              ref={otherInputRef}
              type="text"
              className="sd-input sd-other-input__field"
              placeholder={q.otherPlaceholder || "Please specify..."}
              value={otherText}
              onChange={handleOtherText}
            />
          </div>
        )}
      </div>
    </QuestionShell>
  );
}

function MultiChoice({ q, value, onChange, num, error, onBlur, answers }) {
  // value can be: [code1, code2, ...] or { selected: [...], otherText: "..." } when other_specify
  const hasOther = !!q.otherSpecify;
  const v = hasOther && value && typeof value === "object" && !Array.isArray(value)
    ? (Array.isArray(value.selected) ? value.selected : [])
    : (Array.isArray(value) ? value : []);
  const otherText = hasOther && value && typeof value === "object" && !Array.isArray(value)
    ? (value.otherText || "") : "";
  const isOtherSelected = v.includes("__other__");
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
    }
  };

  const toggleOther = () => {
    if (isOtherSelected) {
      emitValue(v.filter((x) => x !== "__other__"), "");
    } else if (!q.max || v.length < q.max) {
      emitValue([...v.filter((x) => !isExclusive(x)), "__other__"], otherText);
      setTimeout(() => otherInputRef.current && otherInputRef.current.focus(), 50);
    }
  };

  const handleOtherText = (e) => {
    emitValue(v, e.target.value);
  };

  const effectiveCount = v.filter((x) => x !== "__other__").length + (isOtherSelected ? 1 : 0);

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
        {hasOther && (
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
            <span className="sd-choice-label">{q.otherLabel || "Other"}</span>
          </label>
        )}
        {hasOther && isOtherSelected && (
          <div className="sd-other-input">
            <input
              ref={otherInputRef}
              type="text"
              className="sd-input sd-other-input__field"
              placeholder={q.otherPlaceholder || "Please specify..."}
              value={otherText}
              onChange={handleOtherText}
            />
          </div>
        )}
      </div>
      {q.max && (
        <div className="siamang-multi-counter" role="status" aria-live="polite">
          <span className="siamang-multi-counter__count">{effectiveCount} of {q.max} selected</span>
          {q.min && effectiveCount < q.min ? (
            <span className="siamang-multi-counter__hint">Select at least {q.min - effectiveCount} more</span>
          ) : effectiveCount >= q.max ? (
            <span className="siamang-multi-counter__hint is-max">Maximum reached</span>
          ) : null}
        </div>
      )}
    </QuestionShell>
  );
}

function Likert({ q, value, onChange, num, error, onBlur, answers }) {
  const isNA = value === "na";
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
                aria-label={stars ? `${n - start + 1} of ${q.points}` : undefined}
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
                onChange={() => onChange("na")}
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

function Matrix({ q, value, onChange, num, error, onBlur, answers }) {
  const v = value || {};
  const [focusRow, setFocusRow] = useState(0);
  const [focusCol, setFocusCol] = useState(0);

  const handleKeyDown = (e, rowIdx) => {
    if (e.key === "ArrowRight") {
      e.preventDefault();
      const nextCol = Math.min(focusCol + 1, q.columns.length - 1);
      setFocusCol(nextCol);
      onChange({ ...v, [q.rows[rowIdx].id]: matrixColumnCode(q, nextCol) });
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      const nextCol = Math.max(focusCol - 1, 0);
      setFocusCol(nextCol);
      onChange({ ...v, [q.rows[rowIdx].id]: matrixColumnCode(q, nextCol) });
    } else if (e.key === "ArrowDown" && rowIdx < q.rows.length - 1) {
      e.preventDefault();
      setFocusRow(rowIdx + 1);
    } else if (e.key === "ArrowUp" && rowIdx > 0) {
      e.preventDefault();
      setFocusRow(rowIdx - 1);
    }
  };

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
              <tr key={row.id}>
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
                        tabIndex={rowIdx === focusRow && colIdx === focusCol ? 0 : -1}
                        onFocus={() => { setFocusRow(rowIdx); setFocusCol(colIdx); }}
                        onKeyDown={(e) => handleKeyDown(e, rowIdx)}
                        onClick={() => onChange({ ...v, [row.id]: code })}
                      />
                    </td>
                  );
                })}
                {q.naOption ? (
                  <td>
                    <button
                      type="button"
                      className={"sd-matrix__cell" + (v[row.id] === "na" ? " is-selected" : "")}
                      aria-label={`${row.label}: ${q.naOption}`}
                      aria-pressed={v[row.id] === "na"}
                      tabIndex={-1}
                      onClick={() => onChange({ ...v, [row.id]: "na" })}
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

function NumericInput({ q, value, onChange, num, error, onBlur, answers }) {
  const [blurError, setBlurError] = useState(null);

  const handleBlur = () => {
    if (value !== null && value !== undefined && value !== "") {
      if (q.min !== undefined && value < q.min) {
        setBlurError(`Minimum value is ${q.min}`);
        return;
      }
      if (q.max !== undefined && value > q.max) {
        setBlurError(`Maximum value is ${q.max}`);
        return;
      }
    }
    setBlurError(null);
  };

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
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} onBlur={onBlur || handleBlur} answers={answers} media={q.media}>
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
            setBlurError(null);
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
      {blurError && <div className="sd-question__error" role="alert">{blurError}</div>}
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
        <div className="siamang-char-warning" role="alert">{q.maxChars - chars} characters remaining</div>
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
  const ref = useRef(null);

  const visible = visibleOptions(q, answers);
  const filtered = search
    ? visible.filter((o) => o.label.toLowerCase().includes(search.toLowerCase()))
    : visible;

  const selected = visible.find((o) => o.code === value);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} onBlur={onBlur} answers={answers} media={q.media}>
      <div className="siamang-search-dropdown" ref={ref}>
        <button
          type="button"
          className="sd-input siamang-search-dropdown__trigger"
          onClick={() => { setOpen(!open); setSearch(""); }}
          aria-haspopup="listbox"
          aria-expanded={open}
        >
          <span>{selected ? selected.label : "— Select —"}</span>
          <span className="siamang-search-dropdown__arrow" aria-hidden="true"></span>
        </button>
        {open && (
          <div className="siamang-search-dropdown__menu" role="listbox">
            <input
              type="text"
              className="sd-input siamang-search-dropdown__search"
              placeholder="Type to search…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus
            />
            <div className="siamang-search-dropdown__options">
              {filtered.map((opt) => (
                <div
                  key={opt.code}
                  className={"siamang-search-dropdown__option" + (value === opt.code ? " is-selected" : "")}
                  role="option"
                  aria-selected={value === opt.code}
                  onClick={() => { onChange(opt.code); setOpen(false); }}
                >
                  {opt.label}
                </div>
              ))}
              {filtered.length === 0 && (
                <div className="siamang-search-dropdown__empty">No options found</div>
              )}
            </div>
          </div>
        )}
      </div>
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
              {ranked.length > 0 ? "Remaining options" : "Tap or drag to rank"}
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
  /* The same respondent key Script.assign_condition draws arms from, and the
     same FNV-1a hash, so one respondent lands in one version however many
     things are assigned to them. Without a key — a build with no crypto API
     sends no respondent id — the draw is random and does not survive a resume,
     which the docs say out loud rather than hiding. */
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
            <table className="sd-maxdiff__task" key={taskIdx} aria-label={`Task ${taskIdx + 1} of ${tasks.length}`}>
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
                <table className="sd-conjoint__grid" aria-label={`Choice ${taskIdx + 1} of ${tasks.length}`}>
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
function _QuestionDispatcher({ q, qId, value, setAnswer, num, error, handleBlur, answers, onAutoAdvance }) {
  const onChange = (v) => setAnswer(qId, v);
  const onBlur = handleBlur ? () => handleBlur(qId) : undefined;
  switch (q.kind) {
    case "single":   return <SingleChoice q={q} value={value} onChange={onChange} num={num} error={error} onBlur={onBlur} answers={answers} onAutoAdvance={onAutoAdvance} />;
    case "multi":    return <MultiChoice  q={q} value={value} onChange={onChange} num={num} error={error} onBlur={onBlur} answers={answers} />;
    case "likert":   return <Likert       q={q} value={value} onChange={onChange} num={num} error={error} onBlur={onBlur} answers={answers} />;
    case "matrix":   return <Matrix       q={q} value={value} onChange={onChange} num={num} error={error} onBlur={onBlur} answers={answers} />;
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
