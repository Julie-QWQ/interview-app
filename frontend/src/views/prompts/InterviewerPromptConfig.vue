<template>
  <div class="prompt-page" v-loading="loading">
    <el-row :gutter="20">
      <el-col :xs="24" :lg="16">
        <el-card class="config-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>基础系统提示</span>
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
                :rows="5"
                placeholder="定义面试官的基础身份、角色边界和整体行为目标"
              />
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="config-card" shadow="never">
          <template #header>
            <span>基本说话风格</span>
          </template>

          <div class="template-hint">
            <el-alert
              type="info"
              :closable="false"
              show-icon
              title="这里维护面试官的基础说话风格和对话行为规则。主模板中只需要保留 {{ interviewer_style_prompt }} 占位符。"
            />
          </div>

          <el-input
            v-model="config.interviewer_style_prompt"
            type="textarea"
            :rows="18"
            placeholder="输入面试官的基本说话风格和对话行为规则"
          />
        </el-card>

        <el-card class="config-card" shadow="never">
          <template #header>
            <span>面试主 Prompt 模板</span>
          </template>

          <div class="template-hint">
            <el-alert
              type="info"
              :closable="false"
              show-icon
              title="这里编辑面试官使用的 Jinja2 主模板。保存后，后端会优先使用这里的模板内容。"
            />
            <p>
              常用变量：
              <code v-pre>{{ base_system_prompt }}</code>
              <code v-pre>{{ interviewer_style_prompt }}</code>
              <code v-pre>{{ interview.position }}</code>
              <code v-pre>{{ stage.system_instruction }}</code>
              <code v-pre>{{ progress.stage_name }}</code>
              <code v-pre>{{ tool_context_combined }}</code>
            </p>
          </div>

          <el-input
            v-model="config.interviewer_system_template"
            type="textarea"
            :rows="22"
            placeholder="请输入面试官 Prompt 的 Jinja2 模板"
          />
        </el-card>

        <el-card class="config-card" shadow="never">
          <template #header>
            <span>工具上下文模板</span>
          </template>

          <div class="template-hint">
            <el-alert
              type="info"
              :closable="false"
              show-icon
              title="这里定义工具结果如何组合成 {{ tool_context_combined }}。你可以决定标题、顺序和展示格式。"
            />
            <p>
              可用变量：
              <code v-pre>{{ tool_context_items }}</code>
              <code v-pre>{{ tool_context }}</code>
              <code v-pre>{{ item.tool_name }}</code>
              <code v-pre>{{ item.context_label }}</code>
              <code v-pre>{{ item.prompt_context }}</code>
              <code v-pre>{{ item.structured_payload }}</code>
            </p>
          </div>

          <el-input
            v-model="config.tool_context_template"
            type="textarea"
            :rows="10"
            placeholder="请输入工具上下文组合模板"
          />
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
            </el-row>

            <el-row :gutter="20">
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

            <el-form-item label="模型覆盖（可选）">
              <el-input
                v-model="config.llm.model_override"
                placeholder="为空则使用系统默认模型"
                clearable
              />
            </el-form-item>
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
            <span>说明</span>
          </template>

          <div class="info-content">
            <h4>作用范围</h4>
            <p>这里控制面试过程中发送给主 LLM 的基础提示、说话风格、主模板和对话参数。</p>

            <h4>保存方式</h4>
            <p>保存时会保留其他配置字段，不会覆盖工具配置、阶段配置和智能回复配置。</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DocumentCopy, RefreshLeft } from '@element-plus/icons-vue'
import { interviewApi } from '@/api/interview'

const loading = ref(false)
const saving = ref(false)
const resetting = ref(false)

const config = reactive({
  base_system_prompt: '',
  interviewer_style_prompt: '',
  interviewer_system_template: '',
  tool_context_template: '',
  stages: {},
  llm: {
    temperature: 0.7,
    max_tokens: 2000,
    context_messages: 20,
    top_p: 1.0,
    frequency_penalty: 0.0,
    presence_penalty: 0.0,
    model_override: ''
  },
  tools: {}
})

onMounted(async () => {
  await loadConfig()
})

function applyConfig(data) {
  Object.assign(config, data)
  config.base_system_prompt = data?.base_system_prompt || ''
  config.interviewer_style_prompt = data?.interviewer_style_prompt || ''
  config.interviewer_system_template = data?.interviewer_system_template || ''
  config.tool_context_template = data?.tool_context_template || ''
  config.stages = data?.stages || {}
  config.tools = data?.tools || {}
  config.llm = {
    temperature: 0.7,
    max_tokens: 2000,
    context_messages: 20,
    top_p: 1.0,
    frequency_penalty: 0.0,
    presence_penalty: 0.0,
    model_override: '',
    ...(data?.llm || {})
  }
}

async function loadConfig() {
  loading.value = true
  try {
    const data = await interviewApi.getPromptConfig()
    applyConfig(data)
  } catch (error) {
    console.error('加载配置失败', error)
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  try {
    await ElMessageBox.confirm('确认保存面试官 Prompt 配置？', '确认', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      type: 'warning'
    })

    saving.value = true
    await interviewApi.updatePromptConfig(config)
    ElMessage.success('面试官 Prompt 配置保存成功')
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
    await ElMessageBox.confirm('确认重置为默认配置？当前面试官 Prompt 配置将丢失。', '确认', {
      confirmButtonText: '重置',
      cancelButtonText: '取消',
      type: 'warning'
    })

    resetting.value = true
    const result = await interviewApi.resetPromptConfig()
    const data = result?.config || result
    applyConfig(data)
    ElMessage.success('面试官 Prompt 配置已重置')
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
.prompt-page {
  max-width: 1440px;
  margin: 0 auto;
}

.config-card,
.action-card,
.info-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.template-hint {
  margin-bottom: 16px;

  p {
    margin: 12px 0 0;
    color: #6b7280;
    line-height: 1.7;
  }

  code {
    margin-right: 8px;
    padding: 2px 6px;
    border-radius: 6px;
    background: #f3f4f6;
    color: #111827;
  }
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

  p {
    margin: 0;
    color: #666;
    line-height: 1.7;
  }
}
</style>
