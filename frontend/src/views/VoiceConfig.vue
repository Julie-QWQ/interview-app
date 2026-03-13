<template>
  <div class="voice-config" v-loading="loading">
    <h2 class="voice-title">语音配置</h2>

    <el-row :gutter="20">
      <el-col :xs="24" :lg="16">
        <el-card class="config-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>常开语音运行参数</span>
              <div class="header-actions">
                <el-button @click="handleReset" :loading="resetting">重置默认</el-button>
                <el-button type="primary" @click="handleSave" :loading="saving">保存配置</el-button>
              </div>
            </div>
          </template>

          <el-form :model="config" label-position="top" class="voice-form">
            <el-form-item label="启用语音能力">
              <el-switch v-model="config.enabled" />
            </el-form-item>

            <el-form-item label="启用常开语音">
              <el-switch v-model="config.always_on_enabled" />
            </el-form-item>

            <div class="inline-config-grid">
              <div class="inline-number-field">
                <span class="inline-number-label">噪声采样时长(ms)</span>
                <el-input-number
                  v-model="config.noise_floor_sample_ms"
                  class="config-number-input"
                  controls-position="right"
                  :min="100"
                  :max="5000"
                  :step="50"
                />
              </div>

              <div class="inline-number-field">
                <span class="inline-number-label">分片间隔(ms)</span>
                <el-input-number
                  v-model="config.timeslice_ms"
                  class="config-number-input"
                  controls-position="right"
                  :min="50"
                  :max="1000"
                  :step="10"
                />
              </div>

              <div class="inline-number-field">
                <span class="inline-number-label">语音判定阈值倍数</span>
                <el-input-number
                  v-model="config.speech_start_threshold"
                  class="config-number-input"
                  controls-position="right"
                  :min="1"
                  :max="10"
                  :step="0.1"
                  :precision="2"
                />
              </div>

              <div class="inline-number-field">
                <span class="inline-number-label">最小绝对阈值</span>
                <el-input-number
                  v-model="config.min_threshold"
                  class="config-number-input"
                  controls-position="right"
                  :min="0.001"
                  :max="1"
                  :step="0.001"
                  :precision="3"
                />
              </div>

              <div class="inline-number-field">
                <span class="inline-number-label">最短有效语音(ms)</span>
                <el-input-number
                  v-model="config.min_speech_ms"
                  class="config-number-input"
                  controls-position="right"
                  :min="100"
                  :max="5000"
                  :step="50"
                />
              </div>

              <div class="inline-number-field">
                <span class="inline-number-label">静音结束阈值(ms)</span>
                <el-input-number
                  v-model="config.end_silence_ms"
                  class="config-number-input"
                  controls-position="right"
                  :min="100"
                  :max="5000"
                  :step="50"
                />
              </div>

              <div class="inline-number-field">
                <span class="inline-number-label">最大分段时长(ms)</span>
                <el-input-number
                  v-model="config.max_segment_ms"
                  class="config-number-input"
                  controls-position="right"
                  :min="1000"
                  :max="60000"
                  :step="500"
                />
              </div>

              <div class="inline-number-field">
                <span class="inline-number-label">预卷时长(ms)</span>
                <el-input-number
                  v-model="config.pre_roll_ms"
                  class="config-number-input"
                  controls-position="right"
                  :min="0"
                  :max="3000"
                  :step="50"
                />
              </div>

              <div class="inline-number-field">
                <span class="inline-number-label">插话打断阈值(ms)</span>
                <el-input-number
                  v-model="config.barge_in_ms"
                  class="config-number-input"
                  controls-position="right"
                  :min="50"
                  :max="3000"
                  :step="50"
                />
              </div>

              <div class="inline-number-field">
                <span class="inline-number-label">缓存保留时长(ms)</span>
                <el-input-number
                  v-model="config.chunk_retention_ms"
                  class="config-number-input"
                  controls-position="right"
                  :min="1000"
                  :max="120000"
                  :step="500"
                />
              </div>

              <div class="inline-number-field">
                <span class="inline-number-label">自动发送最小字数</span>
                <el-input-number
                  v-model="config.auto_send_min_chars"
                  class="config-number-input"
                  controls-position="right"
                  :min="1"
                  :max="100"
                  :step="1"
                />
              </div>

              <div class="inline-number-field">
                <span class="inline-number-label">手输保护窗口(ms)</span>
                <el-input-number
                  v-model="config.typing_grace_ms"
                  class="config-number-input"
                  controls-position="right"
                  :min="0"
                  :max="10000"
                  :step="100"
                />
              </div>
            </div>

            <el-form-item label="短噪音词列表">
              <el-input
                v-model="noiseWordsDraft"
                type="textarea"
                :rows="6"
                placeholder="每行一个词，例如：嗯"
              />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card class="info-card" shadow="never">
          <template #header>
            <span>说明</span>
          </template>

          <div class="info-content">
            <h4>生效范围</h4>
            <p>配置保存在 `backend/config/config.yaml` 的 `voice` 段，后续新打开的面试页会读取最新值。</p>

            <h4>调整建议</h4>
            <p>环境噪音大时优先增大“语音判定阈值倍数”或“最小绝对阈值”；切句过早时增大“静音结束阈值”。</p>

            <h4>自动发送</h4>
            <p>“自动发送最小字数”越大，系统越保守；“手输保护窗口”越大，越不容易覆盖用户正在编辑的文本。</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { interviewApi } from '@/api/interview'

