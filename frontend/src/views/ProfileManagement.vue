<template>
  <div class="profile-management">
    <h2 class="profile-title">画像管理</h2>

    <el-card class="management-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="type-segment" role="tablist" aria-label="画像类型切换">
            <button
              type="button"
              class="segment-btn"
              :class="{ 'is-active': activeType === 'position' }"
              :aria-pressed="activeType === 'position'"
              @click="activeType = 'position'"
            >
              岗位画像
            </button>
            <button
              type="button"
              class="segment-btn"
              :class="{ 'is-active': activeType === 'interviewer' }"
              :aria-pressed="activeType === 'interviewer'"
              @click="activeType = 'interviewer'"
            >
              面试官画像
            </button>
          </div>
        </div>
      </template>

      <div v-loading="loading" class="profile-grid">
        <button class="create-card" type="button" @click="handleCreate">
          <el-icon class="create-icon"><Plus /></el-icon>
          <span>创建新画像</span>
        </button>

        <article v-for="row in filteredProfiles" :key="row.plugin_id" class="profile-card">
          <header class="profile-card-header">
            <div class="name-cell">
              <el-icon v-if="row.type === 'position'" color="#409EFF"><Briefcase /></el-icon>
              <el-icon v-else color="#67C23A"><User /></el-icon>
              <span>{{ row.name }}</span>
            </div>
            <el-tag v-if="row.is_system" size="small" type="info">系统预设</el-tag>
          </header>

          <div class="profile-card-meta">
            <el-tag :type="row.type === 'position' ? 'primary' : 'success'" size="small">
              {{ row.type === 'position' ? '岗位画像' : '面试官画像' }}
            </el-tag>
          </div>

          <p class="profile-card-desc">{{ row.description || '暂无描述' }}</p>

          <div class="config-info">
            <template v-if="row.type === 'position'">
              <el-tag size="small" v-if="row.config?.ability_weights" type="info">能力权重</el-tag>
              <el-tag size="small" v-if="row.config?.skill_requirements?.core_skills?.length">
                {{ row.config.skill_requirements.core_skills.length }} 个核心技能
              </el-tag>
            </template>
            <template v-else>
              <el-tag size="small" v-if="row.config?.style" type="success">
                {{ getInterviewerStyleLabel(row.config.style) }}
              </el-tag>
              <el-tag size="small" v-if="row.config?.characteristics?.length" type="warning">
                {{ row.config.characteristics.length }} 个特征
              </el-tag>
            </template>
          </div>

          <footer class="profile-card-actions">
            <el-button v-if="!row.is_system" link type="primary" size="small" @click="handleEdit(row)">
              编辑
            </el-button>
            <el-button link type="primary" size="small" @click="handleView(row)">
              查看
            </el-button>
            <el-popconfirm
              v-if="!row.is_system"
              title="确定删除这个画像吗？"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </footer>
        </article>
      </div>

      <el-empty v-if="filteredProfiles.length === 0 && !loading" description="暂无画像数据，可先点击上方加号卡片创建" />
    </el-card>

    <ProfileConfigDialog v-model="dialogVisible" :plugin="editingPlugin" @success="handleDialogSuccess" />

    <el-dialog v-model="viewDialogVisible" :title="viewingPlugin?.name" width="600px">
      <div v-if="viewingPlugin" class="profile-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="类型">
            <el-tag :type="viewingPlugin.type === 'position' ? 'primary' : 'success'" size="small">
              {{ viewingPlugin.type === 'position' ? '岗位画像' : '面试官画像' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="是否系统预设">
            <el-tag :type="viewingPlugin.is_system ? 'info' : ''" size="small">
              {{ viewingPlugin.is_system ? '是' : '否' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">
            {{ viewingPlugin.description }}
          </el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">详细配置</el-divider>

        <div v-if="viewingPlugin.type === 'position'" class="position-config">
          <div v-if="viewingPlugin.config?.ability_weights">
            <h4>能力权重配置</h4>
            <div class="weights-grid">
              <div v-for="(weight, key) in viewingPlugin.config.ability_weights" :key="key" class="weight-item">
                <span class="weight-label">{{ getAbilityLabel(key) }}:</span>
                <el-progress :percentage="weight" :stroke-width="8" />
              </div>
            </div>
          </div>

          <div v-if="viewingPlugin.config?.required_skills?.length" style="margin-top: 16px">
            <h4>必需技能</h4>
            <el-space wrap>
              <el-tag v-for="skill in viewingPlugin.config.required_skills" :key="skill">{{ skill }}</el-tag>
            </el-space>
          </div>

          <div v-if="viewingPlugin.config?.preferred_qualifications" style="margin-top: 16px">
            <h4>优先资格</h4>
            <p>{{ viewingPlugin.config.preferred_qualifications }}</p>
          </div>
        </div>

        <div v-else class="interviewer-config">
          <div v-if="viewingPlugin.config?.style">
            <h4>面试风格</h4>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="提问风格">
                {{ getInterviewerStyleLabel(viewingPlugin.config.style) }}
              </el-descriptions-item>
              <el-descriptions-item label="节奏">
                {{ getPaceLabel(viewingPlugin.config.style.pace) }}
              </el-descriptions-item>
              <el-descriptions-item label="深度">
                {{ getDepthLabel(viewingPlugin.config.style.depth) }}
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <div v-if="viewingPlugin.config?.characteristics?.length" style="margin-top: 16px">
            <h4>特征标签</h4>
            <el-space wrap>
              <el-tag v-for="char in viewingPlugin.config.characteristics" :key="char" type="warning">
                {{ char }}
              </el-tag>
            </el-space>
          </div>

          <div v-if="viewingPlugin.config?.prompt_template" style="margin-top: 16px">
            <h4>Prompt 模板</h4>
            <el-input type="textarea" :model-value="viewingPlugin.config.prompt_template" :rows="6" readonly />
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="viewDialogVisible = false">关闭</el-button>
        <el-button v-if="viewingPlugin && !viewingPlugin.is_system" type="primary" @click="handleEditFromView">
          编辑
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Briefcase, User } from '@element-plus/icons-vue'
import { profileApi } from '@/api/profile'
import ProfileConfigDialog from '@/components/ProfileConfigDialog.vue'

const loading = ref(false)
const activeType = ref('position')
const profiles = ref([])
const dialogVisible = ref(false)
const editingPlugin = ref(null)
const viewDialogVisible = ref(false)
const viewingPlugin = ref(null)

const filteredProfiles = computed(() => {
  return profiles.value.filter((p) => p.type === activeType.value)
})

async function loadProfiles() {
  loading.value = true
  try {
    const response = await profileApi.listPlugins()
    if (response.success) {
      profiles.value = response.data
    }
  } catch (error) {
    console.error('加载画像列表失败', error)
    ElMessage.error('加载画像列表失败')
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  editingPlugin.value = null
  dialogVisible.value = true
}

function handleEdit(row) {
  editingPlugin.value = row
  dialogVisible.value = true
}

function handleView(row) {
  viewingPlugin.value = row
  viewDialogVisible.value = true
}

function handleEditFromView() {
  viewDialogVisible.value = false
  handleEdit(viewingPlugin.value)
}

async function handleDelete(row) {
  try {
    await profileApi.deletePlugin(row.plugin_id)
    ElMessage.success('删除成功')
    await loadProfiles()
  } catch (error) {
    console.error('删除画像失败', error)
    ElMessage.error(error.response?.data?.error || '删除失败')
  }
}

async function handleDialogSuccess() {
  dialogVisible.value = false
  editingPlugin.value = null
  await loadProfiles()
}

function getAbilityLabel(key) {
  const labels = {
    technical: '技术能力',
    communication: '沟通能力',
    problem_solving: '问题解决',
    leadership: '领导力',
    learning: '学习能力'
  }
  return labels[key] || key
}

function getInterviewerStyleLabel(style) {
  if (!style) return ''
  const styleMap = {
    deep_technical: '技术深入型',
    guided: '亲和引导型',
    behavioral: '行为导向型'
  }
  return styleMap[style?.questioning_style] || style?.questioning_style || '标准'
}

function getPaceLabel(pace) {
  const paceMap = {
    fast: '快节奏',
    moderate: '适中',
    slow: '慢节奏'
  }
  return paceMap[pace] || pace
}

function getDepthLabel(depth) {
  const depthMap = {
    deep: '深入',
    moderate: '适中',
    light: '浅层'
  }
  return depthMap[depth] || depth
}

onMounted(() => {
  loadProfiles()
})
</script>

<style scoped lang="scss">
.profile-management {
  max-width: 1400px;
  margin: 0 auto;
}

.profile-title {
  margin: 0 0 18px;
  font-size: 24px;
  line-height: 1.25;
}

.management-card {
  margin-top: 24px;

  .card-header {
    display: flex;
    align-items: center;
  }
}

.type-segment {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: #f8f9fb;
}

.segment-btn {
  border: none;
  background: transparent;
  color: #6b7280;
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 14px;
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.segment-btn:hover {
  background: #eef1f5;
  color: #374151;
}

.segment-btn.is-active {
  background: #111827;
  color: #ffffff;
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.create-card {
  min-height: 208px;
  border: 1px dashed #cfd4dc;
  background: #fafafa;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #6b7280;
  cursor: pointer;
  transition: background-color 0.2s ease, border-color 0.2s ease;

  &:hover {
    background: #f2f3f5;
    border-color: #b8bec8;
  }

  .create-icon {
    font-size: 22px;
  }
}

.profile-card {
  min-height: 208px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #fff;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;

  &:hover {
    background: #f8f9fb;
  }
}

.profile-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.profile-card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.profile-card-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #6b7280;
  min-height: 42px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 8px;

  span {
    font-weight: 500;
  }
}

.config-info {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.profile-card-actions {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.profile-detail {
  h4 {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 16px 0 8px 0;
  }

  .weights-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;

    .weight-item {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .weight-label {
        font-size: 13px;
        color: var(--text-secondary);
      }
    }
  }

  p {
    margin: 0;
    font-size: 14px;
    color: var(--text-primary);
    line-height: 1.6;
  }
}

:deep(.el-descriptions__label) {
  font-weight: 500;
}
</style>
