import axios from 'axios';

// Create an Axios instance with default settings
export const apiClient = axios.create({
    baseURL: 'https://channel-iq.nzxtsol.com/api/', // Use local development URL
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true, // Enable credentials for token-based auth
});

// Add request interceptor to include auth token
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token'); // Changed from authToken to access_token
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

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

// Helper function to validate YouTube URL
const isValidYouTubeUrl = (url) => {
    const regex = /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|embed\/|v\/|shorts\/)|youtu\.be\/)[\w-]{11}/;
    return regex.test(url);
};

// Centralized error handling
const handleApiError = (error, action) => {
    if (error.response) {
        // Server responded with an error status code
        throw new Error(
            `Error ${action}: ${error.response.data?.error || error.response.statusText || "Server error occurred."}`
        );
    } else if (error.request) {
        // Request was made but no response received
        throw new Error(
            `Error ${action}: No response received from the server. Please check your network connection.`
        );
    } else {
        // Something else happened
        throw new Error(`Error ${action}: ${error.message || "An unexpected error occurred."}`);
    }
};
