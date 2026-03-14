import api from './index'
import type {
  Interview,
  CreateInterviewRequest,
  InterviewResponse,
  Message,
  MessageResponse,
  ListParams,
  Snapshot,
  SnapshotData,
  ExpressionReport,
  PromptConfig,
  StreamEvent,
  StreamOptions,
  DigitalHumanSession
} from '@/types/api'

/**
 * 面试相关API接口
 */
export const interviewApi = {
  /**
   * 创建面试
   * @param data 面试创建数据
   * @returns 创建的面试信息
   */
  create(data: CreateInterviewRequest): Promise<Interview> {
    return api.post('/interviews', data)
  },

  /**
   * 获取面试列表
   * @param params 查询参数
   * @returns 面试列表
   */
  list(params?: ListParams): Promise<Interview[]> {
    return api.get('/interviews', { params })
  },

  /**
   * 获取面试详情
   * @param id 面试ID
   * @returns 面试详情
   */
  getDetail(id: number): Promise<InterviewResponse> {
    return api.get(`/interviews/${id}`)
  },

  /**
   * 删除面试
   * @param id 面试ID
   * @returns 删除结果
   */
  delete(id: number): Promise<void> {
    return api.delete(`/interviews/${id}`)
  },

  /**
   * 开始面试
   * @param id 面试ID
   * @returns 开始面试的结果
   */
  start(id: number): Promise<{
    welcome_message: string
    welcome_video?: string
    welcome_avatar_segments?: any[]
    welcome_avatar_error?: string
    current_stage: string
  }> {
    return api.post(`/interviews/${id}/start`)
  },

  /**
   * 创建数字人会话
   * @param id 面试ID
   * @returns 数字人会话信息
   */
  createAvatarSession(id: number): Promise<DigitalHumanSession> {
    return api.post(`/interviews/${id}/avatar-session`)
  },

  /**
   * 完成面试
   * @param id 面试ID
   * @returns 完成面试的结果
   */
  complete(id: number): Promise<{
    report: {
      overall_score: number
      dimension_scores: Record<string, number>
      strengths: string[]
      improvements: string[]
      recommendation: string
    }
  }> {
    return api.post(`/interviews/${id}/complete`, {}, { timeout: 60000 }) // 增加到60秒
  },

  /**
   * 发送聊天消息
   * @param id 面试ID
   * @param content 消息内容
   * @returns AI回复
   */
  chat(id: number, content: string): Promise<MessageResponse> {
    return api.post(`/interviews/${id}/chat`, { content })
  },

  /**
   * 导出面试历史
   * @param id 面试ID
   * @returns 导出的历史记录
   */
  exportHistory(id: number): Promise<{
    messages: Message[]
    interview: Interview
    export_time: string
  }> {
    return api.get(`/interviews/${id}/history-export`)
  },

  /**
   * 获取阶段配置
   * @returns 阶段配置
   */
  getStagesConfig(): Promise<{
    stages: Record<string, {
      name: string
      duration_minutes: number
      focus_areas: string[]
    }>
  }> {
    return api.get('/stages/config')
  },

  /**
   * 获取面试进度
   * @param id 面试ID
   * @returns 当前进度信息
   */
  getProgress(id: number): Promise<{
    current_stage: string
    progress: number
    time_spent: number
    time_remaining: number
  }> {
    return api.get(`/interviews/${id}/progress`)
  },

  /**
   * 更新当前消息节点
   * @param interviewId 面试ID
   * @param messageId 消息ID
   * @returns 更新结果
   */
  updateCurrentMessage(interviewId: number, messageId: number): Promise<void> {
    return api.put(`/interviews/${interviewId}/current-message`, { message_id: messageId })
  },

  // ==================== Prompt配置相关API ====================

  /**
   * 获取Prompt配置
   * @returns Prompt配置
   */
  getPromptConfig(): Promise<PromptConfig> {
    return api.get('/prompts/config')
  },

  /**
   * 更新Prompt配置
   * @param config 配置数据
   * @returns 更新后的配置
   */
  updatePromptConfig(config: any): Promise<PromptConfig> {
    return api.post('/prompts/config', config)
  },

  /**
   * 重置Prompt配置
   * @returns 重置后的配置
   */
  resetPromptConfig(): Promise<PromptConfig> {
    return api.post('/prompts/reset')
  },

  // ==================== 语音配置相关API ====================

  /**
   * 获取语音配置
   * @returns 语音配置
   */
  getVoiceConfig(): Promise<{
    enabled: boolean
    config: Record<string, any>
  }> {
    return api.get('/voice/config')
  },

  /**
   * 更新语音配置
   * @param config 配置数据
   * @returns 更新后的配置
   */
  updateVoiceConfig(config: Record<string, any>): Promise<void> {
    return api.post('/voice/config', config)
  },

  /**
   * 重置语音配置
   * @returns 重置后的配置
   */
  resetVoiceConfig(): Promise<void> {
    return api.post('/voice/config/reset')
  },

  // ==================== 表情分析相关API ====================

  /**
   * 获取表情分析配置
   * @returns 表情分析配置
   */
  getExpressionConfig(): Promise<{
    enabled: boolean
    config: Record<string, any>
  }> {
    return api.get('/expression/config')
  },

  /**
   * 上传表情分析音频段
   * @param interviewId 面试ID
   * @param payload 音频段数据
   * @returns 上传结果
   */
  uploadExpressionAudioSegment(interviewId: number, payload: {
    segment_index: number
    audio_data: string
    started_at: string
    ended_at: string
    metadata?: Record<string, any>
  }): Promise<void> {
    return api.post(`/interviews/${interviewId}/expression/audio-segments`, payload)
  },

  /**
   * 上传表情分析视频窗口
   * @param interviewId 面试ID
   * @param payload 视频窗口数据
   * @returns 上传结果
   */
  uploadExpressionVideoWindow(interviewId: number, payload: {
    window_index: number
    video_data: string
    started_at: string
    ended_at: string
    metadata?: Record<string, any>
  }): Promise<void> {
    return api.post(`/interviews/${interviewId}/expression/video-windows`, payload)
  },

  /**
   * 完成表情分析
   * @param interviewId 面试ID
   * @returns 完成后的报告
   */
  finalizeExpression(interviewId: number): Promise<ExpressionReport> {
    return api.post(`/interviews/${interviewId}/expression/finalize`)
  },

  /**
   * 获取表情分析报告
   * @param interviewId 面试ID
   * @returns 表情分析报告
   */
  getExpressionReport(interviewId: number): Promise<ExpressionReport> {
    return api.get(`/interviews/${interviewId}/expression-report`)
  },

  // ==================== 快照相关API ====================

  /**
   * 创建快照
   * @param interviewId 面试ID
   * @param data 快照数据
   * @returns 创建的快照
   */
  createSnapshot(interviewId: number, data: {
    name: string
    description?: string
  }): Promise<Snapshot> {
    return api.post(`/interviews/${interviewId}/snapshots`, data)
  },

  /**
   * 获取快照列表
   * @param interviewId 面试ID
   * @returns 快照列表
   */
  listSnapshots(interviewId: number): Promise<Snapshot[]> {
    return api.get(`/interviews/${interviewId}/snapshots`)
  },

  /**
   * 获取快照详情
   * @param snapshotId 快照ID
   * @returns 快照详情
   */
  getSnapshot(snapshotId: number): Promise<Snapshot> {
    return api.get(`/snapshots/${snapshotId}`)
  },

  /**
   * 加载快照
   * @param snapshotId 快照ID
   * @returns 快照数据
   */
  loadSnapshot(snapshotId: number): Promise<SnapshotData> {
    return api.post(`/snapshots/${snapshotId}/load`)
  },

  /**
   * 删除快照
   * @param snapshotId 快照ID
   * @returns 删除结果
   */
  deleteSnapshot(snapshotId: number): Promise<void> {
    return api.delete(`/snapshots/${snapshotId}`)
  },

  /**
   * 流式聊天
   * @param id 面试ID
   * @param content 消息内容
   * @param onChunk 文本块回调
   * @param onError 错误回调
   * @param onComplete 完成回调
   * @param options 流式选项
   */
  chatStream(
    id: number,
    content: string,
    onChunk: (chunk: string, audio: any, event: StreamEvent) => void,
    onError: (error: string) => void,
    onComplete: (finalData: any) => void,
    options: StreamOptions = {}
  ): void {
    // 使用相对路径,让 Vite 代理处理
    const url = `/api/interviews/${id}/chat/stream`

    // 支持传递 parent_id 和 branch_id
    const requestBody: Record<string, any> = {
      content,
      enable_tts: false
    }

    if (options.source !== undefined) {
      requestBody.source = options.source
    }
    if (options.parentId !== undefined) {
      requestBody.parent_id = options.parentId
    }
    if (options.branchId !== undefined) {
      requestBody.branch_id = options.branchId
    }

    // 使用fetch API进行流式请求
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

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      try {
        while (true) {
          const { done, value } = await reader.read()

          if (done) {
            onComplete && onComplete(undefined)
            break
          }

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data: StreamEvent = JSON.parse(line.slice(6))

                if (data.error) {
                  onError && onError(data.error)
                  return
                }

                if (data.done) {
                  onComplete && onComplete(data)
                  return
                }

                const audio = data.audio || null
                const chunk = data.type === 'text_chunk' ? (data.content || '') : ''
                onChunk && onChunk(chunk, audio, data)
              } catch (e) {
                console.error('Failed to parse SSE', e, line)
              }
            }
          }
        }
      } catch (error) {
        onError && onError((error as Error).message)
      }
    }).catch(error => {
      onError && onError((error as Error).message)
    })
  }
}

export default interviewApi