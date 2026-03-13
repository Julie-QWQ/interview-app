import { computed, nextTick, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, Microphone, VideoPlay } from '@element-plus/icons-vue'
import { ASRRecorder, checkASRStatus, transcribeAudio } from '@/utils/asrRecorder'
import {
  buildAudioExpressionPayload,
  createVideoExpressionReporter,
  loadExpressionConfig,
  reportAudioExpressionSegment
} from '@/utils/expressionAnalysis'
import { createVoiceSessionController } from '@/utils/voiceSessionController'
import { interviewApi } from '@/api/interview'

const DEFAULT_VOICE_CONFIG = {
  enabled: true,
  always_on_enabled: true,
  noise_floor_sample_ms: 800,
  speech_start_threshold: 1.6,
  min_speech_ms: 220,
  end_silence_ms: 750,
  max_segment_ms: 15000,
  pre_roll_ms: 300,
  barge_in_ms: 250,
  chunk_retention_ms: 20000,
  min_threshold: 0.0015,
  timeslice_ms: 100,
  auto_send_min_chars: 8,
  typing_grace_ms: 1200,
  short_noise_words: ['嗯', '啊', '额', '呃', '哦', '唔', '呀', '那个']
}

export function useVoiceRuntime({
  interviewId,
  currentStage,
  userCameraRef,
  inputMessage,
  thinking,
  isPlaying,
  sendInterviewContent,
  stopAssistantPlayback
}) {
  const asrRecorder = ref(null)
  const voiceSession = ref(null)
  const expressionConfig = ref({
    enabled: true,
    video_sample_interval_ms: 1500
  })
  const expressionVideoReporter = ref(null)
  const manualRecordingStartedAt = ref('')
  const isListening = ref(false)
  const isTranscribing = ref(false)
  const isSpeechSupported = ref(false)
  const isAlwaysOnSupported = ref(false)
  const asrServiceAvailable = ref(false)
  const alwaysOnModeEnabled = ref(false)
  const voiceState = ref('idle')
  const voiceQueue = ref([])
  const voiceQueueBusy = ref(false)
  const lastManualInputAt = ref(0)
  const suppressInputTracking = ref(false)
  const voiceConfig = ref({ ...DEFAULT_VOICE_CONFIG })
  const voiceRms = ref(0)
  const voiceThreshold = ref(0)
  const voiceNoiseFloor = ref(0)
  const voiceDetected = ref(false)

  function voiceDebug(label, payload) {
    void label
    void payload
  }

  const showVoiceStatus = computed(() => {
    return alwaysOnModeEnabled.value || isListening.value || isTranscribing.value || thinking.value
  })

  const isAlwaysOnCapable = computed(() => {
    return isAlwaysOnSupported.value && voiceConfig.value.enabled !== false && voiceConfig.value.always_on_enabled !== false
  })

  const voiceStatusText = computed(() => {
    if (isTranscribing.value) return '正在识别语音...'
    if (alwaysOnModeEnabled.value && voiceState.value === 'barge_in') return '检测到插话，正在打断 AI'
    if (alwaysOnModeEnabled.value && voiceState.value === 'speech_detected') return '检测到说话，正在收集语音'
    if (alwaysOnModeEnabled.value && voiceState.value === 'segment_closing') return '等待停顿结束，准备识别'
    if (alwaysOnModeEnabled.value && isPlaying.value) return 'AI 回答中，可直接打断'
    if (alwaysOnModeEnabled.value) return '监听中，停顿后将自动发送'
    if (isListening.value) return '正在录音...'
    if (thinking.value) return 'AI 正在思考...'
    return '语音已关闭'
  })

  const voiceStatusClass = computed(() => ({
    listening: alwaysOnModeEnabled.value || isListening.value,
    transcribing: isTranscribing.value,
    playing: alwaysOnModeEnabled.value && isPlaying.value
  }))

  const voiceMeterPercent = computed(() => {
    if (!alwaysOnModeEnabled.value) return 0
    const threshold = Math.max(voiceThreshold.value, 0.0001)
    return Math.max(0, Math.min(Math.round((voiceRms.value / threshold) * 100), 100))
  })

  const voiceMeterActive = computed(() => {
    return alwaysOnModeEnabled.value && (voiceDetected.value || voiceRms.value >= voiceThreshold.value)
  })

  const voiceStatusIcon = computed(() => {
    if (isTranscribing.value || thinking.value) return Loading
    if (alwaysOnModeEnabled.value && isPlaying.value) return VideoPlay
    return Microphone
  })

  const voiceActionLabel = computed(() => {
    if (!voiceConfig.value.enabled) {
      return '语音已禁用'
    }

    if (isAlwaysOnCapable.value) {
      if (alwaysOnModeEnabled.value) {
        return isTranscribing.value ? '识别中...' : '关闭常开语音'
      }
      return '开启常开语音'
    }

    if (isListening.value) return '停止录音'
    return isTranscribing.value ? '识别中...' : '点击说话'
  })

  function handleInputChange() {
    if (!suppressInputTracking.value) {
      lastManualInputAt.value = Date.now()
    }
  }

  function setInputMessageSilently(value) {
    suppressInputTracking.value = true
    inputMessage.value = value
    nextTick(() => {
      suppressInputTracking.value = false
    })
  }

  function normalizeRecognizedText(text = '') {
    return String(text || '').replace(/\s+/g, ' ').trim()
  }

  function hasIncompleteTail(text = '') {
    return /[，。、：；]$/.test(text) || /(然后|就是|那个|这个|所以|因为)$/.test(text)
  }

  function shouldDiscardRecognizedText(text = '') {
    if (!text || text.length < 2) return true
    return new Set(voiceConfig.value.short_noise_words || []).has(text)
  }

  function shouldDeferAutoSend(text = '') {
    const minChars = Number(voiceConfig.value.auto_send_min_chars || DEFAULT_VOICE_CONFIG.auto_send_min_chars)
    return text.length < minChars && hasIncompleteTail(text)
  }

  function buildVoiceSessionOptions() {
    return {
      noiseFloorSampleMs: Number(voiceConfig.value.noise_floor_sample_ms),
      speechStartThreshold: Number(voiceConfig.value.speech_start_threshold),
      minSpeechMs: Number(voiceConfig.value.min_speech_ms),
      endSilenceMs: Number(voiceConfig.value.end_silence_ms),
      maxSegmentMs: Number(voiceConfig.value.max_segment_ms),
      preRollMs: Number(voiceConfig.value.pre_roll_ms),
      bargeInMs: Number(voiceConfig.value.barge_in_ms),
      chunkRetentionMs: Number(voiceConfig.value.chunk_retention_ms),
      minThreshold: Number(voiceConfig.value.min_threshold),
      timesliceMs: Number(voiceConfig.value.timeslice_ms)
    }
  }

  async function reportExpressionAudioFromResult({
    segmentId,
    source,
    startedAt,
    endedAt,
    text,
    segmentStats = null
  }) {
    if (!expressionConfig.value.enabled || !interviewId.value) {
      return
    }

    const durationMs = segmentStats?.durationMs ||
      Math.max(0, new Date(endedAt).getTime() - new Date(startedAt).getTime()) ||
      0
    const speechDurationMs = segmentStats?.speechDurationMs || durationMs
    const payload = buildAudioExpressionPayload({
      segmentId,
      stage: currentStage.value || '',
      source,
      startedAt,
      endedAt,
      transcriptText: text,
      durationMs,
      speechDurationMs,
      avgVolume: source === 'always_on_voice' ? voiceRms.value : 0,
      volumeVariation: source === 'always_on_voice'
        ? Math.abs(Number(voiceRms.value || 0) - Number(voiceNoiseFloor.value || 0))
        : 0,
      interruptionRecoveryMs: segmentStats?.bargeInTriggered ? Number(voiceConfig.value.barge_in_ms || 0) : 0
    })

    try {
      await reportAudioExpressionSegment(interviewId.value, payload)
    } catch (error) {
      console.error('上传音频表达特征失败:', error)
    }
  }

  function ensureExpressionVideoReporter() {
    if (!expressionConfig.value.enabled || expressionVideoReporter.value || !interviewId.value) {
      return
    }

    expressionVideoReporter.value = createVideoExpressionReporter({
      interviewId: interviewId.value,
      getStage: () => currentStage.value || '',
      getVideoElement: () => userCameraRef.value?.getVideoElement?.(),
      intervalMs: Number(expressionConfig.value.video_sample_interval_ms || 1500)
    })
  }

  async function loadExpressionRuntimeConfig() {
    try {
      expressionConfig.value = {
        ...expressionConfig.value,
        ...(await loadExpressionConfig())
      }
    } catch (error) {
      console.error('加载表达分析配置失败:', error)
    }
  }

  async function enqueueVoiceSegment(segment) {
    voiceQueue.value.push(segment)
    await processVoiceQueue()
  }

  async function processVoiceQueue() {
    if (voiceQueueBusy.value || isTranscribing.value || thinking.value) {
      return
    }

    const nextSegment = voiceQueue.value.shift()
    if (!nextSegment) {
      return
    }

    voiceQueueBusy.value = true
    isTranscribing.value = true
    voiceState.value = 'transcribing'

    try {
      const result = await transcribeAudio(nextSegment.blob, {
        segment_id: nextSegment.stats.segmentId,
        client_started_at: nextSegment.stats.startedAt,
        client_ended_at: nextSegment.stats.endedAt,
        source: 'always_on_voice'
      })

      const text = normalizeRecognizedText(result?.text)
      await reportExpressionAudioFromResult({
        segmentId: nextSegment.stats.segmentId,
        source: 'always_on_voice',
        startedAt: nextSegment.stats.startedAt,
        endedAt: nextSegment.stats.endedAt,
        text,
        segmentStats: nextSegment.stats
      })

      if (shouldDiscardRecognizedText(text)) {
        return
      }

      const userHasDraft = Boolean(inputMessage.value.trim())
      const userIsTyping = Date.now() - lastManualInputAt.value < Number(
        voiceConfig.value.typing_grace_ms || DEFAULT_VOICE_CONFIG.typing_grace_ms
      )
      const shouldAutoSend = Boolean(result?.should_auto_send) && !shouldDeferAutoSend(text)

      if (shouldAutoSend && !userHasDraft && !userIsTyping) {
        await sendInterviewContent(text, 'always_on_voice')
        return
      }

      if (userHasDraft || userIsTyping) {
        ElMessage.info('检测到已有输入，语音识别结果未自动覆盖')
        return
      }

      setInputMessageSilently(text)
      ElMessage.info('语音已识别，可确认后发送')
    } catch (error) {
      console.error('语音识别失败:', error)
      ElMessage.error(`语音识别失败: ${error.message}`)
    } finally {
      isTranscribing.value = false
      voiceQueueBusy.value = false
      if (alwaysOnModeEnabled.value) {
        voiceState.value = isPlaying.value ? 'assistant_playing' : 'armed'
      }
      if (voiceQueue.value.length > 0 && !thinking.value) {
        processVoiceQueue()
      }
    }
  }

  async function initSpeechRecognition() {
    asrRecorder.value = new ASRRecorder()
    isSpeechSupported.value = asrRecorder.value.supported
    isAlwaysOnSupported.value = Boolean(
      asrRecorder.value.supported &&
      (window.AudioContext || window.webkitAudioContext)
    )

    try {
      const runtimeVoiceConfig = await interviewApi.getVoiceConfig()
      voiceConfig.value = {
        ...DEFAULT_VOICE_CONFIG,
        ...(runtimeVoiceConfig || {})
      }
    } catch (error) {
      console.error('加载语音配置失败:', error)
      voiceConfig.value = { ...DEFAULT_VOICE_CONFIG }
    }

    try {
      const status = await checkASRStatus()
      asrServiceAvailable.value = status.available
      if (!status.available) {
        ElMessage.warning({
          message: '语音识别服务未配置，请联系管理员',
          duration: 5000,
          showClose: true
        })
      }
    } catch (error) {
      asrServiceAvailable.value = false
    }

    if (isAlwaysOnSupported.value) {
      voiceSession.value = createVoiceSessionController({
        ...buildVoiceSessionOptions(),
        onSegmentReady: (blob, stats) => {
          enqueueVoiceSegment({ blob, stats })
        },
        onSpeechStateChange: ({ state, rms, threshold, noiseFloor, voiceActive }) => {
          voiceState.value = state
          voiceRms.value = Number(rms || 0)
          voiceThreshold.value = Number(threshold || 0)
          voiceNoiseFloor.value = Number(noiseFloor || 0)
          voiceDetected.value = Boolean(
            voiceActive || state === 'speech_detected' || state === 'segment_closing' || state === 'barge_in'
          )
        },
        onBargeIn: () => {
          stopAssistantPlayback()
        },
        shouldDetectBargeIn: () => isPlaying.value
      })
    }

    if (!isSpeechSupported.value) {
      ElMessage.info({
        message: '当前浏览器不支持录音功能，请使用 Chrome、Edge 或 Firefox',
        duration: 3000,
        showClose: true
      })
    }
  }

  function toggleSpeechRecognition() {
    if (!voiceConfig.value.enabled) {
      ElMessage.warning('语音能力已在配置中禁用')
      return
    }

    if (isAlwaysOnCapable.value) {
      if (alwaysOnModeEnabled.value) {
        stopAlwaysOnVoice()
      } else {
        startAlwaysOnVoice()
      }
      return
    }

    if (isListening.value) {
      stopSpeechRecognition()
    } else {
      startSpeechRecognition()
    }
  }

  async function startAlwaysOnVoice() {
    if (!isAlwaysOnSupported.value) {
      ElMessage.warning('当前浏览器不支持常开语音，请改用点击说话')
      return
    }
    if (!voiceConfig.value.enabled || !voiceConfig.value.always_on_enabled) {
      ElMessage.warning('常开语音已在配置中禁用')
      return
    }
    if (!asrServiceAvailable.value) {
      ElMessage.warning('语音识别服务不可用，请检查后端配置')
      return
    }

    try {
      await voiceSession.value?.startAlwaysOn()
      alwaysOnModeEnabled.value = true
      voiceState.value = 'armed'
      const status = voiceSession.value?.getStatus?.()
      voiceRms.value = Number(status?.rms || 0)
      voiceThreshold.value = Number(status?.threshold || 0)
      voiceNoiseFloor.value = Number(status?.noiseFloor || 0)
      voiceDetected.value = false
      ElMessage.success('常开语音已开启')
    } catch (error) {
      console.error('开启常开语音失败:', error)
      ElMessage.error(`开启常开语音失败: ${error.message}`)
    }
  }

  async function stopAlwaysOnVoice() {
    try {
      await voiceSession.value?.stopAlwaysOn()
    } catch (error) {
      console.error('关闭常开语音失败:', error)
    } finally {
      alwaysOnModeEnabled.value = false
      voiceState.value = 'idle'
      voiceQueue.value = []
      isTranscribing.value = false
      voiceQueueBusy.value = false
      voiceRms.value = 0
      voiceThreshold.value = 0
      voiceNoiseFloor.value = 0
      voiceDetected.value = false
    }
  }

  async function startSpeechRecognition() {
    if (!voiceConfig.value.enabled) {
      ElMessage.warning('语音能力已在配置中禁用')
      return
    }
    if (!isSpeechSupported.value) {
      ElMessage.warning('当前浏览器不支持录音功能')
      return
    }
    if (!asrRecorder.value) {
      ElMessage.error('录音器未初始化')
      return
    }
    if (!asrServiceAvailable.value) {
      ElMessage.warning('语音识别服务不可用，请检查后端配置')
      return
    }

    try {
      isListening.value = true
      voiceState.value = 'speech_detected'
      manualRecordingStartedAt.value = new Date().toISOString()
      ElMessage.info({
        message: '正在录音...点击停止按钮结束',
        duration: 3000
      })
      await asrRecorder.value.startRecording()
    } catch (error) {
      console.error('启动录音失败:', error)
      ElMessage.error({
        message: `启动录音失败: ${error.message}`,
        duration: 3000
      })
      isListening.value = false
    }
  }

  async function stopSpeechRecognition() {
    if (!asrRecorder.value || !isListening.value) {
      return
    }

    try {
      const audioBlob = await asrRecorder.value.stopRecording()
      if (!audioBlob || audioBlob.size === 0) {
        ElMessage.warning({
          message: '未录制到音频',
          duration: 1500
        })
        isListening.value = false
        return
      }

      isTranscribing.value = true
      isListening.value = false
      voiceState.value = 'transcribing'

      ElMessage.info({
        message: '正在识别语音...',
        duration: 2000,
        iconClass: 'el-icon-loading'
      })

      const result = await transcribeAudio(audioBlob, { source: 'manual_voice' })
      const text = normalizeRecognizedText(result?.text)
      await reportExpressionAudioFromResult({
        segmentId: result?.segment_id || `manual-${Date.now()}`,
        source: 'manual_voice',
        startedAt: manualRecordingStartedAt.value || new Date().toISOString(),
        endedAt: new Date().toISOString(),
        text,
        segmentStats: {
          durationMs: Number(result?.duration_ms || 0),
          speechDurationMs: Number(result?.duration_ms || 0),
          bargeInTriggered: false
        }
      })

      if (text) {
        setInputMessageSilently(text)
        ElMessage.success({
          message: '识别完成',
          duration: 1500
        })

        nextTick(() => {
          const textarea = document.querySelector('.input-area textarea')
          textarea?.focus()
        })
      } else {
        ElMessage.warning({
          message: '未识别到文字',
          duration: 1500
        })
      }
    } catch (error) {
      console.error('语音识别失败:', error)
      ElMessage.error({
        message: `语音识别失败: ${error.message}`,
        duration: 3000
      })
    } finally {
      manualRecordingStartedAt.value = ''
      isListening.value = false
      isTranscribing.value = false
      if (!alwaysOnModeEnabled.value) {
        voiceState.value = 'idle'
      }
    }
  }

  function handleCameraStarted(stream) {
    void stream
    ensureExpressionVideoReporter()
    expressionVideoReporter.value?.start?.()
  }

  function handleCameraStopped() {
    expressionVideoReporter.value?.stop?.()
  }

  function handleCameraError(error) {
    console.error('摄像头错误', error)
  }

  async function cleanupVoiceRuntime() {
    expressionVideoReporter.value?.stop?.()
    if (alwaysOnModeEnabled.value) {
      await stopAlwaysOnVoice()
    }
    if (asrRecorder.value?.isRecording) {
      asrRecorder.value.cancelRecording()
    }
  }

  function syncAssistantPlaybackState(playing) {
    if (!alwaysOnModeEnabled.value || isTranscribing.value) {
      return
    }
    voiceState.value = playing ? 'assistant_playing' : 'armed'
  }

  return {
    voiceConfig,
    isListening,
    isTranscribing,
    isSpeechSupported,
    isAlwaysOnSupported,
    asrServiceAvailable,
    alwaysOnModeEnabled,
    voiceState,
    voiceQueue,
    voiceRms,
    voiceThreshold,
    voiceNoiseFloor,
    voiceDetected,
    showVoiceStatus,
    isAlwaysOnCapable,
    voiceStatusText,
    voiceStatusClass,
    voiceMeterPercent,
    voiceMeterActive,
    voiceStatusIcon,
    voiceActionLabel,
    handleInputChange,
    initSpeechRecognition,
    toggleSpeechRecognition,
    startAlwaysOnVoice,
    stopAlwaysOnVoice,
    startSpeechRecognition,
    stopSpeechRecognition,
    loadExpressionRuntimeConfig,
    handleCameraStarted,
    handleCameraStopped,
    handleCameraError,
    cleanupVoiceRuntime,
    processVoiceQueue,
    syncAssistantPlaybackState
  }
}
