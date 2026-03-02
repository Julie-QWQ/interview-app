/**
 * ASR 录音控制器
 * 使用浏览器录音 API + 后端 ASR 服务
 */

export class ASRRecorder {
  constructor() {
    this.supported = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
    this.mediaRecorder = null
    this.audioChunks = []
    this.isRecording = false
  }

  /**
   * 检查浏览器支持
   */
  checkSupport() {
    if (!this.supported) {
      throw new Error('浏览器不支持录音功能')
    }
    return true
  }

  /**
   * 请求麦克风权限并开始录音
   * @param {Function} onData - 录音数据回调 (可选,用于实时处理)
   * @returns {Promise<MediaStream>}
   */
  async startRecording(onData = null) {
    this.checkSupport()

    if (this.isRecording) {
      return null
    }

    try {
      // 请求麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      // 创建 MediaRecorder
      const options = {}
      if (MediaRecorder.isTypeSupported('audio/webm')) {
        options.mimeType = 'audio/webm'
      } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
        options.mimeType = 'audio/mp4'
      } else if (MediaRecorder.isTypeSupported('audio/wav')) {
        options.mimeType = 'audio/wav'
      }

      this.mediaRecorder = new MediaRecorder(stream, options)
      this.audioChunks = []

      // 监听数据可用事件
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data)
          if (onData) {
            onData(event.data)
          }
        }
      }

      // 监听录音停止事件
      this.mediaRecorder.onstop = () => {
        // 停止所有音频轨道
        stream.getTracks().forEach(track => track.stop())
      }

      // 开始录音
      this.mediaRecorder.start(100) // 每100ms触发一次 ondataavailable
      this.isRecording = true

      return stream

    } catch (error) {
      throw error
    }
  }

  /**
   * 停止录音并返回音频 Blob
   * @returns {Promise<Blob>}
   */
  async stopRecording() {
    if (!this.isRecording || !this.mediaRecorder) {
      return null
    }

    return new Promise((resolve) => {
      this.mediaRecorder.onstop = () => {
        const mimeType = this.mediaRecorder.mimeType || 'audio/webm'
        const blob = new Blob(this.audioChunks, { type: mimeType })
        this.isRecording = false
        resolve(blob)
      }

      this.mediaRecorder.stop()
    })
  }

  /**
   * 取消录音
   */
  cancelRecording() {
    if (this.isRecording && this.mediaRecorder) {
      this.mediaRecorder.onstop = null
      this.mediaRecorder.stop()
      this.isRecording = false
      this.audioChunks = []
    }
  }

  /**
   * 获取录音状态
   */
  getStatus() {
    return {
      isRecording: this.isRecording,
      supported: this.supported
    }
  }
}

/**
 * 调用后端 ASR API 进行语音识别
 * @param {Blob} audioBlob - 音频 Blob
 * @returns {Promise<string>} 识别文本
 */
export async function transcribeAudio(audioBlob) {
  // 使用相对路径,让 Vite 代理处理
  const url = '/api/asr/transcribe'

  // 创建 FormData
  const formData = new FormData()
  formData.append('audio', audioBlob, 'audio.webm')

  try {
    const response = await fetch(url, {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || `HTTP ${response.status}`)
    }

    const data = await response.json()
    return data.text

  } catch (error) {
    console.error('ASR API 调用失败:', error)
    throw error
  }
}

/**
 * 检查 ASR 服务状态
 * @returns {Promise<Object>}
 */
export async function checkASRStatus() {
  // 使用相对路径,让 Vite 代理处理
  const url = '/api/asr/status'

  try {
    const response = await fetch(url)
    const data = await response.json()
    return data
  } catch (error) {
    console.error('检查 ASR 状态失败:', error)
    return {
      available: false,
      error: error.message
    }
  }
}