const DEFAULT_CONFIG = {
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
  short_noise_words: ['嗯', '啊', '哦', '额', '呃', '唉', '哎', '嗨']
}

const loading = ref(false)
const saving = ref(false)
const resetting = ref(false)
const noiseWordsDraft = ref('')
const config = reactive({ ...DEFAULT_CONFIG })

onMounted(async () => {
  await loadConfig()
})

function applyConfig(data = {}) {
  Object.assign(config, DEFAULT_CONFIG, data)
  noiseWordsDraft.value = (config.short_noise_words || []).join('\n')
}

function buildPayload() {
  return {
    ...config,
    short_noise_words: noiseWordsDraft.value
      .split('\n')
      .map((item) => item.trim())
      .filter(Boolean)
  }
}

async function loadConfig() {
  loading.value = true
  try {
    const data = await interviewApi.getVoiceConfig()
    applyConfig(data)
  } catch (error) {
    console.error('加载语音配置失败', error)
    ElMessage.error('加载语音配置失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  try {
    await ElMessageBox.confirm('确认保存语音配置？', '确认', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      type: 'warning'
    })

    saving.value = true
    const result = await interviewApi.updateVoiceConfig(buildPayload())
    applyConfig(result?.config || result)
    ElMessage.success('语音配置保存成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('保存语音配置失败', error)
      ElMessage.error(error?.message || '保存语音配置失败')
    }
  } finally {
    saving.value = false
  }
}

async function handleReset() {
  try {
    await ElMessageBox.confirm('确认重置为默认语音配置？', '确认', {
      confirmButtonText: '重置',
      cancelButtonText: '取消',
      type: 'warning'
    })

    resetting.value = true
    const result = await interviewApi.resetVoiceConfig()
    applyConfig(result?.config || result)
    ElMessage.success('语音配置已重置')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重置语音配置失败', error)
      ElMessage.error('重置语音配置失败')
    }
  } finally {
    resetting.value = false
  }
}
</script>

<style scoped lang="scss">
.voice-config {
  max-width: 1440px;
  margin: 0 auto;
}

.voice-title {
  margin: 0 0 18px;
  font-size: 24px;
  line-height: 1.25;
}

.config-card,
.info-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.info-content {
  h4 {
    font-size: 16px;
    margin: 16px 0 8px;
    color: #333;
  }

  p {
    margin: 0;
    color: #666;
    line-height: 1.7;
  }
}

.voice-form {
  :deep(.el-form-item) {
    margin-bottom: 20px;
  }

  :deep(.el-form-item__label) {
    line-height: 1.4;
    padding-bottom: 8px;
    white-space: normal;
  }
}

.inline-config-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px 24px;
  margin-bottom: 20px;
}

.inline-number-field {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-width: 0;
}

.inline-number-label {
  flex: 1;
  min-width: 0;
  color: #4b5563;
  font-size: 14px;
  line-height: 1.5;
}

:deep(.config-number-input) {
  flex: 0 0 auto;
  width: 120px;
  max-width: 100%;
}

:deep(.config-number-input .el-input__wrapper) {
  padding-left: 12px;
  padding-right: 34px;
}

:deep(.config-number-input .el-input__inner) {
  text-align: center;
  font-variant-numeric: tabular-nums;
}

:deep(.config-number-input .el-input-number__decrease),
:deep(.config-number-input .el-input-number__increase) {
  width: 22px;
  color: #4b5563;
}

@media (max-width: 768px) {
  .card-header,
  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .inline-config-grid {
    grid-template-columns: 1fr;
  }

  .inline-number-field {
    align-items: stretch;
    flex-direction: column;
    gap: 8px;
  }

  :deep(.config-number-input) {
    width: 100%;
  }
}
</style>
