<template>
  <div class="test-digital-human">
    <div class="page-header">
      <h1>讯飞数字人交互测试</h1>
      <p>验证打断、常开语音、ASR 过滤和状态机是否自然。</p>
    </div>

    <div class="main-content">
      <div class="left-panel">
        <el-card shadow="never">
          <div class="panel-title">数字人会话</div>
          <el-button
            type="primary"
            size="large"
            style="width: 100%"
            :loading="starting"
            :disabled="isStarted"
            @click="startDigitalHuman"
          >
            {{ isStarted ? '数字人已启动' : '启动数字人' }}
          </el-button>

          <el-button
            v-if="isStarted"
            type="danger"
            size="large"
            style="width: 100%; margin-top: 12px"
            @click="stopDigitalHuman"
          >
            关闭数字人
          </el-button>

          <div class="status-grid">
            <div class="status-item">
              <span class="label">会话状态</span>
              <el-tag :type="conversationStateTagType">{{ conversationStateLabel }}</el-tag>
            </div>
            <div class="status-item">
              <span class="label">数字人状态</span>
              <el-tag :type="avatarStatusTagType">{{ avatarStatusLabel }}</el-tag>
            </div>
            <div class="status-item">
              <span class="label">抢话触发</span>
              <el-tag :type="lastBargeInTriggered ? 'warning' : 'info'">
                {{ lastBargeInTriggered ? '已触发' : '未触发' }}
              </el-tag>
            </div>
            <div class="status-item">
              <span class="label">ASR 服务</span>
              <el-tag :type="asrAvailable ? 'success' : 'danger'">
                {{ asrAvailable ? '可用' : '不可用' }}
              </el-tag>
            </div>
          </div>
        </el-card>

        <el-card shadow="never">
          <div class="panel-title">输入控制</div>

          <el-input
            v-model="userInput"
            type="textarea"
            :rows="4"
            placeholder="输入候选人回答，或开启常开语音直接说话"
            :disabled="!isStarted || isManualInputDisabled"
            @keydown.enter.ctrl.prevent="sendManualMessage"
          />

          <div class="actions-row">
            <el-button
              type="primary"
              :loading="isProcessing"
              :disabled="!isStarted || !userInput.trim() || isManualInputDisabled"
              @click="sendManualMessage"
            >
              {{ isProcessing ? '处理中...' : '发送文本' }}
            </el-button>

            <el-button
              :type="alwaysOnEnabled ? 'danger' : 'success'"
              :disabled="!isStarted || !voiceSupported || !asrAvailable"
              @click="toggleAlwaysOnVoice"
            >
              {{ alwaysOnEnabled ? '关闭常开语音' : '开启常开语音' }}
            </el-button>

            <el-button
              type="warning"
              :disabled="conversationState !== SESSION_STATES.ASSISTANT_SPEAKING"
              @click="interruptAssistant"
            >
              手动打断
            </el-button>
          </div>

          <div class="meta-list">
            <div class="meta-item">
              <span>最近一次 ASR</span>
              <strong>{{ lastAsrText || '暂无' }}</strong>
            </div>
            <div class="meta-item">
              <span>最近一次丢弃原因</span>
              <strong>{{ lastDiscardReason || '暂无' }}</strong>
            </div>
            <div class="meta-item">
              <span>待处理语音段</span>
              <strong>{{ voiceQueue.length }}</strong>
            </div>
            <div class="meta-item">
              <span>VAD 状态</span>
              <strong>{{ voiceState }}</strong>
            </div>
          </div>

          <div v-if="alwaysOnEnabled" class="voice-meter-panel">
            <div class="voice-meter-track">
              <div class="voice-meter-fill" :style="{ width: `${voiceMeterPercent}%` }"></div>
            </div>
            <div class="voice-meter-meta">
              <span>RMS {{ voiceRms.toFixed(4) }}</span>
              <span>阈值 {{ voiceThreshold.toFixed(4) }}</span>
              <span>底噪 {{ voiceNoiseFloor.toFixed(4) }}</span>
            </div>
          </div>
        </el-card>

        <el-card shadow="never">
          <div class="panel-title">对话记录</div>
          <div class="chat-history">
            <div
              v-for="message in chatMessages"
              :key="message.id"
              :class="['chat-message', message.role]"
            >
              <div class="message-content">
                <div class="message-text">{{ message.content }}</div>
                <div class="message-meta">
                  <span>{{ message.source || '-' }}</span>
                  <span>{{ message.deliveryStatus || '-' }}</span>
                  <span v-if="message.bargeInTriggered">barge-in</span>
                  <span v-if="message.interruptedAt">中断于 {{ message.interruptedAt }}</span>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <div class="right-panel">
        <DigitalAvatar
          v-if="isStarted && digitalHumanConfig"
          ref="digitalHumanRef"
          :session-id="sessionId"
          :digital-human-config="digitalHumanConfig"
          :provider="provider"
          @ready="handleAvatarReady"
          @error="handleAvatarError"
          @status-change="handleAvatarStatusChange"
        />
        <div v-else class="placeholder">
          <p>请先启动数字人</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import DigitalAvatar from '@/components/DigitalAvatar.vue'
