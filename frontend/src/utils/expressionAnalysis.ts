import { interviewApi } from '@/api/interview'

// ==================== Type Definitions ====================

interface TextStats {
  textLength: number
  fillerCount: number
  sentenceCount: number
  selfCorrectionCount: number
  repetitionRatio: number
}

interface AudioExpressionPayload {
  segment_id: string
  stage: string
  source: string
  client_started_at: string
  client_ended_at: string
  transcript_text: string
  text_length: number
  duration_ms: number
  speech_duration_ms: number
  pause_ratio: number
  avg_volume: number
  volume_variation: number
  filler_count: number
  sentence_count: number
  interruption_recovery_ms: number
  self_correction_count: number
  repetition_ratio: number
}

interface AudioExpressionOptions {
  segmentId: string
  stage: string
  source: string
  startedAt?: string
  endedAt?: string
  transcriptText?: string
  durationMs?: number
  speechDurationMs?: number
  avgVolume?: number
  volumeVariation?: number
  interruptionRecoveryMs?: number
}

interface VideoExpressionWindowPayload {
  window_id: string
  stage: string
  source: string
  started_at: string
  ended_at: string
  sample_count: number
  face_present_rate: number
  gaze_aversion_rate: number
  head_jitter: number
  face_center_stability: number
  mouth_activity_stability: number
  expression_intensity_variance: number
  brightness: number
  motion_intensity: number
  face_area_rate: number
  detector_type: string
}

interface VideoExpressionReporterOptions {
  interviewId: number
  getStage: () => string
  getVideoElement: () => HTMLVideoElement | null
  intervalMs?: number
}

interface VideoReporterState {
  timerId: number | null
  canvas: HTMLCanvasElement | null
  context: CanvasRenderingContext2D | null
  detector: FaceDetector | null
  prevFrame: Uint8ClampedArray | null
  prevFaceCenter: { x: number; y: number } | null
  windowIndex: number
  windowStartTs: number
}

interface FaceCenter {
  x: number
  y: number
}

interface DetectionResult {
  faces: DetectedFace[]
  detectorType: string
}

// ==================== Utility Functions ====================

function expressionDebug(label: string, payload: unknown): void {
  void label
  void payload
}

function nowIso(timestamp: number = Date.now()): string {
  return new Date(timestamp).toISOString()
}

function clamp(value: number, min: number = 0, max: number = 1): number {
  return Math.min(max, Math.max(min, value))
}

function computeTextStats(text: string = ''): TextStats {
  const normalized = String(text || '').trim()
  const fillerWords = ['嗯', '啊', '哦', '额', '呃', '那个', '就是', '然后']
  const fillerCount = fillerWords.reduce(
    (sum, word) => sum + normalized.split(word).length - 1,
    0
  )
  const sentenceCount = Math.max(1, (normalized.match(/[。!！？?]/g) || []).length || 1)
  const correctionTokens = ['不是', '重说', '更正', '我的意思是']
  const selfCorrectionCount = correctionTokens.reduce(
    (sum, word) => sum + normalized.split(word).length - 1,
    0
  )
  const tokenList = normalized
    .replace(/[，。!！？?、,.;;：:\n]/g, ' ')
    .split(/\s+/)
    .filter(Boolean)

  let repetitionRatio = 0
  if (tokenList.length > 0) {
    const counter = new Map<string, number>()
    tokenList.forEach((token) => counter.set(token, (counter.get(token) || 0) + 1))
    repetitionRatio = Math.max(...counter.values()) / tokenList.length
  }

  return {
    textLength: normalized.length,
    fillerCount,
    sentenceCount,
    selfCorrectionCount,
    repetitionRatio
  }
}

// ==================== Audio Expression Functions ====================

export async function loadExpressionConfig(): Promise<any> {
  return interviewApi.getExpressionConfig()
}

export async function reportAudioExpressionSegment(
  interviewId: number,
  payload: AudioExpressionPayload
): Promise<any> {
  expressionDebug('reportAudioExpressionSegment', payload)
  return interviewApi.uploadExpressionAudioSegment(interviewId, payload)
}

export async function finalizeExpressionReport(interviewId: number): Promise<any> {
  return interviewApi.finalizeExpression(interviewId)
}

