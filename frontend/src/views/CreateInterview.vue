<template>
  <div class="create-interview-page">
    <div class="page-orb page-orb--primary"></div>
    <div class="page-orb page-orb--secondary"></div>

    <section class="hero-panel">
      <div class="hero-panel__top">
        <el-page-header class="page-back" @back="$router.back()" title="返回" />
        <div class="hero-panel__eyebrow">
          <span class="hero-panel__eyebrow-line"></span>
          <span>Interview Workspace</span>
        </div>
      </div>

      <div class="hero-panel__body">
        <div class="hero-copy">
          <h1>创建面试</h1>
          <p>
            在一个工作台中完成画像、简历与面试配置。页面只调整表现层，所有提交、校验与接口逻辑保持不变。
          </p>

          <div class="hero-status">
            <div class="status-chip">
              <span class="status-chip__label">岗位画像</span>
              <strong>{{ selectedPositionLabel }}</strong>
            </div>
            <div class="status-chip">
              <span class="status-chip__label">面试官画像</span>
              <strong>{{ selectedInterviewerLabel }}</strong>
            </div>
            <div class="status-chip">
              <span class="status-chip__label">预计时长</span>
              <strong>{{ formData.duration_minutes }} 分钟</strong>
            </div>
          </div>
        </div>

        <div class="hero-metrics">
          <article class="metric-card">
            <span class="metric-card__label">可选画像</span>
            <strong class="metric-card__value">{{ totalProfileCount }}</strong>
            <span class="metric-card__meta">岗位 + 面试官配置总数</span>
          </article>
          <article class="metric-card">
            <span class="metric-card__label">流程阶段</span>
            <strong class="metric-card__value">{{ stageCount }}</strong>
            <span class="metric-card__meta">已加载的面试阶段数量</span>
          </article>
          <article class="metric-card">
            <span class="metric-card__label">简历状态</span>
            <strong class="metric-card__value">{{ resumeStatusText }}</strong>
            <span class="metric-card__meta">支持 PDF，最大 10MB</span>
          </article>
        </div>
      </div>
    </section>

    <div class="workspace-grid">
      <main class="workspace-main">
        <el-form
          ref="formRef"
          :model="formData"
          :rules="formRules"
          label-position="top"
          class="workspace-form"
        >
          <section class="workspace-card intro-card">
            <div class="workspace-card__header">
              <div>
                <span class="section-kicker">使用说明</span>
                <h2>开始之前先确认必要信息</h2>
              </div>
            </div>

            <div class="intro-banner">
              <div class="intro-banner__icon">AI</div>
              <div class="intro-banner__content">
                <strong>创建面试需要选择岗位画像与面试官画像</strong>
                <p>简历为可选项。上传后可用于生成更有针对性的面试内容与追问。</p>
              </div>
            </div>
          </section>

          <section class="workspace-card">
            <div class="workspace-card__header">
              <div>
                <span class="section-kicker">Profile Setup</span>
                <h2>画像选择</h2>
                <p>先确定岗位标准与面试官风格，后续配置会围绕这两个画像展开。</p>
              </div>
              <div class="header-badge">{{ selectedProfileCount }}/2 已完成</div>
            </div>

            <div class="profile-grid">
              <article class="profile-panel">
                <div class="profile-panel__head">
                  <div>
                    <h3>岗位画像</h3>
                    <p>用于约束能力权重、技能要求和整场评估重点。</p>
                  </div>
                  <span class="profile-pill">{{ positionProfileCount }} 个可选</span>
                </div>

                <el-form-item label="岗位画像" prop="position_profile_id" class="form-item--tight">
                  <el-select
                    v-model="formData.position_profile_id"
                    placeholder="请选择岗位画像"
                    class="field-control"
                    clearable
                  >
                    <el-option-group label="系统预设">
                      <el-option
                        v-for="plugin in systemPositionProfiles"
                        :key="plugin.plugin_id"
                        :label="plugin.name"
                        :value="plugin.plugin_id"
                      >
                        <div class="profile-option">
                          <span class="profile-option__name">{{ plugin.name }}</span>
                          <span class="profile-option__desc">{{ plugin.description || '暂无描述' }}</span>
                        </div>
                      </el-option>
                    </el-option-group>
                    <el-option-group label="自定义">
                      <el-option
                        v-for="plugin in customPositionProfiles"
                        :key="plugin.plugin_id"
                        :label="plugin.name"
                        :value="plugin.plugin_id"
                      >
                        <div class="profile-option">
                          <span class="profile-option__name">{{ plugin.name }}</span>
                          <span class="profile-option__desc">{{ plugin.description || '暂无描述' }}</span>
                        </div>
                      </el-option>
                    </el-option-group>
                  </el-select>
                </el-form-item>

                <div class="profile-panel__footer">
                  <div class="selection-hint">
                    <span class="selection-hint__label">当前选择</span>
                    <strong>{{ selectedPositionLabel }}</strong>
                  </div>
                  <el-button text type="primary" @click="showProfileConfig('position')">
                    新建自定义岗位画像
                  </el-button>
                </div>
              </article>

              <article class="profile-panel">
                <div class="profile-panel__head">
                  <div>
                    <h3>面试官画像</h3>
                    <p>用于定义提问风格、语气、追问倾向和整体交流氛围。</p>
                  </div>
                  <span class="profile-pill">{{ interviewerProfileCount }} 个可选</span>
                </div>

                <el-form-item label="面试官画像" prop="interviewer_profile_id" class="form-item--tight">
                  <el-select
                    v-model="formData.interviewer_profile_id"
                    placeholder="请选择面试官画像"
                    class="field-control"
                    clearable
                  >
                    <el-option-group label="系统预设">
                      <el-option
                        v-for="plugin in systemInterviewerProfiles"
                        :key="plugin.plugin_id"
                        :label="plugin.name"
                        :value="plugin.plugin_id"
                      >
                        <div class="profile-option">
                          <span class="profile-option__name">{{ plugin.name }}</span>
                          <span class="profile-option__desc">{{ plugin.description || '暂无描述' }}</span>
                        </div>
                      </el-option>
                    </el-option-group>
                    <el-option-group label="自定义">
                      <el-option
                        v-for="plugin in customInterviewerProfiles"
                        :key="plugin.plugin_id"
                        :label="plugin.name"
                        :value="plugin.plugin_id"
                      >
                        <div class="profile-option">
                          <span class="profile-option__name">{{ plugin.name }}</span>
                          <span class="profile-option__desc">{{ plugin.description || '暂无描述' }}</span>
                        </div>
                      </el-option>
                    </el-option-group>
                  </el-select>
                </el-form-item>

                <div class="profile-panel__footer">
                  <div class="selection-hint">
                    <span class="selection-hint__label">当前选择</span>
                    <strong>{{ selectedInterviewerLabel }}</strong>
                  </div>
                  <el-button text type="primary" @click="showProfileConfig('interviewer')">
                    新建自定义面试官画像
                  </el-button>
                </div>
              </article>
            </div>
          </section>

          <section class="workspace-card">
            <div class="workspace-card__header">
              <div>
                <span class="section-kicker">Resume Upload</span>
                <h2>简历上传</h2>
                <p>上传简历后，系统会在创建面试时自动解析文本并写入当前面试上下文。</p>
              </div>
              <div class="header-badge header-badge--soft">{{ resumeStatusText }}</div>
            </div>

            <div class="upload-shell">
              <el-form-item label="简历文件（可选）" class="form-item--upload">
                <el-upload
                  ref="uploadRef"
                  class="resume-uploader"
                  :action="uploadUrl"
                  :headers="uploadHeaders"
                  :on-success="handleUploadSuccess"
                  :on-error="handleUploadError"
                  :on-change="handleFileChange"
                  :before-upload="beforeUpload"
                  :file-list="fileList"
                  :limit="1"
                  accept=".pdf"
                  drag
                  :auto-upload="false"
                >
                  <div class="upload-visual">
                    <div class="upload-visual__icon">
                      <el-icon><UploadFilled /></el-icon>
                    </div>
                    <div class="upload-visual__copy">
                      <strong>拖拽 PDF 到此处，或点击上传</strong>
                      <p>保持原有手动提交流程，不会在选择文件后立即上传。</p>
                    </div>
                  </div>
                </el-upload>
              </el-form-item>

              <div class="upload-meta">
                <div class="upload-rule">
                  <span>文件要求</span>
                  <strong>仅支持 PDF，大小不超过 10MB</strong>
                </div>
                <div class="upload-rule">
                  <span>上传时机</span>
                  <strong>点击“创建面试”后随表单一起处理</strong>
                </div>
              </div>

              <div v-if="selectedResumeName" class="upload-file-state">
                <span class="upload-file-state__label">已选文件</span>
                <strong>{{ selectedResumeName }}</strong>
              </div>
            </div>
          </section>

          <section class="workspace-card">
            <div class="workspace-card__header">
              <div>
                <span class="section-kicker">Interview Settings</span>
                <h2>面试配置</h2>
                <p>调整预计时长与补充要求，不影响既有提交流程与字段结构。</p>
              </div>
              <div class="duration-badge">
                <span>预计时长</span>
                <strong>{{ formData.duration_minutes }} min</strong>
              </div>
            </div>

            <div class="settings-grid">
              <el-form-item label="面试时长" prop="duration_minutes" class="duration-form-item settings-grid__full">
                <div class="slider-shell">
                  <el-slider
                    v-model="formData.duration_minutes"
                    :min="15"
                    :max="120"
                    :step="5"
                    show-stops
                    :marks="durationMarks"
                    class="duration-slider"
                  />
                </div>
              </el-form-item>

              <div class="settings-grid__side">
                <div class="mini-stat">
                  <span>总阶段时长</span>
                  <strong>{{ totalDuration }} 分钟</strong>
                </div>
                <div class="mini-stat">
                  <span>预计轮次上限</span>
                  <strong>{{ totalMaxTurns }} 轮</strong>
                </div>
              </div>
            </div>

            <el-form-item label="额外要求（可选）" class="requirements-item">
              <el-input
                v-model="formData.additional_requirements"
                type="textarea"
                :rows="5"
                placeholder="输入候选人背景、需要强调的题型、答题方式要求或其他补充信息。"
              />
            </el-form-item>
          </section>

          <div class="action-bar">
            <div class="action-bar__summary">
              <span>已完成基础配置，准备创建面试</span>
              <strong>{{ selectedProfileCount }}/2 个必选画像已选择</strong>
            </div>
            <div class="action-bar__buttons">
              <el-button @click="handleReset" size="large">重置</el-button>
              <el-button type="primary" @click="handleSubmit" :loading="loading" size="large">
                创建面试
              </el-button>
            </div>
          </div>
        </el-form>

        <ProfileConfigDialog
          v-model="profileConfigVisible"
          :plugin-type="configPluginType"
          @success="handleProfileConfigSuccess"
        />
      </main>

      <aside class="workspace-sidebar">
        <section class="workspace-card stage-card">
          <div class="workspace-card__header">
            <div>
              <span class="section-kicker">Stage Overview</span>
              <h2>面试阶段计划</h2>
              <p>根据当前阶段配置预览整场面试节奏，右侧面板在桌面端保持吸附。</p>
            </div>
          </div>

          <div class="stage-summary-grid">
            <article class="stage-summary-item">
              <span>总时长</span>
              <strong>{{ totalDuration }}</strong>
              <em>分钟</em>
            </article>
            <article class="stage-summary-item">
              <span>总轮次</span>
              <strong>{{ totalMaxTurns }}</strong>
              <em>轮</em>
            </article>
            <article class="stage-summary-item">
              <span>阶段数</span>
              <strong>{{ stageCount }}</strong>
              <em>个</em>
            </article>
          </div>

          <div v-if="stagesLoading" class="stage-skeleton">
            <div v-for="index in 3" :key="index" class="stage-skeleton__item"></div>
          </div>

          <div v-else-if="stagesConfig.length" class="flow-scroll">
            <div class="flow-track">
              <div
                v-for="(stage, index) in stagesConfig"
                :key="stage.stage"
                :class="['flow-item', { 'flow-item--disabled': stage.enabled === false }]"
              >
                <div class="left-node">
                  <div class="stage-index">{{ index + 1 }}</div>
                  <div v-if="index < stagesConfig.length - 1" class="stage-line"></div>
                </div>

                <div class="stage-item-card">
                  <div class="stage-item-card__top">
                    <strong class="stage-name">{{ stage.name }}</strong>
                    <span class="stage-tag">{{ stage.enabled === false ? '已停用' : '进行中配置' }}</span>
                  </div>
                  <div class="stage-meta">
                    <span>{{ stage.time_allocation }} 分钟</span>
                    <span>{{ stage.min_turns }} - {{ stage.max_turns }} 轮对话</span>
                  </div>
                  <p class="stage-desc">{{ stage.description || '暂无阶段描述' }}</p>
                </div>
              </div>
            </div>
          </div>

          <el-empty v-else description="暂无阶段配置" />

          <div class="sidebar-tip">
            <span class="sidebar-tip__title">创建提示</span>
            <p>如果阶段总时长与当前选择时长不一致，仍以你在表单中设置的预计时长作为提交参数。</p>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { useInterviewStore } from '@/stores/interview'
