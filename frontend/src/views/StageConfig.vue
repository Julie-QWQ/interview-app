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
                  <el-popconfirm
                    title="确定删除这个阶段吗？"
                    @confirm="removeStage(index)"
                  >
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
            <span>编辑阶段：{{ selectedStage.name }}</span>
            <el-tag>{{ selectedStage.stage }}</el-tag>
          </div>
          <div class="editor-header-actions">
            <el-button type="primary" @click="handleSaveCurrentStage" :loading="saving">保存当前阶段</el-button>
            <el-button @click="handleResetCurrentStage" :loading="resetting">重置当前阶段</el-button>
          </div>
        </div>
      </template>

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
                <el-form-item label="最小轮次">
                  <el-input-number v-model="selectedStage.min_turns" :min="1" :max="20" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="8">
                <el-form-item label="最大轮次">
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

const fullConfig = reactive({
  base_system_prompt: '',
  stages: {},
  llm: {}
})

const stageList = ref([])
const selectedStageKey = ref('')

const selectedStageIndex = computed(() => stageList.value.findIndex((s) => s.stage === selectedStageKey.value))
const selectedStage = computed(() => stageList.value.find((s) => s.stage === selectedStageKey.value) || null)
const totalDuration = computed(() => stageList.value.reduce((sum, s) => sum + (s.time_allocation || 0), 0))

onMounted(async () => {
  await loadConfig()
})

function toStageList(stagesObj = {}) {
  return Object.values(stagesObj)
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
    .map((s, idx) => ({
      ...s,
      order: Number.isFinite(s.order) ? s.order : idx + 1
    }))
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

function selectStage(stageKey) {
  selectedStageKey.value = stageKey
}

async function loadConfig() {
  loading.value = true
  try {
    const data = await interviewApi.getPromptConfig()
    Object.assign(fullConfig, data)
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
    ElMessage.warning(`阶段 ${stage.name} 的最小轮次不能大于最大轮次`)
    return false
  }
  return true
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

    // 只持久化当前阶段：从已保存配置出发，仅替换当前阶段
    const persistedStages = { ...(fullConfig.stages || {}) }
    persistedStages[selectedStage.value.stage] = {
      ...selectedStage.value,
      order: persistedStages[selectedStage.value.stage]?.order ?? (selectedStageIndex.value + 1),
    }

    const payload = {
      ...fullConfig,
      stages: persistedStages
    }
    await interviewApi.updatePromptConfig(payload)
    Object.assign(fullConfig, payload)
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

    const persisted = fullConfig.stages?.[selectedStage.value.stage]
    if (!persisted) {
      ElMessage.warning('当前阶段没有已保存版本可重置')
      return
    }

    const idx = selectedStageIndex.value
    if (idx >= 0) {
      stageList.value[idx] = {
        ...stageList.value[idx],
        ...persisted,
      }
    }
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
</script>

<style scoped lang="scss">
.stage-config {
  max-width: 1400px;
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
  font-weight: 600;
}

.editor-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.editor-header-actions {
  display: flex;
  gap: 8px;
}

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
  width: 190px;
  flex: 0 0 190px;
}

.node-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.stage-index {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 2px solid #409eff;
  color: #409eff;
  background: #fff;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.stage-index.is-disabled {
  border-color: #c0c4cc;
  color: #909399;
  background: #f5f7fa;
}

.stage-line {
  flex: 1;
  height: 3px;
  margin-left: 8px;
  border-radius: 999px;
  background: #dcdfe6;
}

.stage-line.is-active {
  background: #409eff;
}

.stage-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px;
  background: #fff;
  min-height: 112px;
  cursor: pointer;
}

.flow-item.is-selected .stage-card {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.12);
}

.stage-card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  font-size: 16px;
  font-weight: 800;
  line-height: 1.2;
  color: #1f2937;
}

.stage-meta {
  margin-top: 6px;
  color: #6b7280;
  font-size: 12px;
}

.stage-desc {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.4;
}

.stage-actions {
  margin-top: 8px;
  display: flex;
  gap: 6px;
}

@media (max-width: 992px) {
  .editor-header-actions {
    width: 100%;
    justify-content: flex-start;
  }
}

@media (max-width: 1200px) {
  .flow-item {
    width: 172px;
    flex: 0 0 172px;
  }

  .stage-card-title {
    font-size: 15px;
  }

  .stage-meta,
  .stage-desc {
    font-size: 11px;
  }
}
</style>
