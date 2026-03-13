import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import { ElMessage } from 'element-plus'

/**
 * API基础配置
 */
const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000
})

/**
 * 请求拦截器
 */
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 可以在这里添加token等认证信息
    // const token = localStorage.getItem('token')
    // if (token && config.headers) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

/**
 * 响应拦截器
 */
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  (error: AxiosError) => {
    // 错误处理
    const responseData = error.response?.data as any
    const message = responseData?.error || error.message || '请求失败'
    ElMessage.error(message)

    // 可以根据不同的HTTP状态码进行不同的处理
    // if (error.response?.status === 401) {
    //   // 处理未授权
    // } else if (error.response?.status === 403) {
    //   // 处理禁止访问
    // } else if (error.response?.status === 404) {
    //   // 处理未找到
    // }

    return Promise.reject(error)
  }
)

/**
 * 通用GET请求
 * @param url 请求地址
 * @param config 请求配置
 * @returns Promise
 */
export function get<T = any>(url: string, config?: InternalAxiosRequestConfig): Promise<T> {
  return api.get(url, config)
}

/**
 * 通用POST请求
 * @param url 请求地址
 * @param data 请求数据
 * @param config 请求配置
 * @returns Promise
 */
export function post<T = any>(url: string, data?: any, config?: InternalAxiosRequestConfig): Promise<T> {
  return api.post(url, data, config)
}

/**
 * 通用PUT请求
 * @param url 请求地址
 * @param data 请求数据
 * @param config 请求配置
 * @returns Promise
 */
export function put<T = any>(url: string, data?: any, config?: InternalAxiosRequestConfig): Promise<T> {
  return api.put(url, data, config)
}

/**
 * 通用DELETE请求
 * @param url 请求地址
 * @param config 请求配置
 * @returns Promise
 */
export function del<T = any>(url: string, config?: InternalAxiosRequestConfig): Promise<T> {
  return api.delete(url, config)
}

/**
 * 通用PATCH请求
 * @param url 请求地址
 * @param data 请求数据
 * @param config 请求配置
 * @returns Promise
 */
export function patch<T = any>(url: string, data?: any, config?: InternalAxiosRequestConfig): Promise<T> {
  return api.patch(url, data, config)
}

export default api