import voiceController from '@/utils/voiceController.ts'
import { createVoiceSessionController } from '@/utils/voiceSessionController.ts'
import { checkASRStatus, transcribeAudio } from '@/utils/asrRecorder.ts'
import { interviewApi } from '@/api/interview'

const SESSION_STATES = {
  IDLE: 'idle',
  ASSISTANT_THINKING: 'assistant_thinking',
  ASSISTANT_SPEAKING: 'assistant_speaking',
  CANDIDATE_READY: 'candidate_ready',
  CANDIDATE_SPEAKING: 'candidate_speaking',
  CANDIDATE_PROCESSING: 'candidate_processing'
}

const DEFAULT_VOICE_CONFIG = {
  enabled: true,
  always_on_enabled: true,
  speech_start_threshold: 1.6,
  min_speech_ms: 220,
  end_silence_ms: 750,
  max_segment_ms: 15000,
  pre_roll_ms: 300,
  barge_in_ms: 250,
  min_threshold: 0.0015,
  auto_send_min_chars: 8,
  typing_grace_ms: 1200,
  short_noise_words: ['嗯', '啊', '哦', '额', '呃', '唉']
}

const sessionId = ref(null)
const digitalHumanConfig = ref(null)
const provider = ref('xunfei')
const isStarted = ref(false)
const starting = ref(false)
const digitalHumanRef = ref(null)

const chatMessages = ref([])
const userInput = ref('')
const isProcessing = ref(false)
const conversationState = ref(SESSION_STATES.IDLE)
const avatarStatus = ref('IDLE')
const currentAssistantMessageId = ref(null)
const pendingAssistantFinish = ref(null)

const voiceConfig = ref({ ...DEFAULT_VOICE_CONFIG })
const voiceSupported = ref(false)
const asrAvailable = ref(false)
const alwaysOnEnabled = ref(false)
const voiceSession = ref(null)
const voiceQueue = ref([])
const voiceQueueBusy = ref(false)
const voiceState = ref('idle')
const voiceRms = ref(0)
const voiceThreshold = ref(0)
const voiceNoiseFloor = ref(0)

const lastAsrText = ref('')
const lastDiscardReason = ref('')
const lastBargeInTriggered = ref(false)
const bargeInGuard = ref(false)
const lastManualInputAt = ref(0)
const ignoreVoiceResultBefore = ref(0)

const isManualInputDisabled = computed(() => isProcessing.value)

const conversationStateLabel = computed(() => {
  const labels = {
    [SESSION_STATES.IDLE]: '空闲',
    [SESSION_STATES.ASSISTANT_THINKING]: '面试官思考中',
    [SESSION_STATES.ASSISTANT_SPEAKING]: '面试官说话中',
    [SESSION_STATES.CANDIDATE_READY]: '等待候选人',
    [SESSION_STATES.CANDIDATE_SPEAKING]: '候选人说话中',
    [SESSION_STATES.CANDIDATE_PROCESSING]: '候选人语音处理中'
  }
  return labels[conversationState.value] || conversationState.value
})

const conversationStateTagType = computed(() => {
  if (conversationState.value === SESSION_STATES.ASSISTANT_SPEAKING) return 'warning'
  if (conversationState.value === SESSION_STATES.ASSISTANT_THINKING) return 'info'
  if (conversationState.value === SESSION_STATES.CANDIDATE_SPEAKING) return 'success'
  if (conversationState.value === SESSION_STATES.CANDIDATE_PROCESSING) return 'primary'
  return ''
})

const avatarStatusLabel = computed(() => {
  const labels = {
    IDLE: '空闲',
    THINKING: '思考中',
    SPEAKING: '说话中',
    LISTENING: '倾听中',
    INTERRUPTED: '已打断'
  }
  return labels[avatarStatus.value] || avatarStatus.value
})

