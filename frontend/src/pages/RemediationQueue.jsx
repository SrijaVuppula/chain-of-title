// Chain of Title -- Remediation Queue (holds + suggested substitutes).
import styles from "./RemediationQueue.module.css";
import Stamp from "../components/Stamp.jsx";

export default function RemediationQueue({ pipelineResult }) {
  if (!pipelineResult) {
    return (
      <div>
        <h2 className={styles.heading}>Remediation Queue</h2>
        <p className={styles.empty}>No manifest has been processed yet. Submit one on the Intake tab first.</p>
      </div>
    );
  }

  const held = pipelineResult.shots.filter((shot) => shot.hold_id);

  if (held.length === 0) {
    return (
      <div>
        <h2 className={styles.heading}>Remediation Queue</h2>
        <p className={styles.empty}>No holds — every shot in this manifest cleared.</p>
      </div>
    );
  }

  return (
    <div>
      <h2 className={styles.heading}>Remediation Queue</h2>
      <p className={styles.manifestId}>
        Manifest <code>{pipelineResult.manifest_id}</code>
      </p>

      <div className={styles.cards}>
        {held.map((shot) => (
          <div key={shot.shot_id} className={styles.card}>
            <div className={styles.cardHeader}>
              <span className={styles.shotNumber}>Shot #{shot.shot_id}</span>
              <Stamp status={shot.status} />
            </div>
            <p className={styles.toolName}>{shot.tool_name}</p>
            <p className={styles.evidence}>{shot.evidence}</p>
            <div className={styles.substituteRow}>
              {shot.suggested_substitute ? (
                <>
                  <span className={styles.arrow}>&rarr;</span>
                  <span>
                    Substitute: <strong>{shot.suggested_substitute}</strong>
                  </span>
                </>
              ) : (
                <span className={styles.noSub}>No cleared substitute available in this category.</span>
              )}
            </div>
            <p className={styles.holdId}>Hold ID: {shot.hold_id}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
