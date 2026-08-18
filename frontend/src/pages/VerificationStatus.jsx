// Chain of Title -- Verification Status list.
// Implemented: BUILD_PLAN.md Day 26 (Aug 27)
import styles from "./VerificationStatus.module.css";

const STATUS_COLORS = {
  cleared: "green",
  needs_review: "yellow",
  flagged: "red",
  discontinued: "red",
  unknown: "red",
};

export default function VerificationStatus({ pipelineResult }) {
  if (!pipelineResult) {
    return (
      <div>
        <h2>Verification Status</h2>
        <p>No manifest has been processed yet. Submit one on the Submit tab first.</p>
      </div>
    );
  }

  return (
    <div>
      <h2>Verification Status</h2>
      <p>
        Manifest: <code>{pipelineResult.manifest_id}</code> — Verdict:{" "}
        <strong>{pipelineResult.verdict}</strong>
      </p>
      <ul className={styles.list}>
        {pipelineResult.shots.map((shot) => (
          <li
            key={shot.shot_id}
            className={`${styles.item} ${styles[STATUS_COLORS[shot.status] || "red"]}`}
          >
            <strong>Shot {shot.shot_id}</strong> — {shot.tool_name} — {shot.status}
            {shot.evidence && <p className={styles.evidence}>{shot.evidence}</p>}
          </li>
        ))}
      </ul>
    </div>
  );
}