import { interviewApi } from '@/api/interview'
import { profileApi } from '@/api/profile'
import ProfileConfigDialog from '@/components/ProfileConfigDialog.vue'

const router = useRouter()
const interviewStore = useInterviewStore()

const formRef = ref(null)
const loading = ref(false)
const stagesConfig = ref([])
const stagesLoading = ref(false)

const profileConfigVisible = ref(false)
const configPluginType = ref('')
const systemPositionProfiles = ref([])
const customPositionProfiles = ref([])
const systemInterviewerProfiles = ref([])
const customInterviewerProfiles = ref([])

const uploadRef = ref(null)
const fileList = ref([])
const formDataResume = ref(null)
const uploadUrl = computed(() => {
  const isDev = import.meta.env.DEV
  return isDev ? 'http://localhost:8000/api/interviews/upload-resume' : '/api/interviews/upload-resume'
})
const uploadHeaders = ref({})

const totalDuration = computed(() => stagesConfig.value.reduce((sum, stage) => sum + stage.time_allocation, 0))
const totalMaxTurns = computed(() => stagesConfig.value.reduce((sum, stage) => sum + stage.max_turns, 0))
const stageCount = computed(() => stagesConfig.value.length)
const positionProfileCount = computed(
  () => systemPositionProfiles.value.length + customPositionProfiles.value.length
)
const interviewerProfileCount = computed(
  () => systemInterviewerProfiles.value.length + customInterviewerProfiles.value.length
)
const totalProfileCount = computed(() => positionProfileCount.value + interviewerProfileCount.value)
const selectedProfileCount = computed(() => {
  let count = 0
  if (formData.position_profile_id) count += 1
  if (formData.interviewer_profile_id) count += 1
  return count
})
const durationMarks = {
  15: '15 分钟',
  30: '30 分钟',
  60: '60 分钟',
  120: '120 分钟'
}

