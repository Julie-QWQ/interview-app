interface VoiceSessionOptions {
  preRollMs?: number
  noiseFloorSampleMs?: number
  speechStartThreshold?: number
  speechEndThresholdRatio?: number
  minSpeechMs?: number
  endSilenceMs?: number
  maxSegmentMs?: number
  bargeInMs?: number
  minThreshold?: number
  smoothingFactor?: number
  onSegmentReady?: (blob: Blob, stats: SegmentStats) => void
  onSpeechStateChange?: (state: SpeechState) => void
  onBargeIn?: () => void
  shouldDetectBargeIn?: () => boolean
}

interface SegmentStats {
  segmentId: string
  state: string
  reason: string
  startedAt: string
  endedAt: string
  durationMs: number
  speechDurationMs: number
  bargeInTriggered: boolean
}

interface SpeechState {
  state: string
  noiseFloor: number
  rms: number
  threshold: number
  voiceActive: boolean
  [key: string]: any
}

interface VoiceStatus {
  supported: boolean
  alwaysOn: boolean
  state: string
  noiseFloor: number
  rms: number
  threshold: number
  voiceActive: boolean
}

interface Callbacks {
  onSegmentReady?: (blob: Blob, stats: SegmentStats) => void
  onSpeechStateChange?: (state: SpeechState) => void
  onBargeIn?: () => void
  shouldDetectBargeIn?: () => boolean
}

const DEFAULT_OPTIONS: Required<Omit<VoiceSessionOptions, 'onSegmentReady' | 'onSpeechStateChange' | 'onBargeIn' | 'shouldDetectBargeIn'>> = {
  preRollMs: 300,
  noiseFloorSampleMs: 800,
  speechStartThreshold: 1.6,
  speechEndThresholdRatio: 0.7,
  minSpeechMs: 220,
  endSilenceMs: 750,
  maxSegmentMs: 15000,
  bargeInMs: 250,
  minThreshold: 0.0015,
  smoothingFactor: 0.22
}

function voiceDebug(label: string, payload?: Record<string, any>): void {
  void label
  void payload
}

function noop(): void {}

function nowIso(timestamp: number): string {
  return new Date(timestamp).toISOString()
}

function getRecorderMimeType(): string {
  if (MediaRecorder.isTypeSupported('audio/mp4')) {
    return 'audio/mp4'
  }
  if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
    return 'audio/webm;codecs=opus'
  }
  if (MediaRecorder.isTypeSupported('audio/webm')) {
    return 'audio/webm'
  }
  return ''
}

export class VoiceSessionController {
  private options: VoiceSessionOptions
  private supported: boolean
  private mediaRecorder: MediaRecorder | null = null
  private stream: MediaStream | null = null
  private audioContext: AudioContext | null = null
  private sourceNode: MediaStreamAudioSourceNode | null = null
  private analyserNode: AnalyserNode | null = null
  private dataBuffer: Uint8Array | null = null
  private animationFrameId: number | null = null

  private recordedChunks: Blob[] = []
  private pendingSegmentStats: SegmentStats | null = null
  private segmentState: string = 'idle'
  private alwaysOn: boolean = false
  private noiseSamples: number[] = []
  private noiseFloor: number = 0
  private segmentStartedAt: number = 0
  private lastSpeechAt: number = 0
  private pendingSpeechSince: number = 0
  private pendingSilenceSince: number = 0
  private segmentCounter: number = 0
  private bargeInTriggered: boolean = false
  private bargeInStartedAt: number = 0
  private smoothedRms: number = 0
  private voiceActive: boolean = false
  private lastLoggedState: string = ''

  private onSegmentReady: (blob: Blob, stats: SegmentStats) => void
  private onSpeechStateChange: (state: SpeechState) => void
  private onBargeIn: () => void
  private shouldDetectBargeIn: () => boolean

  constructor(options: VoiceSessionOptions = {}) {
    this.options = {
      ...DEFAULT_OPTIONS,
      ...options
    }

    const hasMediaDevices = !!navigator.mediaDevices?.getUserMedia
    const hasMediaRecorder = !!window.MediaRecorder
    const hasAudioContext = !!(window.AudioContext || (window as any).webkitAudioContext)

    this.supported = hasMediaDevices && hasMediaRecorder && hasAudioContext

    this.onSegmentReady = options.onSegmentReady || noop
    this.onSpeechStateChange = options.onSpeechStateChange || noop
    this.onBargeIn = options.onBargeIn || noop
    this.shouldDetectBargeIn = options.shouldDetectBargeIn || (() => false)
  }

