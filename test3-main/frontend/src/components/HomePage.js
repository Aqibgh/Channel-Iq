import React, { useContext, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { doc, getDoc } from "firebase/firestore";
import { db } from "../Firebase";
import { UserContext } from "./UserContext";
import './HomePage.css'; // Ensure your CSS file is imported
import './header.css'; 
const HomePage = () => {
  const { user, logout, login } = useContext(UserContext);
  const navigate = useNavigate();
  const [loadingUser, setLoadingUser] = useState(true);
  const [scrollLocked, setScrollLocked] = useState(true);
  const [isMenuOpen, setIsMenuOpen] = useState(false); // State for hamburger menu
  const titleRef = useRef(null);
  const subtitleRef = useRef(null);
  const previewRef = useRef(null);
  const buttonRef = useRef(null);

  // Fetch user from Firestore or localStorage
  useEffect(() => {
    const fetchUserFromFirestore = async () => {
      if (user) {
        setLoadingUser(false);
        return;
      }

      let storedUser = null;
      try {
        storedUser = JSON.parse(localStorage.getItem("user"));
      } catch (e) {
        console.warn("Invalid user data in localStorage");
      }

      if (storedUser?.uid) {
        try {
          const userDoc = await getDoc(doc(db, "users", storedUser.uid));
          if (userDoc.exists()) {
            login(userDoc.data());
          }
        } catch (error) {
          console.error("Error fetching user data from Firestore:", error);
        }
      }

      setLoadingUser(false);
    };

    fetchUserFromFirestore();
  }, [user, login]);

  // Animate elements on mount
  useEffect(() => {
    const elements = [titleRef, subtitleRef, previewRef, buttonRef];
    elements.forEach((ref, index) => {
      if (ref.current) {
        setTimeout(() => {
          ref.current.classList.add("animate-in");
        }, index * 200);
      }
    });
  }, []);
  
  // Text animation effect
  useEffect(() => {
    const animateElements = () => {
      const elements = [
        titleRef.current,
        subtitleRef.current,
        previewRef.current,
        buttonRef.current
      ];
      
      elements.forEach((el, index) => {
        if (el) {
          setTimeout(() => {
            el.style.opacity = 1;
            el.style.transform = 'translateY(0)';
          }, index * 200);
        }
      });
    };

    setTimeout(animateElements, 300);
  }, []);
  // Update the useEffect to actually use the scrollLocked value
// Update your scroll lock useEffect hook to this:


  const scrollToClipper = () => {
    setScrollLocked(false);
    const clipperSection = document.querySelector('.clipper-section');
    if (clipperSection) {
      clipperSection.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="home">
      {/* Background Logo */}

      {/* Navbar */}
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


      {/* Hero Section */}
      <div className="hero">
        <h1 className="hero__title" ref={titleRef}>
          Your All-in-One AI Tool to Instantly Boost <br />
          <span className="hero__title-highlight">Quality, SEO & YouTube Dominance</span>
        </h1>

        <p className="hero__subtitle" ref={subtitleRef}>
          All-powered editing suite for professional creators
        </p>

        {/* Features Grid */}
        {/* Features Grid */}
<div className="features-grid">
  <div className="feature-badge">
    <span className="feature-icon-homepage-icon">✂️</span>
    <span>Smart Clipping</span>
  </div>
  <div className="feature-badge">
    <span className="feature-icon-homepage-icon">📝</span>
    <span>Auto Captions</span>
  </div>
  <div className="feature-badge">
    <span className="feature-icon-homepage-icon">🔇</span>
    <span>Noise Removal</span>
  </div>
  <div className="feature-badge">
    <span className="feature-icon-homepage-icon">🖼️</span>
    <span>4K Upscaling</span>
  </div>
  <div className="feature-badge">
    <span className="feature-icon-homepage-icon">🔍</span>
    <span>SEO Optimization</span>
  </div>
</div>

       {/* Video Preview with enhanced size */}
       <div className="preview" ref={previewRef}>
  <video 
    className="preview__video" 
    autoPlay 
    loop 
    muted 
    playsInline
    onLoadedData={() => console.log("Video loaded successfully")}
    onError={(e) => console.error("Video error:", e.target.error)}
  >
    <source src="/videos/test.mp4" type="video/mp4" />
    <p>Your browser does not support video playback.</p>
  </video>
</div>

        {/* CTA Button */}
        <div className="cta" ref={buttonRef}>
          <button className="cta__button" onClick={() => navigate('/clipper')}>
            Get Started
          </button>
          <div className="cta__glow"></div>
        </div>
      </div>

      
    </div>
  );
};

export default HomePage;
