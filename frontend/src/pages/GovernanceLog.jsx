// Chain of Title -- Governance Audit Log view.
// Implemented: BUILD_PLAN.md Day 29 (Aug 30)
// Update: added manual refresh -- clicking the same nav tab doesn't remount
// the component or re-run useEffect, so a fetch made before the Governance
// Agent caught up would otherwise show a permanently stale empty state.
import { useState, useEffect } from "react";
import styles from "./GovernanceLog.module.css";
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
        <h2>Governance Audit Log</h2>
        <p>No manifest has been processed yet. Submit one on the Submit tab first.</p>
      </div>
    );
  }

  return (
    <div>
      <h2>Governance Audit Log</h2>
      <p>Manifest: <code>{manifestId}</code></p>
      <button onClick={() => setRefreshKey((k) => k + 1)} disabled={status === "loading"}>
        {status === "loading" ? "Refreshing..." : "Refresh"}
      </button>

      {status === "error" && <p className={styles.error}>{error}</p>}
      {status === "success" && entries.length === 0 && (
        <p>
          No audit entries yet. The Governance Agent only logs while
          <code> consume_and_log()</code> is actively running in a terminal —
          if it wasn't running when this manifest was processed, its Kafka
          events are still queued. Run the consumer, then click Refresh.
        </p>
      )}
      {status === "success" && entries.length > 0 && (
        <ul className={styles.list}>
          {entries.map((entry) => (
            <li key={entry.id} className={styles.item}>
              <div className={styles.header}>
                <strong>{entry.decision}</strong> — {entry.tool_name || "unknown tool"} — shot{" "}
                {entry.shot_id}
              </div>
              <div className={styles.timestamp}>{entry.timestamp}</div>
              {entry.reasoning && <div className={styles.reasoning}>{entry.reasoning}</div>}
              <div className={styles.meta}>
                agent: {entry.agent || "—"}
                {entry.confidence != null && ` · confidence: ${entry.confidence}`}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
