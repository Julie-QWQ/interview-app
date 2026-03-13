<template>
  <div class="stage-config" v-loading="loading">
    <h2 class="stage-title">面试阶段管理</h2>

    <el-card class="flow-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>阶段流程</span>
          <div class="header-meta">
            <el-tag type="info">{{ stageList.length }} 个阶段</el-tag>
            <el-tag type="success">总时长 {{ totalDuration }} 分钟</el-tag>
            <el-button type="primary" size="small" @click="openCreateDialog">新增阶段</el-button>
          </div>
        </div>
      </template>

      <el-empty v-if="stageList.length === 0" description="暂无阶段，请先新增阶段" />

      <div v-else class="flow-scroll">
        <div class="flow-track">
          <div
            v-for="(stage, index) in stageList"
            :key="stage.stage"
            class="flow-item"
            :class="{ 'is-selected': stage.stage === selectedStageKey }"
          >
            <div class="node-row">
              <button
                class="stage-index"
                :class="{ 'is-disabled': stage.enabled === false }"
                type="button"
                @click="selectStage(stage.stage)"
              >
                {{ index + 1 }}
              </button>
              <div
                v-if="index < stageList.length - 1"
                class="stage-line"
                :class="{ 'is-active': index < selectedStageIndex }"
              ></div>
            </div>

            <div class="stage-card" @click="selectStage(stage.stage)">
              <div class="stage-card-title">
                <span>{{ stage.name }}</span>
                <el-tag v-if="stage.stage === selectedStageKey" size="small" type="primary">编辑中</el-tag>
              </div>
              <div class="stage-meta">{{ stage.time_allocation }} 分钟 · {{ stage.min_turns }}-{{ stage.max_turns }} 轮</div>
              <p class="stage-desc">{{ stage.description || '暂无阶段描述' }}</p>
            </div>

            <div class="stage-actions">
              <el-button size="small" @click="moveLeft(index)" :disabled="index === 0">左移</el-button>
              <el-button size="small" @click="moveRight(index)" :disabled="index === stageList.length - 1">右移</el-button>
              <el-popconfirm title="确定删除这个阶段吗？" @confirm="removeStage(index)">
                <template #reference>
                  <el-button size="small" type="danger" plain :disabled="stageList.length <= 1">删除</el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <el-card v-if="selectedStage" class="editor-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="editor-header-left">
            <span>阶段配置：{{ selectedStage.name }}</span>
            <el-tag>{{ selectedStage.stage }}</el-tag>
          </div>
          <div class="editor-header-actions">
            <el-button type="primary" @click="handleSaveCurrentStage" :loading="saving">保存当前阶段</el-button>
            <el-button @click="handleResetCurrentStage" :loading="resetting">重置当前阶段</el-button>
          </div>
        </div>
      </template>

      <div class="stage-editor-shell">
        <section class="editor-section">
          <div class="section-heading">
            <h3>阶段信息</h3>
          </div>

          <el-form :model="selectedStage" label-width="120px">
            <el-form-item label="阶段标识">
              <el-input v-model="selectedStage.stage" disabled />
            </el-form-item>

            <el-form-item label="阶段名称">
              <el-input v-model="selectedStage.name" />
            </el-form-item>

            <el-form-item label="阶段描述">
              <el-input v-model="selectedStage.description" />
            </el-form-item>

            <el-row :gutter="20">
              <el-col :xs="24" :md="8">
                <el-form-item label="最少轮次">
                  <el-input-number v-model="selectedStage.min_turns" :min="1" :max="20" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="8">
                <el-form-item label="最多轮次">
                  <el-input-number v-model="selectedStage.max_turns" :min="1" :max="20" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="8">
                <el-form-item label="时长（分钟）">
                  <el-input-number v-model="selectedStage.time_allocation" :min="1" :max="120" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="启用">
              <el-switch v-model="selectedStage.enabled" />
            </el-form-item>

            <el-form-item label="系统指令">
              <el-input
                v-model="selectedStage.system_instruction"
                type="textarea"
                :rows="6"
                placeholder="该阶段注入到 LLM 的系统指令"
              />
            </el-form-item>
          </el-form>
        </section>

        <section class="editor-section editor-section--binding">
          <div class="section-heading">
            <div>
              <h3>阶段工具绑定</h3>
              <p class="binding-subtitle">拖动下方工具气泡到当前阶段的触发器区域，点击气泡右上角叉号可移除。</p>
            </div>
          </div>

          <div class="binding-layout">
            <section class="tool-palette">
              <div class="palette-header">
                <span>工具气泡</span>
                <el-tag type="info">{{ availableToolNames.length }} 个工具</el-tag>
              </div>

              <el-empty v-if="availableToolNames.length === 0" description="暂无工具，请先到工具配置页新增 Provider" />

              <div v-else class="palette-list">
                <button
                  v-for="toolName in availableToolNames"
                  :key="toolName"
                  class="tool-bubble tool-bubble--palette"
                  type="button"
                  draggable="true"
                  @dragstart="handleToolDragStart(toolName)"
                  @dragend="handleToolDragEnd"
                >
                  <span>{{ toolName }}</span>
                </button>
              </div>
            </section>

            <section class="binding-zones">
              <div
                v-for="trigger in triggerKeys"
                :key="trigger"
                class="trigger-zone"
                :class="{ 'is-over': dragOverTrigger === trigger }"
                @dragover.prevent="handleTriggerDragOver(trigger)"
                @dragleave="handleTriggerDragLeave(trigger)"
                @drop.prevent="handleTriggerDrop(trigger)"
              >
                <div class="trigger-header">
                  <div>
                    <strong>{{ triggerLabelMap[trigger] }}</strong>
                    <p>{{ triggerDescMap[trigger] }}</p>
                  </div>
                  <el-tag size="small">{{ currentBinding.trigger_map[trigger].length }} 个</el-tag>
                </div>

                <div class="trigger-bubbles">
                  <button
                    v-for="toolName in currentBinding.trigger_map[trigger]"
                    :key="`${trigger}-${toolName}`"
                    class="tool-bubble tool-bubble--assigned"
                    type="button"
                    draggable="true"
                    @dragstart="handleToolDragStart(toolName)"
                    @dragend="handleToolDragEnd"
                  >
                    <span>{{ toolName }}</span>
                    <span
                      class="bubble-close"
                      role="button"
                      tabindex="0"
                      @click.stop="removeToolFromTrigger(trigger, toolName)"
                      @keydown.enter.stop="removeToolFromTrigger(trigger, toolName)"
                    >
                      ×
                    </span>
                  </button>

                  <div v-if="currentBinding.trigger_map[trigger].length === 0" class="trigger-empty">
                    将工具气泡拖到这里
                  </div>
                </div>
              </div>
            </section>
          </div>
        </section>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { interviewApi } from '@/api/interview'

