// Chain of Title -- Verification Status list.
import styles from "./VerificationStatus.module.css";
import Stamp from "../components/Stamp.jsx";

export default function VerificationStatus({ pipelineResult }) {
  if (!pipelineResult) {
    return (
      <div>
        <h2 className={styles.heading}>Verification Status</h2>
        <p className={styles.empty}>No manifest has been processed yet. Submit one on the Intake tab first.</p>
      </div>
    );
  }

  return (
    <div>
      <div className={styles.summaryRow}>
        <h2 className={styles.heading}>Verification Status</h2>
        <Stamp status={pipelineResult.verdict} />
      </div>
      <p className={styles.manifestId}>
        Manifest <code>{pipelineResult.manifest_id}</code>
      </p>

      <ul className={styles.list}>
        {pipelineResult.shots.map((shot) => (
          <li key={shot.shot_id} className={styles.row}>
            <div className={styles.shotNumber}>#{shot.shot_id}</div>
            <div className={styles.rowBody}>
              <div className={styles.rowHeader}>
                <span className={styles.toolName}>{shot.tool_name}</span>
                <Stamp status={shot.status} />
              </div>
              {shot.evidence && <p className={styles.evidence}>{shot.evidence}</p>}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