export function buildAudioExpressionPayload(
  options: AudioExpressionOptions
): AudioExpressionPayload {
  const {
    segmentId,
    stage,
    source,
    startedAt,
    endedAt,
    transcriptText = '',
    durationMs = 0,
    speechDurationMs = 0,
    avgVolume = 0,
    volumeVariation = 0,
    interruptionRecoveryMs = 0
  } = options

  const safeDurationMs = Math.max(1, Number(durationMs || 0))
  const safeSpeechDurationMs = Math.max(0, Number(speechDurationMs || safeDurationMs))
  const pauseRatio = clamp((safeDurationMs - safeSpeechDurationMs) / safeDurationMs, 0, 1)
  const textStats = computeTextStats(transcriptText)

  return {
    segment_id: segmentId,
    stage,
    source,
    client_started_at: startedAt || nowIso(),
    client_ended_at: endedAt || nowIso(),
    transcript_text: transcriptText || '',
    text_length: textStats.textLength,
    duration_ms: safeDurationMs,
    speech_duration_ms: safeSpeechDurationMs,
    pause_ratio: pauseRatio,
    avg_volume: Number(avgVolume || 0),
    volume_variation: Number(volumeVariation || 0),
    filler_count: textStats.fillerCount,
    sentence_count: textStats.sentenceCount,
    interruption_recovery_ms: Number(interruptionRecoveryMs || 0),
    self_correction_count: textStats.selfCorrectionCount,
    repetition_ratio: textStats.repetitionRatio
  }
}

// ==================== Video Expression Functions ====================