const loading = ref(false)
const saving = ref(false)
const resetting = ref(false)

const triggerKeys = ['interview_start', 'stage_enter', 'user_turn']
const triggerLabelMap = {
  interview_start: 'interview_start',
  stage_enter: 'stage_enter',
  user_turn: 'user_turn'
}
const triggerDescMap = {
  interview_start: '开始面试时触发，适合首轮预加载。',
  stage_enter: '进入当前阶段时触发，适合阶段级预取。',
  user_turn: '用户每轮发言后触发，适合实时追问与补充。'
}

const fullConfig = reactive({
  base_system_prompt: '',
  stages: {},
  llm: {},
  tools: {
    providers: {},
    bindings: {}
  }
})

const stageList = ref([])
const selectedStageKey = ref('')
const draggingToolName = ref('')
const dragOverTrigger = ref('')

const selectedStageIndex = computed(() => stageList.value.findIndex((s) => s.stage === selectedStageKey.value))
const selectedStage = computed(() => stageList.value.find((s) => s.stage === selectedStageKey.value) || null)
const totalDuration = computed(() => stageList.value.reduce((sum, s) => sum + (s.time_allocation || 0), 0))
const availableToolNames = computed(() => Object.keys(fullConfig.tools?.providers || {}))
const currentBinding = computed(() => {
  const stageKey = selectedStageKey.value
  if (!stageKey) return createEmptyBinding()
  if (!fullConfig.tools.bindings[stageKey]) {
    fullConfig.tools.bindings[stageKey] = createEmptyBinding()
  }
  return fullConfig.tools.bindings[stageKey]
})

