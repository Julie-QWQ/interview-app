<template>
  <div class="tool-config" v-loading="loading">
    <h2 class="tool-title">工具配置</h2>

    <el-row :gutter="20">
      <el-col :xs="24" :lg="16">
        <el-card class="config-card" shadow="never">
          <template #header>
            <span>工具超时与缓存参数</span>
          </template>

          <div class="tool-metrics-grid">
            <div class="tool-metric-field">
              <span class="tool-metric-label">对话链路超时(秒)</span>
              <el-input-number
                v-model="config.tools.timeouts.chat_seconds"
                class="config-number-input"
                controls-position="right"
                :min="0.1"
                :max="30"
                :step="0.1"
                :precision="1"
              />
            </div>

            <div class="tool-metric-field">
              <span class="tool-metric-label">预取链路超时(秒)</span>
              <el-input-number
                v-model="config.tools.timeouts.prefetch_seconds"
                class="config-number-input"
                controls-position="right"
                :min="0.1"
                :max="60"
                :step="0.1"
                :precision="1"
              />
            </div>

            <div class="tool-metric-field">
              <span class="tool-metric-label">题库 TopK</span>
              <el-input-number
                v-model="config.tools.cache.question_bank_top_k"
                class="config-number-input"
                controls-position="right"
                :min="1"
                :max="50"
                :step="1"
              />
            </div>

            <div class="tool-metric-field">
              <span class="tool-metric-label">追问 TopK</span>
              <el-input-number
                v-model="config.tools.cache.followup_top_k"
                class="config-number-input"
                controls-position="right"
                :min="1"
                :max="20"
                :step="1"
              />
            </div>

            <div class="tool-metric-field">
              <span class="tool-metric-label">缓存秒数</span>
              <el-input-number
                v-model="config.tools.cache.smart_reply_ttl_seconds"
                class="config-number-input"
                controls-position="right"
                :min="0"
                :max="3600"
                :step="5"
              />
            </div>
          </div>
        </el-card>

        <el-card class="config-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>工具 Provider 配置</span>
              <div class="header-actions">
                <el-button size="small" @click="openCreateDialog">新增工具</el-button>
                <el-button type="primary" size="small" @click="handleSave" :loading="saving">
                  保存配置
                </el-button>
              </div>
            </div>
          </template>

          <div class="palette-header">
            <span>工具列表</span>
            <el-tag type="info">{{ toolNames.length }} 个</el-tag>
          </div>

          <el-empty
            v-if="toolNames.length === 0"
            description="暂无工具 Provider，请先新增工具。"
          />

          <div v-else class="tool-chip-list">
            <button
              v-for="toolName in toolNames"
              :key="toolName"
              type="button"
              class="tool-chip"
              :class="{ 'is-active': activeToolName === toolName && detailDialogVisible }"
              @click="openDetailDialog(toolName)"
            >
              <div class="tool-chip-top">
                <strong>{{ toolName }}</strong>
                <el-tag size="small" :type="config.tools.providers[toolName]?.enabled ? 'success' : 'info'">
                  {{ config.tools.providers[toolName]?.enabled ? '已启用' : '未启用' }}
                </el-tag>
              </div>
              <p>{{ config.tools.providers[toolName]?.description || '暂无描述' }}</p>
            </button>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card class="action-card" shadow="never">
          <template #header>
            <span>操作</span>
          </template>

          <div class="action-list">
            <el-button type="primary" @click="handleSave" :loading="saving">
              <el-icon><Tools /></el-icon>
              保存工具配置
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
            <h4>页面职责</h4>
            <p>这里维护工具 Provider、描述、请求地址、请求头，以及运行时超时和缓存参数。</p>
            <h4>Tool Prompt</h4>
            <p>先为工具选择 `URL` 或 `LLM` 模式。`URL` 模式配置请求地址和请求头；`LLM` 模式额外配置 `System Prompt` 和 `User Prompt`。</p>
            <p><strong>所有工具</strong>都需要配置 `Result Prompt`,用于将工具返回的JSON结果转换为自然语言,然后插入到主面试官的prompt中。</p>
            <p>`structured_payload` 是当前工具自己的结构,不存在全局固定字段。若工具没有稳定结构化字段,可直接使用 `{{ raw_prompt_context }}`。`smart_reply_engine` 的 `action_key / action_label / rationale / utterance` 仅适用于它自己。</p>

            <h4>阶段绑定</h4>
            <p>每个面试阶段在什么触发器下使用哪些工具，请到“阶段配置”页面拖拽绑定。</p>

            <h4>智能回复配置</h4>
            <p>`smart_reply_engine` 的行为目录和语料不在这里维护，请到“智能回复配置”页面编辑。</p>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog
      v-model="detailDialogVisible"
      :title="activeToolName ? `编辑工具：${activeToolName}` : '编辑工具'"
      width="720px"
      destroy-on-close
    >
      <el-form v-if="activeProvider" :model="activeProvider" label-width="120px">
        <el-form-item label="工具名称">
          <el-input :model-value="activeToolName" disabled />
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="activeProvider.description"
            type="textarea"
            :rows="3"
            placeholder="描述这个工具负责什么，适合在哪些场景使用"
          />
        </el-form-item>

        <el-form-item label="启用">
          <el-switch v-model="activeProvider.enabled" />
        </el-form-item>

        <el-form-item label="工具类型">
          <el-radio-group v-model="activeProvider.mode">
            <el-radio-button label="url">URL</el-radio-button>
            <el-radio-button label="llm">LLM</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <template v-if="activeProvider.mode !== 'llm'">
        <el-form-item label="请求地址">
          <el-input
            v-model="activeProvider.url"
            placeholder="例如：http://127.0.0.1:9001/execute"
            clearable
          />
        </el-form-item>

        <el-form-item label="请求头 JSON">
          <el-input
            v-model="providerHeaderDrafts[activeToolName]"
            type="textarea"
            :rows="8"
            placeholder='例如：{"Authorization":"Bearer xxx"}'
          />
        </el-form-item>
        </template>

        <template v-else>
        <el-divider content-position="left">LLM 工具 Prompt</el-divider>

        <el-form-item label="System Prompt">
          <el-input
            v-model="activeToolPrompt.system_prompt"
            type="textarea"
            :rows="6"
            placeholder="可选。仅当该工具自身还会调用 LLM 时才需要；纯 URL 程序工具可留空"
          />
        </el-form-item>

        <el-form-item label="User Prompt">
          <el-input
            v-model="activeToolPrompt.user_prompt_template"
            type="textarea"
            :rows="8"
            placeholder="可选。仅当该工具自身还会调用 LLM 时才需要；纯 URL 程序工具可留空"
          />
        </el-form-item>
        </template>

        <el-divider content-position="left">结果渲染配置</el-divider>

        <el-form-item label="Result Prompt">
          <el-input
            v-model="activeToolPrompt.result_prompt_template"
            type="textarea"
            :rows="8"
            placeholder="工具返回结果如何渲染为主面试官可消费的提示文案。structured_payload 是当前工具自己的结构；若不确定字段，先用 {{ raw_prompt_context }}"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-actions">
          <el-button v-if="activeToolName" type="danger" plain @click="handleRemoveProvider(activeToolName)">
            删除工具
          </el-button>
          <div class="dialog-actions-right">
            <el-button @click="detailDialogVisible = false">关闭</el-button>
            <el-button type="primary" @click="handleSave" :loading="saving">保存配置</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="createDialogVisible" title="新增工具" width="680px" destroy-on-close>
      <el-form :model="createForm" label-width="120px">
        <el-form-item label="工具名称" required>
          <el-input
            v-model="createForm.name"
            placeholder="例如：resume_analyzer_v2"
          />
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="描述这个工具的作用，可先留空"
          />
        </el-form-item>

        <el-form-item label="启用">
          <el-switch v-model="createForm.enabled" />
        </el-form-item>

        <el-form-item label="工具类型">
          <el-radio-group v-model="createForm.mode">
            <el-radio-button label="url">URL</el-radio-button>
            <el-radio-button label="llm">LLM</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="createForm.mode !== 'llm'" label="请求地址">
          <el-input
            v-model="createForm.url"
            placeholder="例如：http://127.0.0.1:9001/execute，可先留空"
            clearable
          />
        </el-form-item>

        <el-form-item v-if="createForm.mode !== 'llm'" label="请求头 JSON">
          <el-input
            v-model="createForm.headers"
            type="textarea"
            :rows="6"
            placeholder='例如：{"Authorization":"Bearer xxx"}，可先留空'
          />
        </el-form-item>

        <el-form-item label="Result Prompt">
          <el-input
            v-model="createForm.result_prompt_template"
            type="textarea"
            :rows="6"
            placeholder="工具返回结果如何渲染为主面试官可消费的提示文案。可先留空"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-actions-right">
          <el-button @click="createDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleCreateProvider">创建工具</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshLeft, Tools } from '@element-plus/icons-vue'
