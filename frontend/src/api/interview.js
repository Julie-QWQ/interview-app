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
  },

  // 流式发送消息
  chatStream(id, content, onChunk, onError, onComplete) {
    const token = localStorage.getItem('token')
    
    return fetch(`${api.defaults.baseURL}/interviews/${id}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      },
      body: JSON.stringify({ content })
    }).then(response => {
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      
      const read = () => {
        reader.read().then(({ done, value }) => {
          if (done) {
            onComplete && onComplete()
            return
          }
          
          const chunk = decoder.decode(value, { stream: true })
          const lines = chunk.split('\n')
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                
                if (data.error) {
                  onError && onError(data.error)
                  return
                }
                
                if (data.done) {
                  onComplete && onComplete(data)
                  return
                }
                
                if (data.content) {
                  onChunk && onChunk(data.content)
                }
              } catch (e) {
                console.error('解析SSE数据失败', e)
              }
            }
          }
          
          read()
        })
      }
      
      read()
    }).catch(error => {
      onError && onError(error.message)
    })
  }
}
