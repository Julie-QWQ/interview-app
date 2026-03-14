<template>
  <div class="dashboard-page">
    <section class="dashboard-hero">
      <div>
        <h1>面试仪表盘</h1>
        <p>集中查看面试总览、执行状态和最近动态</p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" @click="$router.push('/interview/create')">
          <el-icon><Plus /></el-icon>
          新建面试
        </el-button>
        <el-button @click="$router.push('/interviews')">
          <el-icon><List /></el-icon>
          全部面试
        </el-button>
      </div>
    </section>

    <section class="kpi-grid">
      <article class="kpi-card">
        <div class="kpi-head">
          <span>总面试数</span>
          <el-icon><ChatDotRound /></el-icon>
        </div>
        <div class="kpi-value">{{ stats.total }}</div>
      </article>

      <article class="kpi-card">
        <div class="kpi-head">
          <span>待开始</span>
          <el-icon><DocumentChecked /></el-icon>
        </div>
        <div class="kpi-value">{{ stats.created }}</div>
      </article>

      <article class="kpi-card">
        <div class="kpi-head">
          <span>进行中</span>
          <el-icon><VideoPlay /></el-icon>
        </div>
        <div class="kpi-value">{{ stats.inProgress }}</div>
      </article>

      <article class="kpi-card">
        <div class="kpi-head">
          <span>完成率</span>
          <el-icon><TrendCharts /></el-icon>
        </div>
        <div class="kpi-value">{{ completionRate }}%</div>
      </article>
    </section>

    <section class="dashboard-main">
      <el-card shadow="never" class="panel status-panel">
        <template #header>
          <div class="panel-header">
            <span>状态分布</span>
          </div>
        </template>

        <div class="status-item">
          <span>待开始</span>
          <el-progress :percentage="statusPercent.created" :show-text="false" />
          <strong>{{ stats.created }}</strong>
        </div>

        <div class="status-item">
          <span>进行中</span>
          <el-progress status="warning" :percentage="statusPercent.inProgress" :show-text="false" />
          <strong>{{ stats.inProgress }}</strong>
        </div>

        <div class="status-item">
          <span>已完成</span>
          <el-progress status="success" :percentage="statusPercent.completed" :show-text="false" />
          <strong>{{ stats.completed }}</strong>
        </div>

        <div class="status-item">
          <span>已取消</span>
          <el-progress status="exception" :percentage="statusPercent.cancelled" :show-text="false" />
          <strong>{{ stats.cancelled }}</strong>
        </div>
      </el-card>

      <el-card shadow="never" class="panel quick-panel">
        <template #header>
          <div class="panel-header">
            <span>快捷入口</span>
          </div>
        </template>

        <button class="quick-link" @click="$router.push('/interview/create')">
          <span>
            <el-icon><Plus /></el-icon>
            新建面试
          </span>
          <el-icon><ArrowRight /></el-icon>
        </button>

        <button class="quick-link" @click="$router.push('/interviews')">
          <span>
            <el-icon><List /></el-icon>
            面试列表
          </span>
          <el-icon><ArrowRight /></el-icon>
        </button>

        <button class="quick-link" @click="$router.push('/admin/prompts')">
          <span>
            <el-icon><Setting /></el-icon>
            Prompt 配置
          </span>
          <el-icon><ArrowRight /></el-icon>
        </button>

        <button class="quick-link" @click="$router.push('/admin/tools')">
          <span>
            <el-icon><Setting /></el-icon>
            工具配置
          </span>
          <el-icon><ArrowRight /></el-icon>
        </button>

        <button class="quick-link" @click="$router.push('/admin/stages')">
          <span>
            <el-icon><Setting /></el-icon>
            阶段配置
          </span>
          <el-icon><ArrowRight /></el-icon>
        </button>
      </el-card>
    </section>

    <el-card shadow="never" class="panel recent-panel">
      <template #header>
        <div class="panel-header">
          <span>最近面试</span>
          <el-button link type="primary" @click="$router.push('/interviews')">查看全部</el-button>
        </div>
      </template>

      <el-table
        :data="recentInterviews"
        v-loading="loading"
        stripe
        :header-cell-style="{ textAlign: 'center' }"
        :cell-style="{ textAlign: 'center' }"
      >
        <el-table-column prop="candidate_name" label="候选人" min-width="140" />
        <el-table-column prop="position" label="职位" min-width="180" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="170">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button text bg @click="viewDetail(row.id)">进入面试</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && recentInterviews.length === 0" description="暂无面试记录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, List, ChatDotRound, DocumentChecked, TrendCharts, Setting, VideoPlay, ArrowRight } from '@element-plus/icons-vue'
