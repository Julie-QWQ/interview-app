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
        <el-button
          v-if="currentInterview?.status === 'completed'"
          type="primary"
          @click="handleViewReport"
          size="large"
        >
          查看面试报告
        </el-button>
      </div>
    </div>

    <!-- 主要内容区域 - 三列布局 -->
    <div class="main-content">
      <!-- 左侧列 - 视频区域 -->
      <div class="left-column">
        <!-- 面试官数字人 -->
        <div class="video-card digital-human-card">
          <div class="video-placeholder">
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
            :is-recording="isListening"
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
                ? '面试已结束，可查看评估结果与对话流程。'
                : '请先点击右上角的“开始面试”按钮开始面试。' }}
            </el-alert>

            <template v-else>
              <el-input
                v-model="inputMessage"
                type="textarea"
                :rows="3"
                placeholder="请输入您的回答..."
                :disabled="interviewStore.thinking"
                @keydown.enter.ctrl="handleSend"
              />

              <div v-if="isListening || isTranscribing" class="interim-text">
                <el-icon class="is-loading"><Microphone /></el-icon>
                <span>{{ isListening ? '正在录音...' : '正在识别...' }}</span>
              </div>

              <div class="input-actions">
                <div class="left-actions">
                  <el-button
                    :icon="Microphone"
                    :type="isListening ? 'danger' : 'primary'"
                    :loading="isTranscribing"
                    :disabled="isTranscribing"
                    @click="toggleSpeechRecognition"
                    :class="{ 'listening': isListening }"
                  >
                    {{ isListening ? '停止录音' : (isTranscribing ? '识别中...' : '点击说话') }}
                  </el-button>

                  <span class="hint">
                    <template v-if="isTranscribing">
                      <el-icon class="is-loading"><Loading /></el-icon>
                      正在识别...
                    </template>
                    <template v-else-if="interviewStore.thinking">
                      <el-icon class="is-loading"><Loading /></el-icon>
                      AI 正在思考...
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

          <!-- 弹窗内容 -->
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
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { VideoPlay, Check, Loading, RefreshLeft, Briefcase, User, Bell, MuteNotification, Microphone, ArrowLeft, ChatDotRound, Share, Document, List, TrendCharts, Avatar, Camera } from '@element-plus/icons-vue'
import { useInterviewStore } from '@/stores/interview'
import { interviewApi } from '@/api/interview'
import { profileApi } from '@/api/profile'
import ConversationGraph from '@/components/ConversationGraph.vue'
import UserCamera from '@/components/UserCamera.vue'
import { ASRRecorder, transcribeAudio, checkASRStatus } from '@/utils/asrRecorder'
import '@/utils/cameraDiagnostics'  // 鍔犺浇璇婃柇宸ュ叿,鍙湪鎺у埗鍙颁娇鐢?cameraDiagnostics

const route = useRoute()
const router = useRouter()
const interviewStore = useInterviewStore()
const IMMERSIVE_BODY_CLASS = 'interview-immersive-mode'

// 璇煶鐩稿叧鐘舵€?
const isMuted = computed(() => interviewStore.isMuted)
const isPlaying = computed(() => interviewStore.isPlaying)
const currentPlayingMessageId = computed(() => interviewStore.currentPlayingMessageId)

// 璇煶璇嗗埆鐩稿叧鐘舵€?
const asrRecorder = ref(null)
const isListening = ref(false)
const isTranscribing = ref(false)  // 姝ｅ湪涓婁紶鍜岃瘑鍒?
const isSpeechSupported = ref(false)
const asrServiceAvailable = ref(false)  // ASR 鏈嶅姟鏄惁鍙敤

