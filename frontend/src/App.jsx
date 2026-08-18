// Chain of Title -- main app shell.
// Implemented: BUILD_PLAN.md Days 24-30 (Aug 25-31)
import { useState } from "react";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import ManifestSubmission from "./pages/ManifestSubmission.jsx";
import VerificationStatus from "./pages/VerificationStatus.jsx";
import RemediationQueue from "./pages/RemediationQueue.jsx";
import GovernanceLog from "./pages/GovernanceLog.jsx";

export default function App() {
  // Lifted here (not per-page) so Verification/Remediation/Governance all
  // read from the same single pipeline run. See Day 25 design note:
  // run_pipeline() re-writes holds + re-publishes Kafka events if called
  // twice for the same manifest, so pages must NOT independently re-trigger it.
  const [pipelineResult, setPipelineResult] = useState(null);

  return (
    <BrowserRouter>
      <div>
        <h1>Chain of Title</h1>
        <nav>
          <NavLink to="/">Submit</NavLink>
          {" | "}
          <NavLink to="/verification">Verification</NavLink>
          {" | "}
          <NavLink to="/remediation">Remediation</NavLink>
          {" | "}
          <NavLink to="/governance">Governance</NavLink>
        </nav>
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
      </div>
    </BrowserRouter>
  );
}