onMounted(async () => {
  await loadConfig()
})

function createEmptyBinding() {
  return {
    trigger_map: {
      interview_start: [],
      stage_enter: [],
      user_turn: []
    },
    cache_only: false
  }
}

function ensureBinding(binding = {}) {
  return {
    trigger_map: {
      interview_start: Array.isArray(binding?.trigger_map?.interview_start) ? [...binding.trigger_map.interview_start] : [],
      stage_enter: Array.isArray(binding?.trigger_map?.stage_enter) ? [...binding.trigger_map.stage_enter] : [],
      user_turn: Array.isArray(binding?.trigger_map?.user_turn) ? [...binding.trigger_map.user_turn] : []
    },
    cache_only: Boolean(binding?.cache_only)
  }
}

function toStageList(stagesObj = {}) {
  return Object.values(stagesObj)
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
    .map((s, idx) => ({
      ...s,
      order: Number.isFinite(s.order) ? s.order : idx + 1
    }))
}

function selectStage(stageKey) {
  selectedStageKey.value = stageKey
}

async function loadConfig() {
  loading.value = true
  try {
    const data = await interviewApi.getPromptConfig()
    Object.assign(fullConfig, data)
    fullConfig.tools = {
      providers: {},
      bindings: {},
      ...(data?.tools || {})
    }
    const normalizedBindings = {}
    Object.keys(data?.stages || {}).forEach((stageKey) => {
      normalizedBindings[stageKey] = ensureBinding(fullConfig.tools.bindings?.[stageKey] || {})
    })
    fullConfig.tools.bindings = normalizedBindings
    stageList.value = toStageList(data?.stages || {})
    selectedStageKey.value = stageList.value[0]?.stage || ''
  } catch (error) {
    console.error('加载配置失败', error)
    ElMessage.error('加载配置失败')
  } finally {
    loading.value = false
  }
}

function moveLeft(index) {
  if (index <= 0) return
  const tmp = stageList.value[index - 1]
  stageList.value[index - 1] = stageList.value[index]
  stageList.value[index] = tmp
}

function moveRight(index) {
  if (index >= stageList.value.length - 1) return
  const tmp = stageList.value[index + 1]
  stageList.value[index + 1] = stageList.value[index]
  stageList.value[index] = tmp
}

function removeStage(index) {
  if (stageList.value.length <= 1) {
    ElMessage.warning('至少保留一个阶段')
    return
  }
  const removed = stageList.value[index]
  stageList.value.splice(index, 1)
  delete fullConfig.tools.bindings[removed.stage]
  if (selectedStageKey.value === removed.stage) {
    selectedStageKey.value = stageList.value[Math.max(0, index - 1)]?.stage || stageList.value[0]?.stage || ''
  }
}

function generateStageKey(base = 'custom') {
  let counter = 1
  let key = `${base}_${counter}`
  const existing = new Set(stageList.value.map((s) => s.stage))
  while (existing.has(key)) {
    counter += 1
    key = `${base}_${counter}`
  }
  return key
}

