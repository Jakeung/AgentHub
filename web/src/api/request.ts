import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
  withCredentials: true,
})

let isRedirecting = false

request.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data.code === 0) return data
    if (data.code === -2) {
      if (!isRedirecting) {
        isRedirecting = true
        window.location.href = '/login'
      }
      return Promise.reject(data)
    }
    ElMessage.error(data.message || '请求失败')
    return Promise.reject(data)
  },
  (error) => {
    if (!axios.isCancel(error)) {
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        ElMessage.error('请求超时，请稍后重试')
      } else if (error.response?.status === 502 || error.response?.status === 503) {
        ElMessage.error('服务暂时不可用')
      } else {
        ElMessage.error('网络错误')
      }
    }
    return Promise.reject(error)
  },
)

export default request
