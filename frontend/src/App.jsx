// Chain of Title -- main app shell.
// Implemented: BUILD_PLAN.md Days 24-30 (Aug 25-31)
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import ManifestSubmission from "./pages/ManifestSubmission.jsx";
import VerificationStatus from "./pages/VerificationStatus.jsx";
import RemediationQueue from "./pages/RemediationQueue.jsx";
import GovernanceLog from "./pages/GovernanceLog.jsx";

export default function App() {
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
          <Route path="/" element={<ManifestSubmission />} />
          <Route path="/verification" element={<VerificationStatus />} />
          <Route path="/remediation" element={<RemediationQueue />} />
          <Route path="/governance" element={<GovernanceLog />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