const avatarStatusTagType = computed(() => {
  if (avatarStatus.value === 'SPEAKING') return 'warning'
  if (avatarStatus.value === 'INTERRUPTED') return 'danger'
  if (avatarStatus.value === 'LISTENING') return 'success'
  return 'info'
})

const voiceMeterPercent = computed(() => {
  if (!alwaysOnEnabled.value) return 0
  const threshold = Math.max(voiceThreshold.value, 0.0001)
  const ratio = Math.min((voiceRms.value / threshold) * 100, 100)
  return Number.isFinite(ratio) ? ratio : 0
})

const isAssistantSpeakingActive = computed(() => {
  return avatarStatus.value === 'SPEAKING' || conversationState.value === SESSION_STATES.ASSISTANT_SPEAKING
})

function createMessage(role, content, extra = {}) {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role,
    content,
    deliveryStatus: role === 'assistant' ? 'thinking' : 'completed',
    source: extra.source || '',
    interruptedAt: '',
    bargeInTriggered: false
  }
}

function buildChatHistoryPayload() {
  return chatMessages.value
    .filter(message => ['user', 'assistant'].includes(message.role))
    .filter(message => {
      const content = String(message.content || '').trim()
      return content && content !== '...'
    })
    .map(message => ({
      role: message.role,
      content: String(message.content || '').trim()
    }))
    .slice(-12)
}

function setConversationState(nextState) {
  conversationState.value = nextState
  if (nextState === SESSION_STATES.ASSISTANT_THINKING) {
    avatarStatus.value = 'THINKING'
  }
  if (nextState === SESSION_STATES.CANDIDATE_READY) {
    avatarStatus.value = 'LISTENING'
  }
}

function getCurrentAssistantMessage() {
  if (!currentAssistantMessageId.value) return null
  return chatMessages.value.find(message => message.id === currentAssistantMessageId.value) || null
}

function markCurrentAssistantMessage(patch) {
  const message = getCurrentAssistantMessage()
  if (!message) return
  Object.assign(message, patch)
}

function finalizeCurrentAssistantMessage(status) {
  markCurrentAssistantMessage({ deliveryStatus: status })
  currentAssistantMessageId.value = null
  pendingAssistantFinish.value = null
}

function clearPendingVoiceSegments() {
  voiceQueue.value = []
  lastDiscardReason.value = ''
}

function stopPlayback() {
  voiceController.stop()
}

function normalizeRecognizedText(value) {
  return String(value || '')
    .replace(/\s+/g, ' ')
    .replace(/[。！？.!?]+$/g, match => match[0])
    .trim()
}

function hasIncompleteTail(text) {
  return !/[。！？.!?]$/.test(text)
}

function shouldDiscardRecognizedText(text, stats = {}) {
  if (!text) {
    return 'ASR 结果为空'
  }

  const shortNoiseWords = new Set(voiceConfig.value.short_noise_words || [])
  if (shortNoiseWords.has(text)) {
    return '命中短噪声词'
  }

  if (stats.speechDurationMs && stats.speechDurationMs < Number(voiceConfig.value.min_speech_ms || DEFAULT_VOICE_CONFIG.min_speech_ms)) {
    return '语音时长不足'
  }

  if (text.length < Number(voiceConfig.value.auto_send_min_chars || DEFAULT_VOICE_CONFIG.auto_send_min_chars) && hasIncompleteTail(text)) {
    userInput.value = text
    return '文本过短且尾部不完整，已回填输入框'
  }

  return ''
}

function resetVoiceMeters() {
  voiceState.value = 'idle'
  voiceRms.value = 0
  voiceThreshold.value = 0
  voiceNoiseFloor.value = 0
}

