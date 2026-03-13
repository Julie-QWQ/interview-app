<template>
  <div class="interview-detail-wrapper">
    <!-- 顶部导航栏 -->
    <div class="top-navbar">
      <div class="navbar-left">
        <el-button @click="$router.back()" class="back-button" circle>
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <div class="interview-title">
          <h1>{{ currentInterview?.candidate_name }} - {{ currentInterview?.position }}</h1>
          <el-tag v-if="currentInterview" :type="getStatusType(currentInterview.status)" size="small">
            {{ getStatusText(currentInterview.status) }}
          </el-tag>
        </div>
      </div>
      <div class="navbar-right">
        <el-button
          v-if="currentInterview?.status === 'created'"
          type="primary"
          @click="handleStart"
          size="large"
        >
          <el-icon><VideoPlay /></el-icon>
          开始面试
        </el-button>
        <el-button
          v-if="currentInterview?.status === 'in_progress'"
          type="success"
          @click="handleComplete"
          size="large"
        >
          <el-icon><Check /></el-icon>
          完成面试
        </el-button>
      </div>
    </div>

    <!-- 主要内容区域 - 三列布局 -->
    <div class="main-content">
      <!-- 左侧列 - 视频区域 -->
      <div class="left-column">
        <!-- 面试官数字人 -->
        <div class="video-card digital-human-card">
          <DigitalAvatar
            v-if="currentInterview?.status === 'in_progress' || currentInterview?.status === 'completed'"
            :key="digitalAvatarInstanceKey"
            ref="digitalAvatarRef"
            :session-id="interviewStore.sessionId"
            :digital-human-config="interviewStore.digitalHumanConfig"
            :provider="interviewStore.provider"
            :is-speaking="Boolean(isPlaying && currentPlayingMessageId)"
            :is-thinking="interviewStore.thinking"
            :error-message="currentDigitalHumanError"
            @ready="handleDigitalHumanReady"
            @error="handleDigitalHumanError"
            @status-change="handleDigitalHumanStatusChange"
          />
          <div v-else class="video-placeholder">
            <el-icon><Avatar /></el-icon>
            <span class="placeholder-label">面试官数字人</span>
            <span class="placeholder-hint">等待接入...</span>
          </div>
        </div>

        <!-- 分隔线 -->
        <div class="video-divider"></div>

        <!-- 用户摄像头 -->
        <div class="video-card user-camera-card">
            <UserCamera
              ref="userCameraRef"
              :auto-start="false"
              :is-recording="isListening || alwaysOnModeEnabled"
              @camera-started="handleCameraStarted"
              @camera-stopped="handleCameraStopped"
              @camera-error="handleCameraError"
          />
        </div>
      </div>

      <!-- 中间列 - 对话框 -->
      <div class="center-column">
        <div class="chat-container">
          <!-- 对话头部 -->
          <div class="chat-header">
            <div class="chat-title">
              <el-icon><ChatDotRound /></el-icon>
              <span>面试对话</span>
            </div>
            <div class="chat-controls">
              <el-button
                :icon="isMuted ? MuteNotification : Bell"
                :type="isMuted ? 'warning' : 'default'"
                size="small"
                @click="toggleMute"
                :title="isMuted ? '取消静音' : '静音'"
                circle
              />
              <el-tag v-if="currentStage" type="info" class="stage-tag">
                {{ getStageText(currentStage) }}
              </el-tag>
            </div>
          </div>

          <!-- 阶段进度条 -->
          <div v-if="stageProgress" class="stage-progress-bar">
            <div class="stage-info">
              <span class="stage-label">{{ stageProgress.stage_name }}</span>
              <span class="stage-meta">{{ stageProgress.turn_in_stage }}/{{ stageProgress.stage_max_turns }} 问题</span>
            </div>
            <el-progress
              :percentage="stageProgress.overall_progress"
              :stroke-width="8"
              :show-text="true"
            />
            <div class="progress-text">
              总进度 {{ stageProgress.overall_progress }}% | 剩余约 {{ stageProgress.remaining_turns }} 轮
            </div>
          </div>

          <!-- 对话消息区域 -->
          <div class="messages-container" ref="messagesContainer">
            <div v-if="isStartingInterview" class="startup-feedback">
              <div class="startup-feedback-title">正在生成开场问题...</div>
              <div class="startup-feedback-subtitle">LLM 正在思考，请稍候</div>
              <div class="startup-feedback-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>

            <div
              v-for="(message, index) in messages"
              :key="message.id || index"
              :class="['message-wrapper', message.role]"
            >
              <div class="message-bubble" :class="[message.role, { 'streaming': message.isStreaming }]">
                <div class="message-content">
                  <template v-if="message.isStreaming && !message.content">
                    <span class="thinking-dots">AI 正在思考</span>
                  </template>
                  <template v-else>
                    <div
                      v-if="message.role === 'assistant'"
                      class="assistant-rich-content"
                      v-html="renderMessageHtml(message.content)"
                    ></div>
                    <template v-else>{{ message.content }}</template>
                    <span v-if="message.isStreaming" class="cursor">|</span>
                  </template>
                </div>
                <div class="message-time">
                  {{ formatTime(message.timestamp) }}
                  <el-icon
                    v-if="message.role === 'assistant' && currentPlayingMessageId === message.id && isPlaying"
                    class="playing-indicator"
                  >
                    <VideoPlay />
                  </el-icon>
                </div>

                <div
                  v-if="message.role === 'assistant' && !message.isStreaming"
                  class="rewind-button"
                  @click="handleRewindToMessage(index)"
                  title="回到这个状态"
                >
                  <el-icon><RefreshLeft /></el-icon>
                  <span>回溯</span>
                </div>
              </div>
            </div>

            <el-empty v-if="messages.length === 0" description="暂无对话记录" />
          </div>

          <!-- 输入区域 -->
          <div class="input-area">
            <el-alert
              v-if="currentInterview?.status !== 'in_progress'"
              type="info"
              :closable="false"
              show-icon
            >
              {{ currentInterview?.status === 'completed'
                ? '面试已结束，可导出当前历史对话。'
                : '请先点击右上角的“开始面试”按钮开始面试。' }}
            </el-alert>

            <template v-else>
              <el-input
                v-model="inputMessage"
                type="textarea"
                :rows="3"
                placeholder="请输入您的回答..."
                :disabled="interviewStore.thinking"
                @input="handleInputChange"
                @keydown.enter.ctrl="handleSend"
              />

              <div v-if="showVoiceStatus" class="interim-text" :class="voiceStatusClass">
                <el-icon :class="{ 'is-loading': isTranscribing || interviewStore.thinking }">
                  <component :is="voiceStatusIcon" />
                </el-icon>
                <span>{{ voiceStatusText }}</span>
              </div>

              <div v-if="alwaysOnModeEnabled" class="voice-meter-panel" :class="{ active: voiceMeterActive }">
                <div class="voice-meter-track">
                  <div class="voice-meter-fill" :style="{ width: `${voiceMeterPercent}%` }"></div>
                </div>
                <div class="voice-meter-meta">
                  <span>音量 {{ voiceRms.toFixed(4) }}</span>
                  <span>阈值 {{ voiceThreshold.toFixed(4) }}</span>
                  <span>底噪 {{ voiceNoiseFloor.toFixed(4) }}</span>
                </div>
              </div>

              <div class="input-actions">
                <div class="left-actions">
                  <el-button
                    :icon="Microphone"
                    :type="alwaysOnModeEnabled ? 'danger' : 'primary'"
                    :loading="isTranscribing"
                    :disabled="isTranscribing || !voiceConfig.enabled || (!isAlwaysOnCapable && !isSpeechSupported)"
                    @click="toggleSpeechRecognition"
                    :class="{ 'listening': alwaysOnModeEnabled || isListening }"
                  >
                    {{ voiceActionLabel }}
                  </el-button>

                  <span class="hint">
                    <template v-if="isTranscribing">
                      <el-icon class="is-loading"><Loading /></el-icon>
                      正在识别...
                    </template>
                    <template v-else-if="alwaysOnModeEnabled && isPlaying">
                      AI 回答中，可直接打断
                    </template>
                    <template v-else-if="interviewStore.thinking">
                      <el-icon class="is-loading"><Loading /></el-icon>
                      AI 正在思考...
                    </template>
                    <template v-else-if="alwaysOnModeEnabled">
                      常开语音已开启
                    </template>
                    <template v-else>
                      Ctrl + Enter 发送
                    </template>
                  </span>
                </div>

                <el-button
                  type="primary"
                  @click="handleSend"
                  :disabled="interviewStore.thinking || !inputMessage.trim()"
                >
                  {{ interviewStore.thinking ? '思考中...' : '发送' }}
                </el-button>
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- 右侧列 - 信息面板 -->
      <div class="right-column">
        <!-- 面试信息 -->
        <div class="info-panel">
          <div class="panel-title">
            <el-icon><Document /></el-icon>
            <span>面试信息</span>
          </div>
          <div class="info-list">
            <div class="info-item">
              <span class="label">职位：</span>
              <span class="value">{{ currentInterview?.position }}</span>
            </div>
            <div class="info-item">
              <span class="label">技能领域：</span>
              <span class="value">{{ getSkillDomainText(currentInterview?.skill_domain) }}</span>
            </div>
            <div class="info-item">
              <span class="label">技能：</span>
              <div class="skills">
                <el-tag
                  v-for="skill in currentInterview?.skills"
                  :key="skill"
                  size="small"
                >
                  {{ skill }}
                </el-tag>
              </div>
            </div>
            <div class="info-item">
              <span class="label">经验级别：</span>
              <span class="value">{{ currentInterview?.experience_level }}</span>
            </div>
            <div class="info-item">
              <span class="label">预计时长：</span>
              <span class="value">{{ currentInterview?.duration_minutes }} 分钟</span>
            </div>
          </div>
        </div>

        <!-- 分隔线 -->
        <div class="panel-divider"></div>

        <!-- 面试阶段计划 -->
        <div class="stages-panel">
          <div class="panel-title">
            <el-icon><List /></el-icon>
            <span>面试阶段</span>
            <el-tag size="small" type="info">{{ totalDuration }}分钟</el-tag>
          </div>
          <div class="stages-content">
            <el-steps direction="vertical" :space="60" :active="getStageStepIndex(currentStage)">
              <el-step
                v-for="stage in stagesConfig"
                :key="stage.stage"
                :status="getStageStepStatus(stage.stage)"
              >
                <template #title>
                  <div class="stage-step-title">
                    <span class="stage-name">{{ stage.name }}</span>
                    <el-tag
                      size="small"
                      :type="getStageStepType(stage.stage)"
                      v-if="stage.stage === currentStage"
                    >
                      当前
                    </el-tag>
                  </div>
                </template>
                <template #description>
                  <div class="stage-step-desc">
                    <div class="stage-meta">
                      <span>{{ stage.time_allocation }}分钟</span>
                      <span>{{ stage.min_turns }}-{{ stage.max_turns }} 轮</span>
                    </div>
                    <p class="stage-description">{{ stage.description }}</p>
                  </div>
                </template>
              </el-step>
            </el-steps>
          </div>
        </div>

        <!-- 分隔线 -->
        <div class="panel-divider"></div>

        <!-- 流程可视化按钮 -->
        <div class="graph-panel">
          <el-button
            type="primary"
            @click="showGraphDialog = true"
            style="width: 100%"
            size="large"
          >
            <el-icon><Share /></el-icon>
            查看对话流程
          </el-button>
        </div>
      </div>
    </div>

    <!-- 对话流程弹窗 - 全屏模式 -->
    <teleport to="body">
      <transition name="fullscreen-fade">
        <div v-if="showGraphDialog" class="fullscreen-graph-overlay">
          <!-- 自定义标题栏 -->
          <div class="fullscreen-dialog-header">
            <div class="header-left">
              <h2>对话流程可视化</h2>
              <p class="header-subtitle">实时展示面试对话的完整流程和分支</p>
            </div>
            <div class="header-right">
              <el-button size="large" @click="showGraphDialog = false">
                <el-icon><ArrowLeft /></el-icon>
                返回面试
              </el-button>
            </div>
          </div>

          <!-- 内容区域 -->
          <div class="fullscreen-dialog-content">
            <div v-if="currentMessageIndex >= 0" class="rewind-notice-dialog">
              <el-alert
                type="info"
                :closable="false"
                show-icon
              >
                <template #default>
                  当前回溯到第 {{ currentMessageIndex + 1 }} 条消息，后续消息已隐藏。
                  <el-button
                    type="primary"
                    size="small"
                    link
                    @click="handleRestoreAllMessages"
                  >
                    恢复全部
                  </el-button>
                </template>
              </el-alert>
            </div>
            <ConversationGraph
              ref="conversationGraphRef"
              :message-tree="interviewStore.messageTree"
              :current-path="interviewStore.currentMessagePath"
              :current-message-index="currentMessageIndex"
              @switchToBranch="handleSwitchToBranch"
              @locateMessage="handleLocateMessage"
            />
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed, watch } from 'vue'
import { onBeforeRouteUpdate, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { VideoPlay, Check, Loading, RefreshLeft, Briefcase, User, Bell, MuteNotification, Microphone, ArrowLeft, ChatDotRound, Share, Document, List, TrendCharts, Avatar, Camera } from '@element-plus/icons-vue'
import { useInterviewStore } from '@/stores/interview'
import { interviewApi } from '@/api/interview'
import { profileApi } from '@/api/profile'
import ConversationGraph from '@/components/ConversationGraph.vue'
import UserCamera from '@/components/UserCamera.vue'
import DigitalAvatar from '@/components/DigitalAvatar.vue'
import { ASRRecorder, transcribeAudio, checkASRStatus } from '@/utils/asrRecorder.ts'
import {
  buildAudioExpressionPayload,
  createVideoExpressionReporter,
  finalizeExpressionReport,
  loadExpressionConfig,
  reportAudioExpressionSegment
} from '@/utils/expressionAnalysis'
import { createVoiceSessionController } from '@/utils/voiceSessionController.ts'
import '@/utils/cameraDiagnostics'  // 加载诊断工具，可在控制台使用 cameraDiagnostics

const route = useRoute()
const interviewStore = useInterviewStore()
const IMMERSIVE_BODY_CLASS = 'interview-immersive-mode'

// 语音相关状态
const isMuted = computed(() => interviewStore.isMuted)
const isPlaying = computed(() => interviewStore.isPlaying)
const currentPlayingMessageId = computed(() => interviewStore.currentPlayingMessageId)


// 数字人相关状态
const currentAIMessage = computed(() => {
  const aiMessages = messages.value.filter(m => m.role === "assistant")
  return aiMessages.length > 0 ? aiMessages[aiMessages.length - 1].content : ""
})

const currentDigitalHumanMessage = computed(() => {
  const aiMessages = messages.value.filter(m => m.role === "assistant")
  for (let i = aiMessages.length - 1; i >= 0; i -= 1) {
    if (
      (Array.isArray(aiMessages[i]?.avatarSegments) && aiMessages[i].avatarSegments.length > 0) ||
      aiMessages[i]?.avatarError
    ) {
      return aiMessages[i]
    }
  }
  return null
})

const currentDigitalHumanMessageKey = computed(() => currentDigitalHumanMessage.value?.id || '')
const currentDigitalHumanSegments = computed(() => currentDigitalHumanMessage.value?.avatarSegments || [])
const inlineDigitalHumanError = ref('')
const currentDigitalHumanError = computed(() => currentDigitalHumanMessage.value?.avatarError || inlineDigitalHumanError.value || '')
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
  short_noise_words: ['嗯', '啊', '哦', '额', '呃', '唉', '哈', '噢']
}

