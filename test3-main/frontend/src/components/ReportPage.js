import React, { useContext } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "./ReportPage.css"; // We'll create this CSS file next
import { UserContext } from "./UserContext"; // Import User Context

function ReportPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useContext(UserContext); // Access User Context
  const { videoURL, videoTitle, report, thumbnail } = location.state || {};

  // Handle case where page is accessed directly without data
  if (!report) {
    return (
      <div className="report-error-container">
        <h2>Error: No report data found</h2>
        <p>Please generate a report from the clipper page.</p>
        <button onClick={() => navigate("/clipper")} className="btn btn--primary">
          Go to Clipper
        </button>
      </div>
    );
  }

  // Function to format the analysis sections with better styling
  const formatAnalysisSection = (sectionText) => {
    // Replace section headers with styled headers
    const formattedText = sectionText.replace(
      /^(\d+\.\s+[A-Z\s]+)(\s*\(.*?\))?:/gm,
      '<h3 class="section-header">$1$2:</h3>'
    );

    // Format bullet points
    return formattedText
      .split("\n")
      .map((line) => {
        // Convert bullet points to styled list items
        if (line.trim().startsWith("•") ||line.trim().startsWith("*")) {
          return `<li class="bullet-point">${line.trim().substring(1).trim()}</li>`;
        }
        // Keep paragraphs as they are
        return line.trim() ? `<p>${line.trim()}</p>` : "";
      })
      .join("");
  };

  return (
    <div className="report-app">
      {/* Header - Matching other pages */}
      <header className="dashboard-header">
  <div className="logo-container" onClick={() => navigate("/")}>
    <h1 className="logo">
      <span className="logo-bold">Channel-</span>
      <span className="logo-highlight">IQ</span>
    </h1>
  </div>

  <div className="header-right">
    <a 
      className="nav-link" 
      href="/terms" // or use navigate("/terms") if you're using React Router
      style={{ marginRight: '1rem', textDecoration: 'none', color: 'var(--color-text)', fontWeight: 500 }}
    >
      Terms & Services
    </a>
    <a 
        className="nav-link" 
        href="/videos" // Add this new link
        style={{ marginRight: '1rem', textDecoration: 'none', color: 'var(--color-text)', fontWeight: 500 }}
    >
        Videos
    </a>

    {user ? (
      <div className="user-profile">
        <img src={user.picture} alt="User" className="user-avatar" />
        <span className="username">{user.name}</span>
        <button className="logout-button" onClick={logout}>Logout</button>
      </div>
    ) : (
      <button className="login-button" onClick={() => navigate("/login")}>
        Login
      </button>
    )}
  </div>
</header>

      <div className="main-content">
       
        <div className="report-container">
          <div className="page-header">
            <h1>Video Analysis Report</h1>
            <p>Detailed analysis and recommendations for your video</p>
          </div>

         
          <div className="report-sections">
            
            <div className="full-analysis report-box">
              <h3>Full Analysis</h3>
              <div 
                className="analysis-content"
                dangerouslySetInnerHTML={{ __html: formatAnalysisSection(report.full_analysis) }}
              />
            </div>

           
          </div>

          <div className="action-buttons">
            <button 
              className="comparison-btn-lf"
              onClick={() => navigate("/clipper")}
            >
              Return to Clipper
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ReportPage; 