async function loadVoiceCapabilities() {
  voiceSupported.value = Boolean(navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined')

  try {
    const config = await interviewApi.getVoiceConfig()
    voiceConfig.value = {
      ...DEFAULT_VOICE_CONFIG,
      ...config
    }
  } catch (error) {
    console.warn('load voice config failed:', error)
    voiceConfig.value = { ...DEFAULT_VOICE_CONFIG }
  }

  try {
    const status = await checkASRStatus()
    asrAvailable.value = Boolean(status?.available)
  } catch (error) {
    console.warn('check ASR status failed:', error)
    asrAvailable.value = false
  }

  if (!voiceSupported.value) {
    return
  }

  voiceSession.value = createVoiceSessionController({
    noiseFloorSampleMs: Number(voiceConfig.value.noise_floor_sample_ms || 800),
    speechStartThreshold: Number(voiceConfig.value.speech_start_threshold),
    minSpeechMs: Number(voiceConfig.value.min_speech_ms),
    endSilenceMs: Number(voiceConfig.value.end_silence_ms),
    maxSegmentMs: Number(voiceConfig.value.max_segment_ms || 15000),
    preRollMs: Number(voiceConfig.value.pre_roll_ms || 300),
    bargeInMs: Number(voiceConfig.value.barge_in_ms),
    minThreshold: Number(voiceConfig.value.min_threshold),
    onSegmentReady: (blob, stats) => {
      voiceQueue.value.push({ blob, stats, createdAt: Date.now() })
      void processVoiceQueue()
    },
    onSpeechStateChange: ({ state, rms, threshold, noiseFloor }) => {
      voiceState.value = state
      voiceRms.value = Number(rms || 0)
      voiceThreshold.value = Number(threshold || 0)
      voiceNoiseFloor.value = Number(noiseFloor || 0)

      if (state === 'barge_in') {
        setConversationState(SESSION_STATES.CANDIDATE_SPEAKING)
        return
      }

      if (state === 'speech_detected' && !isAssistantSpeakingActive.value) {
        setConversationState(SESSION_STATES.CANDIDATE_SPEAKING)
      }
    },
    onBargeIn: () => {
      void handleBargeIn()
    },
    shouldDetectBargeIn: () => isAssistantSpeakingActive.value
  })
}

async function startDigitalHuman() {
  starting.value = true

  try {
    if (!voiceSession.value) {
      await loadVoiceCapabilities()
    }

    const response = await fetch('/api/test/avatar-session', {
      method: 'POST'
    })
    const data = await response.json()

    if (!data.success) {
      throw new Error(data.error || '启动失败')
    }

    sessionId.value = data.session_id
    digitalHumanConfig.value = data.config
    provider.value = data.provider
    isStarted.value = true
    setConversationState(SESSION_STATES.IDLE)

    await nextTick()
    ElMessage.success('数字人启动成功')
  } catch (error) {
    ElMessage.error(`启动失败: ${error.message}`)
  } finally {
    starting.value = false
  }
}

async function stopAlwaysOnVoice() {
  if (voiceSession.value) {
    await voiceSession.value.stopAlwaysOn()
  }
  alwaysOnEnabled.value = false
  voiceQueue.value = []
  voiceQueueBusy.value = false
  resetVoiceMeters()
}

async function stopDigitalHuman() {
  await stopAlwaysOnVoice()
  stopPlayback()

  if (digitalHumanRef.value) {
    await digitalHumanRef.value.destroy()
  }

  sessionId.value = null
  digitalHumanConfig.value = null
  isStarted.value = false
  chatMessages.value = []
  userInput.value = ''
  currentAssistantMessageId.value = null
  pendingAssistantFinish.value = null
  lastAsrText.value = ''
  lastDiscardReason.value = ''
  lastBargeInTriggered.value = false
  bargeInGuard.value = false
  setConversationState(SESSION_STATES.IDLE)
  avatarStatus.value = 'IDLE'
}

async function handleAvatarReady() {
  avatarStatus.value = 'LISTENING'
  if (isStarted.value) {
    setConversationState(SESSION_STATES.CANDIDATE_READY)
  }
}

function handleAvatarError(error) {
  console.error('avatar error:', error)
  avatarStatus.value = 'IDLE'
  ElMessage.error(`数字人异常: ${error?.message || '未知错误'}`)
}

function handleAvatarStatusChange(status) {
  avatarStatus.value = status

  if (status === 'SPEAKING') {
    pendingAssistantFinish.value = 'normal'
    markCurrentAssistantMessage({
      deliveryStatus: 'speaking'
    })
    setConversationState(SESSION_STATES.ASSISTANT_SPEAKING)
    return
  }

  if (status !== 'LISTENING') {
    return
  }

  const message = getCurrentAssistantMessage()

  if (pendingAssistantFinish.value === 'interrupted' || message?.deliveryStatus === 'interrupted') {
    finalizeCurrentAssistantMessage('interrupted')
    if (conversationState.value !== SESSION_STATES.CANDIDATE_SPEAKING && conversationState.value !== SESSION_STATES.ASSISTANT_THINKING) {
      setConversationState(SESSION_STATES.CANDIDATE_READY)
    }
    return
  }

  if (conversationState.value === SESSION_STATES.ASSISTANT_SPEAKING || message?.deliveryStatus === 'speaking') {
    finalizeCurrentAssistantMessage('completed')
    setConversationState(SESSION_STATES.CANDIDATE_READY)
  }
}

async function interruptAssistant({ bargeInTriggered = false, nextState = SESSION_STATES.CANDIDATE_READY } = {}) {
  if (!isAssistantSpeakingActive.value) {
    return false
  }

  pendingAssistantFinish.value = 'interrupted'
  stopPlayback()
  markCurrentAssistantMessage({
    deliveryStatus: 'interrupted',
    interruptedAt: new Date().toLocaleTimeString(),
    bargeInTriggered
  })
  avatarStatus.value = 'INTERRUPTED'
  setConversationState(nextState)

  if (digitalHumanRef.value) {
    await digitalHumanRef.value.interrupt()
  }

  return true
}

async function handleBargeIn() {
  if (!isAssistantSpeakingActive.value || bargeInGuard.value) {
    return
  }

  bargeInGuard.value = true
  lastBargeInTriggered.value = true

  try {
    await interruptAssistant({
      bargeInTriggered: true,
      nextState: SESSION_STATES.CANDIDATE_SPEAKING
    })
  } finally {
    window.setTimeout(() => {
      bargeInGuard.value = false
    }, 300)
  }
}

async function callTestChat(content, history = []) {
  const response = await fetch('/api/test/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, history })
  })

  if (!response.ok) {
    throw new Error('请求失败')
  }

  return await response.json()
}

