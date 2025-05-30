import React, { useEffect, useState, useContext } from "react";
import { collection, getDocs, query, orderBy } from "firebase/firestore";
import { db } from "../Firebase";
import { UserContext } from "./UserContext";
import VideoDetails from "./videoDetails";
import { useNavigate } from "react-router-dom";
import "./videoDashboard.css";

const AllVideosPage = () => {
    const { user, logout, login } = useContext(UserContext);
    const navigate = useNavigate();
    const [videos, setVideos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [selectedVideo, setSelectedVideo] = useState(null);
    const [showModal, setShowModal] = useState(false);
    
    useEffect(() => {
        const fetchAllVideos = async () => {
            if (!user || !user.uid) {
                setLoading(false);
                return;
            }
            
            setLoading(true);
            try {
                const videosCollectionRef = collection(db, "users", user.uid, "videos");
                const videosQuery = query(
                    videosCollectionRef,
                    orderBy("timestamp", "desc") // Show newest first
                );
                
                const videoFoldersSnapshot = await getDocs(videosQuery);
                
                const videoPromises = videoFoldersSnapshot.docs.map(async (videoFolder) => {
                    const videoTitle = videoFolder.id;
                    const videoData = videoFolder.data();
                    
                    return {
                        id: videoTitle,
                        videoTitle: videoTitle,
                        title: videoData.title || videoTitle,
                        thumbnailUrl: videoData.thumbnailUrl || "/images/fallback-thumbnail.jpg",
                        timestamp: videoData.timestamp,
                        originalS3Url: videoData.originalS3Url,
                        videoURL: videoData.videoURL
                    };
                });
                
                const videoList = await Promise.all(videoPromises);
                setVideos(videoList);
            } catch (error) {
                console.error("Error fetching videos:", error);
                setError("Failed to load videos");
            } finally {
                setLoading(false);
            }
        };

        fetchAllVideos();
    }, [user]);

    const handleVideoClick = (video) => {
        setSelectedVideo(video);
        setShowModal(true);
    };

    const closeModal = () => {
        setShowModal(false);
        setSelectedVideo(null);
    };

    // Main app layout with separated header
    return (
        <>
            {/* Main application header - outside of the dashboard container */}
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

            {/* Dashboard content area */}
            <div className="video-dashboard">
                <div className="dashboard-header">
                    <button className="back-button" onClick={() => navigate(-1)}>
                        &larr; Back
                    </button>
                    <h2>All Optimized Videos</h2>
                </div>
                
                {loading && (
                    <div className="loading-container">
                        <div className="loading-spinner"></div>
                        <p>Loading your videos...</p>
                    </div>
                )}
                
                {error && (
                    <div className="error-container">
                        <p>{error}</p>
                        <button onClick={() => window.location.reload()}>Try Again</button>
                    </div>
                )}
                
                {!loading && !error && videos.length === 0 && (
                    <div className="empty-state">
                        <p>No videos found. Upload your first video to get started!</p>
                    </div>
                )}
                
                {!loading && !error && videos.length > 0 && (
                    <div className="video-grid">
                        {videos.map((video) => (
                            <div
                                key={video.id}
                                className="video-card"
                                onClick={() => handleVideoClick(video)}
                            >
                                <img
                                    src={video.thumbnailUrl}
                                    alt={video.title}
                                    className="video-thumbnail"
                                />
                                <p className="video-title">{video.title}</p>
                                {video.timestamp && (
                                    <p className="video-date">
                                        {new Date(video.timestamp.seconds * 1000).toLocaleDateString()}
                                    </p>
                                )}
                            </div>
                        ))}
                    </div>
                )}
                
                {showModal && selectedVideo && (
                    <VideoDetails 
                        onClose={closeModal} 
                        videoTitle={selectedVideo.videoTitle}
                    />
                )}
            </div>
        </>
    );
};

export default AllVideosPage;