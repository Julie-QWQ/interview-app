<template>
  <div class="interview-detail" v-loading="loading">
    <div class="detail-header">
      <el-page-header @back="$router.back()" title="返回">
        <template #content>
          <h2>{{ currentInterview?.candidate_name }} - {{ currentInterview?.position }}</h2>
        </template>
      </el-page-header>
      <div class="header-actions">
        <el-button
          v-if="currentInterview?.status === 'created'"
          type="primary"
          @click="handleStart"
        >
          <el-icon><VideoPlay /></el-icon>
          开始面试
        </el-button>
        <el-button
          v-if="currentInterview?.status === 'in_progress'"
          type="success"
          @click="handleComplete"
        >
          <el-icon><Check /></el-icon>
          完成面试
        </el-button>
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :xs="24" :md="16">
        <el-card class="chat-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>面试对话</span>
              <div class="header-tags">
                <el-tag :type="getStatusType(currentInterview?.status)">
                  {{ getStatusText(currentInterview?.status) }}
                </el-tag>
                <el-tag v-if="currentStage" type="info" class="stage-tag">
                  {{ getStageText(currentStage) }}
                </el-tag>
              </div>
            </div>
          </template>

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
              总进度: {{ stageProgress.overall_progress }}% | 剩余约 {{ stageProgress.remaining_turns }} 轮
            </div>
          </div>

          <div class="messages-container" ref="messagesContainer">
            <div
              v-for="(message, index) in messages"
              :key="index"
              :class="['message-wrapper', message.role]"
            >
              <div class="message-bubble" :class="message.role">
                <div class="message-content">{{ message.content }}</div>
                <div class="message-time">{{ formatTime(message.timestamp) }}</div>
              </div>
            </div>

            <el-empty v-if="messages.length === 0" description="暂无对话记录" />
          </div>

          <div class="input-area" v-if="currentInterview?.status === 'in_progress'">
            <el-input
              v-model="inputMessage"
              type="textarea"
              :rows="3"
              placeholder="请输入您的回答..."
              :disabled="loading"
              @keydown.enter.ctrl="handleSend"
            />
            <div class="input-actions">
              <span class="hint">Ctrl + Enter 发送</span>
              <el-button type="primary" @click="handleSend" :loading="loading">
                发送
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="8">
        <el-card class="info-card" shadow="never">
          <template #header>
            <span>面试信息</span>
          </template>
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
                  style="margin-right: 4px; margin-bottom: 4px;"
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
            <div class="info-item" v-if="currentInterview?.additional_requirements">
              <span class="label">额外要求：</span>
              <span class="value">{{ currentInterview?.additional_requirements }}</span>
            </div>
            <div class="info-item">
              <span class="label">创建时间：</span>
              <span class="value">{{ formatDate(currentInterview?.created_at) }}</span>
            </div>
          </div>
        </el-card>

        <!-- 阶段计划卡片 -->
        <el-card class="stages-plan-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>面试阶段计划</span>
              <el-tag size="small" type="info">{{ totalDuration }}分钟</el-tag>
            </div>
          </template>

          <el-steps direction="vertical" :space="80" :active="getStageStepIndex(currentStage)">
            <el-step
              v-for="(stage, index) in stagesConfig"
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
        </el-card>

        <el-card class="evaluation-card" shadow="never" v-if="evaluation">
          <template #header>
            <span>评估结果</span>
          </template>
          <div class="evaluation-content">
            <div class="score-section">
              <div class="overall-score">
                <div class="score-number">{{ evaluation.overall_score }}</div>
                <div class="score-label">综合得分</div>
              </div>
            </div>

            <el-divider />

            <div class="dimension-scores">
              <div
                v-for="(score, key) in evaluation.dimension_scores"
                :key="key"
                class="dimension-item"
              >
                <span class="dimension-label">{{ getDimensionLabel(key) }}</span>
                <el-progress :percentage="score" :stroke-width="8" />
              </div>
            </div>

            <el-divider />

            <div class="feedback-section">
              <h4>优势</h4>
              <ul>
                <li v-for="item in evaluation.strengths" :key="item">{{ item }}</li>
              </ul>

              <h4>待提升</h4>
              <ul>
                <li v-for="item in evaluation.weaknesses" :key="item">{{ item }}</li>
              </ul>

              <h4>建议</h4>
              <p class="recommendation" :class="getRecommendationClass(evaluation.recommendation)">
                {{ evaluation.recommendation }}
              </p>

              <h4>详细反馈</h4>
              <p class="feedback-text">{{ evaluation.feedback }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, Check } from '@element-plus/icons-vue'
