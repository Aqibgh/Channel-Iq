import axios from 'axios';

// Configure Axios instance
const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api/',
  withCredentials: true, // Required for cookies
  headers: {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest'
  },
  timeout: 3000000000000,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken'
});

// CSRF token management
let csrfToken = null;

const getCSRFTokenFromCookie = () => {
  try {
    return document.cookie
      .split('; ')
      .find(row => row.startsWith('csrftoken='))
      ?.split('=')[1] || null;
  } catch (error) {
    console.error('Error reading CSRF cookie:', error);
    return null;
  }
};

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add JWT token if available
    const authToken = localStorage.getItem('token');
    if (authToken) {
      config.headers.Authorization = `Bearer ${authToken}`;
    }

    // Handle CSRF for mutating methods
    if (['post', 'put', 'delete', 'patch'].includes(config.method?.toLowerCase())) {
      csrfToken = getCSRFTokenFromCookie();
      if (csrfToken) {
        config.headers['X-CSRFToken'] = csrfToken;
      }
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('user');
      localStorage.removeItem('token');
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

// Your existing API functions
const fetchVideoMetadata = async (url) => {
  if (!isValidYouTubeUrl(url)) {
    throw new Error("Invalid YouTube URL provided");
  }
  try {
    const response = await apiClient.get('/fetch-video/', { params: { url } });
    return response.data;
  } catch (error) {
    handleApiError(error, 'fetching video metadata');
  }
};

const downloadAndUploadVideo = async (url) => {
  if (!isValidYouTubeUrl(url)) {
    throw new Error("Invalid YouTube URL provided");
  }
  try {
    const response = await apiClient.get('/download-video/', { params: { url } });
    return response.data;
  } catch (error) {
    handleApiError(error, 'downloading video');
  }
};

const processVideoSEO = async (data) => {
  try {
    const response = await apiClient.post('/seo/', data);
    return response.data;
  } catch (error) {
    handleApiError(error, 'processing SEO data');
  }
};

// Helper functions
const isValidYouTubeUrl = (url) => {
  const pattern = /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|embed\/|v\/|shorts\/)|youtu\.be\/)[\w-]{11}/;
  return pattern.test(url);
};

const handleApiError = (error, action) => {
  const errorObj = error.response?.data || {};
  const message = errorObj.message || `Error ${action}: ${error.message}`;
  
  if (error.response?.status === 429) {
    throw new Error('Too many requests. Please try again later.');
  }
  
  throw new Error(message);
};

const checkCSRFToken = () => {
  const token = getCSRFTokenFromCookie();
  if (!token) {
    console.warn('Initial CSRF token not found in cookies');
  }
  return token;
};

// Export everything needed
export {
  apiClient, // Now explicitly exported
  fetchVideoMetadata,
  downloadAndUploadVideo,
  processVideoSEO,
  checkCSRFToken
};
