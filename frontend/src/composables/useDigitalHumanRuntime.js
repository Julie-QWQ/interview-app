import { computed, nextTick, ref } from 'vue'
import { interviewApi } from '@/api/interview'

function normalizeAvatarError(error = '') {
  const text = String(error || '').trim()
  if (!text) return ''

  const lower = text.toLowerCase()
  if (lower.includes('not enough credits') || lower.includes('http 402')) {
    return '数字人额度不足'
  }
  if (lower.includes('unauthorized') || lower.includes('http 401')) {
    return '数字人鉴权失败，请检查 D-ID 配置'
  }
  if (lower.includes('timeout') || lower.includes('超时')) {
    return '数字人生成超时'
  }
  return text
}

export function isDigitalHumanRelatedError(error) {
  const text = String(error || '').toLowerCase()
  return text.includes('d-id') ||
    text.includes('digital human') ||
    text.includes('avatar') ||
    text.includes('credits') ||
    text.includes('unauthorized')
}

export function formatDigitalHumanError(error) {
  const text = String(error || '').toLowerCase()
  if (text.includes('credits') || text.includes('402')) {
    return '数字人额度不足，已切换为语音模式'
  }
  if (text.includes('unauthorized') || text.includes('401')) {
    return '数字人鉴权失败，请检查 D-ID 配置'
  }
  if (text.includes('timeout') || text.includes('超时')) {
    return '数字人生成超时，已切换为语音模式'
  }
  return '数字人暂时不可用，已切换为语音模式'
}

