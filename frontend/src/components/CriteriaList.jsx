const CATEGORY_ICON = {
  demographic: "👤",
  diagnosis: "🩺",
  lab: "🧪",
  medication: "💊",
  other: "📝",
};

export default function CriteriaList({ criteria, onDelete }) {
  return (
    <div className="criteria-cols">
      {["inclusion", "exclusion"].map((type) => {
        const rows = criteria.filter((c) => c.type === type);
        return (
          <div key={type} className={`criteria-col ${type}`}>
            <h3 className="cap">{type} criteria <span className="muted">({rows.length})</span></h3>
            {rows.length === 0 && <div className="muted small">None extracted.</div>}
            {rows.map((c, i) => (
              <div key={c.id ?? `${type}-${i}`} className="criterion">
                <div className="criterion-top">
                  <span className="cat" title={c.category}>{CATEGORY_ICON[c.category] || "•"}</span>
                  <span className="criterion-text">{c.description}</span>
                  {onDelete && c.id && (
                    <button className="icon-btn small" title="Remove criterion" onClick={() => onDelete(c)}>✕</button>
                  )}
                </div>
                <div className="chips">
                  {c.structured_rule.checks.map((chk, j) => (
                    <span key={j} className={`chip ${chk.kind}`}>{chk.kind === "text" ? "semantic review" : chk.label}</span>
                  ))}
                </div>
                <div className="muted tiny">Evidence: {c.required_evidence}</div>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
