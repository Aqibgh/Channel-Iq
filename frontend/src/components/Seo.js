import React, { useState, useEffect, useContext } from "react";
import "./Seo.css";
import { useLocation, useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faFileLines, faClosedCaptioning, faSearch, faImage } from "@fortawesome/free-solid-svg-icons";
import { fetchVideoMetadata, apiClient } from "../axios-use/api";
import { UserContext } from "./UserContext"; // Import User Context
import { db } from "../Firebase";  // Import Firebase Firestore
import { addDoc, getDoc, doc, setDoc, collection, query, where, serverTimestamp } from "firebase/firestore";
import './header.css'; 
function SEO({ videoThumbnail }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useContext(UserContext); // Access User Context
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { videoTitle, message, results, videoURL, localVideoPath, selectedFeatures } = location.state || {};
  const isSeoOnly = selectedFeatures?.length === 1 && selectedFeatures?.includes("SEO");
  // ✅ Debugging Logs
  
  

  // ✅ Fix: Ensure `displayMedia` or `selectedClip` is received
  const displayMedia = location.state?.displayMedia || null; 
  const selectedClip = location.state?.selectedClip || null; 


  const [seoMessage, setSeoMessage] = useState(message || "No SEO data received.");
  const [displayVideo, setDisplayVideo] = useState(selectedClip || null);
  const [thumbnail, setThumbnail] = useState(displayMedia || videoThumbnail || "/default-thumbnail.png");
  const [uploading, setUploading] = useState(false);
  const [authorizing, setAuthorizing] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [authToken, setAuthToken] = useState(null);
  const [hasYoutubeAuth, setHasYoutubeAuth] = useState(false);

  const seoData = results?.seo || {};
  const keywords = seoData.keywords?.length ? seoData.keywords.join(", ") : "No keywords available.";
  const description = seoData.description || "No description available.";
  const title = seoData.title || "No title available.";
  const tags = seoData.tags?.length ? seoData.tags.join(", ") : "No tags available.";

  // ✅ Helper function to format text with line breaks
  const formatWithLineBreaks = (text) => {
    if (!text) return "";
    
    // Replace all newline characters with <br /> tags
    return text.split('\n').map((line, index) => (
      <React.Fragment key={index}>
        {line}
        {index < text.split('\n').length - 1 && <br />}
      </React.Fragment>
    ));
  };
  const handleUploadToYouTube = async () => {
  if (!user) {
    setUploadStatus({
      success: false,
      message: "You must be logged in to upload to YouTube"
    });
    return;
  }

  if (!authToken) {
    setUploadStatus({
      success: false,
      message: "Authentication token not found. Please log in again."
    });
    return;
  }

  setUploading(true);
  setUploadStatus(null);

  try {
    // Get the video URL
    const videoUrl = getVideoUrl();
    
    // Check if we have a valid video URL
    if (!videoUrl) {
      setUploadStatus({
        success: false,
        message: "No video found to upload. Please ensure your video was processed successfully."
      });
      setUploading(false);
      return;
    }
    
    // ✅ FIXED: Send as JSON instead of FormData (same as handleUpdateSEO)
    const requestData = {
      video_url: videoUrl,
      title: title || "My Video",
      description: description || "",
      tags: tags || ""
    };
    
    if (results?.s3_upload?.key) {
      requestData.s3_key = results.s3_upload.key;
    }
    
    // Debug logs
    console.log("Request data:", requestData);
    
    // ✅ FIXED: Send as JSON with proper headers (same as handleUpdateSEO)
    const uploadResponse = await apiClient.post('/youtube/upload/', requestData, {
      headers: {
        Authorization: `Token ${authToken}`,
        'Content-Type': 'application/json',
      }
    });
    
    // Access data directly from axios response
    const data = uploadResponse.data;
    
    // Check if the request was successful
    if (uploadResponse.status !== 200) {
      if (uploadResponse.status === 401 && data.needs_auth) {
        // YouTube auth needs renewal
        setHasYoutubeAuth(false);
        setUploadStatus({
          success: false,
          message: data.detail || "Your YouTube authorization has expired. Please reconnect your YouTube account.",
          needsAuth: true
        });
        return;
      }
      throw new Error(`Upload failed with status: ${uploadResponse.status} ${uploadResponse.statusText}`);
    }
    
    if (data.success) {
      setUploadStatus({
        success: true,
        message: `Video uploaded successfully! Video ID: ${data.video_id}`,
        videoId: data.video_id
      });
    } else {
      setUploadStatus({
        success: false,
        message: data.error || "Failed to upload video"
      });
    }
  } catch (error) {
    console.error("Upload error:", error);
    
    // Handle axios error responses
    if (error.response) {
      const { status, data } = error.response;
      
      if (status === 401 && data.needs_auth) {
        setHasYoutubeAuth(false);
        setUploadStatus({
          success: false,
          message: data.detail || "Your YouTube authorization has expired. Please reconnect your YouTube account.",
          needsAuth: true
        });
      } else if (status === 400) {
        setUploadStatus({
          success: false,
          message: data.error || "Bad request. Please check your video data and try again."
        });
      } else {
        setUploadStatus({
          success: false,
          message: data.error || `Upload failed with status: ${status}`
        });
      }
    } else {
      setUploadStatus({
        success: false,
        message: `An error occurred during upload: ${error.message}`
      });
    }
  } finally {
    setUploading(false);
  }
};


  // ✅ Firebase function to save SEO data
  const saveDataToDB = async (user, locationState) => {
    if (!user) {
      console.error("❌ User not logged in. Cannot save data.");
      return;
    }
  
    const extractedUserId = user?.uid;
    if (!extractedUserId) {
      console.error("❌ No userId found.");
      return;
    }
  
    // Extract data from location state
    const {
      videoTitle,
      selectedFeatures = [],
      results = {}
    } = locationState || {};
  
    // ✅ Step 1: Sanitize the video title
    let sanitizedTitle = videoTitle
      ? videoTitle.replace(/[^\w\s-]/gi, "").trim()
      : `video_${Date.now()}`;
  
    if (!sanitizedTitle || sanitizedTitle.trim() === "") {
      console.error("❌ Error: Sanitized video title is empty.");
      return;
    }
  
    try {
      // ✅ Step 2: Firestore Path to store in 'LongForm'
      const longFormRef = doc(db, "users", extractedUserId, "videos", sanitizedTitle, "generate", "LongForm");
  
      // Create an object to hold all data we want to save
      const dataToSave = {
        timestamp: serverTimestamp()
      };
  
      // ✅ Step 3: If SEO is one of the selected features, add SEO data
      if (selectedFeatures.includes('SEO') && results.seo) {
        const { title, description, tags, keywords } = results.seo;
  
        // Format tags and keywords if they exist
        const formattedTags = Array.isArray(tags) && tags.length > 0
          ? tags.join(", ")
          : "No tags available.";
  
        const formattedKeywords = Array.isArray(keywords) && keywords.length > 0
          ? keywords.join(", ")
          : "No keywords available.";
  
        // Add SEO data to save object
        dataToSave.seo = {
          title: title || "Untitled",
          description: description || "No description available.",
          tags: formattedTags,
          keywords: formattedKeywords
        };
  
      }
  
      // ✅ Step 4: Save video processing data inside OptimizedVideo if available
      const optimizedVideoData = {};
  
      // Save audio processing data if available
      if (results.audio_processing) {
        optimizedVideoData.audio_processing = results.audio_processing;
        
      }
      
      // Add video upscaling data if available
      if (results.video_upscaling) {
        optimizedVideoData.video_upscaling = results.video_upscaling;
        
      }
  
      if (results.s3_upload) {
        optimizedVideoData.s3 = results.s3_upload;
        
      }
  
      if (results.email_notification) {
        optimizedVideoData.email_notification = results.email_notification;
        
      }
  
      if (Object.keys(optimizedVideoData).length > 0) {
        dataToSave.OptimizedVid = optimizedVideoData;
      }
  
      // Save selected features
      if (selectedFeatures && selectedFeatures.length > 0) {
        dataToSave.selectedFeatures = selectedFeatures;
        
      }
  
      
  
      // ✅ Step 5: Save all data to Firestore
      await setDoc(longFormRef, dataToSave);
  
     
    } catch (error) {
      console.error("🔥 Error saving data:", error);
    }
  };
  
  // ✅ Automatically Save Data when Component Loads
  useEffect(() => {
    if (user && location.state) {
      // Pass the entire location.state object to our save function
      saveDataToDB(user, location.state);
    }
  }, [user, location.state]);

  
   // Handle copy functionality for SEO data
   const handleCopy = (text) => {
    navigator.clipboard.writeText(text)
      .then(() => {
        alert("Copied to clipboard!");
      })
      .catch(err => {
        console.error('Failed to copy text: ', err);
      });
  };

  // Check for YouTube authorization on component mount
  useEffect(() => {
    const token = localStorage.getItem("token") || sessionStorage.getItem("token");
    setAuthToken(token);
    
    // Check if user has YouTube authorization
    if (token && user) {
      checkYoutubeAuth(token);
    }
  }, [user]);

  // Function to check if user has YouTube authorization
  const checkYoutubeAuth = async (token) => {
    try {
      const response = await apiClient.get('/youtube/check-auth/', {
        headers: {
          Authorization: `Token ${token}`,
        },
      });
      
      const data = response.data;
      
      setHasYoutubeAuth(data.has_youtube_auth || false);
    } catch (error) {
      console.error("Error checking YouTube auth:", error);
      setHasYoutubeAuth(false);
    }
  };

  useEffect(() => {
    const fetchMedia = async () => {
    
      try {
        // First check S3 uploaded versions (highest priority)
        if (results?.s3_upload?.url) {
          setDisplayVideo(results.s3_upload.url);
          
        }
        // Check for S3 links in specific processing results
        else if (results?.audio_processing?.s3_processed_file_path) {
          setDisplayVideo(results.audio_processing.s3_processed_file_path);
          
        }
        else if (results?.video_upscaling?.s3_processed_file_path) {
          setDisplayVideo(results.video_upscaling.s3_processed_file_path);
          
        }
        // Then check local processed files
        else if (results?.audio_processing?.processed_file_path) {
          const filename = results.audio_processing.processed_file_path.split("\\").pop();
          setDisplayVideo(`http://127.0.0.1:8000/media/processed/${filename}`);
          
        } 
        else if (results?.video_upscaling?.processed_file_path) {
          const filename = results.video_upscaling.processed_file_path.split("\\").pop();
          setDisplayVideo(`http://127.0.0.1:8000/media/processed/${filename}`);
          
        }
        // Finally check original local video
        else if (localVideoPath) {
          const filename = localVideoPath.split("\\").pop();
          setDisplayVideo(`http://127.0.0.1:8000/media/${filename}`);
          
        }
        // Last option: Fall back to YouTube thumbnail
        else {
          setDisplayVideo(null);
          if (videoURL) {
            try {
              const data = await fetchVideoMetadata(videoURL);
              if (data.thumbnail) {
                setThumbnail(data.thumbnail);
                
              }
            } catch (error) {
              console.error("Error fetching video metadata:", error);
            }
          }
        }
      } catch (error) {
        console.error("Error setting up video display:", error);
        setDisplayVideo(null);
      }
    };

    fetchMedia();
  }, [results, videoURL, localVideoPath]);

  const getVideoUrl = () => {
    // First check S3 uploaded versions (highest priority)
    if (results?.s3_upload?.url) {
      return results.s3_upload.url;
    }
    // Check for S3 links in specific processing results
    else if (results?.audio_processing?.s3_processed_file_path) {
      return results.audio_processing.s3_processed_file_path;
    }
    else if (results?.video_upscaling?.s3_processed_file_path) {
      return results.video_upscaling.s3_processed_file_path;
    }
    // Then check local processed files
    else if (results?.audio_processing?.processed_file_path) {
      const filename = results.audio_processing.processed_file_path.split("\\").pop();
      return `http://127.0.0.1:8000/media/processed/${filename}`;
    } 
    else if (results?.video_upscaling?.processed_file_path) {
      const filename = results.video_upscaling.processed_file_path.split("\\").pop();
      return `http://127.0.0.1:8000/media/processed/${filename}`;
    }
    // Check original local video
    else if (localVideoPath) {
      const filename = localVideoPath.split("\\").pop();
      return `http://127.0.0.1:8000/media/${filename}`;
    }
    
    return videoURL;
  };

  const handleAuthorizeYouTube = async () => {
    if (!authToken) {
      setUploadStatus({
        success: false,
        message: "Authentication token not found. Please log in again."
      });
      return;
    }
  
    setAuthorizing(true);
    setUploadStatus(null);
  
    try {
      const authResponse = await apiClient.get('/youtube/get-auth-url/', {
        headers: {
          Authorization: `Token ${authToken}`,
          "Content-Type": "application/json"
        }
      });
      
      if (!authResponse.data.auth_url) {
        throw new Error('No auth URL received from server');
      }
      
      // Open the authorization URL in a new window
      const authWindow = window.open(authResponse.data.auth_url, "YouTubeAuth", "width=600,height=700");
      
      // Add event listener for window closing
      let windowClosedManually = false;
      const windowClosedInterval = setInterval(() => {
        if (authWindow && authWindow.closed) {
          clearInterval(windowClosedInterval);
          windowClosedManually = true;
          
          // When window is manually closed, check auth status one more time
          setTimeout(async () => {
            try {
              const finalCheckResponse = await apiClient.get('/youtube/check-auth/', {
                headers: {
                  Authorization: `Token ${authToken}`,
                },
              });
              
              const finalCheckData = finalCheckResponse.data;
              
              if (finalCheckData.has_youtube_auth) {
                setHasYoutubeAuth(true);
                setUploadStatus({
                  success: true,
                  message: "YouTube account successfully connected!"
                });
              } else {
                setHasYoutubeAuth(false);
                setUploadStatus({
                  success: false,
                  message: "YouTube authorization was not completed. Please try again."
                });
              }
            } catch (error) {
              console.error("Error in final auth check:", error);
              setHasYoutubeAuth(false);
              setUploadStatus({
                success: false,
                message: "Failed to verify YouTube authorization. Please try again."
              });
            } finally {
              setAuthorizing(false);
            }
          }, 2000); // Wait 2 seconds after window closure before final check
        }
      }, 500);
      
      // Poll to check if auth is complete
      const checkAuthInterval = setInterval(async () => {
        try {
          if (windowClosedManually) {
            clearInterval(checkAuthInterval);
            return;
          }
          
          const checkResponse = await apiClient.get('/youtube/check-auth/', {
            headers: {
              Authorization: `Token ${authToken}`,
            },
          });
          
          const checkData = checkResponse.data;
          
          if (checkData.has_youtube_auth) {
            clearInterval(checkAuthInterval);
            clearInterval(windowClosedInterval);
            setHasYoutubeAuth(true);
            setUploadStatus({
              success: true,
              message: "YouTube account successfully connected!"
            });
            
            if (authWindow && !authWindow.closed) {
              authWindow.close();
            }
            setAuthorizing(false);
          }
        } catch (error) {
          console.error("Error checking auth status:", error);
        }
      }, 2000); // Check every 2 seconds
      
      // Cleanup interval after 5 minutes (maximum waiting time)
      setTimeout(() => {
        clearInterval(checkAuthInterval);
        clearInterval(windowClosedInterval);
        if (!windowClosedManually) {
          setUploadStatus({
            success: false,
            message: "Authorization timed out. Please try again."
          });
          setAuthorizing(false);
        }
      }, 300000); // 5 minutes
    } catch (error) {
      console.error("Authorization error:", error);
      setUploadStatus({
        success: false,
        message: `Failed to authorize: ${error.message}`
      });
      setAuthorizing(false);
    }
  };

  const handleUpdateSEO = async () => {
  console.log("Starting SEO update with videoURL:", videoURL);
  
  if (!user) {
    setUploadStatus({
      success: false,
      message: "You must be logged in to update YouTube SEO"
    });
    return;
  }

  if (!authToken) {
    setUploadStatus({
      success: false,
      message: "Authentication token not found. Please log in again."
    });
    return;
  }

  if (!hasYoutubeAuth) {
    setUploadStatus({
      success: false,
      message: "You need to connect your YouTube account first"
    });
    return;
  }

  // Check if we have a valid video URL
  if (!videoURL || (!videoURL.includes("youtube.com") && !videoURL.includes("youtu.be"))) {
    setUploadStatus({
      success: false,
      message: "This feature only works with YouTube videos"
    });
    return;
  }

  setUploading(true);
  setUploadStatus(null);

  try {
    // Extract video ID from URL - handle multiple YouTube URL formats
    let videoId = "";
    
    // Handle different YouTube URL formats
    if (videoURL.includes("youtube.com/watch?v=")) {
      videoId = videoURL.split("v=")[1].split("&")[0];
    } else if (videoURL.includes("youtu.be/")) {
      videoId = videoURL.split("youtu.be/")[1].split("?")[0].split("&")[0];
    } else if (videoURL.includes("youtube.com/embed/")) {
      videoId = videoURL.split("embed/")[1].split("?")[0].split("&")[0];
    } else if (videoURL.includes("youtube.com/v/")) {
      videoId = videoURL.split("v/")[1].split("?")[0].split("&")[0];
    } else {
      // Try to find video ID with regex as fallback
      const match = videoURL.match(/(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/);
      if (match) {
        videoId = match[1];
      }
    }

    if (!videoId || videoId.length !== 11) {
      throw new Error("Could not extract valid video ID from URL. Please check the YouTube URL format.");
    }

    console.log("Extracted video ID:", videoId);

    // ✅ FIXED: Send as JSON instead of FormData
    const requestData = {
      video_id: videoId,
      title: seoData.title || title,
      description: seoData.description || description,
      tags: seoData.tags 
        ? (Array.isArray(seoData.tags) ? seoData.tags.join(",") : seoData.tags)
        : ""
    };

    // Debug logs
    console.log("Request data:", requestData);

    // ✅ FIXED: Send as JSON with proper headers
    const updateResponse = await apiClient.post('/youtube/update-seo/', requestData, {
      headers: {
        Authorization: `Token ${authToken}`,
        'Content-Type': 'application/json',
      }
    });

    const data = updateResponse.data;

    if (data.success) {
      setUploadStatus({
        success: true,
        message: "Video SEO updated successfully!"
      });
      
      // After successful YouTube update, update component state
      setSeoMessage("SEO data updated successfully on YouTube!");
    } else {
      setUploadStatus({
        success: false,
        message: data.error || "Failed to update video SEO"
      });
    }
  } catch (error) {
    console.error("Update error:", error);
    
    // Handle specific error responses
    if (error.response) {
      const { status, data } = error.response;
      
      if (status === 403) {
        setUploadStatus({
          success: false,
          message: data.error || "You can only update SEO for videos you own"
        });
      } else if (status === 401 && data.needs_auth) {
        setHasYoutubeAuth(false);
        setUploadStatus({
          success: false,
          message: data.error || "Your YouTube authorization has expired. Please reconnect your YouTube account.",
          needsAuth: true
        });
      } else if (status === 404) {
        setUploadStatus({
          success: false,
          message: "Video not found or not accessible"
        });
      } else if (status === 400) {
        setUploadStatus({
          success: false,
          message: data.error || "Invalid request. Please check your video URL and try again."
        });
      } else {
        setUploadStatus({
          success: false,
          message: data.error || `Request failed with status ${status}`
        });
      }
    } else {
      // Network or other errors
      setUploadStatus({
        success: false,
        message: `An error occurred during update: ${error.message}`
      });
    }
  } finally {
    setUploading(false);
  }
};
  return (
    <div className="seo-app">
      {/* Navbar with User Session */}
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

      <main className="main-content">
       
        <div className="clip-section">
          
            
          

          <div className="customize-clip">
          <h3 className="seo-label">SEO Details</h3>
            <div className="seo-data">
            <div className="seo-box">
                <h2>Title</h2>
                <button className="copy-btn" onClick={() => handleCopy(title)}>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
                <p>{title}</p>
              </div>
              <div className="seo-box">
                <h2>Description</h2>
                <button className="copy-btn" onClick={() => handleCopy(description)}>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
                <div className="description-text">
                  {formatWithLineBreaks(description)}
                </div>
              </div>
              <div className="seo-box">
                <h2>Keywords</h2>
                <button className="copy-btn" onClick={() => handleCopy(keywords)}>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
                <p>{keywords}</p>
              </div>
              <div className="seo-box">
                <h2>Tags</h2>
                <button className="copy-btn" onClick={() => handleCopy(tags)}>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
                <p>{tags}</p>
              </div>
            </div>

            <div className="action-buttons">
                {/* Compare Results Button */}
                <button
                  className="comparison-btn-seo"
                  onClick={() =>
                  navigate("/comparison", {
                    state: {
                      results,
                      selectedFeatures,
                      videoURL,
                      localVideoPath,
                      s3Key: results.s3_upload?.key || null,
                      processedS3Url: getVideoUrl(),
                      seoData: {
                        ...seoData,
                        original_title: seoData.original_title || title,
                        original_description: seoData.original_description || description,
                        original_tags: seoData.original_tags || seoData.tags,
                        original_keywords: seoData.original_keywords || seoData.keywords,
                      },
                    },
                  })
                }
              >
                Compare Results
              </button>

              {/* YouTube Buttons */}
              {videoURL && (
                <>
                  {user && !hasYoutubeAuth ? (
                    <button 
                      className="youtube-auth-btn-seo"
                      onClick={handleAuthorizeYouTube}
                      disabled={authorizing}
                    >
                      {authorizing ? "Authorizing..." : "Connect YouTube"}
                    </button>
                  ) : (
                    <>
                      {isSeoOnly ? (
                        <button 
                          className={`youtube-update-seo-btn ${uploading ? 'uploading' : ''}`}
                          onClick={handleUpdateSEO}
                          disabled={uploading || !user || !hasYoutubeAuth}
                        >
                          {uploading ? "Updating..." : "Update YouTube SEO"}
                        </button>
                      ) : (
                        <button 
                          className={`youtube-upload-btn ${uploading ? 'uploading' : ''}`}
                          onClick={handleUploadToYouTube}
                          disabled={uploading || !user || !hasYoutubeAuth}
                          style={{
                            backgroundColor: '#8f3af5',
                            color: 'white',
                            border: 'none',
                            padding: '12px 24px',
                            marginTop: '20px',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontSize: '16px',
                            fontWeight: '600',
                            transition: 'all 0.3s ease',
                            boxShadow: '0 4px 8px rgba(0, 0, 0, 0.2)'
                          }}
                        >
                          {uploading ? "Uploading..." : "Upload to YouTube"}
                        </button>
                      )}
                    </>
                  )}
                </>
              )}
            </div>{uploadStatus && (
              <div className={`upload-status ${uploadStatus.success ? 'success' : 'error'}`}>
                <p>{uploadStatus.message}</p>
                {uploadStatus.success && uploadStatus.videoId && (
                  <a 
                    href={`https://www.youtube.com/watch?v=${uploadStatus.videoId}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="view-video-link"
                  >
                    View on YouTube
                  </a>
                )}
                {uploadStatus.needsAuth && (
                  <button
                    className="youtube-auth-btn-seo"
                    onClick={handleAuthorizeYouTube}
                    disabled={authorizing}
                  >
                    Connect YouTube Again
                  </button>
                )}
              </div>
            )}
          </div>
          </div>
      </main>
    </div>
  );
}

export default SEO;