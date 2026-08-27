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
  if (!q.options) return [];
  return q.options.filter((opt) => gateOption(opt, answers));
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

function processPipedText(text, answers) {
  if (!text || typeof text !== 'string' || !answers) return text;
  return text.replace(/\{(answer|label|var):([a-zA-Z0-9_]+)\}/g, (match, type, key) => {
    if (type === 'answer' || type === 'var') {
      const val = answers[key];
      return val !== null && val !== undefined ? String(val) : match;
    }
    if (type === 'label') {
      const val = answers[key];
      return val !== null && val !== undefined ? String(val) : match;
    }
    return match;
  });
}

function QuestionShell({ num, title, required, description, error, children, onBlur, answers, media }) {
  const processedTitle = processPipedText(title, answers);
  return (
    <div className={"sd-question" + (error ? " has-error" : "")} onBlur={onBlur}>
      <div className="sd-question__header">
        <h3 className="sd-question__title">
          {num ? <span className="sd-question__num">{num}</span> : null}
          <span>{processedTitle}</span>
          {required ? <span className="sd-question__required-text" aria-hidden="true">*</span> : null}
        </h3>
        {description ? <p className="sd-question__description">{description}</p> : null}
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

  const toggle = (code) => {
    if (v.includes(code)) {
      emitValue(v.filter((x) => x !== code), otherText);
    } else if (!q.max || v.length < q.max) {
      emitValue([...v, code], otherText);
    }
  };

  const toggleOther = () => {
    if (isOtherSelected) {
      emitValue(v.filter((x) => x !== "__other__"), "");
    } else if (!q.max || v.length < q.max) {
      emitValue([...v, "__other__"], otherText);
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
  return (
    <QuestionShell num={num} title={q.title} required={q.required} description={q.description} error={error} onBlur={onBlur} answers={answers} media={q.media}>
      <div className="sd-rating">
        <div className="sd-rating__scale" role="radiogroup" aria-label={q.title}>
          {Array.from({ length: q.points }, (_, i) => i + 1).map((n) => (
            <button
              type="button"
              key={n}
              className={"sd-rating__item" + (value === n ? " is-selected" : "")}
              onClick={() => onChange(n)}
              aria-pressed={value === n}
            >
              <span className="sd-rating__num">{n}</span>
            </button>
          ))}
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

function Matrix({ q, value, onChange, num, error, onBlur, answers }) {
  const v = value || {};
  const [focusRow, setFocusRow] = useState(0);
  const [focusCol, setFocusCol] = useState(0);

  const handleKeyDown = (e, rowIdx) => {
    if (e.key === "ArrowRight") {
      e.preventDefault();
      const nextCol = Math.min(focusCol + 1, q.columns.length - 1);
      setFocusCol(nextCol);
      onChange({ ...v, [q.rows[rowIdx].id]: nextCol + 1 });
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      const nextCol = Math.max(focusCol - 1, 0);
      setFocusCol(nextCol);
      onChange({ ...v, [q.rows[rowIdx].id]: nextCol + 1 });
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
            </tr>
          </thead>
          <tbody>
            {q.rows.map((row, rowIdx) => (
              <tr key={row.id}>
                <td>{row.label}</td>
                {q.columns.map((_, colIdx) => {
                  const code = colIdx + 1;
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
  const extraProps = q.multiline ? { rows: 4 } : { type: "text" };

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
  return true;
});

Object.assign(window, { Question, QuestionShell });
