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
          <div v-if="row.type === 'interviewer' && row.config?.display_image_url" class="profile-visual">
            <img :src="row.config.display_image_url" :alt="row.name" class="profile-image" />
          </div>

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
              <el-tag v-if="row.config?.ability_weights" size="small" type="info">能力权重</el-tag>
              <el-tag v-if="row.config?.skill_requirements?.core_skills?.length" size="small">
                {{ row.config.skill_requirements.core_skills.length }} 个核心技能
              </el-tag>
            </template>
            <template v-else>
              <el-tag v-if="row.config?.style_tone" size="small">
                {{ getToneLabel(row.config.style_tone) }}
              </el-tag>
              <el-tag v-if="row.config?.difficulty" size="small" type="warning">
                {{ getDifficultyLabel(row.config.difficulty) }}
              </el-tag>
              <el-tag v-if="row.config?.prompt" size="small" type="warning">
                已配置风格
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

      <el-empty
        v-if="filteredProfiles.length === 0 && !loading"
        description="暂无画像数据，可先创建一个"
      />
    </el-card>

    <ProfileConfigDialog
      v-model="dialogVisible"
      :plugin="editingPlugin"
      :plugin-type="activeType"
      @success="handleDialogSuccess"
    />

    <el-dialog v-model="viewDialogVisible" :title="viewingPlugin?.name" width="680px">
      <div v-if="viewingPlugin" class="profile-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="类型">
            <el-tag :type="viewingPlugin.type === 'position' ? 'primary' : 'success'" size="small">
              {{ viewingPlugin.type === 'position' ? '岗位画像' : '面试官画像' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="系统预设">
            <el-tag :type="viewingPlugin.is_system ? 'info' : ''" size="small">
              {{ viewingPlugin.is_system ? '是' : '否' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">
            {{ viewingPlugin.description || '暂无描述' }}
          </el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">详细配置</el-divider>

        <div v-if="viewingPlugin.type === 'position'">
          <div v-if="viewingPlugin.config?.ability_weights">
            <h4>能力权重配置</h4>
            <div class="weights-grid">
              <div
                v-for="(weight, key) in viewingPlugin.config.ability_weights"
                :key="key"
                class="weight-item"
              >
                <span class="weight-label">{{ getAbilityLabel(key) }}:</span>
                <el-progress :percentage="Math.round(Number(weight || 0) * 100)" :stroke-width="8" />
              </div>
            </div>
          </div>

          <div v-if="viewingPlugin.config?.skill_requirements?.core_skills?.length" style="margin-top: 16px">
            <h4>核心技能</h4>
            <el-space wrap>
              <el-tag
                v-for="skill in viewingPlugin.config.skill_requirements.core_skills"
                :key="skill"
              >
                {{ skill }}
              </el-tag>
            </el-space>
          </div>
        </div>

        <div v-else class="interviewer-config">
          <div v-if="viewingPlugin.config?.display_image_url" class="detail-visual">
            <img :src="viewingPlugin.config.display_image_url" :alt="viewingPlugin.name" class="detail-image" />
          </div>

          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="风格强度">
              {{ getToneLabel(viewingPlugin.config?.style_tone) }}
            </el-descriptions-item>
            <el-descriptions-item label="难度等级">
              {{ getDifficultyLabel(viewingPlugin.config?.difficulty) }}
            </el-descriptions-item>
          </el-descriptions>

          <div v-if="viewingPlugin.config?.prompt" style="margin-top: 16px">
            <h4>面试官风格</h4>
            <el-input type="textarea" :model-value="viewingPlugin.config.prompt" :rows="8" readonly />
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
import { computed, onMounted, ref } from 'vue'
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

const filteredProfiles = computed(() => profiles.value.filter(profile => profile.type === activeType.value))

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
    learning_potential: '学习能力'
  }
  return labels[key] || key
}

function getToneLabel(tone) {
  const toneMap = {
    gentle: '平和',
    balanced: '平衡',
    strict: '严格'
  }
  return toneMap[tone] || '平衡'
}

function getDifficultyLabel(difficulty) {
  const difficultyMap = {
    basic: '低难度',
    standard: '中难度',
    challenging: '高难度'
  }
  return difficultyMap[difficulty] || '中难度'
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
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;

  &.is-active {
    background: #111827;
    color: #fff;
  }
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 18px;
}

.create-card,
.profile-card {
  border: 1px solid #e5e7eb;
  border-radius: 20px;
  background: #fff;
  min-height: 220px;
}

.create-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #2563eb;
  cursor: pointer;
}

.create-icon {
  font-size: 28px;
}

.profile-card {
  padding: 18px;
}

.profile-visual {
  width: 100%;
  aspect-ratio: 16 / 10;
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 14px;
  background: #f3f4f6;
}

.profile-image,
.detail-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.profile-card-header,
.profile-card-actions,
.config-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.profile-card-meta,
.profile-card-desc {
  margin-top: 12px;
}

.profile-card-desc {
  color: #6b7280;
  line-height: 1.6;
  min-height: 44px;
}

.detail-visual {
  width: 100%;
  max-width: 360px;
  aspect-ratio: 16 / 10;
  border-radius: 16px;
  overflow: hidden;
  background: #f3f4f6;
  margin-bottom: 16px;
}

.profile-card-actions {
  margin-top: 18px;
}

.weights-grid {
  display: grid;
  gap: 12px;
}

.weight-item {
  display: grid;
  gap: 6px;
}

.weight-label {
  color: #374151;
  font-weight: 500;
}

</style>
