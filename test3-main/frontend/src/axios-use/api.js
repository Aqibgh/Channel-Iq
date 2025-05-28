import axios from 'axios';

// Create Axios instance with combined auth
export const apiClient = axios.create({
    baseURL: 'https://channel-iq.nzxtsol.com/api/',
    headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
    },
    withCredentials: true, // Required for cookies
    xsrfCookieName: 'csrftoken',
    xsrfHeaderName: 'X-CSRFToken',
    timeout: 3000000000,
});

// CSRF token management
let csrfToken = null;
let isRefreshingCSRF = false;

// Request interceptor
apiClient.interceptors.request.use(
    async (config) => {
        // Add authorization token
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }

        // Handle CSRF for mutating methods
        if (['post', 'put', 'delete', 'patch'].includes(config.method?.toLowerCase())) {
            if (!csrfToken && !isRefreshingCSRF) {
                isRefreshingCSRF = true;
                try {
                    const response = await axios.get(
                        `${config.baseURL}csrf/`,
                        { withCredentials: true }
                    );
                    csrfToken = response.data.csrfToken;
                } catch (error) {
                    console.error('CSRF Token Fetch Failed:', error);
                } finally {
                    isRefreshingCSRF = false;
                }
            }
            config.headers['X-CSRFToken'] = csrfToken;
        }

        return config;
    },
    error => Promise.reject(error)
);

// Response interceptor
apiClient.interceptors.response.use(
    response => response,
    async (error) => {
        const originalRequest = error.config;
        
        // Handle CSRF token errors
        if (error.response?.status === 403 && error.response.data?.code === 'csrf_token_missing') {
            try {
                const response = await axios.get(
                    `${originalRequest.baseURL}csrf/`,
                    { withCredentials: true }
                );
                csrfToken = response.data.csrfToken;
                originalRequest.headers['X-CSRFToken'] = csrfToken;
                return apiClient(originalRequest);
            } catch (csrfError) {
                return Promise.reject(csrfError);
            }
        }

        // Handle 401 Unauthorized
        if (error.response?.status === 401) {
            localStorage.removeItem('user');
            localStorage.removeItem('token');
            window.location.href = '/login';
        }

        return Promise.reject(error);
    }
);

// Keep your existing functions exactly as they were
export const fetchVideoMetadata = async (url) => {
    if (!isValidYouTubeUrl(url)) {
        throw new Error("Invalid YouTube URL provided. Please enter a valid YouTube link.");
    }

    try {
        const response = await apiClient.get('/fetch-video/', { params: { url } });
        return response.data;
    } catch (error) {
        handleApiError(error, 'fetching video metadata');
    }
};

export const downloadAndUploadVideo = async (url) => {
    if (!isValidYouTubeUrl(url)) {
        throw new Error("Invalid YouTube URL provided. Please enter a valid YouTube link.");
    }

    try {
        const response = await apiClient.get('/download-video/', { params: { url } });
        return response.data;
    } catch (error) {
        throw error;
    }
};

export const processVideoSEO = async (data) => {
    try {
        const response = await apiClient.post('/seo/', data);
        return response.data;
    } catch (error) {
        handleApiError(error, 'processing video SEO');
    }
};

// Keep the rest of your helper functions unchanged
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