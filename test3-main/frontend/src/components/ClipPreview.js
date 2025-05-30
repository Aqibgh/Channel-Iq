import React, { useEffect, useState, useContext } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { db } from "../Firebase";
import { collection, getDocs, serverTimestamp, doc, setDoc } from "firebase/firestore";
import { UserContext } from "./UserContext";
import "./clippreview.css";
import { apiClient } from '../axios-use/api';
import './header.css'; 
function ClipPreview() {
    const { user, logout } = useContext(UserContext);
    const location = useLocation();
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const navigate = useNavigate();
    const { clipPaths = [], videoURL = null, videoTitle = null } = location.state || {};
    const [error, setError] = useState(null);
    const [processedClips, setProcessedClips] = useState([]);
    const [selectedClip, setSelectedClip] = useState(null);
    const [selectedFeatures, setSelectedFeatures] = useState([]);
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('clips');
    

    // Function to save clip details to Firebase
    const saveClipDataToFirebase = async (clipPath, features, videoTitle) => {
        if (!user) {
            return;
        }
    
        try {
            const videosRef = collection(db, "users", user.uid, "videos");
            const querySnapshot = await getDocs(videosRef);
    
            let sanitizedTitle = videoTitle 
                ? videoTitle.replace(/[^\w\s-]/gi, "").trim()
                : null;
    
            let originalTitle = videoTitle || null;
    
            if (!sanitizedTitle) {
                querySnapshot.forEach((doc) => {
                    const videoData = doc.data();
                    
                    if (videoData.title) {
                        let title = videoData.title.replace(/[^\w\s-]/gi, "").trim();
                        
                        if (!sanitizedTitle) {
                            sanitizedTitle = title;
                            originalTitle = videoData.title;
                        }
                    }
                });
            }
    
            if (!sanitizedTitle) {
                sanitizedTitle = `video_${Date.now()}`;
                originalTitle = "Unknown Video"; 
            }
    
            const clipDocRef = doc(db, `users/${user.uid}/videos/${sanitizedTitle}/generate/ShortForm`);
    
            await setDoc(clipDocRef, {
                clipPath: clipPath.url || clipPath,
                clipKey: clipPath.key || clipPath,
                selectedFeatures: features,
                processedClips: processedClips || [],
                timestamp: serverTimestamp(),
                videoTitle: originalTitle,
                videoURL: videoURL,
            });
    
        } catch (error) {
            console.error("Error saving clip data:", error);
        }
    };

    useEffect(() => {
        if (!clipPaths || clipPaths.length === 0) {
            setError("No clips found to display.");
            return;
        }
        
        // Handle the new S3 format
        const clips = clipPaths.map(clip => {
            // Check if the clip is an object with url and key properties (S3 format)
            if (typeof clip === 'object' && clip.url) {
                return {
                    url: clip.url,
                    key: clip.key
                };
            } else {
                // Fallback for older format (local path)
                return {
                    url: `http://127.0.0.1:8000/media/${clip}`,
                    key: clip
                };
            }
        });
        
        setProcessedClips(clips);
        // Always select the first clip by default
        setSelectedClip(clips[0]);
    }, [clipPaths]); // Only depend on clipPaths change

    const handleClipSelection = (clip) => {
        // Since we want one clip selected at all times, don't allow deselection
        // Just change selection to the clicked clip
        setSelectedClip(clip);
    };

    const handleFeatureToggle = (feature) => {
        setSelectedFeatures((prevFeatures) =>
            prevFeatures.includes(feature)
                ? prevFeatures.filter((f) => f !== feature)
                : [...prevFeatures, feature]
        );
    };

    const handleOptimize = async () => {
        if (!selectedClip) {
            alert("Please select a clip to optimize.");
            return;
        }
    
        if (selectedFeatures.length === 0) {
            alert("Please select at least one feature to apply.");
            return;
        }
    
        setLoading(true);
    
        try {
            const videoTitle = location.state?.videoTitle || "Untitled Video";
            const isSEOIncluded = selectedFeatures.includes("SEO");
            const response = await apiClient.post('/optimize_shortform/', {
                clipPath: selectedClip.url,
                clipKey: selectedClip.key,
                selectedFeatures: selectedFeatures,
                videoURL: videoURL,
                userEmail: user?.email,
                timestamp: serverTimestamp(),
            });
            if (response.status === 200) {
                const result = response.data;
                await saveClipDataToFirebase(selectedClip, selectedFeatures, videoTitle);
                if (isSEOIncluded) {
                    
                    navigate("/seo_shortform", {
                        state: {
                            message: result.message,
                            results: result.results,
                            selectedFeatures,
                            selectedClip,
                            videoTitle
                        }
                    });
                } else {
                    
                    navigate("/optimizevideo_shortform", {
                        state: {
                            message: result.message,
                            results: result.results,
                            selectedFeatures,
                            selectedClip,
                            videoTitle
                        }
                    });
                }
            } else {
                alert("An error occurred during optimization. Please try again.");
                console.error("[DEBUG] Non-200 response:", response);
            }
        } catch (error) {
            alert("An error occurred. Please check your connection and try again.\n" + (error?.message || error));
            console.error("[DEBUG] Error during optimization:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleClipperClick = () => {
        navigate('/clipper');
    };

    const features = [
        { id: "NoiseReduction", name: "Noise Reduction", icon: "🔊" },
        { id: "VideoQuality", name: "Video Quality", icon: "🎬" },
        { id: "SEO", name: "SEO", icon: "🔍" },
        { id: "Captions", name: "Captions", icon: "💬" }
    ];

    return (
        <div className="dashboard-container">
            {/* Header */}
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

            {/* Main Content */}
            <div className="dashboard-content">
                {/* Sidebar */}
                <div className="sidebar">
                    <div className="sidebar-header">
                        <h2>Dashboard</h2>
                    </div>
                    <nav className="sidebar-nav">
                        <button 
                            className={`sidebar-button ${activeTab === 'clips' ? 'active' : ''}`}
                            onClick={() => setActiveTab('clips')}
                        >
                            <span className="sidebar-icon">🎬</span>
                            <span>Clips</span>
                        </button>
                        <button 
                            className={`sidebar-button ${activeTab === 'features' ? 'active' : ''}`}
                            onClick={() => setActiveTab('features')}
                        >
                            <span className="sidebar-icon">⚙️</span>
                            <span>Features</span>
                        </button>
                       
                    </nav>
                </div>

                {/* Main Content Area */}
                <div className="main-area">
                    <div className="content-container">
                        <div className="content-header">
                            <h2 className="content-title">
                                {activeTab === 'clips' ? 'Your Viral Clips' : 'Optimization Features'}
                            </h2>
                        </div>

                        {/* Content Body */}
                        <div className="content-body">
                            {activeTab === 'clips' ? (
                                <div className="clips-container">
                                    {error ? (
                                        <div className="error-card">
                                            <p className="error-message">{error}</p>
                                        </div>
                                    ) : (
                                        <>
                                            <div className="clips-grid-preview">
                                                {processedClips.map((clip, index) => (
                                                    <div 
                                                        key={index} 
                                                        className={`clip-card ${selectedClip === clip ? 'selected' : ''}`}
                                                        onClick={() => handleClipSelection(clip)}
                                                    >
                                                        <div className="clip-preview">
                                                            <video
                                                                src={clip.url}
                                                                controls
                                                                className="clip-videos"
                                                            />
                                                        </div>
                                                        
                                                    </div>
                                                ))}
                                            </div>
                                            
                                            
                                        </>
                                    )}
                                </div>
                            ) : (
                                <div className="features-container">
                                    <div className="features-grid">
                                        {features.map((feature) => (
                                            <div 
                                                key={feature.id} 
                                                className={`feature-card ${selectedFeatures.includes(feature.name) ? 'selected' : ''}`}
                                                onClick={() => handleFeatureToggle(feature.name)}
                                            >
                                                <div className="feature-icon-clips">{feature.icon}</div>
                                                <h3 className="feature-name">{feature.name}</h3>
                                                <div className="feature-selected-indicator">
                                                    {selectedFeatures.includes(feature.name) && (
                                                        <span className="selected-icon">✓</span>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Action Section */}
                        <div className="action-section">
                            <div className="action-container">
                                <div className="selected-items">
                                    <div className="selected-item">
                                        <span className="item-label">Selected Clip:</span>
                                        <span className="item-value">
                                            {selectedClip ? `Clip ${processedClips.indexOf(selectedClip) + 1}` : 'None'}
                                        </span>
                                    </div>
                                    <div className="selected-item">
                                        <span className="item-label">Selected Features:</span>
                                        <span className="item-value">
                                            {selectedFeatures.length > 0 
                                                ? selectedFeatures.join(', ') 
                                                : 'None'}
                                        </span>
                                    </div>
                                </div>
                                <button 
                                    className="optimize-button"
                                    onClick={handleOptimize}
                                    disabled={!selectedClip || selectedFeatures.length === 0 || loading}
                                >
                                    {loading ? "Processing..." : "Optimize"}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default ClipPreview;