  setCallbacks(callbacks: Callbacks = {}): void {
    if (callbacks.onSegmentReady) this.onSegmentReady = callbacks.onSegmentReady
    if (callbacks.onSpeechStateChange) this.onSpeechStateChange = callbacks.onSpeechStateChange
    if (callbacks.onBargeIn) this.onBargeIn = callbacks.onBargeIn
    if (callbacks.shouldDetectBargeIn) this.shouldDetectBargeIn = callbacks.shouldDetectBargeIn
  }

  getStatus(): VoiceStatus {
    return {
      supported: this.supported,
      alwaysOn: this.alwaysOn,
      state: this.segmentState,
      noiseFloor: this.noiseFloor,
      rms: this.smoothedRms,
      threshold: this.getDynamicThreshold(),
      voiceActive: this.voiceActive
    }
  }

  private emitState(state: string, extra: Record<string, any> = {}): void {
    this.segmentState = state
    if (this.lastLoggedState !== state) {
      this.lastLoggedState = state
      voiceDebug(`state -> ${state}`, {
        noiseFloor: this.noiseFloor,
        rms: this.smoothedRms,
        threshold: this.getDynamicThreshold(),
        voiceActive: this.voiceActive,
        ...extra
      })
    }
    this.onSpeechStateChange({
      state,
      noiseFloor: this.noiseFloor,
      rms: this.smoothedRms,
      threshold: this.getDynamicThreshold(),
      voiceActive: this.voiceActive,
      ...extra
    })
  }

