// Chain of Title -- Governance Audit Log view.
// Includes a manual refresh control: React Router doesn't remount this
// component or re-run its fetch when you click a nav link to the tab
// you're already on, so a fetch made before the Governance Agent had
// caught up would otherwise leave a permanently stale empty state.
import { useState, useEffect } from "react";
import styles from "./GovernanceLog.module.css";
import Stamp from "../components/Stamp.jsx";
import { API_BASE } from "../config.js";

export default function GovernanceLog({ manifestId }) {
  const [entries, setEntries] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | loading | success | error
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!manifestId) return;

    let cancelled = false;
    setStatus("loading");
    setError("");

    fetch(`${API_BASE}/audit-log/${manifestId}`)
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to load audit log.");
        return data;
      })
      .then((data) => {
        if (cancelled) return;
        setEntries(data.entries || []);
        setStatus("success");
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || "Failed to load audit log.");
        setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [manifestId, refreshKey]);

  if (!manifestId) {
    return (
      <div>
        <h2 className={styles.heading}>Governance Audit Log</h2>
        <p className={styles.empty}>No manifest has been processed yet. Submit one on the Intake tab first.</p>
      </div>
    );
  }

  return (
    <div>
      <div className={styles.headerRow}>
        <h2 className={styles.heading}>Governance Audit Log</h2>
        <button onClick={() => setRefreshKey((k) => k + 1)} disabled={status === "loading"}>
          {status === "loading" ? "Refreshing..." : "Refresh"}
        </button>
      </div>
      <p className={styles.manifestId}>
        Manifest <code>{manifestId}</code>
      </p>

      {status === "error" && <p className={styles.error}>{error}</p>}
      {status === "success" && entries.length === 0 && (
        <p className={styles.empty}>No audit entries yet for this manifest. Try Refresh in a moment.</p>
      )}
      {status === "success" && entries.length > 0 && (
        <ul className={styles.ledger}>
          {entries.map((entry) => (
            <li key={entry.id} className={styles.entry}>
              <span className={styles.timestamp}>{entry.timestamp}</span>
              <div className={styles.entryBody}>
                <div className={styles.entryHeader}>
                  <span className={styles.tool}>{entry.tool_name || "unknown tool"}</span>
                  <span className={styles.shot}>shot {entry.shot_id}</span>
                  <Stamp status={entry.decision} />
                </div>
                {entry.reasoning && <p className={styles.reasoning}>{entry.reasoning}</p>}
                <p className={styles.meta}>
                  agent: {entry.agent || "—"}
                  {entry.confidence != null && ` · confidence: ${entry.confidence}`}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
