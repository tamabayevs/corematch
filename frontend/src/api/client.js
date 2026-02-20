import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace(/\/+$/, "")}/api`
  : "/api";

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Lazy accessor to break circular dependency: client → authStore → auth → client
// The import resolves after all modules are initialized.
let _authStoreModule = null;
function getAuthStore() {
  if (!_authStoreModule) {
    _authStoreModule = import("../store/authStore");
  }
  return _authStoreModule;
}

// Attach JWT access token to every request
api.interceptors.request.use(async (config) => {
  // Read XSRF-TOKEN cookie for CSRF protection
  const xsrfToken = document.cookie
    .split("; ")
    .find((row) => row.startsWith("XSRF-TOKEN="))
    ?.split("=")[1];
  if (xsrfToken) {
    config.headers["X-XSRF-Token"] = decodeURIComponent(xsrfToken);
  }

  // Attach access token from auth store
  const { useAuthStore } = await getAuthStore();
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// Auto-refresh on 401 and retry the original request
let isRefreshing = false;
let failedQueue = [];

function processQueue(error, token = null) {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Don't retry refresh, login, or signup endpoints
    const skipPaths = ["/auth/refresh", "/auth/login", "/auth/signup"];
    if (
      error.response?.status !== 401 ||
      originalRequest._retry ||
      skipPaths.some((p) => originalRequest.url?.includes(p))
    ) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const { useAuthStore } = await getAuthStore();
      const newToken = await useAuthStore.getState().refresh();
      processQueue(null, newToken);
      originalRequest.headers.Authorization = `Bearer ${newToken}`;
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      const { useAuthStore } = await getAuthStore();
      useAuthStore.getState().logout();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default api;
