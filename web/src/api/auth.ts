import axios from 'axios'

// Auth API uses raw axios to handle login/register responses manually
const rawRequest = axios.create({
  baseURL: '/api',
  timeout: 30000,
  withCredentials: true,
})

export const authApi = {
  login: (data: { username: string; password: string }) =>
    rawRequest.post('/auth/login', data).then((r) => r.data),

  register: (data: { username: string; password: string; email?: string }) =>
    rawRequest.post('/auth/register', data).then((r) => r.data),

  logout: () =>
    rawRequest.post('/auth/logout').then((r) => r.data),

  me: () =>
    rawRequest.get('/auth/me').then((r) => r.data),
}
