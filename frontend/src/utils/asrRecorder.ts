/**
 * ASR 录音控制器
 * 使用浏览器录音 API + 后端 ASR 服务
 */

interface ASRDebugPayload {
  [key: string]: any
}

interface ResponsePayload {
  rawText: string
  data: any | null
}

interface ASRMetadata {
  [key: string]: any | undefined
}

interface AudioNormalizationResult {
  blob: Blob
  filename: string
}

interface ASRStatus {
  available: boolean
  error?: string
  [key: string]: any
}

interface TranscribeResult {
  text?: string
  [key: string]: any
}

function asrDebug(label: string, payload?: ASRDebugPayload): void {
  void label
  void payload
}

async function readResponsePayload(response: Response): Promise<ResponsePayload> {
  const rawText = await response.text()
  if (!rawText) {
    return {
      rawText: '',
      data: null
    }
  }

  try {
    return {
      rawText,
      data: JSON.parse(rawText)
    }
  } catch {
    return {
      rawText,
      data: null
    }
  }
}

export class ASRRecorder {
  private supported: boolean
  private mediaRecorder: MediaRecorder | null = null
  private audioChunks: Blob[] = []
  private isRecording: boolean = false

  constructor() {
    this.supported = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
  }

  /**
   * 检查浏览器支持
   */
  checkSupport(): boolean {
    if (!this.supported) {
      throw new Error('浏览器不支持录音功能')
    }
    return true
  }

  /**
   * 请求麦克风权限并开始录音
   * @param onData - 录音数据回调
   * @returns Promise<MediaStream>
   */
  async startRecording(onData?: (blob: Blob) => void): Promise<MediaStream | null> {
    this.checkSupport()

    if (this.isRecording) {
      return null
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    asrDebug('startRecording: microphone stream acquired')

    const options: MediaRecorderOptions = {}
    if (MediaRecorder.isTypeSupported('audio/webm')) {
      options.mimeType = 'audio/webm'
    } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
      options.mimeType = 'audio/mp4'
    } else if (MediaRecorder.isTypeSupported('audio/wav')) {
      options.mimeType = 'audio/wav'
    }

    this.mediaRecorder = new MediaRecorder(stream, options)
    asrDebug('startRecording: MediaRecorder created', {
      mimeType: this.mediaRecorder.mimeType || options.mimeType || 'default'
    })
    this.audioChunks = []

    this.mediaRecorder.ondataavailable = (event: BlobEvent) => {
      if (event.data.size > 0) {
        this.audioChunks.push(event.data)
        asrDebug('startRecording: chunk captured', {
          size: event.data.size,
          mimeType: event.data.type,
          totalChunks: this.audioChunks.length
        })
        if (onData) {
          onData(event.data)
        }
      }
    }

    this.mediaRecorder.onstop = () => {
      stream.getTracks().forEach(track => track.stop())
    }

    this.mediaRecorder.start(100)
    this.isRecording = true

    return stream
  }

  /**
   * 停止录音并返回音频 Blob
   * @returns Promise<Blob>
   */
  async stopRecording(): Promise<Blob | null> {
    if (!this.isRecording || !this.mediaRecorder) {
      return null
    }

    return new Promise((resolve) => {
      if (!this.mediaRecorder) {
        resolve(null)
        return
      }

      this.mediaRecorder.onstop = () => {
        const mimeType = this.mediaRecorder!.mimeType || 'audio/webm'
        const blob = new Blob(this.audioChunks, { type: mimeType })
        this.isRecording = false
        asrDebug('stopRecording: blob ready', {
          size: blob.size,
          mimeType: blob.type,
          chunkCount: this.audioChunks.length
        })
        resolve(blob)
      }

      this.mediaRecorder.stop()
    })
  }

  /**
   * 取消录音
   */
  cancelRecording(): void {
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
  getStatus(): { isRecording: boolean; supported: boolean } {
    return {
      isRecording: this.isRecording,
      supported: this.supported
    }
  }
}

function getFilenameForBlob(audioBlob: Blob | null | undefined): string {
  const mimeType = audioBlob?.type || 'audio/webm'
  if (mimeType.includes('mp4')) return 'audio.mp4'
  if (mimeType.includes('wav')) return 'audio.wav'
  return 'audio.webm'
}

function interleaveToMono(audioBuffer: AudioBuffer): Float32Array {
  const channelCount = audioBuffer.numberOfChannels
  const frameCount = audioBuffer.length

  if (channelCount === 1) {
    return audioBuffer.getChannelData(0)
  }

  const mono = new Float32Array(frameCount)
  for (let channel = 0; channel < channelCount; channel += 1) {
    const channelData = audioBuffer.getChannelData(channel)
    for (let i = 0; i < frameCount; i += 1) {
      mono[i] += channelData[i] / channelCount
    }
  }

  return mono
}

function resampleLinear(input: Float32Array, inputSampleRate: number, outputSampleRate: number): Float32Array {
  if (inputSampleRate === outputSampleRate) {
    return input
  }

  const ratio = inputSampleRate / outputSampleRate
  const outputLength = Math.max(1, Math.round(input.length / ratio))
  const output = new Float32Array(outputLength)

  for (let i = 0; i < outputLength; i += 1) {
    const position = i * ratio
    const leftIndex = Math.floor(position)
    const rightIndex = Math.min(leftIndex + 1, input.length - 1)
    const weight = position - leftIndex
    output[i] = (input[leftIndex] * (1 - weight)) + (input[rightIndex] * weight)
  }

  return output
}

function encodeWavFromMonoPcm(samples: Float32Array, sampleRate: number): Blob {
  const bytesPerSample = 2
  const blockAlign = bytesPerSample
  const buffer = new ArrayBuffer(44 + (samples.length * bytesPerSample))
  const view = new DataView(buffer)

  const writeString = (offset: number, value: string): void => {
    for (let i = 0; i < value.length; i += 1) {
      view.setUint8(offset + i, value.charCodeAt(i))
    }
  }

  writeString(0, 'RIFF')
  view.setUint32(4, 36 + (samples.length * bytesPerSample), true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * blockAlign, true)
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, 16, true)
  writeString(36, 'data')
  view.setUint32(40, samples.length * bytesPerSample, true)