export function useDigitalHumanRuntime({ interviewId, currentInterview, messages }) {
  const sessionId = ref(null)
  const digitalHumanConfig = ref(null)
  const provider = ref('xunfei')
  const avatarStatus = ref('LISTENING')
  const digitalHumanReady = ref(false)
  const digitalHumanAvailable = ref(false)
  const digitalHumanError = ref('')
  const activeSpeechMode = ref('none')
  const isPlaying = ref(false)
  const currentPlayingMessageId = ref(null)
  const isMuted = ref(false)

  const digitalAvatarInstanceKey = computed(() => {
    const interviewKey = String(interviewId.value || 'unknown')
    const sessionKey = String(sessionId.value || 'pending')
    const avatarKey = String(digitalHumanConfig.value?.avatarId || 'default')
    return `${interviewKey}-${sessionKey}-${avatarKey}`
  })

  function resetSpeechState() {
    activeSpeechMode.value = 'none'
    isPlaying.value = false
    currentPlayingMessageId.value = null
    avatarStatus.value = 'LISTENING'
  }

  function setDigitalHumanReady(ready) {
    digitalHumanReady.value = Boolean(ready)
    if (digitalHumanReady.value) {
      digitalHumanAvailable.value = true
      digitalHumanError.value = ''
      if (activeSpeechMode.value === 'none') {
        avatarStatus.value = 'LISTENING'
      }
    }
  }

  function setDigitalHumanError(error = '') {
    digitalHumanError.value = normalizeAvatarError(error)
    digitalHumanReady.value = false
    digitalHumanAvailable.value = false
  }

  function setAvatarStatus(status) {
    avatarStatus.value = status
    if (status === 'SPEAKING') {
      activeSpeechMode.value = 'digital_human'
      isPlaying.value = true
      return
    }

    if (status === 'LISTENING' && activeSpeechMode.value === 'digital_human') {
      resetSpeechState()
    }
  }

  function beginAssistantSpeech(messageId = null) {
    activeSpeechMode.value = 'digital_human'
    currentPlayingMessageId.value = messageId || null
    isPlaying.value = true
    avatarStatus.value = 'THINKING'
  }

  function finishAssistantSpeech() {
    resetSpeechState()
  }

  function interruptAssistant() {
    const mode = activeSpeechMode.value
    activeSpeechMode.value = 'none'
    isPlaying.value = false
    currentPlayingMessageId.value = null
    avatarStatus.value = 'INTERRUPTED'
    return { mode }
  }

  function toggleMute() {
    isMuted.value = !isMuted.value
    if (isMuted.value) {
      isPlaying.value = false
      currentPlayingMessageId.value = null
    }
    return isMuted.value
  }

  function stopVoice() {
    activeSpeechMode.value = 'none'
    isPlaying.value = false
    currentPlayingMessageId.value = null
  }

  async function initAvatarSession(targetInterviewId = interviewId.value) {
    try {
      const response = await interviewApi.createAvatarSession(targetInterviewId)
      if (response.success) {
        provider.value = response.provider || 'xunfei'
        sessionId.value = response.session_id
        digitalHumanConfig.value = response.config
        avatarStatus.value = 'LISTENING'
        digitalHumanError.value = ''
        return response
      }

      provider.value = 'disabled'
      sessionId.value = null
      digitalHumanConfig.value = null
      setDigitalHumanError(response.error || '')
      return response
    } catch (error) {
      provider.value = 'disabled'
      sessionId.value = null
      digitalHumanConfig.value = null
      setDigitalHumanError(error?.message || String(error || ''))
      throw error
    }
  }

  async function ensureDigitalHumanSession(targetInterviewId = interviewId.value) {
    const status = currentInterview.value?.status
    if (!['in_progress', 'completed'].includes(status)) {
      return
    }
    if (sessionId.value || provider.value === 'disabled') {
      return
    }
    await initAvatarSession(targetInterviewId)
  }

  function delay(ms) {
    return new Promise(resolve => window.setTimeout(resolve, ms))
  }

  async function waitForDigitalHumanReady(digitalAvatarRef, timeoutMs = 10000) {
    const startedAt = Date.now()

    while (Date.now() - startedAt < timeoutMs) {
      await nextTick()
      if (
        digitalAvatarRef.value &&
        provider.value === 'xunfei' &&
        digitalHumanConfig.value &&
        digitalHumanReady.value
      ) {
        return true
      }
      await delay(100)
    }

    return false
  }

  function getLatestAssistantMessageId() {
    for (let index = messages.value.length - 1; index >= 0; index -= 1) {
      const message = messages.value[index]
      if (message?.role === 'assistant' && !message?.isStreaming) {
        return message.id
      }
    }
    return null
  }

  async function speakAssistantText(text, digitalAvatarRef, messageId = null) {
    const normalizedText = String(text || '').trim()
    if (!normalizedText || isMuted.value) {
      return false
    }

    const ready = await waitForDigitalHumanReady(digitalAvatarRef)
    if (!ready) {
      return false
    }

    const targetMessageId = messageId ?? getLatestAssistantMessageId()
    beginAssistantSpeech(targetMessageId)

    try {
      await digitalAvatarRef.value.speakText(normalizedText)
      return true
    } catch (error) {
      finishAssistantSpeech()
      setDigitalHumanError(error?.message || String(error || ''))
      throw error
    }
  }

  function clearDigitalHumanSession() {
    sessionId.value = null
    digitalHumanConfig.value = null
    provider.value = 'xunfei'
    avatarStatus.value = 'LISTENING'
    digitalHumanReady.value = false
    digitalHumanAvailable.value = false
    digitalHumanError.value = ''
    activeSpeechMode.value = 'none'
    isPlaying.value = false
    currentPlayingMessageId.value = null
    isMuted.value = false
  }

  function handleDigitalHumanReady() {
    setDigitalHumanReady(true)
  }

  function handleDigitalHumanError(error) {
    const message = error?.message || String(error || '')
    setDigitalHumanError(message)
  }

  function handleDigitalHumanStatusChange(status) {
    setAvatarStatus(status)
  }

  return {
    sessionId,
    digitalHumanConfig,
    provider,
    avatarStatus,
    digitalHumanReady,
    digitalHumanAvailable,
    digitalHumanError,
    isPlaying,
    currentPlayingMessageId,
    isMuted,
    digitalAvatarInstanceKey,
    initAvatarSession,
    ensureDigitalHumanSession,
    speakAssistantText,
    beginAssistantSpeech,
    finishAssistantSpeech,
    interruptAssistant,
    toggleMute,
    stopVoice,
    clearDigitalHumanSession,
    handleDigitalHumanReady,
    handleDigitalHumanError,
    handleDigitalHumanStatusChange
  }
}