  async startAlwaysOn(): Promise<VoiceStatus> {
    if (!this.supported) {
      throw new Error('Current browser does not support always-on voice mode')
    }
    if (this.alwaysOn) {
      return this.getStatus()
    }

    const AudioContextCtor = window.AudioContext || (window as any).webkitAudioContext
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    })

    this.audioContext = new AudioContextCtor()
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume()
    }

    this.sourceNode = this.audioContext.createMediaStreamSource(this.stream!)
    this.analyserNode = this.audioContext.createAnalyser()
    this.analyserNode.fftSize = 2048
    this.dataBuffer = new Uint8Array(this.analyserNode.frequencyBinCount)
    this.sourceNode.connect(this.analyserNode)

    const mimeType = getRecorderMimeType()
    this.mediaRecorder = mimeType
      ? new MediaRecorder(this.stream!, { mimeType })
      : new MediaRecorder(this.stream!)

    this.mediaRecorder.ondataavailable = (event: BlobEvent) => {
      if (!event.data || event.data.size === 0) {
        return
      }
      this.recordedChunks.push(event.data)
      voiceDebug('segmentRecording: chunk captured', {
        size: event.data.size,
        mimeType: event.data.type,
        totalChunks: this.recordedChunks.length
      })
    }

    this.mediaRecorder.onstop = () => {
      this.handleRecorderStop()
    }

    this.alwaysOn = true
    this.recordedChunks = []
    this.pendingSegmentStats = null
    this.noiseSamples = []
    this.noiseFloor = 0
    this.segmentStartedAt = 0
    this.lastSpeechAt = 0
    this.pendingSpeechSince = 0
    this.pendingSilenceSince = 0
    this.bargeInTriggered = false
    this.bargeInStartedAt = 0
    this.smoothedRms = 0
    this.voiceActive = false
    this.lastLoggedState = ''

    voiceDebug('startAlwaysOn: audio context ready', {
      sampleRate: this.audioContext.sampleRate || 48000,
      mimeType: this.mediaRecorder.mimeType || mimeType || 'default'
    })

    this.emitState('armed')
    this.monitor()
    voiceDebug('startAlwaysOn: listening started')

    return this.getStatus()
  }

  async stopAlwaysOn(): Promise<void> {
    this.alwaysOn = false
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId)
      this.animationFrameId = null
    }

    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.pendingSegmentStats = null
      this.recordedChunks = []
      this.mediaRecorder.stop()
    }
    this.mediaRecorder = null

    if (this.sourceNode) {
      this.sourceNode.disconnect()
      this.sourceNode = null
    }
    if (this.analyserNode) {
      this.analyserNode.disconnect()
      this.analyserNode = null
    }

    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop())
      this.stream = null
    }

    if (this.audioContext) {
      await this.audioContext.close()
      this.audioContext = null
    }

    this.recordedChunks = []
    this.pendingSegmentStats = null
    this.dataBuffer = null
    this.smoothedRms = 0
    this.voiceActive = false
    this.lastLoggedState = ''
    this.emitState('idle')
    voiceDebug('stopAlwaysOn: listening stopped')
  }

  private computeRms(): number {
    if (!this.analyserNode || !this.dataBuffer) {
      return 0
    }

    this.analyserNode.getByteTimeDomainData(this.dataBuffer as any)
    let sum = 0
    for (let i = 0; i < this.dataBuffer.length; i += 1) {
      const normalized = (this.dataBuffer[i] - 128) / 128
      sum += normalized * normalized
    }
    return Math.sqrt(sum / this.dataBuffer.length)
  }

  private getDynamicThreshold(): number {
    const threshold = this.noiseFloor * (this.options.speechStartThreshold || DEFAULT_OPTIONS.speechStartThreshold)
    return Math.max(threshold, this.options.minThreshold || DEFAULT_OPTIONS.minThreshold)
  }

  private getSpeechEndThreshold(): number {
    return Math.max(
      this.getDynamicThreshold() * (this.options.speechEndThresholdRatio || DEFAULT_OPTIONS.speechEndThresholdRatio),
      (this.options.minThreshold || DEFAULT_OPTIONS.minThreshold) * (this.options.speechEndThresholdRatio || DEFAULT_OPTIONS.speechEndThresholdRatio)
    )
  }

  private startSegmentRecording(): void {
    if (!this.mediaRecorder || this.mediaRecorder.state !== 'inactive') {
      return
    }
    this.recordedChunks = []
    this.pendingSegmentStats = null
    this.mediaRecorder.start()
    voiceDebug('startSegmentRecording: recorder started', {
      mimeType: this.mediaRecorder.mimeType || 'default'
    })
  }

  private handleRecorderStop(): void {
    const stats = this.pendingSegmentStats
    const mimeType = this.mediaRecorder?.mimeType || 'audio/webm'
    const blob = new Blob(this.recordedChunks, { type: mimeType })

    voiceDebug('handleRecorderStop: blob ready', {
      ...(stats || {}),
      mimeType,
      blobSize: blob.size,
      chunkCount: this.recordedChunks.length
    })

    this.recordedChunks = []
    this.pendingSegmentStats = null

    if (!stats) {
      return
    }

    if (blob.size === 0 || stats.speechDurationMs < (this.options.minSpeechMs || DEFAULT_OPTIONS.minSpeechMs)) {
      voiceDebug('finalizeSegment: discarded', {
        blobSize: blob.size,
        speechDurationMs: stats.speechDurationMs,
        minSpeechMs: this.options.minSpeechMs || DEFAULT_OPTIONS.minSpeechMs
      })
      return
    }

    voiceDebug('finalizeSegment: segment ready', {
      ...stats,
      blobSize: blob.size,
      mimeType
    })
    this.onSegmentReady(blob, stats)
  }

  private finalizeSegment(reason: string, endedAt: number = Date.now()): void {
    if (!this.segmentStartedAt) {
      this.emitState('armed')
      return
    }

    const speechDurationMs = Math.max(this.lastSpeechAt - this.segmentStartedAt, 0)
    const stats: SegmentStats = {
      segmentId: `voice-segment-${Date.now()}-${this.segmentCounter}`,
      state: this.segmentState,
      reason,
      startedAt: nowIso(this.segmentStartedAt),
      endedAt: nowIso(endedAt),
      durationMs: Math.max(endedAt - this.segmentStartedAt, 0),
      speechDurationMs,
      bargeInTriggered: this.bargeInTriggered
    }

    this.segmentCounter += 1
    this.segmentStartedAt = 0
    this.lastSpeechAt = 0
    this.pendingSpeechSince = 0
    this.pendingSilenceSince = 0
    this.bargeInTriggered = false
    this.bargeInStartedAt = 0
    this.voiceActive = false
    this.emitState('armed')

    if (speechDurationMs < (this.options.minSpeechMs || DEFAULT_OPTIONS.minSpeechMs)) {
      voiceDebug('finalizeSegment: discarded', {
        speechDurationMs,
        minSpeechMs: this.options.minSpeechMs || DEFAULT_OPTIONS.minSpeechMs
      })
      return
    }

    this.pendingSegmentStats = stats
    if (this.mediaRecorder?.state === 'recording') {
      this.mediaRecorder.stop()
      return
    }

    this.handleRecorderStop()
  }

  private handleSpeechDetected(currentTime: number): void {
    this.voiceActive = true
    if (!this.segmentStartedAt) {
      this.segmentStartedAt = currentTime
      this.lastSpeechAt = currentTime
      this.pendingSilenceSince = 0
      this.startSegmentRecording()
      this.emitState('speech_detected')
      return
    }

    this.lastSpeechAt = currentTime
    this.pendingSilenceSince = 0
    if (this.segmentState !== 'speech_detected') {
      this.emitState('speech_detected')
    }
  }

  private handleSilenceDetected(currentTime: number): void {
    if (!this.segmentStartedAt) {
      this.voiceActive = false
      return
    }

    if (!this.pendingSilenceSince) {
      this.pendingSilenceSince = currentTime
      this.emitState('segment_closing')
      return
    }

    if (currentTime - this.pendingSilenceSince >= (this.options.endSilenceMs || DEFAULT_OPTIONS.endSilenceMs)) {
      this.finalizeSegment('silence_timeout', currentTime)
    }
  }

  private maybeTriggerBargeIn(currentTime: number, isSpeaking: boolean): void {
    if (!this.shouldDetectBargeIn() || this.bargeInTriggered) {
      this.bargeInStartedAt = 0
      return
    }

    if (!isSpeaking) {
      this.bargeInStartedAt = 0
      return
    }

    if (!this.bargeInStartedAt) {
      this.bargeInStartedAt = currentTime
      return
    }

    if (currentTime - this.bargeInStartedAt >= (this.options.bargeInMs || DEFAULT_OPTIONS.bargeInMs)) {
      this.bargeInTriggered = true
      this.emitState('barge_in')
      voiceDebug('maybeTriggerBargeIn: barge-in triggered')
      this.onBargeIn()
    }
  }

  private async monitor(): Promise<void> {
    if (!this.alwaysOn) {
      return
    }

    if (this.audioContext?.state === 'suspended') {
      try {
        await this.audioContext.resume()
      } catch (error) {
        console.error('Failed to resume audio context', error)
      }
    }

    const currentTime = Date.now()
    const rms = this.computeRms()
    const smoothingFactor = this.options.smoothingFactor || DEFAULT_OPTIONS.smoothingFactor
    this.smoothedRms = this.smoothedRms === 0
      ? rms
      : (this.smoothedRms * (1 - smoothingFactor)) + (rms * smoothingFactor)

    const noiseFloorSampleMs = this.options.noiseFloorSampleMs || DEFAULT_OPTIONS.noiseFloorSampleMs
    if (this.noiseSamples.length * 100 < noiseFloorSampleMs) {
      this.noiseSamples.push(this.smoothedRms)
      const sortedSamples = [...this.noiseSamples].sort((a, b) => a - b)
      const median = sortedSamples[Math.floor(sortedSamples.length / 2)] || this.smoothedRms
      this.noiseFloor = median
      this.emitState(this.segmentStartedAt ? this.segmentState : 'armed')
    } else {
      const adaptiveRms = Math.min(this.smoothedRms, this.getDynamicThreshold())
      this.noiseFloor = this.noiseFloor === 0
        ? adaptiveRms
        : (this.noiseFloor * 0.985) + (adaptiveRms * 0.015)
    }

    const startThreshold = this.getDynamicThreshold()
    const endThreshold = this.getSpeechEndThreshold()
    const isSpeaking = this.voiceActive
      ? this.smoothedRms >= endThreshold
      : this.smoothedRms >= startThreshold

    this.maybeTriggerBargeIn(currentTime, isSpeaking)

    const minSpeechMs = this.options.minSpeechMs || DEFAULT_OPTIONS.minSpeechMs
    if (isSpeaking) {
      if (!this.pendingSpeechSince) {
        this.pendingSpeechSince = currentTime
      }
      if (currentTime - this.pendingSpeechSince >= minSpeechMs) {
        this.handleSpeechDetected(currentTime)
      }
    } else {
      this.voiceActive = false
      this.pendingSpeechSince = 0
      this.handleSilenceDetected(currentTime)
    }

    const maxSegmentMs = this.options.maxSegmentMs || DEFAULT_OPTIONS.maxSegmentMs
    if (this.segmentStartedAt && currentTime - this.segmentStartedAt >= maxSegmentMs) {
      this.finalizeSegment('max_duration', currentTime)
    }

    this.animationFrameId = requestAnimationFrame(() => {
      this.monitor()
    })
  }
}

export function createVoiceSessionController(options?: VoiceSessionOptions): VoiceSessionController {
  return new VoiceSessionController(options)
}