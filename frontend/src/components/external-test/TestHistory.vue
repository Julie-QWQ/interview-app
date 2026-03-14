<template>
  <div class="test-history">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>📜 测试历史记录</span>
          <el-button type="danger" @click="clearHistory" :disabled="testResults.length === 0">
            🗑️ 清空记录
          </el-button>
        </div>
      </template>

      <div v-if="testResults.length > 0">
        <el-table :data="testResults" stripe style="width: 100%">
          <el-table-column prop="timestamp" label="时间" width="180" />

          <el-table-column prop="type" label="测试类型" width="150">
            <template #default="scope">
              <el-tag :type="getTypeColor(scope.row.type)">
                {{ scope.row.type }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag :type="scope.row.status === 'success' ? 'success' : 'danger'">
                {{ scope.row.status === 'success' ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="duration" label="耗时" width="100">
            <template #default="scope">
              {{ scope.row.duration }} ms
            </template>
          </el-table-column>

          <el-table-column prop="summary" label="摘要" show-overflow-tooltip />

          <el-table-column prop="details" label="详情" show-overflow-tooltip />

          <el-table-column label="操作" width="100" fixed="right">
            <template #default="scope">
              <el-button
                type="primary"
                size="small"
                @click="viewDetail(scope.row)"
                text
              >
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="statistics">
          <el-divider />
          <el-row :gutter="20">
            <el-col :span="6">
              <el-statistic title="总测试次数" :value="testResults.length" />
            </el-col>
            <el-col :span="6">
              <el-statistic
                title="成功次数"
                :value="successCount"
                suffix="次"
              >
                <template #prefix>
                  <el-icon color="#67c23a"><SuccessFilled /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="6">
              <el-statistic title="失败次数" :value="failCount">
                <template #prefix>
                  <el-icon color="#f56c6c"><CircleCloseFilled /></el-icon>
                </template>
              </el-statistic>
            </el-col>
            <el-col :span="6">
              <el-statistic
                title="平均响应时间"
                :value="averageDuration"
                suffix="ms"
              />
            </el-col>
          </el-row>
        </div>
      </div>

      <div v-else class="empty-result">
        <el-empty description="暂无测试记录">
          <template #image>
            <el-icon :size="100"><Document /></el-icon>
          </template>
        </el-empty>
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="测试详情" width="50%">
      <div v-if="currentDetail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="测试时间">
            {{ currentDetail.timestamp }}
          </el-descriptions-item>
          <el-descriptions-item label="测试类型">
            <el-tag :type="getTypeColor(currentDetail.type)">
              {{ currentDetail.type }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="测试状态">
            <el-tag :type="currentDetail.status === 'success' ? 'success' : 'danger'">
              {{ currentDetail.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="响应时间">
            {{ currentDetail.duration }} ms
          </el-descriptions-item>
          <el-descriptions-item label="测试摘要">
            {{ currentDetail.summary }}
          </el-descriptions-item>
          <el-descriptions-item label="详细信息">
            {{ currentDetail.details }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { SuccessFilled, CircleCloseFilled, Document } from '@element-plus/icons-vue'

const props = defineProps({
  testResults: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['clear-history'])

const detailDialogVisible = ref(false)
const currentDetail = ref(null)

const successCount = computed(() =>
  props.testResults.filter(r => r.status === 'success').length
)

const failCount = computed(() =>
  props.testResults.filter(r => r.status === 'error').length
)

const averageDuration = computed(() => {
  if (props.testResults.length === 0) return 0
  const total = props.testResults.reduce((sum, r) => sum + (r.duration || 0), 0)
  return Math.round(total / props.testResults.length)
})

const getTypeColor = (type) => {
  const colors = {
    '题目检索': 'primary',
    '知识检索': 'success',
    '追问提示': 'warning',
    '学习资源推荐': 'danger'
  }
  return colors[type] || 'info'
}

const viewDetail = (row) => {
  currentDetail.value = row
  detailDialogVisible.value = true
}

const clearHistory = () => {
  emit('clear-history')
  ElMessage.success('测试历史已清空')
}
</script>

<style scoped>
.test-history {
  padding: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.statistics {
  margin-top: 20px;
}

.empty-result {
  text-align: center;
  padding: 60px 20px;
}
</style>
