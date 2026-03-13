/**
 * 语音识别控制器
 * 使用 Web Speech API 实现语音转文字功能
 *
 * 浏览器支持:
 * - Chrome: ✅ 完整支持
 * - Edge: ✅ 完整支持
 * - Firefox: ❌ 不支持
 * - Safari: ❌ 不支持
 *
 * 注意: 需要 HTTPS 环境 (localhost 除外)
 */

interface SpeechRecognitionOptions {
  lang?: string
  continuous?: boolean
  interimResults?: boolean
}

// interface SpeechRecognitionCallbacks {
//   onResult: (transcript: string, isFinal: boolean) => void
//   onEnd?: () => void
//   onError?: (error: Error) => void
// }

// 扩展 Window 接口以支持 Web Speech API
declare global {
  interface Window {
    SpeechRecognition: any
    webkitSpeechRecognition: any
  }
}

export class SpeechRecognitionController {
  private supported: boolean
  private recognition: any
  private onResultCallback: ((transcript: string, isFinal: boolean) => void) | null = null
  private onErrorCallback: ((error: Error) => void) | null = null

  /**
   * @param options - 配置选项
   * @param options.lang - 语言代码 (默认: 'zh-CN')
   * @param options.continuous - 是否持续识别 (默认: false)
   * @param options.interimResults - 是否返回实时结果 (默认: true)
   */
  constructor(options: SpeechRecognitionOptions = {}) {
    // 检测浏览器支持
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition

    this.supported = !!SpeechRecognition

    if (!this.supported) {
      console.warn('当前浏览器不支持语音识别,请使用 Chrome 或 Edge 浏览器')
      return
    }

    // 创建识别实例
    this.recognition = new SpeechRecognition()

    // 配置识别参数
    this.recognition.lang = options.lang || 'zh-CN'
    // 设置 continuous=true 以便持续识别,直到手动停止
    this.recognition.continuous = true
    // 显示 interimResults 以便实时显示识别结果
    this.recognition.interimResults = true

    // 绑定事件
    this._bindEvents()

    console.log('语音识别控制器已初始化', {
      lang: this.recognition.lang,
      continuous: this.recognition.continuous,
      interimResults: this.recognition.interimResults
    })
  }

  /**
   * 绑定识别事件
   * @private
   */
  private _bindEvents(): void {
    this.recognition.onresult = (event: any) => {
      if (!this.onResultCallback) return

      // 获取最新结果
      const result = event.results[event.results.length - 1]
      const transcript = result[0].transcript
      const isFinal = result.isFinal

      console.log('语音识别结果:', { transcript, isFinal })

      this.onResultCallback(transcript, isFinal)
    }

    this.recognition.onend = () => {
      console.log('语音识别结束 (onend 事件)')
      // 如果正在监听状态,说明是非正常结束(如超时),尝试重启
      // 注意:这里不调用 onEndCallback,让外部手动处理
    }

    this.recognition.onerror = (event: any) => {
      console.error('语音识别错误:', event.error)

      let errorMessage = '语音识别错误'

      switch (event.error) {
        case 'no-speech':
          errorMessage = '未检测到语音,请重试'
          break
        case 'audio-capture':
          errorMessage = '未找到麦克风设备'
          break
        case 'not-allowed':
          errorMessage = '麦克风权限被拒绝,请在浏览器设置中允许访问'
          break
        case 'network':
          errorMessage = '网络错误,请检查网络连接'
          break
        case 'aborted':
          errorMessage = '语音识别已取消'
          break
        default:
          errorMessage = `语音识别失败: ${event.error}`
      }

      if (this.onErrorCallback) {
        this.onErrorCallback(new Error(errorMessage))
      }
    }
  }

  /**
   * 开始语音识别
   * @param onResult - 识别结果回调 (transcript, isFinal) => {}
   * @param onEnd - 识别结束回调 () => {}
   * @param onError - 错误回调 (error) => {}
   * @returns 是否成功启动
   */
  start(
    onResult: (transcript: string, isFinal: boolean) => void,
    _onEnd?: (() => void) | null,
    onError?: (error: Error) => void
  ): boolean {
    if (!this.supported) {
      if (onError) {
        onError(new Error('浏览器不支持语音识别'))
      }
      return false
    }

    // 设置回调
    this.onResultCallback = onResult
    this.onErrorCallback = onError || null

    try {
      // 每次启动前重新创建识别实例,避免复用导致的问题
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      this.recognition = new SpeechRecognition()
      this.recognition.lang = 'zh-CN'
      // 改为 false,更适合手动控制
      this.recognition.continuous = false
      this.recognition.interimResults = true

      // 重新绑定事件
      this._bindEvents()

      this.recognition.start()
      console.log('语音识别已启动')
      return true
    } catch (error: any) {
      console.error('启动语音识别失败:', error)

      // 如果是 "already started" 错误,先停止再启动
      if (error.message && error.message.includes('already started')) {
        try {
          this.recognition.stop()
          setTimeout(() => {
            this.recognition.start()
          }, 100)
          return true
        } catch (e) {
          if (onError) {
            onError(error)
          }
          return false
        }
      }

      if (onError) {
        onError(error)
      }
      return false
    }
  }

  /**
   * 停止语音识别
   */
  stop(): void {
    if (!this.supported || !this.recognition) return

    try {
      this.recognition.stop()
      console.log('语音识别已停止')
    } catch (error) {
      console.error('停止语音识别失败:', error)
    }
  }

  /**
   * 取消语音识别
   */
  abort(): void {
    if (!this.supported || !this.recognition) return

    try {
      this.recognition.abort()
      console.log('语音识别已取消')
    } catch (error) {
      console.error('取消语音识别失败:', error)
    }
  }

  /**
   * 设置识别语言
   * @param lang - 语言代码 (如: 'zh-CN', 'en-US')
   */
  setLanguage(lang: string): void {
    if (!this.supported) return

    this.recognition.lang = lang
    console.log('识别语言已设置为:', lang)
  }

  /**
   * 检查是否支持
   * @returns boolean
   */
  isSupported(): boolean {
    return this.supported
  }
}

/**
 * 创建语音识别控制器实例
 * @param options - 配置选项
 * @returns SpeechRecognitionController
 */
export function createSpeechRecognition(options?: SpeechRecognitionOptions): SpeechRecognitionController {
  return new SpeechRecognitionController(options)
}