onMounted(async () => {
  await loadStagesConfig()
  await loadProfiles()
})

async function loadProfiles() {
  try {
    const [positionRes, interviewerRes] = await Promise.all([
      profileApi.listPlugins({ type: 'position' }),
      profileApi.listPlugins({ type: 'interviewer' })
    ])

    if (positionRes.success) {
      systemPositionProfiles.value = positionRes.data.filter(p => p.is_system)
      customPositionProfiles.value = positionRes.data.filter(p => !p.is_system)
    }
    if (interviewerRes.success) {
      systemInterviewerProfiles.value = interviewerRes.data.filter(p => p.is_system)
      customInterviewerProfiles.value = interviewerRes.data.filter(p => !p.is_system)
    }
  } catch (error) {
    console.error('加载画像列表失败', error)
  }
}

async function loadStagesConfig() {
  stagesLoading.value = true
  try {
    const data = await interviewApi.getStagesConfig()
    stagesConfig.value = data.stages
  } catch (error) {
    console.error('加载阶段配置失败', error)
  } finally {
    stagesLoading.value = false
  }
}

const formData = reactive({
  position_profile_id: '',
  interviewer_profile_id: '',
  duration_minutes: 30,
  additional_requirements: '',
  resume_file_id: ''
})

const formRules = {
  position_profile_id: [
    { required: true, message: '请选择岗位画像', trigger: 'change' }
  ],
  interviewer_profile_id: [
    { required: true, message: '请选择面试官画像', trigger: 'change' }
  ]
}

