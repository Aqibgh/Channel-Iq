import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';  // Import the App component
import { checkCSRFToken } from './axios-use/api';  // Import the CSRF token check function

// Check CSRF token on app load
checkCSRFToken();

const root = ReactDOM.createRoot(document.getElementById('root'));

root.render(
  <App />  // Render the App component
);