import { interviewApi } from '@/api/interview'

const loading = ref(false)
const saving = ref(false)
const resetting = ref(false)
const createDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const activeToolName = ref('')

const config = reactive({
  base_system_prompt: '',
  interviewer_system_template: '',
  stages: {},
  llm: {},
  tools: {
    providers: {},
    tool_prompts: {},
    bindings: {},
    timeouts: {
      chat_seconds: 2.0,
      prefetch_seconds: 4.0
    },
    cache: {
      question_bank_top_k: 5,
      followup_top_k: 3,
      smart_reply_ttl_seconds: 60
    },
    smart_reply_catalog: {
      actions: []
    }
  }
})

const createForm = reactive({
  name: '',
  description: '',
  mode: 'url',
  enabled: false,
  url: '',
  headers: '{}',
  result_prompt_template: ''
})

const providerHeaderDrafts = reactive({})
const toolNames = computed(() => Object.keys(config.tools.providers || {}))
const activeProvider = computed(() => {
  if (!activeToolName.value) return null
  return config.tools.providers[activeToolName.value] || null
})
const activeToolPrompt = computed(() => {
  if (!activeToolName.value) return null
  if (!config.tools.tool_prompts[activeToolName.value]) {
    config.tools.tool_prompts[activeToolName.value] = createEmptyToolPrompt()
  }
  return config.tools.tool_prompts[activeToolName.value]
})