const selectedPositionLabel = computed(() => {
  const matched = [...systemPositionProfiles.value, ...customPositionProfiles.value]
    .find(plugin => plugin.plugin_id === formData.position_profile_id)
  return matched?.name || '未选择'
})

const selectedInterviewerLabel = computed(() => {
  const matched = [...systemInterviewerProfiles.value, ...customInterviewerProfiles.value]
    .find(plugin => plugin.plugin_id === formData.interviewer_profile_id)
  return matched?.name || '未选择'
})

const selectedResumeName = computed(() => {
  const currentFile = fileList.value[0]
  return currentFile?.name || formDataResume.value?.name || ''
})

const resumeStatusText = computed(() => (selectedResumeName.value ? '已选文件' : '未上传'))

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    loading.value = true

    let resumeText = null
    if (formDataResume.value) {
      try {
        const resumeFormData = new FormData()
        resumeFormData.append('file', formDataResume.value)

        const response = await fetch(uploadUrl.value, {
          method: 'POST',
          body: resumeFormData
        })

        if (!response.ok) {
          throw new Error('简历上传失败')
        }

        const result = await response.json()
        formData.resume_file_id = result.file_id
        resumeText = result.resume_text
      } catch (error) {
        ElMessage.error('简历上传失败，请重试')
        loading.value = false
        return
      }
    } else {
      formData.resume_file_id = ''
    }

    await interviewStore.createInterview({
      ...formData,
      resume_text: resumeText
    })

    ElMessage.success('面试创建成功')
    router.push('/interviews')
  } catch (error) {
    if (error !== false) {
      console.error('创建面试失败', error)
    }
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  formRef.value.resetFields()
  formData.resume_file_id = ''
  formDataResume.value = null
  fileList.value = []
  uploadRef.value?.clearFiles?.()
}

