import React, { useContext, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "./ReportPage.css"; // We'll create this CSS file next
import { UserContext } from "./UserContext"; // Import User Context

import './header.css'; 
function ReportPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
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
      <header className="homepage-header">
        {/* Left Section - Logo */}
        <div className="homepage-header-left">
          {/* Desktop Logo */}
          <div className="homepage-logo-container desktop-only" onClick={() => navigate("/")}>
            <h1 className="homepage-logo">
              <span className="homepage-logo-bold">Channel-</span>
              <span className="homepage-logo-highlight">IQ</span>
            </h1>
          </div>

          {/* Mobile Login - Hidden on desktop */}
          <div className="mobile-only">
            {user ? (
              <div className="homepage-user-profile">
                <img src={user.picture} alt="User" className="homepage-user-avatar" />
                <button className="homepage-logout-button" onClick={logout}>Logout</button>
              </div>
            ) : (
              <button className="homepage-login-button" onClick={() => navigate("/login")}>
                Login
              </button>
            )}
          </div>
        </div>

        {/* Mobile Logo - Center section only for mobile */}
        <div className="homepage-center">
          <div className="mobile-only homepage-logo-container" onClick={() => navigate("/")}>
            <h1 className="homepage-logo">
              <span className="homepage-logo-bold">Channel-</span>
              <span className="homepage-logo-highlight">IQ</span>
            </h1>
          </div>
        </div>

        {/* Right Section - Navigation, Profile and mobile hamburger */}
        <div className="homepage-header-right">
          {/* Desktop Navigation */}
          <nav className="homepage-nav desktop-only">
            <a href="/terms">Terms & Services</a>
            <a href="/videos">Videos</a>
          </nav>
          
          {/* Desktop Profile */}
          <div className="desktop-only">
            {user ? (
              <div className="homepage-user-profile">
                <img src={user.picture} alt="User" className="homepage-user-avatar" />
                <span className="homepage-username">{user.name}</span>
                <button className="homepage-logout-button" onClick={logout}>Logout</button>
              </div>
            ) : (
              <button className="homepage-login-button" onClick={() => navigate("/login")}>
                Login
              </button>
            )}
          </div>

          {/* Mobile Hamburger Menu */}
          <div className="homepage-hamburger-menu">
            <button 
              className="homepage-hamburger-button"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              aria-label="Toggle menu"
            >
              <span className="homepage-hamburger-icon">☰</span>
            </button>
            
            {isMenuOpen && (
              <div className="homepage-menu-dropdown">
                <a 
                  className="homepage-menu-item" 
                  href="/terms"
                  onClick={() => setIsMenuOpen(false)}
                >
                  Terms & Services
                </a>
                <a 
                  className="homepage-menu-item" 
                  href="/videos"
                  onClick={() => setIsMenuOpen(false)}
                >
                  Videos
                </a>
              </div>
            )}
          </div>
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
              onClick={() => navigate("/home")}
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