onMounted(async () => {
  await loadConfig()
})

function deepClone(value) {
  return JSON.parse(JSON.stringify(value))
}

function createEmptyProvider() {
  return {
    description: '',
    mode: 'url',
    enabled: false,
    url: '',
    headers: {}
  }
}

function createEmptyToolPrompt() {
  return {
    system_prompt: '',
    user_prompt_template: '',
    context_label: '',
    result_prompt_template: ''
  }
}

function resetCreateForm() {
  createForm.name = ''
  createForm.description = ''
  createForm.mode = 'url'
  createForm.enabled = false
  createForm.url = ''
  createForm.headers = '{}'
  createForm.result_prompt_template = ''
}

function openDetailDialog(toolName) {
  activeToolName.value = toolName
  detailDialogVisible.value = true
}

function applyConfig(data) {
  Object.assign(config, data)
  config.tools = {
    providers: {},
    tool_prompts: {},
    bindings: {},
    timeouts: {
      chat_seconds: 2.0,
      prefetch_seconds: 4.0
    },
    cache: {
      question_bank_top_k: 5,
      followup_top_k: 3,
      smart_reply_ttl_seconds: 60
    },
    smart_reply_catalog: {
      actions: []
    },
    ...(data?.tools || {})
  }

  Object.keys(providerHeaderDrafts).forEach((key) => {
    delete providerHeaderDrafts[key]
  })

  Object.entries(config.tools.providers || {}).forEach(([toolName, provider]) => {
    config.tools.providers[toolName] = {
      ...createEmptyProvider(),
      ...(provider || {})
    }
    providerHeaderDrafts[toolName] = JSON.stringify(provider?.headers || {}, null, 2)
    config.tools.tool_prompts[toolName] = {
      ...createEmptyToolPrompt(),
      ...(config.tools.tool_prompts?.[toolName] || {})
    }
  })

  if (activeToolName.value && !config.tools.providers[activeToolName.value]) {
    activeToolName.value = ''
    detailDialogVisible.value = false
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

function parseHeaders(raw, toolName) {
  try {
    const parsed = JSON.parse(raw || '{}')
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
      throw new Error('headers 必须是对象')
    }
    return parsed
  } catch (error) {
    throw new Error(`工具 ${toolName} 的请求头 JSON 格式不正确`)
  }
}

function buildPayload() {
  const payload = deepClone(config)
  Object.keys(payload.tools.providers || {}).forEach((toolName) => {
    payload.tools.providers[toolName].headers = parseHeaders(providerHeaderDrafts[toolName], toolName)
    payload.tools.tool_prompts = payload.tools.tool_prompts || {}
    payload.tools.tool_prompts[toolName] = {
      ...createEmptyToolPrompt(),
      ...(payload.tools.tool_prompts[toolName] || {})
    }
  })
  return payload
}

async function handleSave() {
  try {
    await ElMessageBox.confirm('确认保存工具配置？', '确认', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      type: 'warning'
    })

    saving.value = true
    const payload = buildPayload()
    await interviewApi.updatePromptConfig(payload)
    applyConfig(payload)
    ElMessage.success('工具配置保存成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('保存失败', error)
      ElMessage.error(error?.message || '保存失败')
    }
  } finally {
    saving.value = false
  }
}