function showProfileConfig(type) {
  configPluginType.value = type
  profileConfigVisible.value = true
}

async function handleProfileConfigSuccess(newPlugin) {
  await loadProfiles()

  if (newPlugin.type === 'position') {
    formData.position_profile_id = newPlugin.plugin_id
  } else if (newPlugin.type === 'interviewer') {
    formData.interviewer_profile_id = newPlugin.plugin_id
  }

  ElMessage.success(`画像“${newPlugin.name}”创建成功并已选中`)
}

function beforeUpload(file) {
  const isPDF = file.type === 'application/pdf'
  const isLt10M = file.size / 1024 / 1024 < 10

  if (!isPDF) {
    ElMessage.error('只能上传 PDF 格式的简历')
    return false
  }
  if (!isLt10M) {
    ElMessage.error('简历文件大小不能超过 10MB')
    return false
  }
  return true
}

function handleFileChange(file) {
  if (file.raw) {
    formDataResume.value = file.raw
  }
}

function handleUploadSuccess(response) {
  formData.resume_file_id = response.file_id
}

function handleUploadError(error) {
  console.error('Upload error:', error)
}
</script>

<style scoped lang="scss">
.create-interview-page {
  position: relative;
  max-width: 1480px;
  margin: 0 auto;
  padding: 18px 0 40px;
  overflow: hidden;
}

.page-orb {
  position: absolute;
  border-radius: 999px;
  filter: blur(16px);
  opacity: 0.65;
  pointer-events: none;
}

.page-orb--primary {
  top: 54px;
  right: -90px;
  width: 280px;
  height: 280px;
  background: radial-gradient(circle, rgba(103, 160, 255, 0.24) 0%, rgba(103, 160, 255, 0) 72%);
}

.page-orb--secondary {
  top: 260px;
  left: -120px;
  width: 320px;
  height: 320px;
  background: radial-gradient(circle, rgba(74, 196, 177, 0.16) 0%, rgba(74, 196, 177, 0) 74%);
}

.hero-panel,
.workspace-card,
.action-bar {
  position: relative;
  border: 1px solid rgba(255, 255, 255, 0.85);
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(249, 251, 255, 0.92) 100%);
  box-shadow:
    0 24px 50px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(18px);
}

.hero-panel {
  padding: 22px 24px 28px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(245, 249, 255, 0.94) 50%, rgba(241, 249, 248, 0.92) 100%);
}

.hero-panel::before,
.workspace-card::before,
.action-bar::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 1px;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.05), rgba(143, 170, 255, 0.6), rgba(255, 255, 255, 0.05));
}

.hero-panel__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}

.page-back {
  margin-right: auto;
}

.hero-panel__eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: #60708d;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.hero-panel__eyebrow-line {
  width: 34px;
  height: 1px;
  background: linear-gradient(90deg, #3d7cff, rgba(61, 124, 255, 0));
}

.hero-panel__body {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(320px, 0.9fr);
  gap: 22px;
}

.hero-copy h1 {
  margin: 0;
  font-size: 40px;
  line-height: 1.08;
  font-weight: 800;
  color: #152033;
}

.hero-copy p {
  margin: 14px 0 0;
  max-width: 760px;
  color: #60708d;
  font-size: 15px;
  line-height: 1.8;
}

.hero-status {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 24px;
}

.status-chip {
  min-width: 180px;
  padding: 14px 16px;
  border: 1px solid rgba(140, 157, 186, 0.18);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.78);
}

.status-chip__label {
  display: block;
  margin-bottom: 6px;
  color: #7b88a1;
  font-size: 12px;
}

