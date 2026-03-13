<template>
  <div class="smart-reply-config" v-loading="loading">
    <h2 class="page-title">智能回复配置</h2>

    <el-row :gutter="20">
      <el-col :xs="24" :lg="16">
        <el-card class="config-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>行为目录</span>
              <el-tag type="info">{{ actions.length }} 个行为</el-tag>
            </div>
          </template>

          <div class="action-list">
            <el-empty v-if="actions.length === 0" description="暂无智能回复行为配置" />

            <el-collapse v-else v-model="activePanels">
              <el-collapse-item
                v-for="action in actions"
                :key="action.action_key"
                :name="action.action_key"
              >
                <template #title>
                  <div class="action-title">
                    <div class="action-title-main">
                      <strong>{{ action.label || action.action_key }}</strong>
                      <span class="action-key">{{ action.action_key }}</span>
                    </div>
                    <el-tag size="small" :type="action.enabled ? 'success' : 'info'">
                      {{ action.enabled ? '已启用' : '已禁用' }}
                    </el-tag>
                  </div>
                </template>

                <el-form :model="action" label-width="120px" class="action-form">
                  <el-form-item label="启用">
                    <el-switch v-model="action.enabled" />
                  </el-form-item>

                  <el-form-item label="展示名称">
                    <el-input v-model="action.label" placeholder="例如：追细节" />
                  </el-form-item>

                  <el-form-item label="行为说明">
                    <el-input
                      v-model="action.description"
                      type="textarea"
                      :rows="3"
                      placeholder="说明该行为适用于什么场景"
                    />
                  </el-form-item>

                  <el-form-item label="语料列表">
                    <div class="template-list">
                      <div
                        v-for="(template, index) in action.utterance_templates"
                        :key="`${action.action_key}-${index}`"
                        class="template-row"
                      >
                        <el-input
                          v-model="action.utterance_templates[index]"
                          type="textarea"
                          :rows="2"
                          placeholder="输入该行为可复用的语料模板"
                        />
                        <el-button
                          type="danger"
                          plain
                          @click="removeTemplate(action.action_key, index)"
                        >
                          删除
                        </el-button>
                      </div>

                      <el-button plain @click="appendTemplate(action.action_key)">
                        新增语料
                      </el-button>
                    </div>
                  </el-form-item>
                </el-form>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card class="action-card" shadow="never">
          <template #header>
            <span>操作</span>
          </template>

          <div class="action-buttons">
            <el-button type="primary" @click="handleSave" :loading="saving">
              保存智能回复配置
            </el-button>
            <el-button @click="handleRestoreDefaults">
              恢复默认行为语料
            </el-button>
            <el-button @click="reloadConfig">
              重新加载
            </el-button>
          </div>
        </el-card>

        <el-card class="info-card" shadow="never">
          <template #header>
            <span>说明</span>
          </template>

          <div class="info-content">
            <h4>配置范围</h4>
            <p>这里维护 `smart_reply_engine` 可用的行为列表、展示名称、说明和候选语料。</p>

            <h4>执行方式</h4>
            <p>后端会把已启用的行为目录传给外部 HTTP Provider，由 Provider 返回一个主行为和一条推荐语料。</p>

            <h4>约束</h4>
            <p>当前版本不支持新增自定义 `action_key`，仅支持维护内置行为。</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { interviewApi } from '@/api/interview'

const DEFAULT_ACTIONS = [
  {
    action_key: 'ask_new_question',
    enabled: true,
    label: '提新问题',
    description: '当前回答已足够，可以切入下一个问题。',
    utterance_templates: ['我们进入下一个问题。', '这个点我了解了，接下来想换个角度问你。']
  },
  {
    action_key: 'probe_detail',
    enabled: true,
    label: '追细节',
    description: '继续深挖技术细节、方案细节或实现细节。',
    utterance_templates: ['你把这一部分的具体实现再展开讲讲。', '这里的关键细节是什么？请具体说明。']
  },
  {
    action_key: 'probe_contribution',
    enabled: true,
    label: '追个人贡献',
    description: '聚焦候选人在项目中的个人职责和实际产出。',
    utterance_templates: ['这里你个人具体负责了哪一部分？', '这个结果里，哪些是你亲自推动完成的？']
  },
  {
    action_key: 'challenge',
    enabled: true,
    label: '质疑',
    description: '对模糊、可疑或前后不一致的表述进行挑战。',
    utterance_templates: ['这个说法我想再核实一下，你的依据是什么？', '如果按你这个方案执行，风险点会在哪里？']
  },
  {
    action_key: 'clarify',
    enabled: true,
    label: '澄清',
    description: '候选人表达模糊、跳跃或缺少关键信息时先澄清。',
    utterance_templates: ['我先确认一下，你刚才的意思是？', '这里我理解得还不够清楚，你能换个方式再说一遍吗？']
  },
  {
    action_key: 'refocus',
    enabled: true,
    label: '拉回主线',
    description: '用户跑题、回避或信息噪声过多时拉回目标问题。',
    utterance_templates: ['我们先回到刚才那个核心问题。', '先聚焦在你刚提到的这个关键点上。']
  },
  {
    action_key: 'transition',
    enabled: true,
    label: '转场',
    description: '当前话题可以收束，准备切换到新的主题或阶段。',
    utterance_templates: ['这个部分先到这里，我们切到下一个主题。', '我想从另一个维度继续了解你。']
  },
  {
    action_key: 'close',
    enabled: true,
    label: '收尾',
    description: '当前轮次或阶段适合做简短收束。',
    utterance_templates: ['这个问题我了解得差不多了，我们做个小结。', '好的，这部分先收一下。']
  }
]

