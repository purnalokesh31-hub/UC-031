// Shared axios instance — reuses the same connection pool,
// adds base URL and default timeouts once, avoids repeated config.
import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: 10000,
  headers: { "Content-Type": "application/json" },
});

// Convenience: check if an error is a cancellation (not a real failure)
export const isCancel = axios.isCancel;