.status-chip strong {
  color: #16213a;
  font-size: 16px;
  font-weight: 700;
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.metric-card {
  padding: 18px;
  border-radius: 22px;
  background:
    linear-gradient(180deg, rgba(253, 254, 255, 0.94), rgba(241, 245, 252, 0.88));
  border: 1px solid rgba(145, 164, 198, 0.18);
  min-height: 142px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.metric-card__label,
.metric-card__meta {
  color: #72819c;
  font-size: 12px;
}

.metric-card__value {
  color: #15213b;
  font-size: 30px;
  font-weight: 800;
  line-height: 1.1;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(320px, 0.9fr);
  gap: 24px;
  margin-top: 24px;
}

.workspace-main,
.workspace-sidebar {
  min-width: 0;
}

.workspace-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.workspace-card {
  padding: 26px;
}

.workspace-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}

.workspace-card__header h2 {
  margin: 6px 0 0;
  font-size: 24px;
  line-height: 1.2;
  color: #142038;
}

.workspace-card__header p {
  margin: 10px 0 0;
  color: #72809a;
  font-size: 14px;
  line-height: 1.75;
}

.section-kicker {
  display: inline-block;
  color: #4d78d8;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.header-badge,
.profile-pill,
.stage-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 7px 12px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.header-badge {
  color: #1742a3;
  background: rgba(79, 128, 255, 0.12);
}

.header-badge--soft {
  color: #2f6b66;
  background: rgba(83, 181, 166, 0.12);
}

.intro-card {
  padding-bottom: 24px;
}

.intro-banner {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 18px 20px;
  border-radius: 22px;
  background: linear-gradient(135deg, rgba(239, 245, 255, 0.92), rgba(244, 252, 250, 0.95));
  border: 1px solid rgba(144, 168, 211, 0.18);
}

.intro-banner__icon {
  flex: 0 0 52px;
  width: 52px;
  height: 52px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #214fd6, #4caec1);
  color: #fff;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.intro-banner__content strong {
  display: block;
  color: #1c2a45;
  font-size: 16px;
}

.intro-banner__content p {
  margin: 8px 0 0;
  color: #66758f;
  line-height: 1.7;
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.profile-panel {
  padding: 20px;
  border-radius: 24px;
  border: 1px solid rgba(143, 164, 198, 0.16);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(246, 249, 253, 0.94));
}

.profile-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.profile-panel__head h3 {
  margin: 0;
  color: #17243d;
  font-size: 18px;
}

.profile-panel__head p {
  margin: 8px 0 0;
  color: #73819c;
  font-size: 13px;
  line-height: 1.7;
}

.profile-pill {
  color: #315ba9;
  background: rgba(112, 141, 210, 0.12);
}

.profile-panel__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 14px;
}

.selection-hint {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.selection-hint__label {
  color: #7c8aa2;
  font-size: 12px;
}

.selection-hint strong {
  color: #16213a;
  font-size: 14px;
}

.upload-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.upload-visual {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18px;
  min-height: 180px;
}

.upload-visual__icon {
  width: 68px;
  height: 68px;
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  color: #3367e6;
  background: linear-gradient(135deg, rgba(80, 130, 255, 0.14), rgba(90, 191, 176, 0.14));
}

.upload-visual__copy {
  text-align: left;
}

.upload-visual__copy strong {
  display: block;
  color: #19233d;
  font-size: 18px;
}

.upload-visual__copy p {
  margin: 8px 0 0;
  color: #71809a;
  line-height: 1.7;
}

.upload-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.upload-rule,
.upload-file-state,
.mini-stat {
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(141, 163, 195, 0.16);
  background: rgba(255, 255, 255, 0.72);
}

.upload-rule span,
.upload-file-state__label,
.mini-stat span {
  display: block;
  color: #7c8aa2;
  font-size: 12px;
  margin-bottom: 6px;
}

.upload-rule strong,
.upload-file-state strong,
.mini-stat strong {
  color: #18233c;
  font-size: 14px;
  line-height: 1.6;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 12px;
}

.settings-grid__full {
  grid-column: 1 / -1;
  margin-bottom: 0;
}

.settings-grid__side {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  grid-column: 1 / -1;
}

.slider-shell {
  width: 100%;
  padding: 22px 18px 12px;
  border-radius: 22px;
  border: 1px solid rgba(141, 163, 195, 0.16);
  background: rgba(255, 255, 255, 0.72);
}

.duration-badge {
  min-width: 138px;
  padding: 12px 14px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(63, 112, 228, 0.12), rgba(74, 190, 171, 0.12));
  text-align: right;
}

.duration-badge span {
  display: block;
  color: #62708d;
  font-size: 12px;
}

.duration-badge strong {
  color: #12203a;
  font-size: 22px;
  font-weight: 800;
}

.requirements-item {
  margin-top: 10px;
}

.action-bar {
  position: sticky;
  bottom: 12px;
  z-index: 4;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 22px;
}

.action-bar__summary span {
  display: block;
  color: #6d7b95;
  font-size: 13px;
  margin-bottom: 4px;
}

.action-bar__summary strong {
  color: #15213b;
  font-size: 18px;
}

.action-bar__buttons {
  display: flex;
  align-items: center;
  gap: 12px;
}

.workspace-sidebar {
  position: relative;
}

.stage-card {
  position: sticky;
  top: 24px;
}

.stage-summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 22px;
}

