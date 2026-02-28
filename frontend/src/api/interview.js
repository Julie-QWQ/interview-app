import api from './index'

export const interviewApi = {
  // 创建面试
  create(data) {
    return api.post('/interviews', data)
  },

  // 获取面试列表
  list(params) {
    return api.get('/interviews', { params })
  },

  // 获取面试详情
  getDetail(id) {
    return api.get(`/interviews/${id}`)
  },

  // 删除面试
  delete(id) {
    return api.delete(`/interviews/${id}`)
  },

  // 开始面试
  start(id) {
    return api.post(`/interviews/${id}/start`)
  },

  // 完成面试
  complete(id) {
    return api.post(`/interviews/${id}/complete`)
  },

  // 发送消息
  chat(id, content) {
    return api.post(`/interviews/${id}/chat`, { content })
  },

  // 获取评估
  getEvaluation(id) {
    return api.get(`/interviews/${id}/evaluation`)
  },

  // 获取阶段配置
  getStagesConfig() {
    return api.get('/stages/config')
  },

  // 获取面试进度
  getProgress(id) {
    return api.get(`/interviews/${id}/progress`)
  }
}