  let offset = 44
  for (let i = 0; i < samples.length; i += 1) {
    const normalized = Math.max(-1, Math.min(1, samples[i]))
    const pcm = normalized < 0 ? normalized * 0x8000 : normalized * 0x7fff
    view.setInt16(offset, pcm, true)
    offset += bytesPerSample
  }

  return new Blob([buffer], { type: 'audio/wav' })
}

async function convertAudioBlobToWav(audioBlob: Blob, targetSampleRate: number = 16000): Promise<Blob> {
  const AudioContextCtor = window.AudioContext || (window as any).webkitAudioContext
  if (!AudioContextCtor) {
    return audioBlob
  }

  const audioContext = new AudioContextCtor()

  try {
    const arrayBuffer = await audioBlob.arrayBuffer()
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer.slice(0))
    const mono = interleaveToMono(audioBuffer)
    const resampled = resampleLinear(mono, audioBuffer.sampleRate, targetSampleRate)
    return encodeWavFromMonoPcm(resampled, targetSampleRate)
  } finally {
    await audioContext.close()
  }
}

async function normalizeAudioForUpload(audioBlob: Blob | null | undefined): Promise<AudioNormalizationResult> {
  const mimeType = audioBlob?.type || ''
  asrDebug('normalizeAudioForUpload: input', {
    size: audioBlob?.size,
    mimeType
  })
  if (mimeType.includes('wav')) {
    return {
      blob: audioBlob!,
      filename: 'audio.wav'
    }
  }

  try {
    const wavBlob = await convertAudioBlobToWav(audioBlob!)
    asrDebug('normalizeAudioForUpload: converted to wav', {
      size: wavBlob.size,
      mimeType: wavBlob.type
    })
    return {
      blob: wavBlob,
      filename: 'audio.wav'
    }
  } catch (error) {
    console.warn('音频转 WAV 失败，回退为原始格式上传:', error)
    return {
      blob: audioBlob!,
      filename: getFilenameForBlob(audioBlob)
    }
  }
}

/**
 * 调用后端 ASR API 进行语音识别
 * @param audioBlob - 音频 Blob
 * @param metadata - 元数据
 * @returns Promise<Object>
 */
export async function transcribeAudio(
  audioBlob: Blob,
  metadata: ASRMetadata = {}
): Promise<TranscribeResult> {
  const url = '/api/asr/transcribe'
  const normalizedAudio = await normalizeAudioForUpload(audioBlob)
  asrDebug('transcribeAudio: request start', {
    url,
    originalSize: audioBlob?.size,
    originalType: audioBlob?.type,
    uploadSize: normalizedAudio.blob?.size,
    uploadType: normalizedAudio.blob?.type,
    metadata
  })

  const formData = new FormData()
  formData.append('audio', normalizedAudio.blob, normalizedAudio.filename)
  Object.entries(metadata).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      formData.append(key, String(value))
    }
  })

  try {
    const response = await fetch(url, {
      method: 'POST',
      body: formData
    })

    const payload = await readResponsePayload(response)

    if (!response.ok) {
      const errorMessage = payload.data?.error || payload.rawText || `HTTP ${response.status}`
      asrDebug('transcribeAudio: request failed', {
        status: response.status,
        error: payload.data,
        rawText: payload.rawText
      })
      throw new Error(errorMessage)
    }

    const data = payload.data || {}
    asrDebug('transcribeAudio: request success', data)
    return data
  } catch (error) {
    console.error('ASR API 调用失败:', error)
    throw error
  }
}

/**
 * 检查 ASR 服务状态
 * @returns Promise<Object>
 */
export async function checkASRStatus(): Promise<ASRStatus> {
  const url = '/api/asr/status'

  try {
    const response = await fetch(url)
    return await response.json()
  } catch (error) {
    console.error('检查 ASR 状态失败:', error)
    return {
      available: false,
      error: (error as Error).message
    }
  }
}