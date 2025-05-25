import React, { createContext, useState, useEffect } from "react";


// Create User Context
export const UserContext = createContext();

// User Provider Component
export const UserProvider = ({ children }) => {
  const [user, setUser] = useState(undefined);  // `undefined` to show loading state

  // Load user from localStorage when the app loads
  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    const storedToken = localStorage.getItem("token");
  
    if (storedUser && storedToken) {
      setUser(JSON.parse(storedUser));
    } else {
      setUser(null);
    }
  }, []);
  
  // Login function to set user & store token
  const login = (userData) => {
    if (!userData) {
      console.error("❌ Error: Missing userData in login function");
      return;
    }

    // Ensure we have the required data
    const formattedUser = {
      uid: userData.id || userData.uid || userData.firebase_uid,
      name: userData.name,
      email: userData.email,
      picture: userData.picture,
      access_token: userData.access_token,
      refresh_token: userData.refresh_token
    };

    // Validate required fields
    if (!formattedUser.uid || !formattedUser.access_token) {
      console.error("❌ Error: Missing required user data (uid or token)");
      return;
    }

    // Update state and localStorage
    setUser(formattedUser);
    localStorage.setItem("user", JSON.stringify(formattedUser));
    localStorage.setItem("token", formattedUser.access_token);
  };

  // Logout function to clear session
  const logout = () => {
    setUser(null);
    localStorage.removeItem("user");
    localStorage.removeItem("token");
  };

  return (
    <UserContext.Provider value={{ user, login, logout }}>
      {user === undefined ? null : children} {/* 🚀 Wait for user state to load */}
    </UserContext.Provider>
  );



 
};
