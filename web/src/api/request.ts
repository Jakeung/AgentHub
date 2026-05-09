import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
  withCredentials: true,
})

request.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data.code === 0) return data
    if (data.code === -2) {
      // Not logged in — redirect handled by router guard
      window.location.href = '/login'
      return Promise.reject(data)
    }
    ElMessage.error(data.message || '请求失败')
    return Promise.reject(data)
  },
  (error) => {
    ElMessage.error('网络错误')
    return Promise.reject(error)
  },
)

export default request
