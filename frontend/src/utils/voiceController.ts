/**
 * Audio playback queue controller.
 * Handles sequential playback and exposes state changes for UI synchronization.
 */

export interface VoiceState {
  isPlaying: boolean
  currentMessageId: string | null
  queueLength: number
  isMuted: boolean
}

export type StateListener = (state: VoiceState) => void

interface AudioQueueItem {
  audio: HTMLAudioElement
  messageId: string | null
}

export class VoiceController {
  private queue: AudioQueueItem[] = []
  private isPlaying: boolean = false
  private currentAudio: HTMLAudioElement | null = null
  private isMuted: boolean = false
  private currentMessageId: string | null = null
  private interruptedAudio: HTMLAudioElement | null = null
  private listeners: Set<StateListener> = new Set()

  emitStateChange(): void {
    const snapshot: VoiceState = {
      isPlaying: this.isPlaying,
      currentMessageId: this.currentMessageId,
      queueLength: this.queue.length,
      isMuted: this.isMuted
    }

    this.listeners.forEach(listener => {
      try {
        listener(snapshot)
      } catch (error) {
        console.error('音频状态监听器执行失败:', error)
      }
    })
  }

  subscribe(listener: StateListener): () => void {
    if (typeof listener !== 'function') {
      return () => {}
    }

    this.listeners.add(listener)
    this.emitStateChange()

    return () => {
      this.listeners.delete(listener)
    }
  }

  enqueue(audioBase64: string, messageId: string | null = null): void {
    if (this.isMuted || !audioBase64) {
      return
    }

    try {
      const audioSrc = `data:audio/mpeg;base64,${audioBase64}`
      const audio = new Audio(audioSrc)

      audio.onended = () => {
        this.isPlaying = false
        this.currentAudio = null
        this.currentMessageId = null
        this.emitStateChange()
        this.playNext()
      }

      audio.onerror = (error: any) => {
        console.error('音频播放失败:', error)
        this.isPlaying = false
        this.currentAudio = null
        this.currentMessageId = null
        this.emitStateChange()
        this.playNext()
      }

      this.queue.push({ audio, messageId })
      this.emitStateChange()

      if (!this.isPlaying) {
        this.playNext()
      }
    } catch (error) {
      console.error('创建音频对象失败:', error)
    }
  }

  private playNext(): void {
    if (this.queue.length === 0) {
      this.emitStateChange()
      return
    }

    const { audio, messageId } = this.queue.shift()!
    this.currentAudio = audio
    this.currentMessageId = messageId
    this.isPlaying = true
    this.emitStateChange()

    audio.play().catch((error: Error) => {
      if (error?.name === 'AbortError' && this.interruptedAudio === audio) {
        this.interruptedAudio = null
        this.isPlaying = false
        this.currentAudio = null
        this.currentMessageId = null
        this.emitStateChange()
        return
      }

      console.error('播放失败:', error)
      this.isPlaying = false
      this.currentAudio = null
      this.currentMessageId = null
      this.emitStateChange()
      this.playNext()
    })
  }

  stop(): void {
    if (this.currentAudio) {
      this.interruptedAudio = this.currentAudio
      this.currentAudio.pause()
      this.currentAudio = null
    }

    this.queue = []
    this.isPlaying = false
    this.currentMessageId = null
    this.emitStateChange()
  }

  toggleMute(): boolean {
    this.isMuted = !this.isMuted
    if (this.isMuted) {
      this.stop()
    } else {
      this.emitStateChange()
    }
    return this.isMuted
  }

  setMute(muted: boolean): boolean {
    this.isMuted = Boolean(muted)
    if (this.isMuted) {
      this.stop()
    } else {
      this.emitStateChange()
    }
    return this.isMuted
  }

  pause(): void {
    if (this.currentAudio && this.isPlaying) {
      this.interruptedAudio = this.currentAudio
      this.currentAudio.pause()
      this.isPlaying = false
      this.emitStateChange()
    }
  }

  resume(): void {
    if (this.currentAudio && !this.isPlaying && !this.isMuted) {
      this.currentAudio.play().then(() => {
        this.isPlaying = true
        this.emitStateChange()
      }).catch((error: Error) => {
        if (error?.name !== 'AbortError') {
          console.error('恢复播放失败:', error)
        }
      })
    }
  }
}

const voiceController = new VoiceController()
export default voiceController