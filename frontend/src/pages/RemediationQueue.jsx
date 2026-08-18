// Chain of Title -- Remediation Queue (holds + suggested substitutes).
// Implemented: BUILD_PLAN.md Day 27 (Aug 28)
import styles from "./RemediationQueue.module.css";

export default function RemediationQueue({ pipelineResult }) {
  if (!pipelineResult) {
    return (
      <div>
        <h2>Remediation Queue</h2>
        <p>No manifest has been processed yet. Submit one on the Submit tab first.</p>
      </div>
    );
  }

  const held = pipelineResult.shots.filter((shot) => shot.hold_id);

  if (held.length === 0) {
    return (
      <div>
        <h2>Remediation Queue</h2>
        <p>No holds — every shot in this manifest cleared.</p>
      </div>
    );
  }

  return (
    <div>
      <h2>Remediation Queue</h2>
      <p>Manifest: <code>{pipelineResult.manifest_id}</code></p>
      <ul className={styles.list}>
        {held.map((shot) => (
          <li key={shot.shot_id} className={styles.item}>
            <div>
              <strong>Shot {shot.shot_id}</strong> — {shot.tool_name} ({shot.status})
            </div>
            <div className={styles.evidence}>{shot.evidence}</div>
            <div className={styles.substitute}>
              {shot.suggested_substitute ? (
                <>Suggested substitute: <strong>{shot.suggested_substitute}</strong></>
              ) : (
                "No cleared substitute available in this category."
              )}
            </div>
            <div className={styles.holdId}>Hold ID: {shot.hold_id}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