import { useInterviewStore } from '@/stores/interview'
import { interviewApi } from '@/api/interview'

const route = useRoute()
const router = useRouter()
const interviewStore = useInterviewStore()

const loading = ref(false)
const currentInterview = ref(null)
const messages = ref([])
const evaluation = ref(null)
const inputMessage = ref('')
const messagesContainer = ref(null)
const stagesConfig = ref([])

const interviewId = computed(() => parseInt(route.params.id))

// 从 store 获取阶段和进度信息
const currentStage = computed(() => interviewStore.currentStage)
const stageProgress = computed(() => interviewStore.stageProgress)

// 计算总时长
const totalDuration = computed(() => {
  return stagesConfig.value.reduce((sum, stage) => sum + stage.time_allocation, 0)
})

onMounted(async () => {
  await loadStagesConfig()
  await loadInterviewDetail()
  await loadEvaluation()
  scrollToBottom()
})

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
    const data = await interviewStore.fetchInterviewDetail(interviewId.value)
    currentInterview.value = data
    messages.value = data.messages || []
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
    // 评估可能不存在，忽略错误
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

    loading.value = true
    await interviewStore.startInterview(interviewId.value)
    ElMessage.success('面试已开始')
    await loadInterviewDetail()
    scrollToBottom()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('开始面试失败', error)
    }
  } finally {
    loading.value = false
  }
}

async function handleSend() {
  const content = inputMessage.value.trim()
  if (!content) {
    ElMessage.warning('请输入消息内容')
    return
  }

  try {
    loading.value = true
    await interviewStore.sendMessage(interviewId.value, content)
    inputMessage.value = ''
    await nextTick()
    scrollToBottom()
  } catch (error) {
    console.error('发送消息失败', error)
  } finally {
    loading.value = false
  }
}

async function handleComplete() {
  try {
    await ElMessageBox.confirm('确认完成面试并生成评估报告？', '提示', {
      confirmButtonText: '完成',
      cancelButtonText: '取消',
      type: 'warning'
    })

    loading.value = true
    const result = await interviewStore.completeInterview(interviewId.value)
    ElMessage.success('面试已完成，评估报告已生成')
    await loadInterviewDetail()
    await loadEvaluation()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('完成面试失败', error)
    }
  } finally {
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
    welcome: '🎯 开场介绍',
    technical: '💻 技术问题',
    scenario: '🎨 情景问题',
    closing: '📝 结束阶段'
  }
  return textMap[stage] || stage
}

function getStageStepIndex(currentStageValue) {
  const stageOrder = ['welcome', 'technical', 'scenario', 'closing']
  return stageOrder.indexOf(currentStageValue)
}

function getStageStepStatus(stageValue) {
  const current = currentStage.value
  const stageOrder = ['welcome', 'technical', 'scenario', 'closing']
  
  if (!current) return 'wait'
  
  const currentIndex = stageOrder.indexOf(current)
  const stageIndex = stageOrder.indexOf(stageValue)
  
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
  if (recommendation.includes('录') || recommendation.includes('通过')) {
    return 'recommend-positive'
  } else if (recommendation.includes('不') || recommendation.includes('拒绝')) {
    return 'recommend-negative'
  }
  return 'recommend-neutral'
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
</script>

<style scoped lang="scss">
.interview-detail {
  max-width: 1400px;
  margin: 0 auto;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;

  h2 {
    margin: 0;
    font-size: 24px;
  }

  .header-actions {
    display: flex;
    gap: 12px;
  }
}

.chat-card {
  margin-bottom: 20px;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-tags {
      display: flex;
      gap: 8px;
      align-items: center;

      .stage-tag {
        font-size: 13px;
      }
    }
  }

  .stage-progress-bar {
    padding: 16px 0;
    border-bottom: 1px solid #eee;
    margin-bottom: 16px;

    .stage-info {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;

      .stage-label {
        font-size: 16px;
        font-weight: 600;
        color: #333;
      }

      .stage-meta {
        font-size: 13px;
        color: #666;
      }
    }

    .progress-text {
      text-align: center;
      font-size: 12px;
      color: #999;
      margin-top: 8px;
    }
  }

  .messages-container {
    min-height: 400px;
    max-height: 600px;
    overflow-y: auto;
    padding: 20px 0;
  }
}

