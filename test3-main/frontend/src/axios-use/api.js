import axios from 'axios';

// Create an Axios instance with default settings
export const apiClient = axios.create({
    baseURL: 'https://channel-iq.nzxtsol.com/api/',
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true, // Enable credentials for token-based auth
    timeout: 300000000, // 30 second timeout
});

// Add request interceptor to include auth token and CSRF token
apiClient.interceptors.request.use(
    async (config) => {
        // Add authentication token
        const token = localStorage.getItem('token');
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }

        // Add CSRF token for POST, PUT, DELETE requests
        if (['post', 'put', 'delete', 'patch'].includes(config.method?.toLowerCase())) {
            const csrfToken = await getCSRFToken();
            if (csrfToken) {
                config.headers['X-CSRFToken'] = csrfToken;
            }
        }

        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Add response interceptor for better error handling
apiClient.interceptors.response.use(
    (response) => {
        return response;
    },
    async (error) => {
        // Handle different types of errors
        if (error.response) {
            // Server responded with error status
            console.error('API Response Error:', error.response.status, error.response.data);
            
            // Handle 401 Unauthorized errors
            if (error.response.status === 401) {
                // Clear local storage and redirect to login
                localStorage.removeItem('user');
                localStorage.removeItem('token');
                window.location.href = '/login';
            }
        } else if (error.request) {
            // Request was made but no response received
            console.error('API Request Error:', error.request);
        } else {
            // Something else happened
            console.error('API Error:', error.message);
        }
        return Promise.reject(error);
    }
);

// Function to get CSRF token
const getCSRFToken = async () => {
    try {
        const response = await axios.get('https://channel-iq.nzxtsol.com/api/csrf/', { 
            withCredentials: true,
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        return response.data.csrfToken;
    } catch (error) {
        console.error('CSRF Token Error:', error);
        return null;
    }
};

// Helper function to get cookie value
const getCookie = (name) => {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
};

// Fetch video metadata
export const fetchVideoMetadata = async (url) => {
    if (!isValidYouTubeUrl(url)) {
        throw new Error("Invalid YouTube URL provided. Please enter a valid YouTube link.");
    }

    try {
        const response = await apiClient.get('/fetch-video/', {
            params: { url },
        });
        return response.data;
    } catch (error) {
        handleApiError(error, 'fetching video metadata');
    }
};

// Download and upload video to S3
export const downloadAndUploadVideo = async (url) => {
    if (!isValidYouTubeUrl(url)) {
        throw new Error("Invalid YouTube URL provided. Please enter a valid YouTube link.");
    }

    try {
        const response = await apiClient.get('/download-video/', {
            params: { url },
        });
        return response.data;
    } catch (error) {
        throw error;
    }
};

// SEO processing function
export const processVideoSEO = async (data) => {
    try {
        const response = await apiClient.post('/seo/', data);
        return response.data;
    } catch (error) {
        handleApiError(error, 'processing video SEO');
    }
};

// Helper function to validate YouTube URL
const isValidYouTubeUrl = (url) => {
    const regex = /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|embed\/|v\/|shorts\/)|youtu\.be\/)[\w-]{11}/;
    return regex.test(url);
};

// Centralized error handling
const handleApiError = (error, action) => {
    if (error.response) {
        // Server responded with an error status code
        const errorMessage = error.response.data?.error || 
                           error.response.data?.message || 
                           error.response.statusText || 
                           "Server error occurred.";
        throw new Error(`Error ${action}: ${errorMessage}`);
    } else if (error.request) {
        // Request was made but no response received
        if (error.code === 'ERR_NETWORK') {
            throw new Error(`Error ${action}: Unable to connect to server. This could be due to CORS policy or network issues.`);
        }
        throw new Error(`Error ${action}: No response received from the server. Please check your network connection.`);
    } else {
        // Something else happened
        throw new Error(`Error ${action}: ${error.message || "An unexpected error occurred."}`);
    }
};