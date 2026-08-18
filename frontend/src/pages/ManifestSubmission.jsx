// Chain of Title -- Manifest Submission form.
// Implemented: BUILD_PLAN.md Day 25 (Aug 26)
// Day 25 update: now chains /run-pipeline right after /submit-manifest and
// lifts the result to App.jsx via onPipelineComplete, instead of storing
// pipeline results locally.
import { useState } from "react";
import styles from "./ManifestSubmission.module.css";
import { API_BASE } from "../config.js";

function emptyShot() {
  return { shot_id: "", description: "", ai_tool: "" };
}

export default function ManifestSubmission({ onPipelineComplete }) {
  const [production, setProduction] = useState("");
  const [submittedBy, setSubmittedBy] = useState("");
  const [shots, setShots] = useState([emptyShot()]);
  const [status, setStatus] = useState("idle"); // idle | submitting | processing | success | error
  const [manifestId, setManifestId] = useState(null);
  const [verdict, setVerdict] = useState(null);
  const [error, setError] = useState("");

  function updateShot(index, field, value) {
    setShots((prev) =>
      prev.map((shot, i) => (i === index ? { ...shot, [field]: value } : shot))
    );
  }

  function addShot() {
    setShots((prev) => [...prev, emptyShot()]);
  }

  function removeShot(index) {
    setShots((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!production.trim()) {
      setError("Production name is required.");
      return;
    }
    for (const shot of shots) {
      if (!shot.shot_id.trim() || !shot.ai_tool.trim()) {
        setError("Every shot needs a Shot ID and an AI Tool.");
        return;
      }
    }

    setStatus("submitting");
    try {
      const submitRes = await fetch(`${API_BASE}/submit-manifest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          production: production.trim(),
          submitted_by: submittedBy.trim() || undefined,
          shots,
        }),
      });
      const submitData = await submitRes.json();
      if (!submitRes.ok) {
        throw new Error(submitData.error || "Manifest submission failed.");
      }

      const newManifestId = submitData.manifest_id;
      setManifestId(newManifestId);
      setStatus("processing");

      const pipelineRes = await fetch(`${API_BASE}/run-pipeline/${newManifestId}`, {
        method: "POST",
      });
      const pipelineData = await pipelineRes.json();
      if (!pipelineRes.ok) {
        throw new Error(
          pipelineData.error ||
            "Manifest was submitted but the compliance pipeline failed to run."
        );
      }

      setVerdict(pipelineData.verdict);
      onPipelineComplete(pipelineData);
      setStatus("success");
    } catch (err) {
      setError(err.message || "Something went wrong.");
      setStatus("error");
    }
  }

  function handleReset() {
    setProduction("");
    setSubmittedBy("");
    setShots([emptyShot()]);
    setStatus("idle");
    setManifestId(null);
    setVerdict(null);
    setError("");
  }

  if (status === "success") {
    return (
      <div className={styles.container}>
        <h2>Manifest Processed</h2>
        <p>Manifest ID: <code>{manifestId}</code></p>
        <p>Verdict: <strong>{verdict}</strong></p>
        <p>Check the Verification, Remediation, and Governance tabs for details.</p>
        <button onClick={handleReset}>Submit another manifest</button>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <h2>Submit Manifest</h2>
      <form onSubmit={handleSubmit}>
        <div className={styles.field}>
          <label htmlFor="production">Production name</label>
          <input
            id="production"
            type="text"
            value={production}
            onChange={(e) => setProduction(e.target.value)}
            placeholder="e.g. Midnight Harbor"
          />
        </div>

        <div className={styles.field}>
          <label htmlFor="submittedBy">Submitted by (optional)</label>
          <input
            id="submittedBy"
            type="text"
            value={submittedBy}
            onChange={(e) => setSubmittedBy(e.target.value)}
            placeholder="e.g. VFX supervisor name"
          />
        </div>

        <h3>Shots</h3>
        {shots.map((shot, index) => (
          <div key={index} className={styles.shotRow}>
            <input
              type="text"
              placeholder="Shot ID (e.g. 34)"
              value={shot.shot_id}
              onChange={(e) => updateShot(index, "shot_id", e.target.value)}
            />
            <input
              type="text"
              placeholder="Description"
              value={shot.description}
              onChange={(e) => updateShot(index, "description", e.target.value)}
            />
            <input
              type="text"
              placeholder="AI tool used"
              value={shot.ai_tool}
              onChange={(e) => updateShot(index, "ai_tool", e.target.value)}
            />
            {shots.length > 1 && (
              <button type="button" onClick={() => removeShot(index)}>
                Remove
              </button>
            )}
          </div>
        ))}
        <button type="button" onClick={addShot}>
          + Add shot
        </button>

        {error && <p className={styles.error}>{error}</p>}

        <div className={styles.actions}>
          <button type="submit" disabled={status === "submitting" || status === "processing"}>
            {status === "submitting"
              ? "Submitting manifest..."
              : status === "processing"
              ? "Running compliance checks..."
              : "Submit manifest"}
          </button>
        </div>
      </form>
    </div>
  );
}
