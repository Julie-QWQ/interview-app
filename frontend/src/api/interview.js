import api from './index'

export const interviewApi = {
  create(data) {
    return api.post('/interviews', data)
  },

  list(params) {
    return api.get('/interviews', { params })
  },

  getDetail(id) {
    return api.get(`/interviews/${id}`)
  },

  delete(id) {
    return api.delete(`/interviews/${id}`)
  },

  start(id) {
    return api.post(`/interviews/${id}/start`)
  },

  complete(id) {
    return api.post(`/interviews/${id}/complete`)
  },

  chat(id, content) {
    return api.post(`/interviews/${id}/chat`, { content })
  },

  getEvaluation(id) {
    return api.get(`/interviews/${id}/evaluation`)
  },

  exportHistory(id) {
    return api.get(`/interviews/${id}/history-export`)
  },

  getStagesConfig() {
    return api.get('/stages/config')
  },

  getProgress(id) {
    return api.get(`/interviews/${id}/progress`)
  },

  updateCurrentMessage(interviewId, messageId) {
    return api.put(`/interviews/${interviewId}/current-message`, { message_id: messageId })
  },

  // Prompt配置相关API
  getPromptConfig() {
    return api.get('/prompts/config')
  },

  updatePromptConfig(config) {
    return api.post('/prompts/config', config)
  },

  resetPromptConfig() {
    return api.post('/prompts/reset')
  },

  // 快照相关API
  createSnapshot(interviewId, data) {
    return api.post(`/interviews/${interviewId}/snapshots`, data)
  },

  listSnapshots(interviewId) {
    return api.get(`/interviews/${interviewId}/snapshots`)
  },

  getSnapshot(snapshotId) {
    return api.get(`/snapshots/${snapshotId}`)
  },

  loadSnapshot(snapshotId) {
    return api.post(`/snapshots/${snapshotId}/load`)
  },

  deleteSnapshot(snapshotId) {
    return api.delete(`/snapshots/${snapshotId}`)
  },

  chatStream(id, content, onChunk, onError, onComplete, options = {}) {
    // 使用相对路径,让 Vite 代理处理
    const url = `/api/interviews/${id}/chat/stream`

    // 支持传递 parent_id 和 branch_id
    const requestBody = {
      content,
      enable_tts: true // 默认启用 TTS
    }
    if (options.parentId !== undefined) {
      requestBody.parent_id = options.parentId
    }
    if (options.branchId !== undefined) {
      requestBody.branch_id = options.branchId
    }

    // 不返回 Promise，让回调处理所有事情
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    }).then(async response => {
      if (!response.ok) {
        onError && onError(`HTTP ${response.status}: ${response.statusText}`)
        return
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      try {
        while (true) {
          const { done, value } = await reader.read()

          if (done) {
            onComplete && onComplete()
            break
          }

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

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
                  // 传递内容,如果包含音频数据也一并传递
                  const audio = data.audio || null
                  onChunk && onChunk(data.content, audio)
                }
              } catch (e) {
                console.error('Failed to parse SSE', e, line)
              }
            }
          }
        }
      } catch (error) {
        onError && onError(error.message)
      }
    }).catch(error => {
      onError && onError(error.message)
    })
  }
}
