<template>
  <div class="create-interview">
    <el-page-header @back="$router.back()" title="返回">
      <template #content>
        <h2>创建面试</h2>
      </template>
    </el-page-header>

    <el-row :gutter="20">
      <el-col :xs="24" :lg="16">
        <el-card class="form-card" shadow="never">
          <el-form
            ref="formRef"
            :model="formData"
            :rules="formRules"
            label-width="120px"
            label-position="top"
          >
            <el-alert
              type="info"
              :closable="false"
              show-icon
              title="创建面试需选择岗位画像和面试官画像；简历可选（上传后可提升面试针对性）。"
              style="margin-bottom: 16px"
            />

            <el-form-item label="岗位画像" prop="position_profile_id">
              <div class="profile-select-wrapper">
                <el-select
                  v-model="formData.position_profile_id"
                  placeholder="请选择岗位画像"
                  style="width: 100%"
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
                        <span class="profile-name">{{ plugin.name }}</span>
                        <span class="profile-desc">{{ plugin.description }}</span>
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
                        <span class="profile-name">{{ plugin.name }}</span>
                        <span class="profile-desc">{{ plugin.description }}</span>
                      </div>
                    </el-option>
                  </el-option-group>
                </el-select>
                <el-button
                  text
                  type="primary"
                  size="small"
                  @click="showProfileConfig('position')"
                  style="margin-top: 8px"
                >
                  <el-icon><Plus /></el-icon>
                  创建自定义岗位画像
                </el-button>
              </div>
            </el-form-item>

            <el-form-item label="面试官画像" prop="interviewer_profile_id">
              <div class="profile-select-wrapper">
                <el-select
                  v-model="formData.interviewer_profile_id"
                  placeholder="请选择面试官画像"
                  style="width: 100%"
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
                        <span class="profile-name">{{ plugin.name }}</span>
                        <span class="profile-desc">{{ plugin.description }}</span>
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
                        <span class="profile-name">{{ plugin.name }}</span>
                        <span class="profile-desc">{{ plugin.description }}</span>
                      </div>
                    </el-option>
                  </el-option-group>
                </el-select>
                <el-button
                  text
                  type="primary"
                  size="small"
                  @click="showProfileConfig('interviewer')"
                  style="margin-top: 8px"
                >
                  <el-icon><Plus /></el-icon>
                  创建自定义面试官画像
                </el-button>
              </div>
            </el-form-item>

            <el-form-item label="简历上传（可选）">
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
                <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                <div class="el-upload__text">
                  将简历文件拖到此处，或<em>点击上传</em>
                </div>
                <template #tip>
                  <div class="el-upload__tip">只支持 PDF 格式，文件大小不超过 10MB</div>
                </template>
              </el-upload>
            </el-form-item>

            <el-divider content-position="left">面试配置</el-divider>

            <el-form-item label="面试时长" prop="duration_minutes" class="duration-form-item">
              <el-slider
                class="duration-slider"
                v-model="formData.duration_minutes"
                :min="15"
                :max="120"
                :step="5"
                show-stops
                :marks="{ 15: '15分钟', 30: '30分钟', 60: '60分钟', 120: '120分钟' }"
              />
              <div class="duration-display">预计时长：{{ formData.duration_minutes }} 分钟</div>
            </el-form-item>

            <el-form-item label="额外要求（可选）">
              <el-input
                v-model="formData.additional_requirements"
                type="textarea"
                :rows="4"
                placeholder="请输入额外的面试要求或注意事项"
              />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="handleSubmit" :loading="loading" size="large">
                <el-icon><Check /></el-icon>
                创建面试
              </el-button>
              <el-button @click="handleReset" size="large">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <ProfileConfigDialog
          v-model="profileConfigVisible"
          :plugin-type="configPluginType"
          @success="handleProfileConfigSuccess"
        />
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card class="stages-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>面试阶段计划</span>
              <el-tag type="info">{{ totalDuration }}分钟</el-tag>
            </div>
          </template>

          <div v-if="stagesConfig.length" class="flow-scroll">
            <div class="flow-track">
              <div
                v-for="(stage, index) in stagesConfig"
                :key="stage.stage"
                class="flow-item"
              >
                <div class="left-node">
                  <div class="stage-index" :class="{ 'is-disabled': stage.enabled === false }">{{ index + 1 }}</div>
                  <div v-if="index < stagesConfig.length - 1" class="stage-line"></div>
                </div>

                <div class="stage-item-card">
                  <div class="stage-header">
                    <span class="stage-name">{{ stage.name }}</span>
                  </div>
                  <div class="stage-meta">{{ stage.time_allocation }} 分钟 · {{ stage.min_turns }}-{{ stage.max_turns }} 轮</div>
                  <p class="stage-desc">{{ stage.description }}</p>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无阶段配置" />

          <el-divider />

          <div class="stages-summary">
            <div class="summary-item">
              <span class="label">总时长：</span>
              <span class="value">{{ totalDuration }} 分钟</span>
            </div>
            <div class="summary-item">
              <span class="label">总轮次：</span>
              <span class="value">约 {{ totalMaxTurns }} 轮对话</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check, Plus, UploadFilled } from '@element-plus/icons-vue'
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
.create-interview {
  max-width: 1400px;
  margin: 0 auto;
}