.stage-summary-item {
  padding: 16px 14px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(249, 251, 255, 0.95), rgba(241, 245, 252, 0.92));
  border: 1px solid rgba(141, 163, 195, 0.16);
  text-align: center;
}

.stage-summary-item span,
.stage-summary-item em {
  display: block;
  color: #7a88a0;
  font-size: 12px;
  font-style: normal;
}

.stage-summary-item strong {
  display: block;
  margin: 8px 0 4px;
  color: #15213b;
  font-size: 26px;
  font-weight: 800;
}

.stage-skeleton {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stage-skeleton__item {
  height: 104px;
  border-radius: 22px;
  background: linear-gradient(90deg, rgba(238, 242, 248, 0.9), rgba(247, 249, 253, 0.98), rgba(238, 242, 248, 0.9));
  background-size: 220% 100%;
  animation: skeleton-shimmer 1.8s infinite linear;
}

.flow-scroll {
  max-height: 520px;
  overflow: auto;
  padding-right: 4px;
}

.flow-track {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.flow-item {
  display: flex;
  align-items: stretch;
  gap: 12px;
}

.flow-item--disabled {
  opacity: 0.62;
}

.left-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 34px;
  flex: 0 0 34px;
}

.stage-index {
  width: 34px;
  height: 34px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 14px;
  font-weight: 800;
  background: linear-gradient(135deg, #2d64ef, #55b5b0);
  box-shadow: 0 14px 22px rgba(59, 102, 214, 0.22);
}

.stage-line {
  width: 2px;
  flex: 1;
  margin-top: 8px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(62, 112, 226, 0.4), rgba(62, 112, 226, 0.06));
}

.stage-item-card {
  flex: 1;
  min-width: 0;
  padding: 16px 16px 18px;
  border-radius: 22px;
  border: 1px solid rgba(141, 163, 195, 0.16);
  background: rgba(255, 255, 255, 0.82);
}

.stage-item-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.stage-name {
  color: #18233c;
  font-size: 16px;
  font-weight: 700;
}

.stage-tag {
  color: #315ba9;
  background: rgba(112, 141, 210, 0.12);
}

.stage-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin-top: 10px;
  color: #74839d;
  font-size: 12px;
}

.stage-desc {
  margin: 10px 0 0;
  color: #6d7c95;
  font-size: 13px;
  line-height: 1.7;
}

.sidebar-tip {
  margin-top: 20px;
  padding: 16px 18px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(245, 248, 255, 0.95), rgba(242, 250, 248, 0.96));
  border: 1px solid rgba(141, 163, 195, 0.16);
}

.sidebar-tip__title {
  display: block;
  margin-bottom: 8px;
  color: #1b2a46;
  font-size: 14px;
  font-weight: 700;
}

.sidebar-tip p {
  margin: 0;
  color: #6f7e97;
  font-size: 13px;
  line-height: 1.7;
}

.field-control {
  width: 100%;
}

.form-item--tight,
.form-item--upload {
  margin-bottom: 0;
}

.profile-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.profile-option__name {
  color: #16213a;
  font-weight: 600;
}

.profile-option__desc {
  color: #7b88a1;
  font-size: 12px;
}

:deep(.el-page-header__title) {
  color: #55637d;
  font-weight: 700;
}

:deep(.el-form-item__label) {
  margin-bottom: 10px;
  color: #22304a;
  font-size: 13px;
  font-weight: 700;
}

:deep(.el-input__wrapper),
:deep(.el-select__wrapper),
:deep(.el-textarea__inner) {
  border-radius: 16px;
  min-height: 50px;
  border: 1px solid transparent;
  background: rgba(248, 250, 253, 0.9);
  box-shadow: inset 0 0 0 1px rgba(149, 166, 195, 0.18);
  transition: box-shadow 0.2s ease, transform 0.2s ease, background 0.2s ease;
}