const loading = ref(false)
const saving = ref(false)
const activePanels = ref([])

const fullConfig = reactive({
  base_system_prompt: '',
  interviewer_system_template: '',
  stages: {},
  llm: {},
  tools: {
    providers: {},
    bindings: {},
    timeouts: {},
    cache: {},
    smart_reply_catalog: {
      actions: []
    }
  }
})

const actions = computed(() => fullConfig.tools.smart_reply_catalog.actions || [])

onMounted(async () => {
  await reloadConfig()
})

function deepClone(value) {
  return JSON.parse(JSON.stringify(value))
}

function normalizeAction(action) {
  return {
    action_key: action?.action_key || '',
    enabled: action?.enabled !== false,
    label: action?.label || '',
    description: action?.description || '',
    utterance_templates: Array.isArray(action?.utterance_templates)
      ? action.utterance_templates.map((item) => String(item ?? ''))
      : []
  }
}

function ensureCatalog(actionsInput = []) {
  const inputMap = new Map(actionsInput.map((item) => [item.action_key, normalizeAction(item)]))
  return DEFAULT_ACTIONS.map((item) => {
    const existing = inputMap.get(item.action_key)
    return existing ? { ...item, ...existing } : deepClone(item)
  })
}

function applyConfig(data) {
  Object.assign(fullConfig, data)
  fullConfig.tools = {
    providers: {},
    bindings: {},
    timeouts: {},
    cache: {},
    smart_reply_catalog: {
      actions: []
    },
    ...(data?.tools || {})
  }
  fullConfig.tools.smart_reply_catalog = {
    actions: ensureCatalog(fullConfig.tools.smart_reply_catalog?.actions || [])
  }
  activePanels.value = []
}

async function reloadConfig() {
  loading.value = true
  try {
    const data = await interviewApi.getPromptConfig()
    applyConfig(data)
    ElMessage.success('智能回复配置加载成功')
  } catch (error) {
    console.error('加载智能回复配置失败', error)
    ElMessage.error('加载智能回复配置失败')
  } finally {
    loading.value = false
  }
}

function appendTemplate(actionKey) {
  const target = actions.value.find((item) => item.action_key === actionKey)
  if (!target) return
  target.utterance_templates.push('')
}

function removeTemplate(actionKey, index) {
  const target = actions.value.find((item) => item.action_key === actionKey)
  if (!target) return
  target.utterance_templates.splice(index, 1)
}

function buildPayload() {
  const payload = deepClone(fullConfig)
  payload.tools = payload.tools || {}
  payload.tools.smart_reply_catalog = {
    actions: ensureCatalog(payload.tools.smart_reply_catalog?.actions || []).map((item) => ({
      ...item,
      utterance_templates: (item.utterance_templates || []).map((template) => String(template || '').trim()).filter(Boolean)
    }))
  }
  return payload
}

async function handleSave() {
  try {
    await ElMessageBox.confirm('确认保存智能回复配置？', '确认', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      type: 'warning'
    })

    saving.value = true
    const payload = buildPayload()
    await interviewApi.updatePromptConfig(payload)
    applyConfig(payload)
    ElMessage.success('智能回复配置保存成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('保存智能回复配置失败', error)
      ElMessage.error('保存智能回复配置失败')
    }
  } finally {
    saving.value = false
  }
}

async function handleRestoreDefaults() {
  try {
    await ElMessageBox.confirm('确认恢复默认行为和语料？未保存的修改会被覆盖。', '确认', {
      confirmButtonText: '恢复',
      cancelButtonText: '取消',
      type: 'warning'
    })

    fullConfig.tools.smart_reply_catalog = {
      actions: deepClone(DEFAULT_ACTIONS)
    }
    activePanels.value = []
    ElMessage.success('已恢复默认行为语料')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('恢复默认失败', error)
      ElMessage.error('恢复默认失败')
    }
  }
}
</script>

<style scoped lang="scss">
.smart-reply-config {
  max-width: 1440px;
  margin: 0 auto;
}

.page-title {
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
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.action-list :deep(.el-collapse) {
  border-top: none;
}

.action-title {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-right: 8px;
}

.action-title-main {
  display: flex;
  align-items: center;
  gap: 10px;
}

.action-key {
  font-size: 12px;
  color: #6b7280;
}

.action-form {
  padding-top: 8px;
}

.template-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.template-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: start;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;

  > * {
    width: 100%;
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

@media (max-width: 768px) {
  .template-row {
    grid-template-columns: 1fr;
  }
}
</style>