export function createVideoExpressionReporter(
  options: VideoExpressionReporterOptions
): { start: () => Promise<void>; stop: () => void } {
  const { interviewId, getStage, getVideoElement, intervalMs = 1500 } = options

  const state: VideoReporterState = {
    timerId: null,
    canvas: null,
    context: null,
    detector: null,
    prevFrame: null,
    prevFaceCenter: null,
    windowIndex: 0,
    windowStartTs: 0
  }

  const ensureCanvas = (video: HTMLVideoElement): void => {
    if (!state.canvas) {
      state.canvas = document.createElement('canvas')
      state.context = state.canvas.getContext('2d', { willReadFrequently: true })
    }
    const width = Math.max(160, Math.min(320, video.videoWidth || 320))
    const height = Math.max(120, Math.min(240, video.videoHeight || 240))
    if (state.canvas.width !== width || state.canvas.height !== height) {
      state.canvas.width = width
      state.canvas.height = height
    }
  }

  const detectFaces = async (canvas: HTMLCanvasElement): Promise<DetectionResult> => {
    if ('FaceDetector' in window) {
      if (!state.detector) {
        state.detector = new (window as any).FaceDetector({
          fastMode: true,
          maxDetectedFaces: 1
        })
      }
      try {
        const faces = await state.detector.detect(canvas)
        return { faces, detectorType: 'face_detector' }
      } catch (error) {
        expressionDebug('FaceDetector.detect failed', error)
      }
    }
    return { faces: [], detectorType: 'heuristic' }
  }

  const sampleFrame = async (): Promise<void> => {
    const video = getVideoElement?.()
    if (!video || video.readyState < 2 || !video.videoWidth || !video.videoHeight) {
      return
    }

    ensureCanvas(video)
    const { canvas, context } = state
    if (!context) return

    context.drawImage(video, 0, 0, canvas.width, canvas.height)
    const image = context.getImageData(0, 0, canvas.width, canvas.height)
    const pixels = image.data

    let brightnessSum = 0
    let deltaSum = 0
    for (let i = 0; i < pixels.length; i += 4) {
      const brightness = (pixels[i] + pixels[i + 1] + pixels[i + 2]) / (255 * 3)
      brightnessSum += brightness
      if (state.prevFrame) {
        const prevBrightness =
          (state.prevFrame[i] + state.prevFrame[i + 1] + state.prevFrame[i + 2]) / (255 * 3)
        deltaSum += Math.abs(brightness - prevBrightness)
      }
    }
    const pixelCount = Math.max(1, pixels.length / 4)
    const brightness = brightnessSum / pixelCount
    const motionIntensity = state.prevFrame ? deltaSum / pixelCount : 0

    const { faces, detectorType } = await detectFaces(canvas)
    const face = faces[0] || null
    const now = Date.now()
    const windowId = `video-window-${now}-${state.windowIndex}`
    const startedAt = state.windowStartTs || now - intervalMs
    state.windowStartTs = now
    state.windowIndex += 1

    let facePresentRate = 0
    let gazeAversionRate = 1
    let headJitter = 0
    let faceCenterStability = 0
    let mouthActivityStability = 0
    let expressionIntensityVariance = 0
    let faceAreaRate = 0

    if (face?.boundingBox) {
      const { x, y, width, height } = face.boundingBox
      const centerX = (x + width / 2) / canvas.width
      const centerY = (y + height / 2) / canvas.height
      facePresentRate = 1
      faceAreaRate = clamp((width * height) / (canvas.width * canvas.height), 0, 1)
      const offsetX = Math.abs(centerX - 0.5)
      const offsetY = Math.abs(centerY - 0.5)
      gazeAversionRate = clamp(offsetX * 1.6 + offsetY * 0.6, 0, 1)
      faceCenterStability = clamp(1 - (offsetX + offsetY), 0, 1)

      if (state.prevFaceCenter) {
        const dx = centerX - state.prevFaceCenter.x
        const dy = centerY - state.prevFaceCenter.y
        headJitter = Math.sqrt(dx * dx + dy * dy)
      }
      state.prevFaceCenter = { x: centerX, y: centerY }

      const faceImage = context.getImageData(
        Math.max(0, Math.floor(x)),
        Math.max(0, Math.floor(y)),
        Math.max(1, Math.min(canvas.width - Math.floor(x), Math.floor(width))),
        Math.max(1, Math.min(canvas.height - Math.floor(y), Math.floor(height)))
      )
      const mouthTop = Math.floor(faceImage.height * 0.6)
      let faceDelta = 0
      let mouthDelta = 0
      for (let i = 0; i < faceImage.data.length; i += 4) {
        const localIndex = i / 4
        const row = Math.floor(localIndex / faceImage.width)
        const value = (faceImage.data[i] + faceImage.data[i + 1] + faceImage.data[i + 2]) / (255 * 3)
        faceDelta += Math.abs(value - brightness)
        if (row >= mouthTop) {
          mouthDelta += Math.abs(value - brightness)
        }
      }
      expressionIntensityVariance = clamp(
        faceDelta / Math.max(1, faceImage.data.length / 4),
        0,
        1
      )
      mouthActivityStability = clamp(
        1 - mouthDelta / Math.max(1, faceImage.data.length / 6),
        0,
        1
      )
    } else {
      state.prevFaceCenter = null
    }

    state.prevFrame = new Uint8ClampedArray(image.data)

    const payload: VideoExpressionWindowPayload = {
      window_id: windowId,
      stage: getStage?.() || '',
      source: 'camera',
      started_at: nowIso(startedAt),
      ended_at: nowIso(now),
      sample_count: 1,
      face_present_rate: facePresentRate,
      gaze_aversion_rate: gazeAversionRate,
      head_jitter: headJitter,
      face_center_stability: faceCenterStability,
      mouth_activity_stability: mouthActivityStability,
      expression_intensity_variance: expressionIntensityVariance,
      brightness,
      motion_intensity: motionIntensity,
      face_area_rate: faceAreaRate,
      detector_type: detectorType
    }

    expressionDebug('report video window', payload)
    try {
      await interviewApi.uploadExpressionVideoWindow(interviewId, payload)
    } catch (error) {
      console.error('上传视频表达特征失败:', error)
    }
  }

  return {
    async start(): Promise<void> {
      if (state.timerId || !interviewId) return
      state.windowStartTs = Date.now()
      state.timerId = window.setInterval(() => {
        sampleFrame().catch((error) => {
          console.error('视频表达分析采样失败:', error)
        })
      }, intervalMs)
    },
    stop(): void {
      if (state.timerId) {
        window.clearInterval(state.timerId)
        state.timerId = null
      }
    }
  }
}
