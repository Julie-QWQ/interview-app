/**
 * 语音播放控制器
 * 管理音频播放队列、播放状态、静音控制
 */
export class VoiceController {
  constructor() {
    this.queue = [] // 音频播放队列
    this.isPlaying = false // 是否正在播放
    this.currentAudio = null // 当前播放的音频对象
    this.isMuted = false // 是否静音
    this.currentMessageId = null // 当前播放的消息ID
  }

  /**
   * 将音频加入播放队列
   * @param {string} audioBase64 - base64 编码的音频数据
   * @param {string} messageId - 消息ID
   */
  enqueue(audioBase64, messageId) {
    if (this.isMuted) {
      console.log('语音已静音,跳过播放')
      return
    }

    if (!audioBase64) {
      console.warn('音频数据为空,跳过播放')
      return
    }

    try {
      const audioSrc = `data:audio/mpeg;base64,${audioBase64}`
      const audio = new Audio(audioSrc)

      audio.onended = () => {
        console.log('音频播放完成')
        this.isPlaying = false
        this.currentMessageId = null
        this.playNext()
      }

      audio.onerror = (error) => {
        console.error('音频播放失败:', error)
        this.isPlaying = false
        this.currentMessageId = null
        this.playNext()
      }

      this.queue.push({ audio, messageId })
      console.log(`音频已加入队列,队列长度: ${this.queue.length}`)

      if (!this.isPlaying) {
        this.playNext()
      }
    } catch (error) {
      console.error('创建音频对象失败:', error)
    }
  }

  /**
   * 播放下一个音频
   */
  playNext() {
    if (this.queue.length === 0) {
      console.log('播放队列为空')
      return
    }

    const { audio, messageId } = this.queue.shift()
    this.currentAudio = audio
    this.currentMessageId = messageId
    this.isPlaying = true

    console.log(`开始播放音频,消息ID: ${messageId}`)
    audio.play().catch(error => {
      console.error('播放失败:', error)
      this.isPlaying = false
      this.playNext()
    })
  }

  /**
   * 停止当前播放并清空队列
   */
  stop() {
    console.log('停止音频播放')
    if (this.currentAudio) {
      this.currentAudio.pause()
      this.currentAudio = null
    }
    this.queue = []
    this.isPlaying = false
    this.currentMessageId = null
  }

  /**
   * 切换静音状态
   */
  toggleMute() {
    this.isMuted = !this.isMuted
    console.log(`静音状态: ${this.isMuted}`)
    if (this.isMuted) {
      this.stop()
    }
    return this.isMuted
  }

  /**
   * 设置静音状态
   * @param {boolean} muted - 是否静音
   */
  setMute(muted) {
    this.isMuted = muted
    if (this.isMuted) {
      this.stop()
    }
    return this.isMuted
  }

  /**
   * 暂停当前播放
   */
  pause() {
    if (this.currentAudio && this.isPlaying) {
      this.currentAudio.pause()
      this.isPlaying = false
      console.log('音频已暂停')
    }
  }

  /**
   * 恢复播放
   */
  resume() {
    if (this.currentAudio && !this.isPlaying && !this.isMuted) {
      this.currentAudio.play()
      this.isPlaying = true
      console.log('恢复音频播放')
    }
  }
}

// 导出全局单例
const voiceController = new VoiceController()
export default voiceController
