/**
 * 画像插件API服务
 */
import api from './index'

export const profileApi = {
  // 获取画像插件列表
  listPlugins(params) {
    return api.get('/profiles/plugins', { params })
  },

  // 创建自定义画像插件
  createPlugin(data) {
    return api.post('/profiles/plugins', data)
  },

  // 获取插件详情
  getPlugin(pluginId) {
    return api.get(`/profiles/plugins/${pluginId}`)
  },

  // 更新插件配置
  updatePlugin(pluginId, data) {
    return api.put(`/profiles/plugins/${pluginId}`, data)
  },

  // 删除自定义插件
  deletePlugin(pluginId) {
    return api.delete(`/profiles/plugins/${pluginId}`)
  },

  // 应用画像到面试
  applyToInterview(interviewId, data) {
    return api.post(`/profiles/interviews/${interviewId}/apply`, data)
  },

  // 获取面试的画像配置
  getInterviewProfile(interviewId) {
    return api.get(`/profiles/interviews/${interviewId}`)
  }
}
