// Chain of Title -- main app shell.
import { useState } from "react";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import styles from "./App.module.css";
import ManifestSubmission from "./pages/ManifestSubmission.jsx";
import VerificationStatus from "./pages/VerificationStatus.jsx";
import RemediationQueue from "./pages/RemediationQueue.jsx";
import GovernanceLog from "./pages/GovernanceLog.jsx";

const TABS = [
  { to: "/", label: "Intake", end: true },
  { to: "/verification", label: "Verification" },
  { to: "/remediation", label: "Remediation" },
  { to: "/governance", label: "Governance" },
];

// Color-bar strip -- a nod to SMPTE broadcast color bars, the calibration
// pattern that precedes footage on a finished master. Drawn from the app's
// own palette (clear/review/hold/accent) plus two supporting hues.
const BAR_COLORS = [
  "#E8C547",
  "#4FC3E0",
  "#35C177",
  "#A65B95",
  "#EF4B4B",
  "#4FC3E0",
];

export default function App() {
  // Lifted here (not per-page) so Verification/Remediation/Governance all
  // read from the same single pipeline run. run_pipeline() re-writes holds
  // and re-publishes Kafka events if called twice for the same manifest, so
  // pages must NOT independently re-trigger it -- they only ever read this
  // shared result.
  const [pipelineResult, setPipelineResult] = useState(null);

  return (
    <BrowserRouter>
      <div className={styles.appShell}>
        <div className={styles.colorBar}>
          {BAR_COLORS.map((color, i) => (
            <span key={i} style={{ background: color }} />
          ))}
        </div>

        <header className={styles.letterhead}>
          <p className={styles.eyebrow}>Compliance Record · Form CT-1</p>
          <h1 className={styles.title}>Chain of Title</h1>
          <p className={styles.subtitle}>
            AI tool authorization for film &amp; television production
          </p>
        </header>

        <nav className={styles.nav}>
          {TABS.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.end}
              className={({ isActive }) =>
                isActive ? `${styles.tab} ${styles.tabActive}` : styles.tab
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>

        <main className={styles.page}>
          <Routes>
            <Route
              path="/"
              element={<ManifestSubmission onPipelineComplete={setPipelineResult} />}
            />
            <Route
              path="/verification"
              element={<VerificationStatus pipelineResult={pipelineResult} />}
            />
            <Route
              path="/remediation"
              element={<RemediationQueue pipelineResult={pipelineResult} />}
            />
            <Route
              path="/governance"
              element={<GovernanceLog manifestId={pipelineResult?.manifest_id} />}
            />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