async function sendMessage(content, source = 'manual_text') {
  const normalizedContent = String(content || '').trim()
  if (!normalizedContent || isProcessing.value) return

  if (isAssistantSpeakingActive.value) {
    await interruptAssistant({
      bargeInTriggered: source !== 'manual_text'
    })
  }

  if (source === 'manual_text') {
    ignoreVoiceResultBefore.value = Date.now()
  }
  clearPendingVoiceSegments()
  lastManualInputAt.value = Date.now()

  const history = buildChatHistoryPayload()

  const userMessage = createMessage('user', normalizedContent, { source })
  chatMessages.value.push(userMessage)
  userInput.value = ''

  const assistantMessage = createMessage('assistant', '...', { source })
  assistantMessage.deliveryStatus = 'thinking'
  chatMessages.value.push(assistantMessage)
  currentAssistantMessageId.value = assistantMessage.id
  pendingAssistantFinish.value = null

  isProcessing.value = true
  setConversationState(SESSION_STATES.ASSISTANT_THINKING)

  try {
    const data = await callTestChat(normalizedContent, history)
    assistantMessage.content = data.reply || ''

    if (digitalHumanRef.value && data.reply) {
      assistantMessage.deliveryStatus = 'speaking'
      Promise.resolve(digitalHumanRef.value.speakText(data.reply)).catch(error => {
        assistantMessage.content = `发送失败: ${error.message}`
        finalizeCurrentAssistantMessage('completed')
        setConversationState(SESSION_STATES.CANDIDATE_READY)
        ElMessage.error(`发送失败: ${error.message}`)
      })
    } else {
      finalizeCurrentAssistantMessage('completed')
      setConversationState(SESSION_STATES.CANDIDATE_READY)
    }
  } catch (error) {
    assistantMessage.content = `发送失败: ${error.message}`
    finalizeCurrentAssistantMessage('completed')
    setConversationState(SESSION_STATES.CANDIDATE_READY)
    ElMessage.error(`发送失败: ${error.message}`)
  } finally {
    isProcessing.value = false
  }
}

async function sendManualMessage() {
  await sendMessage(userInput.value, 'manual_text')
}

