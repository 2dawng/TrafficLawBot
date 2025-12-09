// API helper with automatic token refresh

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

console.log("API_BASE_URL:", API_BASE_URL);

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
    failedQueue.forEach((prom) => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(token);
        }
    });

    failedQueue = [];
};

const refreshAccessToken = async () => {
    const refreshToken = localStorage.getItem("refresh_token");

    if (!refreshToken) {
        throw new Error("No refresh token available");
    }

    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
        throw new Error("Failed to refresh token");
    }

    const data = await response.json();

    // Update tokens in localStorage
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);

    return data.access_token;
};

const apiRequest = async (url, options = {}) => {
    const token = localStorage.getItem("access_token");

    // Add authorization header if token exists
    const headers = {
        ...options.headers,
    };

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const config = {
        ...options,
        headers,
    };

    try {
        const response = await fetch(url, config);

        // If 401, try to refresh token
        if (response.status === 401) {
            if (isRefreshing) {
                // Wait for the token to be refreshed
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                })
                    .then((token) => {
                        headers["Authorization"] = `Bearer ${token}`;
                        return fetch(url, { ...config, headers });
                    })
                    .catch((err) => {
                        return Promise.reject(err);
                    });
            }

            isRefreshing = true;

            try {
                const newToken = await refreshAccessToken();
                isRefreshing = false;
                processQueue(null, newToken);

                // Retry the original request with new token
                headers["Authorization"] = `Bearer ${newToken}`;
                return fetch(url, { ...config, headers });
            } catch (refreshError) {
                isRefreshing = false;
                processQueue(refreshError, null);

                // Refresh failed, redirect to login
                localStorage.clear();
                window.location.href = "/";
                throw refreshError;
            }
        }

        return response;
    } catch (error) {
        throw error;
    }
};

// Export helper methods
export const api = {
    get: async (url, options = {}) => {
        const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
        const response = await apiRequest(fullUrl, { ...options, method: "GET" });
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            return response.json();
        }
        return response.text();
    },

    post: async (url, data, options = {}) => {
        const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
        const response = await apiRequest(fullUrl, {
            ...options,
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...options.headers,
            },
            body: JSON.stringify(data),
        });
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            return response.json();
        }
        return response.text();
    },

    put: async (url, data, options = {}) => {
        const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
        const response = await apiRequest(fullUrl, {
            ...options,
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                ...options.headers,
            },
            body: JSON.stringify(data),
        });
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            return response.json();
        }
        return response.text();
    },

    delete: async (url, options = {}) => {
        const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`;
        const response = await apiRequest(fullUrl, { ...options, method: "DELETE" });
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            return response.json();
        }
        return response.text();
    },
};

export default api;
