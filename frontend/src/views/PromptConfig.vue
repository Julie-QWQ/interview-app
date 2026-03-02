<template>
  <div class="prompt-config" v-loading="loading">
    <h2 class="prompt-title">Prompt 配置管理</h2>

    <el-row :gutter="20">
      <el-col :xs="24" :lg="16">
        <el-card class="config-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>基础配置</span>
              <el-button type="primary" size="small" @click="handleSave" :loading="saving">
                保存配置
              </el-button>
            </div>
          </template>

          <el-form :model="config" label-width="120px">
            <el-form-item label="基础系统提示">
              <el-input
                v-model="config.base_system_prompt"
                type="textarea"
                :rows="4"
                placeholder="AI 的基础身份和行为设定"
              />
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="config-card" shadow="never">
          <template #header>
            <span>LLM 对话参数</span>
          </template>

          <el-form :model="config.llm" label-width="150px">
            <el-row :gutter="20">
              <el-col :xs="24" :md="12">
                <el-form-item label="温度 Temperature">
                  <el-input-number
                    v-model="config.llm.temperature"
                    :min="0"
                    :max="2"
                    :step="0.1"
                    :precision="1"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="评估温度">
                  <el-input-number
                    v-model="config.llm.evaluation_temperature"
                    :min="0"
                    :max="2"
                    :step="0.1"
                    :precision="1"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :xs="24" :md="12">
                <el-form-item label="最大输出 Tokens">
                  <el-input-number
                    v-model="config.llm.max_tokens"
                    :min="100"
                    :max="8000"
                    :step="100"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="上下文消息条数">
                  <el-input-number
                    v-model="config.llm.context_messages"
                    :min="1"
                    :max="100"
                    :step="1"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :xs="24" :md="12">
                <el-form-item label="Top P">
                  <el-input-number
                    v-model="config.llm.top_p"
                    :min="0"
                    :max="1"
                    :step="0.05"
                    :precision="2"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="模型覆盖（可选）">
                  <el-input
                    v-model="config.llm.model_override"
                    placeholder="留空则使用系统默认模型"
                    clearable
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :xs="24" :md="12">
                <el-form-item label="频率惩罚">
                  <el-input-number
                    v-model="config.llm.frequency_penalty"
                    :min="-2"
                    :max="2"
                    :step="0.1"
                    :precision="1"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="存在惩罚">
                  <el-input-number
                    v-model="config.llm.presence_penalty"
                    :min="-2"
                    :max="2"
                    :step="0.1"
                    :precision="1"
                    style="width: 100%"
                  />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </el-card>

      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card class="action-card" shadow="never">
          <template #header>
            <span>操作</span>
          </template>

          <div class="action-list">
            <el-button type="primary" @click="handleSave" :loading="saving">
              <el-icon><DocumentCopy /></el-icon>
              保存配置
            </el-button>

            <el-button @click="handleReset" :loading="resetting">
              <el-icon><RefreshLeft /></el-icon>
              重置为默认
            </el-button>
          </div>
        </el-card>

        <el-card class="info-card" shadow="never">
          <template #header>
            <span>配置说明</span>
          </template>

          <div class="info-content">
            <h4>配置生效时机</h4>
            <p>配置保存后，新创建的面试会使用新配置，进行中的面试不受影响。</p>
          </div>
        </el-card>
      </el-col>
    </el-row>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DocumentCopy, RefreshLeft } from '@element-plus/icons-vue'
import { interviewApi } from '@/api/interview'

const loading = ref(false)
const saving = ref(false)
const resetting = ref(false)
const config = reactive({
  base_system_prompt: '你是一位专业的技术面试官，具有丰富的招聘经验。',
  stages: {
    welcome: {
      stage: 'welcome',
      name: '开场介绍',
      description: '欢迎候选人，介绍面试流程，了解基础背景',
      max_turns: 2,
      min_turns: 1,
      time_allocation: 2,
      system_instruction: '',
      enabled: true
    },
    technical: {
      stage: 'technical',
      name: '技术问题',
      description: '针对岗位技能进行深入技术考察',
      max_turns: 10,
      min_turns: 5,
      time_allocation: 18,
      system_instruction: '',
      enabled: true
    },
    scenario: {
      stage: 'scenario',
      name: '情景问题',
      description: '提供实际工作场景，评估问题解决思路',
      max_turns: 5,
      min_turns: 2,
      time_allocation: 8,
      system_instruction: '',
      enabled: true
    },
    closing: {
      stage: 'closing',
      name: '结束阶段',
      description: '总结候选人表现，给出评估并回答候选人问题',
      max_turns: 3,
      min_turns: 2,
      time_allocation: 2,
      system_instruction: '',
      enabled: true
    }
  },
  llm: {
    temperature: 0.7,
    max_tokens: 2000,
    context_messages: 20,
    top_p: 1.0,
    frequency_penalty: 0.0,
    presence_penalty: 0.0,
    model_override: '',
    evaluation_temperature: 0.3
  }
})

onMounted(async () => {
  await loadConfig()
})

function applyConfig(data) {
  Object.assign(config, data)
  config.llm = {
    temperature: 0.7,
    max_tokens: 2000,
    context_messages: 20,
    top_p: 1.0,
    frequency_penalty: 0.0,
    presence_penalty: 0.0,
    model_override: '',
    evaluation_temperature: 0.3,
    ...(data?.llm || {})
  }
}

async function loadConfig() {
  loading.value = true
  try {
    const data = await interviewApi.getPromptConfig()
    applyConfig(data)
    ElMessage.success('配置加载成功')
  } catch (error) {
    console.error('加载配置失败', error)
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  try {
    await ElMessageBox.confirm('确认保存配置？新配置将影响后续面试。', '确认', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      type: 'warning'
    })

    saving.value = true
    await interviewApi.updatePromptConfig(config)
    ElMessage.success('配置保存成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('保存失败', error)
      ElMessage.error('保存失败')
    }
  } finally {
    saving.value = false
  }
}

async function handleReset() {
  try {
    await ElMessageBox.confirm('确认重置为默认配置？当前配置将丢失。', '确认', {
      confirmButtonText: '重置',
      cancelButtonText: '取消',
      type: 'warning'
    })

    resetting.value = true
    const result = await interviewApi.resetPromptConfig()
    const data = result?.config || result
    applyConfig(data)
    ElMessage.success('配置已重置')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重置失败', error)
      ElMessage.error('重置失败')
    }
  } finally {
    resetting.value = false
  }
}

</script>

<style scoped lang="scss">
.prompt-config {
  max-width: 1400px;
  margin: 0 auto;
}

.prompt-title {
  margin: 0 0 18px;
  font-size: 24px;
  line-height: 1.25;
}

.config-card,
.action-card,
.info-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.action-list {
  display: flex;
  flex-direction: column;
  gap: 12px;

  > * {
    width: 100%;
  }

  .el-button {
    width: 100%;
    justify-content: flex-start;
    margin-left: 0;
    padding: 0 14px;
  }

  .el-icon {
    width: 16px;
    margin-right: 8px;
  }
}

.info-content {
  h4 {
    font-size: 16px;
    margin: 16px 0 8px;
    color: #333;
  }

  ul {
    margin: 8px 0;
    padding-left: 20px;

    li {
      margin-bottom: 6px;
      color: #666;
      line-height: 1.6;

      strong {
        color: #333;
      }
    }
  }

  p {
    margin: 8px 0;
    color: #666;
    line-height: 1.6;
  }
}

:deep(.el-textarea__inner) {
  font-family: 'Courier New', monospace;
  font-size: 13px;
}
</style>