h2 {
  margin: 0;
  font-size: 24px;
}

.form-card {
  margin-top: 24px;
}

.stages-card {
  margin-top: 24px;
  position: sticky;
  top: 24px;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
  }

  .stages-summary {
    .summary-item {
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      font-size: 14px;

      .label {
        color: #666;
      }

      .value {
        font-weight: 600;
        color: #333;
      }
    }
  }
}

.flow-scroll {
  overflow: auto;
  max-height: 440px;
  padding-right: 4px;
}

.flow-track {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.flow-item {
  display: flex;
  align-items: stretch;
  gap: 10px;
  width: 100%;
}

.left-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 30px;
  flex: 0 0 30px;
}

.stage-index {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 2px solid #409eff;
  color: #409eff;
  background: #fff;
  font-size: 15px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stage-index.is-disabled {
  border-color: #c0c4cc;
  color: #909399;
  background: #f5f7fa;
}

.stage-line {
  flex: 1;
  width: 3px;
  min-height: 24px;
  margin-top: 6px;
  border-radius: 999px;
  background: #dcdfe6;
}

.stage-item-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px;
  background: #fff;
  min-height: 114px;
  flex: 1;
}

.stage-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.stage-name {
  font-weight: 700;
  font-size: 16px;
  color: #1f2937;
}

.stage-meta {
  font-size: 12px;
  color: #6b7280;
}

.stage-desc {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: #6b7280;
}

.duration-display {
  text-align: center;
  color: #667eea;
  font-weight: 600;
  margin-top: 22px;
}

.duration-form-item {
  :deep(.el-form-item__content) {
    overflow: visible;
  }
}

.duration-slider {
  width: calc(100% - 28px);
  margin: 0 14px;

  :deep(.el-slider__marks-text) {
    margin-top: 16px;
    white-space: nowrap;
  }

  :deep(.el-slider__marks-text:first-child) {
    transform: translateX(0);
    left: 0 !important;
  }

  :deep(.el-slider__marks-text:last-child) {
    transform: translateX(-100%);
    left: 100% !important;
  }
}

:deep(.el-form-item__label) {
  font-weight: 600;
}

@media (max-width: 992px) {
  .stages-card {
    position: static;
  }
}

.profile-select-wrapper {
  width: 100%;

  .profile-option {
    display: flex;
    flex-direction: column;
    gap: 4px;

    .profile-name {
      font-weight: 500;
      color: var(--el-text-color-primary);
    }

    .profile-desc {
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
  }
}

:deep(.el-select-dropdown__item) {
  height: auto;
  padding: 8px 12px;
}

.resume-uploader {
  width: 100%;

  :deep(.el-upload) {
    width: 100%;
  }

  :deep(.el-upload-dragger) {
    width: 100%;
    padding: 40px;
  }

  :deep(.el-icon--upload) {
    font-size: 48px;
    color: var(--el-color-primary);
    margin-bottom: 16px;
  }
}
</style>