const loading = ref(false)
const isStartingInterview = ref(false)
const currentInterview = computed(() => interviewStore.currentInterview)
const messages = computed(() => {
  // 鐩存帴杩斿洖 store 涓殑 messages锛屽畠宸茬粡鏄綋鍓嶈矾寰勭殑绾挎€ц〃绀?
  // 涓嶉渶瑕佸啀鐢?currentMessageIndex 鏉?slice
  const storeMessages = interviewStore.messages
  return storeMessages
})
const allMessages = computed(() => {
  return interviewStore.messages
}) // 鎵€鏈夋秷鎭巻鍙?
const evaluation = ref(null)
const inputMessage = ref('')
const messagesContainer = ref(null)
const stagesConfig = ref([])
const conversationGraphRef = ref(null)
const userCameraRef = ref(null)
const activeCollapse = ref(['graph'])  // 榛樿灞曞紑鍥捐〃闈㈡澘
const currentMessageIndex = ref(-1) // 褰撳墠瀵硅瘽浣嶇疆绱㈠紩锛?1琛ㄧず鏄剧ず鎵€鏈夋秷鎭紝>=0琛ㄧず鍥炴函鍒版煇鏉℃秷鎭級
const interviewProfile = ref(null) // 鐢诲儚閰嶇疆
const showGraphDialog = ref(false) // 鏄惁鏄剧ず娴佺▼鍥惧脊绐?
// 娉ㄦ剰锛歝urrentMessageIndex 鍙兘閫氳繃浠ヤ笅涓ょ鏂瑰紡鏀瑰彉锛?
// 1. 瀵硅瘽杩涜鏃讹紙鍙戦€佹秷鎭垨鎺ユ敹鍥炲锛? 鑷姩閲嶇疆涓?-1
// 2. 鐢ㄦ埛鐐瑰嚮鍥炴函鎸夐挳 - 璁剧疆涓哄洖婧綅缃?
// 鐐瑰嚮娴佺▼鍥捐妭鐐逛笉浼氭敼鍙樻鍊硷紝鍙細婊氬姩鍒板搴旀秷鎭?

const interviewId = computed(() => parseInt(route.params.id))

// 浠?store 鑾峰彇闃舵鍜岃繘搴︿俊鎭?
const currentStage = computed(() => interviewStore.currentStage)
const stageProgress = computed(() => interviewStore.stageProgress)

// 璁＄畻鎬绘椂闀?
const totalDuration = computed(() => {
  return stagesConfig.value.reduce((sum, stage) => sum + stage.time_allocation, 0)
})

onMounted(async () => {
  document.body.classList.add(IMMERSIVE_BODY_CLASS)
  await loadStagesConfig()
  await loadInterviewDetail()
  await loadEvaluation()
  await loadInterviewProfile()
  scrollToBottom()

  // 鍒濆鍖栬闊宠瘑鍒?
  initSpeechRecognition()
})

onUnmounted(() => {
  document.body.classList.remove(IMMERSIVE_BODY_CLASS)
})

// 鍔犺浇闈㈣瘯鐢诲儚閰嶇疆
async function loadInterviewProfile() {
  try {
    const res = await profileApi.getInterviewProfile(interviewId.value)
    if (res.success) {
      interviewProfile.value = res.data
    }
  } catch (error) {
    // 濡傛灉闈㈣瘯娌℃湁閰嶇疆鐢诲儚锛屼笉鏄剧ず閿欒
    // 璇ラ潰璇曟湭閰嶇疆鐢诲儚
  }
}

// 鑾峰彇鐢诲儚鍚嶇О
function getProfileName(profile, type) {
  if (type === 'position' && profile.position_config) {
    return profile.position_config.name || '未知岗位画像'
  }
  if (type === 'interviewer' && profile.interviewer_config) {
    return profile.interviewer_config.name || '未知面试官画像'
  }
  return '未知画像'
}

// 鑾峰彇闈㈣瘯瀹橀鏍兼爣绛?
function getInterviewerStyleLabel(style) {
  if (!style) return ''
  const styleMap = {
    'deep_technical': '技术深入型',
    'guided': '亲和引导型',
    'behavioral': '行为导向型'
  }
  const questioningStyle = styleMap[style?.questioning_style] || style?.questioning_style || '标准'
  const paceMap = {
    'fast': '快节奏',
    'moderate': '适中',
    'slow': '慢节奏'
  }
  const pace = paceMap[style?.pace] || ''
  return pace ? `${questioningStyle} · ${pace}` : questioningStyle
}