async function openCreateDialog() {
  try {
    const { value } = await ElMessageBox.prompt('请输入新阶段名称', '新增阶段', {
      confirmButtonText: '创建',
      cancelButtonText: '取消',
      inputPlaceholder: '例如：项目追问',
      inputValidator: (val) => {
        if (!val || !val.trim()) return '阶段名称不能为空'
        return true
      }
    })

    const name = value.trim()
    const stageKey = generateStageKey('custom')
    const nextStage = {
      stage: stageKey,
      name,
      description: '',
      min_turns: 1,
      max_turns: 3,
      time_allocation: 5,
      system_instruction: '',
      enabled: true,
      order: stageList.value.length + 1
    }

    stageList.value.push(nextStage)
    fullConfig.tools.bindings[stageKey] = createEmptyBinding()
    selectedStageKey.value = stageKey
    ElMessage.success('已新增阶段，请编辑后保存')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('新增阶段失败', error)
      ElMessage.error('新增阶段失败')
    }
  }
}

function validateStage(stage) {
  if (!stage) {
    ElMessage.warning('未选择阶段')
    return false
  }
  if (!stage.name?.trim()) {
    ElMessage.warning(`阶段 ${stage.stage} 的名称不能为空`)
    return false
  }
  if (stage.min_turns > stage.max_turns) {
    ElMessage.warning(`阶段 ${stage.name} 的最少轮次不能大于最多轮次`)
    return false
  }
  return true
}

function buildStagesObject() {
  const next = {}
  stageList.value.forEach((s, idx) => {
    next[s.stage] = {
      ...s,
      order: idx + 1
    }
  })
  return next
}

async function handleSaveCurrentStage() {
  try {
    if (!selectedStage.value) {
      ElMessage.warning('请先选择一个阶段')
      return
    }
    if (!validateStage(selectedStage.value)) {
      return
    }

    await ElMessageBox.confirm('确认保存当前阶段配置？', '确认', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      type: 'warning'
    })

    saving.value = true

    const payload = {
      ...fullConfig,
      stages: buildStagesObject(),
      tools: {
        ...fullConfig.tools,
        bindings: {
          ...(fullConfig.tools.bindings || {}),
          [selectedStage.value.stage]: ensureBinding(fullConfig.tools.bindings?.[selectedStage.value.stage] || {})
        }
      }
    }

    await interviewApi.updatePromptConfig(payload)
    Object.assign(fullConfig, payload)
    stageList.value = toStageList(payload.stages)
    ElMessage.success('当前阶段保存成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('保存失败', error)
      ElMessage.error('保存失败')
    }
  } finally {
    saving.value = false
  }
}

async function handleResetCurrentStage() {
  try {
    if (!selectedStage.value) {
      ElMessage.warning('请先选择一个阶段')
      return
    }

    await ElMessageBox.confirm('确认重置当前阶段为已保存版本？', '确认', {
      confirmButtonText: '重置',
      cancelButtonText: '取消',
      type: 'warning'
    })

    resetting.value = true
    await loadConfig()
    ElMessage.success('当前阶段已重置')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重置失败', error)
      ElMessage.error('重置失败')
    }
  } finally {
    resetting.value = false
  }
}

function handleToolDragStart(toolName) {
  draggingToolName.value = toolName
}

function handleToolDragEnd() {
  draggingToolName.value = ''
  dragOverTrigger.value = ''
}

function handleTriggerDragOver(trigger) {
  dragOverTrigger.value = trigger
}

function handleTriggerDragLeave(trigger) {
  if (dragOverTrigger.value === trigger) {
    dragOverTrigger.value = ''
  }
}

function handleTriggerDrop(trigger) {
  const toolName = draggingToolName.value
  dragOverTrigger.value = ''
  if (!toolName || !selectedStageKey.value) return

  const binding = currentBinding.value
  const currentList = binding.trigger_map[trigger] || []
  if (!currentList.includes(toolName)) {
    binding.trigger_map[trigger] = [...currentList, toolName]
  }
  draggingToolName.value = ''
}

function removeToolFromTrigger(trigger, toolName) {
  const binding = currentBinding.value
  binding.trigger_map[trigger] = (binding.trigger_map[trigger] || []).filter((item) => item !== toolName)
}
</script>

<style scoped lang="scss">
.stage-config {
  max-width: 1440px;
  margin: 0 auto;
}

.stage-title {
  margin: 0 0 18px;
  font-size: 24px;
  line-height: 1.25;
}