:deep(.el-textarea__inner) {
  min-height: 140px;
  padding: 14px 16px;
}

:deep(.el-input__wrapper.is-focus),
:deep(.el-select__wrapper.is-focused),
:deep(.el-textarea__inner:focus) {
  background: rgba(255, 255, 255, 0.98);
  box-shadow:
    inset 0 0 0 1px rgba(76, 130, 255, 0.4),
    0 0 0 4px rgba(76, 130, 255, 0.08);
  transform: translateY(-1px);
}

:deep(.el-button) {
  height: 44px;
  padding: 0 18px;
  border-radius: 14px;
  font-weight: 700;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #1f4fd4, #3fa4c1);
  border: none;
  box-shadow: 0 16px 28px rgba(49, 92, 193, 0.24);
}

:deep(.el-button--primary:hover),
:deep(.el-button--primary:focus-visible) {
  opacity: 0.94;
}

:deep(.el-button:not(.el-button--primary)) {
  border-color: rgba(147, 164, 193, 0.24);
  color: #22304a;
  background: rgba(255, 255, 255, 0.82);
}

:deep(.el-button.is-text) {
  height: auto;
  padding: 0;
  background: transparent;
  box-shadow: none;
}

:deep(.el-upload) {
  width: 100%;
}

:deep(.el-upload-dragger) {
  width: 100%;
  padding: 0 24px;
  border-radius: 26px;
  border: 1px dashed rgba(92, 127, 195, 0.38);
  background:
    linear-gradient(135deg, rgba(247, 250, 255, 0.94), rgba(241, 249, 247, 0.92));
  overflow: hidden;
  transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
}

:deep(.el-upload-dragger:hover) {
  transform: translateY(-2px);
  border-color: rgba(74, 116, 216, 0.56);
  box-shadow: 0 18px 30px rgba(27, 55, 113, 0.08);
}

:deep(.el-upload-list__item) {
  border-radius: 14px;
}

:deep(.el-slider__runway) {
  height: 8px;
  border-radius: 999px;
  background: rgba(162, 176, 202, 0.22);
}

:deep(.el-slider__bar) {
  height: 8px;
  border-radius: 999px;
  background: linear-gradient(90deg, #2f63ec, #4db8b1);
}

:deep(.el-slider__button) {
  width: 18px;
  height: 18px;
  border: 4px solid #ffffff;
  background: #2f63ec;
  box-shadow: 0 8px 16px rgba(46, 99, 236, 0.28);
}

:deep(.el-slider__marks-text) {
  margin-top: 14px;
  color: #7a88a0;
  white-space: nowrap;
}

:deep(.duration-slider) {
  width: 100%;
}

:deep(.el-form-item.is-error .el-input__wrapper),
:deep(.el-form-item.is-error .el-select__wrapper),
:deep(.el-form-item.is-error .el-textarea__inner) {
  box-shadow: inset 0 0 0 1px rgba(215, 77, 77, 0.34);
}

@keyframes skeleton-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -20% 0;
  }
}

@media (max-width: 1280px) {
  .hero-panel__body,
  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .hero-metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 992px) {
  .create-interview-page {
    padding-top: 8px;
  }

  .hero-copy h1 {
    font-size: 32px;
  }

  .profile-grid,
  .upload-meta,
  .stage-summary-grid,
  .hero-metrics {
    grid-template-columns: 1fr;
  }

  .profile-panel__footer,
  .workspace-card__header,
  .hero-panel__top,
  .action-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .action-bar {
    position: static;
  }

  .action-bar__buttons {
    width: 100%;
  }

  .action-bar__buttons :deep(.el-button) {
    flex: 1;
  }

  .stage-card {
    position: static;
  }
}

@media (max-width: 640px) {
  .hero-panel,
  .workspace-card,
  .action-bar {
    border-radius: 22px;
  }

  .hero-panel,
  .workspace-card {
    padding: 20px;
  }

  .upload-visual {
    flex-direction: column;
    text-align: center;
  }

  .upload-visual__copy {
    text-align: center;
  }

  .settings-grid__side {
    grid-template-columns: 1fr;
  }

  .action-bar__buttons {
    flex-direction: column;
  }

  .action-bar__buttons :deep(.el-button) {
    width: 100%;
  }
}
</style>