// 鐩戝惉娑堟伅鍙樺寲锛岃嚜鍔ㄦ粴鍔ㄥ埌搴曢儴锛堟敮鎸佹祦寮忚緭鍑猴級
watch(messages, () => {
  nextTick(() => {
    scrollToBottom()
  })
}, { deep: true })

async function loadStagesConfig() {
  try {
    const data = await interviewApi.getStagesConfig()
    stagesConfig.value = data.stages
  } catch (error) {
    console.error('加载阶段配置失败', error)
  }
}

async function loadInterviewDetail() {
  loading.value = true
  try {
    await interviewStore.fetchInterviewDetail(interviewId.value)
    // messages 鐜板湪浠?computed 鑾峰彇,涓嶉渶瑕佹墜鍔ㄨ缃?
  } catch (error) {
    ElMessage.error('加载面试详情失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function loadEvaluation() {
  try {
    evaluation.value = await interviewApi.getEvaluation(interviewId.value)
  } catch (error) {
    // 璇勪及鍙兘涓嶅瓨鍦紝蹇界暐閿欒
    evaluation.value = null
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
    await interviewStore.startInterview(interviewId.value)
    ElMessage.success('面试已开始')
    await loadInterviewDetail()
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
      ElMessage.error('开始面试失败，请重试')
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

  if (interviewStore.thinking) {
    return
  }

  try {
    inputMessage.value = ''

    if (currentMessageIndex.value >= 0 && currentMessageIndex.value < messages.value.length - 1) {
      const targetMessage = messages.value[currentMessageIndex.value]
      interviewStore.createNewBranch(targetMessage.id)
      currentMessageIndex.value = -1
      ElMessage.info('已创建新的对话分支')
    }

    await interviewStore.sendMessage(interviewId.value, content)
  } catch (error) {
    console.error('发送消息失败', error)
    ElMessage.error('发送失败，请重试')
  }
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
    await loadEvaluation()
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

function handleViewReport() {
  router.push(`/interviews/${interviewId.value}/report`)
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

function getRecommendationClass(recommendation) {
  if (recommendation.includes('建议') || recommendation.includes('通过')) {
    return 'recommend-positive'
  } else if (recommendation.includes('不') || recommendation.includes('拒绝')) {
    return 'recommend-negative'
  }
  return 'recommend-neutral'
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

// 璇煶鎺у埗鏂规硶
function toggleMute() {
  interviewStore.toggleMute()
  ElMessage.info(isMuted.value ? '已静音' : '已取消静音')
}

// 璇煶璇嗗埆鐩稿叧鏂规硶
async function initSpeechRecognition() {
  // 鍒涘缓 ASR 褰曢煶鍣?
  asrRecorder.value = new ASRRecorder()
  isSpeechSupported.value = asrRecorder.value.supported

  // 妫€鏌ュ悗绔?ASR 鏈嶅姟鐘舵€?
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
    // 妫€鏌?ASR 鏈嶅姟澶辫触
    asrServiceAvailable.value = false
  }

  if (isSpeechSupported.value) {
  } else {
    ElMessage.info({
      message: '当前浏览器不支持录音功能，请使用 Chrome、Edge 或 Firefox',
      duration: 3000,
      showClose: true
    })
  }
}

function toggleSpeechRecognition() {
  if (isListening.value) {
    stopSpeechRecognition()
  } else {
    startSpeechRecognition()
  }
}

async function startSpeechRecognition() {
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
    inputMessage.value = '' // 娓呯┖杈撳叆妗?鍑嗗鎺ユ敹鏂扮殑璇煶杈撳叆

    ElMessage.info({
      message: '正在录音...点击停止按钮结束',
      duration: 3000
    })

    // 寮€濮嬪綍闊?
    await asrRecorder.value.startRecording()
    // 褰曢煶宸插紑濮?

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
    // 鍋滄褰曢煶骞惰幏鍙栭煶棰?Blob
    const audioBlob = await asrRecorder.value.stopRecording()

    if (!audioBlob || audioBlob.size === 0) {
      ElMessage.warning({
        message: '未录制到音频',
        duration: 1500
      })
      isListening.value = false
      return
    }

    // 褰曢煶宸插仠姝? 寮€濮嬭瘑鍒?
    isTranscribing.value = true
    isListening.value = false

    ElMessage.info({
      message: '正在识别语音...',
      duration: 2000,
      iconClass: 'el-icon-loading'
    })

    // 璋冪敤鍚庣 ASR API
    const text = await transcribeAudio(audioBlob)

    if (text && text.trim()) {
      inputMessage.value = text.trim()
      ElMessage.success({
        message: '识别完成',
        duration: 1500
      })

      // 鑷姩鑱氱劍鍒拌緭鍏ユ,鏂逛究鐢ㄦ埛缂栬緫
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
    isListening.value = false
    isTranscribing.value = false
  }
}

function handleKeyPress(event) {
  // Ctrl+M 蹇嵎閿垏鎹㈣闊宠瘑鍒?
  if (event.ctrlKey && event.key === 'm') {
    event.preventDefault()
    if (isSpeechSupported.value) {
      toggleSpeechRecognition()
    }
  }
}

function handleSelectMessage(messageId) {
  // 杩欎釜鍑芥暟宸插簾寮冿紝浣跨敤 handleLocateMessage 鍜?handleSwitchToBranch 鏇夸唬
}

// 瀹氫綅娑堟伅锛堝彧婊氬姩锛屼笉鍒囨崲鍒嗘敮锛?
function handleLocateMessage(messageId) {
  // 鎵惧埌瀵瑰簲娑堟伅鐨勭储寮?
  const index = messages.value.findIndex(m => m.id === messageId)
  if (index >= 0) {
    // 婊氬姩鍒板搴旀秷鎭?
    nextTick(() => {
      const messageElements = messagesContainer.value?.querySelectorAll('.message-wrapper')
      if (messageElements && messageElements[index]) {
        messageElements[index].scrollIntoView({ behavior: 'smooth', block: 'center' })
        // 娣诲姞涓存椂楂樹寒鏍峰紡
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

// 鍒囨崲鍒拌鑺傜偣鐨勫垎鏀?
async function handleSwitchToBranch(messageId) {
  try {
    await interviewStore.switchToBranch(messageId)
    ElMessage.success('已切换到该分支')
  } catch (error) {
    console.error('切换分支失败', error)
    ElMessage.error('切换分支失败')
  }
}


// 鍥炴函鍒版寚瀹氭秷鎭?
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

// 鎽勫儚澶寸浉鍏虫柟娉?
function handleCameraStarted(stream) {
  console.log('摄像头已启动', stream)
}

function handleCameraStopped() {
  console.log('摄像头已停止')
}

function handleCameraError(error) {
  console.error('摄像头错误', error)
}
</script>

<style>
/* 鍏ㄥ眬鏍峰紡 - 浠呭湪闈㈣瘯璇︽儏椤甸殣钘忛《閮ㄥ鑸爮 */
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

/* 鍏ㄥ睆瀵硅瘽娴佺▼鍥炬牱寮?*/
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
  /* 鍚敤纭欢鍔犻€?*/
  transform: translateZ(0);
  will-change: transform;
  /* 浼樺寲娓叉煋 */
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
  /* 浼樺寲娓叉煋 */
  transform: translateZ(0);
  will-change: transform;

  .header-left {
    h2 {
      margin: 0 0 4px 0;
      font-size: 20px;
      font-weight: 600;
      color: #303133;
      /* 鏂囧瓧鎶楅敮榻?*/
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
  /* 浼樺寲婊氬姩鎬ц兘 */
  overflow-x: hidden;
  overflow-y: hidden;
  /* 鍚敤纭欢鍔犻€?*/
  transform: translateZ(0);
  will-change: scroll-position;
  /* 浼樺寲娓叉煋 */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  /* 纭繚鍗犳弧鏁翠釜鍙敤绌洪棿 */
  width: 100%;
  height: calc(100vh - 80px); /* 鍑忓幓 header 楂樺害 */

  /* 绉婚櫎婊氬姩鏉?璁╁唴閮ㄧ粍浠跺鐞?*/
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