async function handleReset() {
  try {
    await ElMessageBox.confirm('确认重置为默认配置？当前工具配置将丢失。', '确认', {
      confirmButtonText: '重置',
      cancelButtonText: '取消',
      type: 'warning'
    })

    resetting.value = true
    const result = await interviewApi.resetPromptConfig()
    const data = result?.config || result
    applyConfig(data)
    ElMessage.success('工具配置已重置')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重置失败', error)
      ElMessage.error('重置失败')
    }
  } finally {
    resetting.value = false
  }
}

function openCreateDialog() {
  resetCreateForm()
  createDialogVisible.value = true
}

function handleCreateProvider() {
  const toolName = (createForm.name || '').trim()
  if (!toolName) {
    ElMessage.warning('工具名称不能为空')
    return
  }
  if (config.tools.providers[toolName]) {
    ElMessage.warning('工具名称已存在')
    return
  }

  let headers = {}
  try {
    headers = parseHeaders(createForm.headers, toolName)
  } catch (error) {
    ElMessage.error(error.message)
    return
  }

  config.tools.providers[toolName] = {
    description: createForm.description || '',
    mode: createForm.mode || 'url',
    enabled: Boolean(createForm.enabled),
    url: createForm.url || '',
    headers
  }
  config.tools.tool_prompts[toolName] = {
    ...createEmptyToolPrompt(),
    result_prompt_template: createForm.result_prompt_template || ''
  }
  providerHeaderDrafts[toolName] = JSON.stringify(headers, null, 2)
  activeToolName.value = toolName
  createDialogVisible.value = false
  detailDialogVisible.value = true
  resetCreateForm()
  ElMessage.success('工具已新增，请记得保存配置')
}

async function handleRemoveProvider(toolName) {
  if (!toolName) return

  try {
    await ElMessageBox.confirm(`确认删除工具 ${toolName}？该工具也会从所有阶段绑定中移除。`, '确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })

    delete config.tools.providers[toolName]
    delete config.tools.tool_prompts[toolName]
    delete providerHeaderDrafts[toolName]
    if (activeToolName.value === toolName) {
      activeToolName.value = ''
      detailDialogVisible.value = false
    }

    Object.values(config.tools.bindings || {}).forEach((binding) => {
      Object.keys(binding?.trigger_map || {}).forEach((triggerKey) => {
        binding.trigger_map[triggerKey] = (binding.trigger_map[triggerKey] || []).filter((item) => item !== toolName)
      })
    })

    ElMessage.success('工具已移除，请记得保存配置')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除工具失败', error)
      ElMessage.error('删除工具失败')
    }
  }
}
</script>

<style scoped lang="scss">
.tool-config {
  max-width: 1440px;
  margin: 0 auto;
}

.tool-title {
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
  gap: 12px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.tool-metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px 24px;
}

.tool-metric-field {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-width: 0;
}

.tool-metric-label {
  flex: 1;
  min-width: 0;
  color: #4b5563;
  font-size: 14px;
  line-height: 1.5;
}

.palette-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.tool-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
}

.tool-chip {
  width: 260px;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background: linear-gradient(180deg, #fff 0%, #f8fafc 100%);
  padding: 14px 16px;
  text-align: left;
  cursor: pointer;
  transition: all 0.18s ease;
}

.tool-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 22px rgba(15, 23, 42, 0.08);
}

.tool-chip.is-active {
  border-color: #111318;
  box-shadow: 0 16px 28px rgba(17, 19, 24, 0.12);
}

.tool-chip-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.tool-chip p {
  margin: 10px 0 0;
  color: #6b7280;
  line-height: 1.6;
  font-size: 13px;
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

.dialog-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.dialog-actions-right {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

:deep(.config-number-input) {
  flex: 0 0 auto;
  width: 150px;
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
  .dialog-actions,
  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .tool-metrics-grid {
    grid-template-columns: 1fr;
  }

  .tool-metric-field {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .tool-chip {
    width: 100%;
  }

  .dialog-actions-right {
    width: 100%;
  }

  :deep(.config-number-input) {
    width: 100%;
  }
}
</style>