async function processVoiceQueue() {
  if (voiceQueueBusy.value || !voiceQueue.value.length || isProcessing.value) {
    return
  }

  const nextSegment = voiceQueue.value.shift()
  if (!nextSegment) {
    return
  }

  voiceQueueBusy.value = true
  setConversationState(SESSION_STATES.CANDIDATE_PROCESSING)

  try {
    if (nextSegment.createdAt < ignoreVoiceResultBefore.value) {
      lastDiscardReason.value = '手动发送优先，旧语音段已忽略'
      setConversationState(SESSION_STATES.CANDIDATE_READY)
      return
    }

    const result = await transcribeAudio(nextSegment.blob, {
      source: 'always_on_voice'
    })

    if (nextSegment.createdAt < ignoreVoiceResultBefore.value) {
      lastDiscardReason.value = '手动发送优先，转写结果已忽略'
      setConversationState(SESSION_STATES.CANDIDATE_READY)
      return
    }

    const text = normalizeRecognizedText(result?.text || result?.transcript || '')
    lastAsrText.value = text

    const discardReason = shouldDiscardRecognizedText(text, nextSegment.stats)
    if (discardReason) {
      lastDiscardReason.value = discardReason
      setConversationState(SESSION_STATES.CANDIDATE_READY)
      return
    }

    const userIsTyping =
      Date.now() - lastManualInputAt.value <
      Number(voiceConfig.value.typing_grace_ms || DEFAULT_VOICE_CONFIG.typing_grace_ms)

    if (userIsTyping) {
      lastDiscardReason.value = '用户最近正在键入，已回填输入框'
      userInput.value = text
      setConversationState(SESSION_STATES.CANDIDATE_READY)
      return
    }

    await sendMessage(text, 'always_on_voice')
  } catch (error) {
    lastDiscardReason.value = `ASR 失败: ${error.message}`
    setConversationState(SESSION_STATES.CANDIDATE_READY)
    ElMessage.error(`语音识别失败: ${error.message}`)
  } finally {
    voiceQueueBusy.value = false
    if (voiceQueue.value.length > 0 && !isProcessing.value) {
      void processVoiceQueue()
    }
  }
}

async function toggleAlwaysOnVoice() {
  if (!voiceSession.value) {
    await loadVoiceCapabilities()
  }

  if (!voiceSession.value || !voiceSupported.value) {
    ElMessage.error('当前浏览器不支持常开语音')
    return
  }

  if (!asrAvailable.value) {
    ElMessage.error('ASR 服务当前不可用')
    return
  }

  if (alwaysOnEnabled.value) {
    await stopAlwaysOnVoice()
    if (isStarted.value) {
      setConversationState(SESSION_STATES.CANDIDATE_READY)
    }
    return
  }

  await voiceSession.value.startAlwaysOn()
  alwaysOnEnabled.value = true
  if (isStarted.value && conversationState.value !== SESSION_STATES.ASSISTANT_SPEAKING) {
    setConversationState(SESSION_STATES.CANDIDATE_READY)
  }
}

onBeforeUnmount(async () => {
  stopPlayback()
  if (voiceSession.value) {
    await voiceSession.value.stopAlwaysOn()
  }
})
</script>

<style scoped>
.test-digital-human {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0 0 8px;
  font-size: 28px;
}

.page-header p {
  margin: 0;
  color: #4b5563;
}

.main-content {
  display: grid;
  grid-template-columns: minmax(360px, 460px) minmax(0, 1fr);
  gap: 24px;
  align-items: stretch;
}

.left-panel,
.right-panel {
  min-width: 0;
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.left-panel :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.status-grid,
.meta-list {
  display: grid;
  gap: 12px;
}

.status-item,
.meta-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
}

.status-item .label,
.meta-item span {
  color: #4b5563;
}

.actions-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.voice-meter-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.voice-meter-track {
  height: 10px;
  border-radius: 999px;
  overflow: hidden;
  background: #dbe5f0;
}

.voice-meter-fill {
  height: 100%;
  background: linear-gradient(90deg, #22c55e 0%, #f59e0b 70%, #ef4444 100%);
  transition: width 0.12s ease;
}

.voice-meter-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: #6b7280;
}

.chat-history {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 420px;
  overflow-y: auto;
}

.chat-message {
  display: flex;
}

.chat-message.user {
  justify-content: flex-end;
}

.chat-message.assistant {
  justify-content: flex-start;
}

.message-content {
  max-width: 90%;
  padding: 12px 14px;
  border-radius: 16px;
  background: #eef2ff;
}

.chat-message.user .message-content {
  background: #dcfce7;
}

.message-text {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
  color: #111827;
}

.message-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}

.right-panel {
  min-height: 720px;
}

.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 720px;
  border-radius: 24px;
  background: linear-gradient(180deg, #e2e8f0 0%, #cbd5e1 100%);
  color: #475569;
  font-size: 18px;
}

@media (max-width: 1024px) {
  .main-content {
    grid-template-columns: 1fr;
  }

  .right-panel,
  .placeholder {
    min-height: 560px;
  }
}
</style>