// 语音识别相关状态
function voiceDebug(label, payload) {
  void label
  void payload
}

const asrRecorder = ref(null)
const voiceSession = ref(null)
const expressionConfig = ref({
  enabled: true,
  video_sample_interval_ms: 1500
})
const expressionVideoReporter = ref(null)
const manualRecordingStartedAt = ref('')
const isListening = ref(false)
const isTranscribing = ref(false)  // 正在上传和识别
const isSpeechSupported = ref(false)
const isAlwaysOnSupported = ref(false)
const asrServiceAvailable = ref(false)  // ASR 服务是否可用
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

const loading = ref(false)
const isStartingInterview = ref(false)
const currentInterview = computed(() => interviewStore.currentInterview)
const messages = computed(() => {
  // 直接返回 store 中的 messages，它已经是当前路径的线性表示
  // 不需要再用 currentMessageIndex 来 slice
  const storeMessages = interviewStore.messages
  return storeMessages
})
const allMessages = computed(() => {
  return interviewStore.messages
}) // 所有消息历史
const inputMessage = ref('')
const messagesContainer = ref(null)
const stagesConfig = ref([])
const conversationGraphRef = ref(null)
const userCameraRef = ref(null)
const activeCollapse = ref(['graph'])  // 默认展开图表面板
const currentMessageIndex = ref(-1) // 当前对话位置索引，-1 表示显示所有消息，>=0 表示回溯到某条消息
const interviewProfile = ref(null) // 画像配置
const showGraphDialog = ref(false) // 是否显示流程图弹窗
const digitalAvatarRef = ref(null)
const routeReloading = ref(false)
const digitalAvatarInstanceKey = computed(() => {
  const interviewKey = String(interviewId.value || 'unknown')
  const sessionKey = String(interviewStore.sessionId || 'pending')
  const avatarKey = String(interviewStore.digitalHumanConfig?.avatarId || 'default')
  return `${interviewKey}-${sessionKey}-${avatarKey}`
})
// 注意：currentMessageIndex 只能通过以下两种方式改变：
// 1. 对话进行时（发送消息或接收回复）自动重置为 -1
// 2. 用户点击回溯按钮，设置为回溯位置
// 点击流程图节点不会改变此值，只会滚动到对应消息

