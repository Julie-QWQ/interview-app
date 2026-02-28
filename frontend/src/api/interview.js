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

  getStagesConfig() {
    return api.get('/stages/config')
  },

  getProgress(id) {
    return api.get(`/interviews/${id}/progress`)
  },

  chatStream(id, content, onChunk, onError, onComplete) {
    const isDev = import.meta.env.DEV
    const baseURL = isDev ? 'http://localhost:8000/api' : '/api'
    const url = `${baseURL}/interviews/${id}/chat/stream`

    // 不返回 Promise，让回调处理所有事情
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ content })
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
                  onChunk && onChunk(data.content)
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
