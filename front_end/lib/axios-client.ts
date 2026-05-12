import axios from 'axios';

export const api = axios.create({
  baseURL: typeof window !== 'undefined' ? '' : process.env.INTERNAL_API_BASE ?? '',
  timeout: 30_000,
});

api.interceptors.response.use(
  (res) => res,
  (err) => Promise.reject(err),
);