const interviewId = computed(() => parseInt(route.params.id))
// 从 store 获取阶段和进度信息
const currentStage = computed(() => interviewStore.currentStage)
const stageProgress = computed(() => interviewStore.stageProgress)

// 计算总时长
const totalDuration = computed(() => {
  return stagesConfig.value.reduce((sum, stage) => sum + stage.time_allocation, 0)
})

const showVoiceStatus = computed(() => {
  return alwaysOnModeEnabled.value || isListening.value || isTranscribing.value || interviewStore.thinking
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
  if (interviewStore.thinking) return 'AI 正在思考...'
  return '语音已关闭'
})

const voiceStatusClass = computed(() => {
  return {
    listening: alwaysOnModeEnabled.value || isListening.value,
    transcribing: isTranscribing.value,
    playing: alwaysOnModeEnabled.value && isPlaying.value
  }
})

const voiceMeterPercent = computed(() => {
  if (!alwaysOnModeEnabled.value) return 0
  const threshold = Math.max(voiceThreshold.value, 0.0001)
  const ratio = voiceRms.value / threshold
  return Math.max(0, Math.min(Math.round(ratio * 100), 100))
})

const voiceMeterActive = computed(() => {
  return alwaysOnModeEnabled.value && (voiceDetected.value || voiceRms.value >= voiceThreshold.value)
})