.flow-card,
.editor-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-weight: 600;
}

.binding-subtitle {
  margin: 6px 0 0;
  color: #8a93a3;
  font-size: 13px;
  font-weight: 400;
}

.editor-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.editor-header-actions,
.header-meta {
  display: flex;
  gap: 8px;
}

.flow-scroll {
  overflow-x: auto;
  padding-bottom: 6px;
}

.flow-track {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: max-content;
}

.flow-item {
  width: 260px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.flow-item.is-selected .stage-card {
  border-color: #111318;
  box-shadow: 0 14px 28px rgba(17, 19, 24, 0.12);
}

.node-row {
  display: flex;
  align-items: center;
}

.stage-index {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  border: none;
  background: #111318;
  color: #fff;
  font-weight: 700;
  cursor: pointer;
}

.stage-index.is-disabled {
  background: #b8bec8;
}

.stage-line {
  flex: 1;
  height: 2px;
  background: #d7dbe2;
  margin-left: 10px;
}

.stage-line.is-active {
  background: #111318;
}

.stage-card {
  border: 1px solid #dfe4ea;
  border-radius: 16px;
  background: #fff;
  padding: 16px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.stage-card-title {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: flex-start;
  font-weight: 700;
}

.stage-meta {
  margin-top: 8px;
  color: #6b7280;
  font-size: 13px;
}

.stage-desc {
  margin: 10px 0 0;
  color: #4b5563;
  line-height: 1.6;
  font-size: 14px;
}

.stage-actions {
  display: flex;
  gap: 8px;
}

.stage-editor-shell {
  display: grid;
  gap: 24px;
}

.editor-section {
  padding: 20px;
  border: 1px solid #e7ebf0;
  border-radius: 20px;
  background: linear-gradient(180deg, #ffffff 0%, #fafbfc 100%);
}

.editor-section--binding {
  padding-top: 18px;
}

.section-heading {
  margin-bottom: 18px;
}

.section-heading h3 {
  margin: 0;
  font-size: 17px;
  color: #111827;
}

.binding-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 18px;
}

.tool-palette,
.trigger-zone {
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  background: #fbfbfc;
}

.tool-palette {
  padding: 16px;
  align-self: start;
}

.palette-header,
.trigger-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.palette-list,
.trigger-bubbles {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.binding-zones {
  display: grid;
  gap: 14px;
}

.trigger-zone {
  padding: 16px;
  min-height: 140px;
  transition: all 0.16s ease;
}

.trigger-zone.is-over {
  border-color: #111318;
  background: #f3f5f8;
  box-shadow: inset 0 0 0 1px rgba(17, 19, 24, 0.08);
}

.trigger-header p {
  margin: 6px 0 0;
  color: #8a93a3;
  font-size: 13px;
  line-height: 1.5;
}

.tool-bubble {
  position: relative;
  border: 1px solid #d5dbe3;
  border-radius: 999px;
  background: #ffffff;
  color: #111827;
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
  padding: 10px 16px;
  cursor: grab;
  transition: all 0.16s ease;
}

.tool-bubble:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(17, 24, 39, 0.08);
}

.tool-bubble--palette {
  background: linear-gradient(135deg, #fff 0%, #f6f8fb 100%);
}

.tool-bubble--assigned {
  padding-right: 30px;
  background: #111318;
  border-color: #111318;
  color: #fff;
}

.bubble-close {
  position: absolute;
  top: -4px;
  right: -2px;
  width: 18px;
  height: 18px;
  border-radius: 999px;
  background: #ffefe9;
  color: #d14343;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.trigger-empty {
  width: 100%;
  min-height: 72px;
  border: 1px dashed #d5dbe3;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #98a2b3;
  font-size: 13px;
  background: #fff;
}

@media (max-width: 960px) {
  .binding-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .card-header,
  .editor-header-actions,
  .header-meta {
    flex-direction: column;
    align-items: flex-start;
  }

  .stage-actions {
    flex-wrap: wrap;
  }
}
</style>
