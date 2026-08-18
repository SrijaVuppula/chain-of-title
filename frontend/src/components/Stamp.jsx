// Renders a compliance verdict as a tally indicator -- an LED dot + mono
// label, styled after a camera's tally light. Used everywhere a status
// appears (per-shot and per-manifest) so the metaphor stays consistent.
import styles from "./Stamp.module.css";

const LABELS = {
  cleared: "Cleared",
  Greenlit: "Greenlit",
  needs_review: "Needs Review",
  "Needs-Review": "Needs Review",
  flagged: "Flagged",
  discontinued: "Discontinued",
  unknown: "Unknown",
  Held: "Held",
};

const TONES = {
  cleared: "clear",
  Greenlit: "clear",
  needs_review: "review",
  "Needs-Review": "review",
  flagged: "hold",
  discontinued: "hold",
  unknown: "hold",
  Held: "hold",
};

export default function Stamp({ status }) {
  const tone = TONES[status] || "hold";
  const label = LABELS[status] || status;
  return (
    <span className={`${styles.tally} ${styles[tone]}`}>
      <span className={styles.dot} />
      {label}
    </span>
  );
}
