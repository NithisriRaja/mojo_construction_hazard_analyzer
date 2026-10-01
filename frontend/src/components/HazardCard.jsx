export default function HazardCard({ hazard }) {
  const sev = hazard.severity.toLowerCase();
  return (
    <li className={`hazard sev-${sev}`}>
      <div className="hazard-head">
        <span className={`badge sev-${sev}`}>{hazard.severity}</span>
        <h3>{hazard.title}</h3>
      </div>
      <p className="hazard-desc">{hazard.description}</p>
      <span className="category">{hazard.category}</span>
    </li>
  );
}