.message-wrapper {
  margin-bottom: 16px;
  display: flex;

  &.user {
    justify-content: flex-end;
  }

  &.assistant {
    justify-content: flex-start;
  }
}

.message-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  word-wrap: break-word;

  &.user {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-bottom-right-radius: 4px;
  }

  &.assistant {
    background: #f5f7fa;
    color: #333;
    border-bottom-left-radius: 4px;
  }

  .message-content {
    white-space: pre-wrap;
    line-height: 1.6;
  }

  .message-time {
    font-size: 12px;
    opacity: 0.7;
    margin-top: 8px;
  }
}

.input-area {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;

  .input-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 12px;

    .hint {
      font-size: 12px;
      color: #999;
    }
  }
}

.info-card, .evaluation-card, .stages-plan-card {
  margin-bottom: 20px;
}

.stages-plan-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
  }

  .stage-step-title {
    display: flex;
    align-items: center;
    gap: 8px;

    .stage-name {
      font-weight: 600;
      font-size: 15px;
    }
  }

  .stage-step-desc {
    .stage-meta {
      display: flex;
      gap: 16px;
      margin-bottom: 8px;
      font-size: 13px;
      color: #666;
    }

    .stage-description {
      margin: 0;
      font-size: 13px;
      color: #999;
      line-height: 1.6;
    }
  }

  :deep(.el-step__head.is-process) {
    color: #667eea;
    border-color: #667eea;
  }

  :deep(.el-step__title.is-process) {
    color: #667eea;
  }

  :deep(.el-step__description.is-process) {
    color: #667eea;
  }
}

.info-list {
  .info-item {
    display: flex;
    margin-bottom: 12px;
    align-items: flex-start;

    &:last-child {
      margin-bottom: 0;
    }

    .label {
      font-weight: 600;
      min-width: 100px;
      color: #666;
    }

    .value {
      flex: 1;
    }

    .skills {
      flex: 1;
    }
  }
}

.evaluation-content {
  .score-section {
    text-align: center;
    padding: 20px 0;

    .overall-score {
      display: inline-block;

      .score-number {
        font-size: 64px;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1;
      }

      .score-label {
        font-size: 16px;
        color: #666;
        margin-top: 8px;
      }
    }
  }

  .dimension-scores {
    .dimension-item {
      margin-bottom: 16px;

      .dimension-label {
        display: block;
        margin-bottom: 8px;
        font-size: 14px;
        color: #666;
      }
    }
  }

  .feedback-section {
    h4 {
      font-size: 16px;
      margin: 16px 0 8px;
      color: #333;
    }

    ul {
      margin: 8px 0;
      padding-left: 20px;

      li {
        margin-bottom: 4px;
        color: #666;
      }
    }

    .recommendation {
      padding: 12px;
      border-radius: 8px;
      font-weight: 600;
      text-align: center;

      &.recommend-positive {
        background: #f0f9ff;
        color: #0ea5e9;
      }

      &.recommend-negative {
        background: #fef2f2;
        color: #ef4444;
      }

      &.recommend-neutral {
        background: #fefce8;
        color: #eab308;
      }
    }

    .feedback-text {
      line-height: 1.8;
      color: #666;
    }
  }
}

@media (max-width: 768px) {
  .detail-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .message-bubble {
    max-width: 85%;
  }
}
</style>
