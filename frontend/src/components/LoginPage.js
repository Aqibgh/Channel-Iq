import React, { useContext, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { signInWithPopup } from "firebase/auth";
import { auth, provider, db, firebaseConfigured } from "../Firebase";
import { arrayUnion, doc, setDoc, updateDoc } from "firebase/firestore";
import { UserContext } from "./UserContext";
import "./LoginPage.css";
import { apiClient } from '../axios-use/api';

const LoginPage = () => {
  const navigate = useNavigate();
  const { user, login } = useContext(UserContext);

  // Check if user is already logged in & navigate to home
  useEffect(() => {
    if (user) {
      navigate("/home");
    }
  }, [user, navigate]);

  const handleGoogleLogin = async () => {
    if (!firebaseConfigured) {
      alert("Google login is not configured for this demo. Add the Firebase values from frontend/.env.example.");
      return;
    }

    try {
      
      // 🔹 Step 1: Sign in with Firebase
      const result = await signInWithPopup(auth, provider);
      const user = result.user;
  
      // 🔹 Step 2: Get Firebase ID Token with retry logic
      let idToken;
      let retryCount = 0;
      const maxRetries = 3;
      
      while (retryCount < maxRetries) {
        try {
          // Add a small delay to ensure token is ready
          await new Promise(resolve => setTimeout(resolve, 1000));
          idToken = await user.getIdToken(true);
          break;
        } catch (tokenError) {
          console.error("❌ Token error:", tokenError);
          if (tokenError.message.includes('Token used too early')) {
            retryCount++;
            if (retryCount === maxRetries) {
              throw new Error('Token timing issue. Please check your system clock and try again.');
            }
            // Wait longer between retries
            await new Promise(resolve => setTimeout(resolve, 2000 * retryCount));
          } else {
            throw tokenError;
          }
        }
      }

      
  
      // 🔹 Step 3: Send Firebase Token and User ID to Django Backend
      
      
  
      const authResponse = await apiClient.post('auth/google-login/', {
        token: idToken,
        userId: user.uid
      });
  
  
      // Check if the response was successful
      if (!authResponse.data || !authResponse.data.access_token) {
        throw new Error("❌ Google login failed in Django Backend: Invalid response");
      }
  
  
      // 🔹 Step 4: Store JWT Tokens
      localStorage.setItem("access_token", authResponse.data.access_token);
      localStorage.setItem("refresh_token", authResponse.data.refresh_token);
  
      // 🔹 Step 5: Store User Data in Firebase Firestore
      const userRef = doc(db, "users", user.uid);
  
      // ✅ Store basic user details (merged with existing)
      await setDoc(
        userRef,
        {
          name: user.displayName,
          email: user.email,
          profilePicture: user.photoURL,
          uid: user.uid,
          lastLogin: new Date(),
        },
        { merge: true }
      );
  
      // 🔹 Step 6: Add login history
      const loginTime = new Date();
      await updateDoc(userRef, {
        loginHistory: arrayUnion({
          timestamp: loginTime,
          method: 'google',
          success: true
        })
      });
  
      // 🔹 Step 7: Update User Context with complete data
      const userData = {
        uid: user.uid,
        name: user.displayName,
        email: user.email,
        picture: user.photoURL,
        access_token: authResponse.data.access_token,
        refresh_token: authResponse.data.refresh_token,
        firebase_uid: user.uid
      };
  
      login(userData);
  
      // 🔹 Step 8: Navigate to Home
      navigate("/home");
  
    } catch (error) {
      console.error("❌ Login Error Details:");
      console.error("Error message:", error.message);
      console.error("Error response:", error.response?.data);
      console.error("Error status:", error.response?.status);
      console.error("Full error:", error);
      
      // Show more detailed error message
      let errorMessage = "An error occurred during login. Please try again.";
      if (error.response?.data?.error) {
        errorMessage = error.response.data.error;
        if (error.response.data.debug) {
          console.error("Debug info:", error.response.data.debug);
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      alert(errorMessage);
    }
  };

  return (
    <div className="login-page">
      <div className="login-wrapper">
        {/* Left side marketing content */}
        <div className="marketing-panel">
          
          <div className="marketing-content">
            <h1 className="main-title">
              Turn your long videos into <br /> <span className="highlight">VIRAL</span> short clips
            </h1>
            
            <div className="tag-badge">#1 AI VIDEO CLIPPING TOOL</div>
            
            <h2 className="trust-text">
              Trusted by <span className="highlight">50+</span> creators and businesses worldwide
            </h2>
            
            <div className="featurex-list">
              <div className="featurex-item">
                <div className="featurex-icon">✔</div>
                <span>AI SEO</span>
              </div>
              <div className="featurex-item">
                <div className="featurex-icon">✔</div>
                <span>Auto Caption</span>
              </div>
              <div className="featurex-item">
                <div className="featurex-icon">✔</div>
                <span>Auto Clipping</span>
              </div>
              <div className="featurex-item">
                <div className="featurex-icon">✔</div>
                <span>Quality Enhancer</span>
              </div>
              <div className="featurex-item">
                <div className="featurex-icon">✔</div>
                <span>Sound Improvement</span>
              </div>
            </div>
            
            
          </div>
        </div>

        {/* Right side login form */}
        <div className="login-panel">
          <div className="login-form">
            <h1 className="channel-iq-logo">
            Channel-<span className="highlight">IQ</span>
            </h1>
            <h3 className="login-title">
              Sign up to get viral clips
            </h3>
            <p className="login-subtitle">
              Free plan available. No credit card required.
            </p>

            <button className="google-signin-btn" onClick={handleGoogleLogin}>
              <svg className="google-icon" viewBox="0 0 48 48">
                <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"></path>
                <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"></path>
                <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"></path>
                <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"></path>
              </svg>
              Continue with Google
            </button>

            <div className="divider">
              <span>or</span>
            </div>

            <div className="terms-text">
              By continuing, you agree to <Link to="/terms" className="highlight">Channel-IQ's</Link> Terms of Service.
              <br />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
