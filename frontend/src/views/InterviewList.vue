<template>
  <div class="interview-list-page">
    <section class="toolbar-card">
      <div>
        <h3>面试列表</h3>
        <p>查看候选人、岗位、状态与时间信息</p>
      </div>
      <el-button type="primary" @click="$router.push('/interview/create')">
        <el-icon><Plus /></el-icon>
        创建面试
      </el-button>
    </section>

    <el-card shadow="never" class="list-card">
      <el-table
        :data="pagedInterviews"
        v-loading="loading"
        stripe
        :header-cell-style="{ textAlign: 'center' }"
        :cell-style="{ textAlign: 'center' }"
      >
        <el-table-column prop="id" label="ID" width="90" />
        <el-table-column prop="candidate_name" label="候选人" min-width="140" />
        <el-table-column prop="position" label="岗位" min-width="180" />
        <el-table-column label="技能" min-width="220">
          <template #default="{ row }">
            <div class="skill-tags">
              <el-tag
                v-for="skill in row.skills || []"
                :key="skill"
                size="small"
                effect="plain"
              >
                {{ skill }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="190">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button text bg @click="viewDetail(row.id)">进入面试</el-button>
            <el-button
              text
              bg
              :disabled="!canViewReport(row)"
              @click="viewReport(row.id)"
            >
              查看报告
            </el-button>
            <el-popconfirm
              v-if="canDelete(row.status)"
              title="确认删除该面试记录？"
              @confirm="handleDelete(row.id)"
            >
              <template #reference>
                <el-button text bg class="danger-btn">删除</el-button>
              </template>
            </el-popconfirm>
            <el-button v-else text bg disabled class="disabled-delete-btn">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && interviews.length > 0" class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="interviews.length"
          :page-sizes="[10, 20, 50]"
        />
      </div>

      <el-empty v-if="!loading && interviews.length === 0" description="暂无面试记录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useInterviewStore } from '@/stores/interview'

const router = useRouter()
const interviewStore = useInterviewStore()

const loading = ref(false)
const interviews = ref([])
const currentPage = ref(1)
const pageSize = ref(10)

const pagedInterviews = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return interviews.value.slice(start, end)
})

onMounted(async () => {
  await loadInterviews()
})

async function loadInterviews() {
  loading.value = true
  try {
    interviews.value = await interviewStore.fetchInterviews()
    ensureCurrentPageValid()
  } finally {
    loading.value = false
  }
}

function viewDetail(id) {
  router.push(`/interviews/${id}`)
}

function viewReport(id) {
  router.push(`/interviews/${id}/report`)
}

async function handleDelete(id) {
  try {
    await interviewStore.deleteInterview(id)
    ElMessage.success('删除成功')
    await loadInterviews()
    ensureCurrentPageValid()
  } catch (error) {
    console.error('删除失败', error)
  }
}

function ensureCurrentPageValid() {
  const total = interviews.value.length
  const maxPage = Math.max(1, Math.ceil(total / pageSize.value))
  if (currentPage.value > maxPage) {
    currentPage.value = maxPage
  }
}

function getStatusType(status) {
  const typeMap = {
    created: 'info',
    in_progress: 'warning',
    completed: 'success',
    cancelled: 'danger'
  }
  return typeMap[status] || 'info'
}

function canDelete(status) {
  return status === 'created' || status === 'completed'
}

function canViewReport(row) {
  return row.status === 'completed' && Boolean(row.expression_report_ready)
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
</script>

<style scoped lang="scss">
.interview-list-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.toolbar-card {
  background: var(--surface-bg);
  border: 1px solid var(--line-color);
  border-radius: var(--radius-lg);
  padding: 16px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  h3 {
    margin: 0;
    font-size: 22px;
    color: var(--text-primary);
  }

  p {
    margin: 6px 0 0;
    font-size: 14px;
    color: var(--text-secondary);
  }
}

.list-card {
  border-radius: var(--radius-lg);
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.danger-btn {
  color: var(--danger-text) !important;
}

.disabled-delete-btn {
  color: #a8b0bd !important;
  cursor: not-allowed;
}

@media (max-width: 720px) {
  .toolbar-card {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
