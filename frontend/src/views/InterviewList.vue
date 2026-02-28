<template>
  <div class="interview-list">
    <div class="list-header">
      <h2>面试列表</h2>
      <el-button type="primary" @click="$router.push('/interview/create')">
        <el-icon><Plus /></el-icon>
        创建面试
      </el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="interviews" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="candidate_name" label="候选人" width="150" />
        <el-table-column prop="position" label="职位" width="200" />
        <el-table-column label="技能" min-width="200">
          <template #default="{ row }">
            <el-tag v-for="skill in row.skills" :key="skill" size="small" style="margin-right: 4px; margin-bottom: 4px;">
              {{ skill }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewDetail(row.id)">查看</el-button>
            <el-popconfirm
              v-if="row.status === 'created' || row.status === 'completed'"
              title="确定删除此面试？"
              @confirm="handleDelete(row.id)"
            >
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && interviews.length === 0" description="暂无面试记录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useInterviewStore } from '@/stores/interview'

const router = useRouter()
const interviewStore = useInterviewStore()

const loading = ref(false)
const interviews = ref([])

onMounted(async () => {
  await loadInterviews()
})

async function loadInterviews() {
  loading.value = true
  try {
    interviews.value = await interviewStore.fetchInterviews()
  } finally {
    loading.value = false
  }
}

function viewDetail(id) {
  router.push(`/interviews/${id}`)
}

async function handleDelete(id) {
  try {
    await interviewStore.deleteInterview(id)
    ElMessage.success('删除成功')
    await loadInterviews()
  } catch (error) {
    console.error('删除失败', error)
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

function getStatusText(status) {
  const textMap = {
    created: '已创建',
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消'
  }
  return textMap[status] || status
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}
</script>

<style scoped lang="scss">
.interview-list {
  max-width: 1200px;
  margin: 0 auto;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  h2 {
    margin: 0;
    font-size: 24px;
  }
}
</style>