import { useInterviewStore } from '@/stores/interview'

const router = useRouter()
const interviewStore = useInterviewStore()

const loading = ref(false)
const interviews = ref([])

const stats = computed(() => {
  const total = interviews.value.length
  const created = interviews.value.filter(i => i.status === 'created').length
  const inProgress = interviews.value.filter(i => i.status === 'in_progress').length
  const completed = interviews.value.filter(i => i.status === 'completed').length
  const cancelled = interviews.value.filter(i => i.status === 'cancelled').length

  return {
    total,
    created,
    inProgress,
    completed,
    cancelled
  }
})

const completionRate = computed(() => {
  if (!stats.value.total) return 0
  return Math.round((stats.value.completed / stats.value.total) * 100)
})

const statusPercent = computed(() => {
  const total = stats.value.total || 1
  return {
    created: Math.round((stats.value.created / total) * 100),
    inProgress: Math.round((stats.value.inProgress / total) * 100),
    completed: Math.round((stats.value.completed / total) * 100),
    cancelled: Math.round((stats.value.cancelled / total) * 100)
  }
})

const recentInterviews = computed(() => interviews.value.slice(0, 6))

onMounted(async () => {
  loading.value = true
  try {
    interviews.value = await interviewStore.fetchInterviews()
  } catch (error) {
    console.error('获取首页数据失败', error)
  } finally {
    loading.value = false
  }
})

function getStatusType(status) {
  const typeMap = {
    created: 'info',
    in_progress: 'warning',
    completed: 'success',
    cancelled: 'danger'
  }
  return typeMap[status] || 'info'
}

function getStatusText(status) {
  const textMap = {
    created: '待开始',
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消'
  }
  return textMap[status] || status
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

function viewDetail(id) {
  router.push(`/interviews/${id}`)
}
</script>

<style scoped lang="scss">
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dashboard-hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: linear-gradient(135deg, #ffffff 0%, #f3f8ff 100%);

  h1 {
    margin: 0;
    font-size: 24px;
    color: var(--text-primary);
  }

  p {
    margin: 8px 0 0;
    color: var(--text-secondary);
  }
}

.hero-actions {
  display: flex;
  gap: 8px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.kpi-card {
  background: #ffffff;
  border: 1px solid #d6dde8;
  border-radius: 14px;
  padding: 16px;
  box-shadow: 0 4px 12px rgba(16, 24, 40, 0.06);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;

  &:hover {
    transform: translateY(-2px);
    border-color: #bfcadb;
    box-shadow: 0 10px 24px rgba(16, 24, 40, 0.1);
  }

  .kpi-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #667085;
    font-size: 14px;
  }

  .kpi-value {
    margin-top: 10px;
    font-size: 40px;
    line-height: 1.1;
    font-weight: 700;
    color: #1e3a8a;
  }
}

.dashboard-main {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 12px;
}

.panel {
  border-radius: 10px;
  border: 1px solid var(--border-color);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.status-panel {
  display: flex;
  flex-direction: column;

  :deep(.el-card__body) {
    flex: 1;
    min-height: 180px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .status-item {
    display: grid;
    grid-template-columns: 74px 1fr 42px;
    align-items: center;
    gap: 10px;

    span {
      color: var(--text-secondary);
      font-size: 14px;
    }

    strong {
      text-align: right;
      color: var(--text-primary);
      font-size: 14px;
      font-weight: 600;
    }
  }
}

.quick-panel {
  display: flex;
  flex-direction: column;
}

.quick-link {
  width: 100%;
  border: 1px solid var(--border-color);
  background: #fff;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-primary);
  cursor: pointer;
  transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease;

  span {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }

  &:hover {
    background: #f1f3f5;
  }

  &:last-child {
    margin-bottom: 0;
  }

  &.external-test-link {
    border-color: #67c23a;
    background: linear-gradient(135deg, #f0f9ff 0%, #e6f7ff 100%);

    &:hover {
      border-color: #85ce61;
      background: linear-gradient(135deg, #e6f7ff 0%, #d6f4ff 100%);
    }
  }
}

@media (max-width: 992px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard-main {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .dashboard-hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-actions {
    width: 100%;

    .el-button {
      flex: 1;
    }
  }
}
</style>