const voiceStatusIcon = computed(() => {
  if (isTranscribing.value || interviewStore.thinking) return Loading
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

async function reloadInterviewView(targetInterviewId = interviewId.value) {
  if (!targetInterviewId || routeReloading.value) {
    return
  }

  routeReloading.value = true
  loading.value = true
  inlineDigitalHumanError.value = ''
  interviewProfile.value = null
  currentMessageIndex.value = -1

  try {
    if (digitalAvatarRef.value) {
      await digitalAvatarRef.value.destroy()
    }
    interviewStore.clearCurrentInterview()
    await loadInterviewDetail(Number(targetInterviewId))
    await loadInterviewProfile()
    scrollToBottom()
  } catch (error) {
    console.error('切换面试详情失败', error)
    ElMessage.error('切换面试详情失败')
  } finally {
    loading.value = false
    routeReloading.value = false
  }
}

onMounted(async () => {
  document.body.classList.add(IMMERSIVE_BODY_CLASS)
  await loadStagesConfig()
  await reloadInterviewView(interviewId.value)
  await loadExpressionRuntimeConfig()
  scrollToBottom()

  // 初始化语音识别
  initSpeechRecognition()
})

watch(
  () => route.params.id,
  async (newId, oldId) => {
    if (!newId || newId === oldId) {
      return
    }
    await reloadInterviewView(Number(newId))
  }
)

onBeforeRouteUpdate(async (to, from) => {
  if (to.name !== 'InterviewDetail' || to.params.id === from.params.id) {
    return
  }
  await reloadInterviewView(Number(to.params.id))
})

onUnmounted(async () => {
  document.body.classList.remove(IMMERSIVE_BODY_CLASS)
  expressionVideoReporter.value?.stop?.()
  if (alwaysOnModeEnabled.value) {
    await stopAlwaysOnVoice()
  }
  if (asrRecorder.value?.isRecording) {
    asrRecorder.value.cancelRecording()
  }
  if (digitalAvatarRef.value) {
    await digitalAvatarRef.value.destroy()
  }
})

// 加载面试画像配置
async function loadInterviewProfile() {
  try {
    const res = await profileApi.getInterviewProfile(interviewId.value)
    if (res.success) {
      interviewProfile.value = res.data
    }
  } catch (error) {
    // 如果面试没有配置画像，不显示错误
    // 该面试未配置画像
  }
}

// 获取画像名称
function getProfileName(profile, type) {
  if (type === 'position' && profile.position_config) {
    return profile.position_config.name || '未知岗位画像'
  }
  if (type === 'interviewer' && profile.interviewer_config) {
    return profile.interviewer_config.name || '未知面试官画像'
  }
  return '未知画像'
}

// 获取面试官风格标签
function getInterviewerStyleLabel(style) {
  if (!style) return ''
  const styleMap = {
    analytical: '分析型',
    guided: '引导型',
    behavioral: '行为型'
  }
  const difficultyMap = {
    basic: '基础',
    standard: '标准',
    challenging: '提升'
  }
  const questioningStyle = styleMap[style?.questioning_style] || style?.questioning_style || '标准'
  const difficulty = difficultyMap[style?.difficulty] || style?.difficulty || ''
  return difficulty ? `${questioningStyle} · ${difficulty}` : questioningStyle
}

// 监听消息变化，自动滚动到底部（支持流式输出）
watch(messages, () => {
  nextTick(() => {
    scrollToBottom()
  })
}, { deep: true })

watch(() => interviewStore.thinking, (thinking) => {
  if (!thinking && voiceQueue.value.length > 0) {
    processVoiceQueue()
  }
})

watch(isPlaying, (playing) => {
  if (!alwaysOnModeEnabled.value || isTranscribing.value) {
    return
  }
  voiceState.value = playing ? 'assistant_playing' : 'armed'
})

async function loadStagesConfig() {
  try {
    const data = await interviewApi.getStagesConfig()
    stagesConfig.value = data.stages
  } catch (error) {
    console.error('加载阶段配置失败', error)
  }
}

async function loadInterviewDetail(targetInterviewId = interviewId.value) {
  loading.value = true
  try {
    await interviewStore.fetchInterviewDetail(targetInterviewId)
    await ensureDigitalHumanSession(targetInterviewId)
    // messages 现在从 computed 获取，不需要手动设置
  } catch (error) {
    ElMessage.error('加载面试详情失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function ensureDigitalHumanSession(targetInterviewId = interviewId.value) {
  const status = currentInterview.value?.status
  if (!['in_progress', 'completed'].includes(status)) {
    return
  }
  if (interviewStore.sessionId || interviewStore.provider === 'disabled') {
    return
  }
  try {
    await interviewStore.initAvatarSession(targetInterviewId)
  } catch (error) {
    console.warn('初始化数字人会话失败:', error)
  }
}

function handleDigitalHumanReady() {
  inlineDigitalHumanError.value = ''
  interviewStore.setDigitalHumanReady(true)
}

function handleDigitalHumanError(error) {
  const message = error?.message || String(error || '')
  inlineDigitalHumanError.value = formatDigitalHumanError(message)
  interviewStore.setDigitalHumanError(message)
}

function handleDigitalHumanStatusChange(status) {
  interviewStore.setAvatarStatus(status)
}

function delay(ms) {
  return new Promise(resolve => window.setTimeout(resolve, ms))
}

async function waitForDigitalHumanReady(timeoutMs = 10000) {
  const startedAt = Date.now()

  while (Date.now() - startedAt < timeoutMs) {
    await nextTick()
    if (
      digitalAvatarRef.value &&
      interviewStore.provider === 'xunfei' &&
      interviewStore.digitalHumanConfig &&
      interviewStore.digitalHumanReady
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

async function speakAssistantText(text, messageId = null) {
  const normalizedText = String(text || '').trim()
  if (!normalizedText || isMuted.value) {
    return false
  }

  const ready = await waitForDigitalHumanReady()
  if (!ready) {
    console.warn('数字人未就绪，跳过本次播报')
    return false
  }

  const targetMessageId = messageId ?? getLatestAssistantMessageId()
  interviewStore.beginAssistantSpeech(targetMessageId)

  try {
    await digitalAvatarRef.value.speakText(normalizedText)
    return true
  } catch (error) {
    console.error('数字人播报失败:', error)
    interviewStore.finishAssistantSpeech()
    interviewStore.setDigitalHumanError(error?.message || String(error || ''))
    throw error
  }
}


async function handleStart() {
  try {
    await ElMessageBox.confirm('确认开始面试？', '提示', {
      confirmButtonText: '开始',
      cancelButtonText: '取消',
      type: 'info'
    })

    isStartingInterview.value = true
    inlineDigitalHumanError.value = ''

    if (digitalAvatarRef.value?.unlockAudio) {
      await digitalAvatarRef.value.unlockAudio()
    }

    try {
      await interviewStore.initAvatarSession(interviewId.value)
    } catch (error) {
      console.warn('初始化 Avatar Dialog 失败，将使用 D-ID 备用方案:', error)
    }

    const result = await interviewStore.startInterview(interviewId.value)

    if (result?.welcome_message) {
      await speakAssistantText(result.welcome_message, result.message_id)
    }

    ElMessage.success('面试已开始')
    scrollToBottom()

    if (userCameraRef.value) {
      try {
        await userCameraRef.value.startCamera()
      } catch (error) {
        console.error('自动启动摄像头失败', error)
      }
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('开始面试失败', error)
      if (isDigitalHumanRelatedError(error)) {
        inlineDigitalHumanError.value = formatDigitalHumanError(error)
      } else {
        ElMessage.error('开始面试失败，请重试')
      }
    }
  } finally {
    isStartingInterview.value = false
  }
}

async function handleSend() {
  const content = inputMessage.value.trim()
  if (!content) {
    ElMessage.warning('请输入消息内容')
    return
  }

  try {
    voiceDebug('handleSend: manual send requested', {
      length: content.length,
      queueLength: voiceQueue.value.length
    })
    voiceQueue.value = []
    inputMessage.value = ''
    inlineDigitalHumanError.value = ''
    await sendInterviewContent(content, 'text_input')
  } catch (error) {
    console.error('发送消息失败', error)
    if (isDigitalHumanRelatedError(error)) {
      inlineDigitalHumanError.value = formatDigitalHumanError(error)
    } else {
      ElMessage.error('发送失败，请重试')
    }
  }
}

async function sendInterviewContent(content, source = 'text_input') {
  voiceDebug('sendInterviewContent: sending message', {
    source,
    length: content?.length,
    preview: String(content || '').slice(0, 80)
  })
  if (interviewStore.thinking) {
    throw new Error('AI 正在思考，请稍候')
  }

  if (currentMessageIndex.value >= 0 && currentMessageIndex.value < messages.value.length - 1) {
    const targetMessage = messages.value[currentMessageIndex.value]
    interviewStore.createNewBranch(targetMessage.id)
    currentMessageIndex.value = -1
    ElMessage.info('已创建新的对话分支')
  }

  const result = await interviewStore.sendMessage(interviewId.value, content, { source })
  const replyText = result?.reply || messages.value[messages.value.length - 1]?.content || ''
  const replyMessageId = result?.message_id ?? getLatestAssistantMessageId()
  await speakAssistantText(replyText, replyMessageId)
  return result
}

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
  return String(text || '')
    .replace(/\s+/g, ' ')
    .trim()
}

function hasIncompleteTail(text = '') {
  return /[，,、：:（(]$/.test(text) || /(然后|就是|那个|这个|所以|因为)$/.test(text)
}

function shouldDiscardRecognizedText(text = '') {
  if (!text) return true
  if (text.length < 2) return true
  return new Set(voiceConfig.value.short_noise_words || []).has(text)
}

function shouldDeferAutoSend(text = '') {
  return text.length < Number(voiceConfig.value.auto_send_min_chars || DEFAULT_VOICE_CONFIG.auto_send_min_chars) && hasIncompleteTail(text)
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

async function enqueueVoiceSegment(segment) {
  voiceQueue.value.push(segment)
  voiceDebug('enqueueVoiceSegment: queued', {
    queueLength: voiceQueue.value.length,
    stats: segment.stats,
    blobSize: segment.blob?.size,
    blobType: segment.blob?.type
  })
  await processVoiceQueue()
}

async function processVoiceQueue() {
  if (voiceQueueBusy.value || isTranscribing.value || interviewStore.thinking) {
    voiceDebug('processVoiceQueue: skipped', {
      voiceQueueBusy: voiceQueueBusy.value,
      isTranscribing: isTranscribing.value,
      thinking: interviewStore.thinking,
      queueLength: voiceQueue.value.length
    })
    return
  }

  const nextSegment = voiceQueue.value.shift()
  if (!nextSegment) {
    voiceDebug('processVoiceQueue: no pending segment')
    return
  }

  voiceQueueBusy.value = true
  isTranscribing.value = true
  voiceState.value = 'transcribing'

  try {
    voiceDebug('processVoiceQueue: transcribing segment', nextSegment.stats)
    const result = await transcribeAudio(nextSegment.blob, {
      segment_id: nextSegment.stats.segmentId,
      client_started_at: nextSegment.stats.startedAt,
      client_ended_at: nextSegment.stats.endedAt,
      source: 'always_on_voice'
    })

    const text = normalizeRecognizedText(result?.text)
    voiceDebug('processVoiceQueue: transcription result', {
      result,
      normalizedText: text
    })
    await reportExpressionAudioFromResult({
      segmentId: nextSegment.stats.segmentId,
      source: 'always_on_voice',
      startedAt: nextSegment.stats.startedAt,
      endedAt: nextSegment.stats.endedAt,
      text,
      segmentStats: nextSegment.stats
    })
    if (shouldDiscardRecognizedText(text)) {
      voiceDebug('processVoiceQueue: discarded recognized text', {
        text,
        reason: !text ? 'empty' : text.length < 2 ? 'too_short' : 'noise_word'
      })
      return
    }

    const userHasDraft = Boolean(inputMessage.value.trim())
    const userIsTyping = Date.now() - lastManualInputAt.value < Number(voiceConfig.value.typing_grace_ms || DEFAULT_VOICE_CONFIG.typing_grace_ms)
    const shouldAutoSend = Boolean(result?.should_auto_send) && !shouldDeferAutoSend(text)
    voiceDebug('processVoiceQueue: send decision', {
      userHasDraft,
      userIsTyping,
      shouldAutoSend,
      shouldDefer: shouldDeferAutoSend(text),
      textLength: text.length
    })

    if (shouldAutoSend && !userHasDraft && !userIsTyping) {
      await sendInterviewContent(text, 'always_on_voice')
      return
    }

    if (userHasDraft || userIsTyping) {
      ElMessage.info('检测到已有输入，语音识别结果未自动覆盖')
      return
    }

    setInputMessageSilently(text)
    voiceDebug('processVoiceQueue: filled input without auto-send', { text })
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
    if (voiceQueue.value.length > 0 && !interviewStore.thinking) {
      processVoiceQueue()
    }
  }
}

function isDigitalHumanRelatedError(error) {
  const text = String(error || '').toLowerCase()
  return text.includes('d-id') ||
    text.includes('digital human') ||
    text.includes('avatar') ||
    text.includes('credits') ||
    text.includes('unauthorized')
}

function formatDigitalHumanError(error) {
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

async function handleComplete() {
  let loadingService = null
  try {
    await ElMessageBox.confirm('确认完成面试并导出当前历史对话？', '提示', {
      confirmButtonText: '完成',
      cancelButtonText: '取消',
      type: 'warning'
    })

    loading.value = true
    loadingService = ElLoading.service({
      lock: true,
      text: '正在导出历史对话，请稍候...',
      background: 'rgba(0, 0, 0, 0.2)',
      customClass: 'complete-loading-mask'
    })

    if (alwaysOnModeEnabled.value) {
      await stopAlwaysOnVoice()
    }

    if (userCameraRef.value) {
      try {
        await userCameraRef.value.stopCamera()
        console.log('摄像头已停止')
      } catch (error) {
        console.error('停止摄像头失败', error)
      }
    }

    await interviewStore.completeInterview(interviewId.value)
    ElMessage.success('面试已完成')
    await loadInterviewDetail()
    } catch (error) {
    if (error !== 'cancel') {
      console.error('完成面试失败', error)
    }
  } finally {
    if (loadingService) {
      loadingService.close()
    }
    loading.value = false
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function getStatusType(status) {
  const typeMap = {
    created: 'info',
    in_progress: 'warning',
    completed: 'success',
    cancelled: 'danger'
  }
  return typeMap[status] || 'info'
}

function getStatusText(status) {
  const textMap = {
    created: '已创建',
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消'
  }
  return textMap[status] || status
}

function getStageText(stage) {
  const textMap = {
    welcome: '开场介绍',
    technical: '技术问题',
    scenario: '情景问题',
    closing: '结束阶段'
  }
  return textMap[stage] || stage
}

function getStageStepIndex(currentStageValue) {
  if (!currentStageValue) return 0
  const idx = stagesConfig.value.findIndex((s) => s.stage === currentStageValue)
  return idx >= 0 ? idx : 0
}

function getStageStepStatus(stageValue) {
  const current = currentStage.value
  if (!current) return 'wait'
  const currentIndex = stagesConfig.value.findIndex((s) => s.stage === current)
  const stageIndex = stagesConfig.value.findIndex((s) => s.stage === stageValue)
  if (currentIndex < 0 || stageIndex < 0) return 'wait'

  if (stageIndex < currentIndex) return 'finish'
  if (stageIndex === currentIndex) return 'process'
  return 'wait'
}

function getStageStepType(stageValue) {
  const typeMap = {
    welcome: 'primary',
    technical: 'success',
    scenario: 'warning',
    closing: 'info'
  }
  return typeMap[stageValue] || 'info'
}

function getSkillDomainText(domain) {
  const textMap = {
    frontend: '前端开发',
    backend: '后端开发',
    fullstack: '全栈开发',
    ai_ml: 'AI/机器学习',
    data_engineering: '数据工程',
    other: '其他'
  }
  return textMap[domain] || domain
}

function getDimensionLabel(key) {
  const labelMap = {
    technical: '技术能力',
    problem_solving: '问题解决',
    communication: '沟通表达',
    learning_potential: '学习潜力'
  }
  return labelMap[key] || key
}


function escapeHtml(input = '') {
  return String(input)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function renderMessageHtml(content = '') {
  const escaped = escapeHtml(content)

  let html = escaped
    .replace(/^###\s+(.+)$/gm, '<h3>$1</h3>')
    .replace(/^##\s+(.+)$/gm, '<h2>$1</h2>')
    .replace(/^#\s+(.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`\n]+)`/g, '<code>$1</code>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')

  html = html.replace(/(?:<li>.*?<\/li>\s*)+/gs, (match) => `<ul>${match}</ul>`)
  html = html.replace(/\n/g, '<br>')
  return html
}
function formatTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

function handleRestoreAllMessages() {
  currentMessageIndex.value = -1
  ElMessage.success('已恢复显示所有消息')
}

// 语音控制方法
function toggleMute() {
  interviewStore.toggleMute()
  ElMessage.info(isMuted.value ? '已静音' : '已取消静音')
}

// 语音识别相关方法
async function initSpeechRecognition() {
  asrRecorder.value = new ASRRecorder()
  isSpeechSupported.value = asrRecorder.value.supported
  isAlwaysOnSupported.value = Boolean(
    asrRecorder.value.supported &&
    (window.AudioContext || window.webkitAudioContext)
  )
  voiceDebug('initSpeechRecognition: support check', {
    speechSupported: isSpeechSupported.value,
    alwaysOnSupported: isAlwaysOnSupported.value
  })

  try {
    const runtimeVoiceConfig = await interviewApi.getVoiceConfig()
    voiceConfig.value = {
      ...DEFAULT_VOICE_CONFIG,
      ...(runtimeVoiceConfig || {})
    }
    voiceDebug('initSpeechRecognition: voice config loaded', voiceConfig.value)
  } catch (error) {
    console.error('加载语音配置失败:', error)
    voiceConfig.value = { ...DEFAULT_VOICE_CONFIG }
  }

  try {
    const status = await checkASRStatus()
    asrServiceAvailable.value = status.available
    voiceDebug('initSpeechRecognition: ASR status', status)

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
        voiceDebug('initSpeechRecognition: onSegmentReady callback', {
          stats,
          blobSize: blob?.size,
          blobType: blob?.type
        })
        enqueueVoiceSegment({ blob, stats })
      },
      onSpeechStateChange: ({ state, rms, threshold, noiseFloor, voiceActive }) => {
        voiceState.value = state
        voiceRms.value = Number(rms || 0)
        voiceThreshold.value = Number(threshold || 0)
        voiceNoiseFloor.value = Number(noiseFloor || 0)
        voiceDetected.value = Boolean(voiceActive || state === 'speech_detected' || state === 'segment_closing' || state === 'barge_in')
        if (state !== 'armed' || voiceDetected.value) {
          voiceDebug('initSpeechRecognition: VAD update', {
            state,
            rms: voiceRms.value,
            threshold: voiceThreshold.value,
            noiseFloor: voiceNoiseFloor.value,
            voiceDetected: voiceDetected.value
          })
        }
      },
      onBargeIn: () => {
        voiceDebug('initSpeechRecognition: barge-in callback')
        interviewStore.stopVoice()
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
  voiceDebug('toggleSpeechRecognition: clicked', {
    enabled: voiceConfig.value.enabled,
    alwaysOnCapable: isAlwaysOnCapable.value,
    alwaysOnModeEnabled: alwaysOnModeEnabled.value,
    isListening: isListening.value
  })
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
  voiceDebug('startAlwaysOnVoice: requested')
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
    voiceDebug('startAlwaysOnVoice: started', status)
    ElMessage.success('常开语音已开启')
  } catch (error) {
    console.error('开启常开语音失败:', error)
    ElMessage.error(`开启常开语音失败: ${error.message}`)
  }
}

async function stopAlwaysOnVoice() {
  voiceDebug('stopAlwaysOnVoice: requested')
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

async function startSpeechRecognition() {
  voiceDebug('startSpeechRecognition: requested')
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

    // 开始录音
    await asrRecorder.value.startRecording()
    voiceDebug('startSpeechRecognition: recording started')
    // 录音已开始

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
  voiceDebug('stopSpeechRecognition: requested')
  if (!asrRecorder.value || !isListening.value) {
    return
  }

  try {
    const audioBlob = await asrRecorder.value.stopRecording()
    voiceDebug('stopSpeechRecognition: blob received', {
      size: audioBlob?.size,
      type: audioBlob?.type
    })

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

    const result = await transcribeAudio(audioBlob, {
      source: 'manual_voice'
    })
    const text = normalizeRecognizedText(result?.text)
    voiceDebug('stopSpeechRecognition: transcription result', { result, normalizedText: text })
    await reportExpressionAudioFromResult({
      segmentId: result?.segment_id || `manual-${Date.now()}`,
      source: 'manual_voice',
      startedAt: manualRecordingStartedAt.value || new Date(Date.now() - Number(result?.duration_ms || 0)).toISOString(),
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
        if (textarea) {
          textarea.focus()
        }
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

function handleKeyPress(event) {
  // Ctrl+M 快捷键切换语音识别
  if (event.ctrlKey && event.key === 'm') {
    event.preventDefault()
    if (isSpeechSupported.value) {
      toggleSpeechRecognition()
    }
  }
}

function handleSelectMessage(messageId) {
  // 这个函数已废弃，使用 handleLocateMessage 和 handleSwitchToBranch 替代
}

// 定位消息（只滚动，不切换分支）
function handleLocateMessage(messageId) {
  // 找到对应消息的索引
  const index = messages.value.findIndex(m => m.id === messageId)
  if (index >= 0) {
    // 滚动到对应消息
    nextTick(() => {
      const messageElements = messagesContainer.value?.querySelectorAll('.message-wrapper')
      if (messageElements && messageElements[index]) {
        messageElements[index].scrollIntoView({ behavior: 'smooth', block: 'center' })
        // 添加临时高亮样式
        messageElements[index].classList.add('highlight')
        setTimeout(() => {
          messageElements[index].classList.remove('highlight')
        }, 2000)
      }
    })
  } else {
    ElMessage.warning('消息不在当前显示的分支中')
  }
}

// 切换到该节点的分支
async function handleSwitchToBranch(messageId) {
  try {
    await interviewStore.switchToBranch(messageId)
    ElMessage.success('已切换到该分支')
  } catch (error) {
    console.error('切换分支失败', error)
    ElMessage.error('切换分支失败')
  }
}


// 回溯到指定消息
async function handleRewindToMessage(messageIndex) {
  try {
    const targetMessage = messages.value[messageIndex]
    await ElMessageBox.confirm(
      `确认回溯到第 ${messageIndex + 1} 条消息？这将把对话状态回溯到“${targetMessage.content.substring(0, 30)}...”，后续消息会被隐藏。从该位置继续发送会创建新的对话分支。`,
      '确认回溯',
      {
        confirmButtonText: '回溯',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: false
      }
    )

    interviewStore.switchToMessage(targetMessage.id)

    currentMessageIndex.value = messageIndex

    ElMessage.success(`已回溯到第 ${messageIndex + 1} 条消息，后续消息已隐藏`)
    scrollToBottom()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('回溯失败', error)
      ElMessage.error('回溯失败')
    }
  }
}

// 摄像头相关方法
function handleCameraStarted(stream) {
  console.log('摄像头已启动', stream)
  ensureExpressionVideoReporter()
  expressionVideoReporter.value?.start?.()
}

function handleCameraStopped() {
  console.log('摄像头已停止')
  expressionVideoReporter.value?.stop?.()
}

function handleCameraError(error) {
  console.error('摄像头错误', error)
}
</script>

<style>
/* 全局样式 - 仅在面试详情页隐藏顶部导航栏 */
body.interview-immersive-mode .app-header {
  display: none !important;
}

body.interview-immersive-mode {
  overflow: hidden;
}

body.interview-immersive-mode .app-main {
  padding: 0 !important;
  max-width: none !important;
  height: 100vh !important;
}

body.interview-immersive-mode .app-container {
  min-height: 100vh !important;
}

/* 全屏对话流程图样式 */
.fullscreen-graph-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: #f5f7fa;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  /* 启用硬件加速 */
  transform: translateZ(0);
  will-change: transform;
  /* 优化渲染 */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.fullscreen-dialog-header {
  height: 80px;
  background: white;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 32px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  /* 优化渲染 */
  transform: translateZ(0);
  will-change: transform;

  .header-left {
    h2 {
      margin: 0 0 4px 0;
      font-size: 20px;
      font-weight: 600;
      color: #303133;
      /* 文字抗锯齿 */
      -webkit-font-smoothing: antialiased;
    }

    .header-subtitle {
      margin: 0;
      font-size: 14px;
      color: #909399;
      -webkit-font-smoothing: antialiased;
    }
  }

  .header-right {
    display: flex;
    gap: 12px;
  }
}

.fullscreen-dialog-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  padding: 0;
  /* 优化滚动性能 */
  overflow-x: hidden;
  overflow-y: hidden;
  /* 启用硬件加速 */
  transform: translateZ(0);
  will-change: scroll-position;
  /* 优化渲染 */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  /* 确保占满整个可用空间 */
  width: 100%;
  height: calc(100vh - 80px); /* 减去 header 高度 */

  /* 移除滚动条，让内部组件处理 */
  &::-webkit-scrollbar {
    display: none;
  }

  :deep(.conversation-graph) {
    flex: 1;
    min-height: 0;
  }
}

.fullscreen-fade-enter-active,
.fullscreen-fade-leave-active {
  transition: opacity 0.3s ease;
}

.fullscreen-fade-enter-from,
.fullscreen-fade-leave-to {
  opacity: 0;
}

.startup-feedback {
  margin: 8px 0 14px;
  padding: 12px 14px;
  border: 1px solid #d9ecff;
  background: #ecf5ff;
  border-radius: 10px;
  color: #1f2937;
}

.startup-feedback-title {
  font-size: 14px;
  font-weight: 600;
}

.startup-feedback-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

.startup-feedback-dots {
  margin-top: 8px;
  display: inline-flex;
  gap: 6px;
}

.startup-feedback-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #409eff;
  animation: startupDot 1.2s infinite ease-in-out;
}

.startup-feedback-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.startup-feedback-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes startupDot {
  0%, 80%, 100% {
    transform: scale(0.7);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.complete-loading-mask {
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

</style>

<style scoped lang="scss">
@import '@/styles/immersive-interview-new.scss';
</style>
