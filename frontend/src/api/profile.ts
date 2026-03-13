/**
 * 画像插件API服务
 */
import api from './index'
import type {
  ProfilePlugin,
  ProfileConfig,
  InterviewProfile
} from '@/types/api'

/**
 * 查询参数类型
 */
export interface ListPluginsParams {
  type?: 'position' | 'interviewer'
  is_system?: boolean
}

/**
 * 创建插件数据类型
 */
export interface CreatePluginRequest {
  plugin_id: string
  type: 'position' | 'interviewer'
  name: string
  description?: string
  config: ProfileConfig
}

/**
 * 更新插件数据类型
 */
export interface UpdatePluginRequest {
  name: string
  description?: string
  config: ProfileConfig
}

/**
 * 应用画像到面试数据类型
 */
export interface ApplyProfileRequest {
  position_plugin_id?: string
  interviewer_plugin_id?: string
  custom_config?: Record<string, any>
}

/**
 * 面试画像响应类型
 */
export interface InterviewProfileResponse {
  id: number
  interview_id: number
  position_plugin_id: string | null
  interviewer_plugin_id: string | null
  custom_config: Record<string, any> | null
  position_plugin?: ProfilePlugin
  interviewer_plugin?: ProfilePlugin
  created_at: string
  updated_at: string
}

/**
 * 画像插件API接口
 */
export const profileApi = {
  /**
   * 获取画像插件列表
   * @param params 查询参数
   * @returns 画像插件列表
   */
  listPlugins(params?: ListPluginsParams): Promise<ProfilePlugin[]> {
    return api.get('/profiles/plugins', { params })
  },

  /**
   * 创建自定义画像插件
   * @param data 插件数据
   * @returns 创建的插件
   */
  createPlugin(data: CreatePluginRequest): Promise<ProfilePlugin> {
    return api.post('/profiles/plugins', data)
  },

  /**
   * 获取插件详情
   * @param pluginId 插件ID
   * @returns 插件详情
   */
  getPlugin(pluginId: string): Promise<ProfilePlugin> {
    return api.get(`/profiles/plugins/${pluginId}`)
  },

  /**
   * 更新插件配置
   * @param pluginId 插件ID
   * @param data 更新数据
   * @returns 更新后的插件
   */
  updatePlugin(pluginId: string, data: UpdatePluginRequest): Promise<ProfilePlugin> {
    return api.put(`/profiles/plugins/${pluginId}`, data)
  },

  /**
   * 删除自定义插件
   * @param pluginId 插件ID
   * @returns 删除结果
   */
  deletePlugin(pluginId: string): Promise<void> {
    return api.delete(`/profiles/plugins/${pluginId}`)
  },

  /**
   * 应用画像到面试
   * @param interviewId 面试ID
   * @param data 画像数据
   * @returns 应用结果
   */
  applyToInterview(interviewId: number, data: ApplyProfileRequest): Promise<InterviewProfile> {
    return api.post(`/profiles/interviews/${interviewId}/apply`, data)
  },

  /**
   * 获取面试的画像配置
   * @param interviewId 面试ID
   * @returns 面试画像配置
   */
  getInterviewProfile(interviewId: number): Promise<InterviewProfileResponse> {
    return api.get(`/profiles/interviews/${interviewId}`)
  }
}

export default profileApi