<template>
  <div class="external-module-test" v-loading="loading">
    <h2 class="page-title">🧪 题库RAG外部模块测试</h2>

    <!-- 服务状态卡片 -->
    <el-row :gutter="20" class="status-row">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="status-card" shadow="never">
          <div class="status-content">
            <div class="status-label">服务状态</div>
            <div class="status-value">
              <el-tag :type="serviceStatus.type" size="large">
                {{ serviceStatus.text }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="status-card" shadow="never">
          <div class="status-content">
            <div class="status-label">接口地址</div>
            <div class="status-value">
              <span class="url-text">{{ externalUrl }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="24" :md="12">
        <el-card class="status-card" shadow="never">
          <div class="status-content">
            <div class="status-label">测试统计</div>
            <div class="status-value">
              <el-statistic-group direction="horizontal">
                <el-statistic title="总测试" :value="testStats.total" />
                <el-statistic title="成功" :value="testStats.success" />
                <el-statistic title="失败" :value="testStats.failed" />
              </el-statistic-group>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 功能标签页 -->
    <el-card class="main-card" shadow="never">
      <el-tabs v-model="activeTab" type="card">
        <!-- 题目检索测试 -->
        <el-tab-pane label="题目检索" name="question">
          <template #label>
            <span>📚 题目检索</span>
          </template>
          <QuestionSearchTest
            @test-result="handleTestResult"
            ref="questionSearchRef"
          />
        </el-tab-pane>

        <!-- 知识检索测试 -->
        <el-tab-pane label="知识检索" name="knowledge">
          <template #label>
            <span>📖 知识检索(RAG)</span>
          </template>
          <KnowledgeSearchTest
            @test-result="handleTestResult"
            ref="knowledgeSearchRef"
          />
        </el-tab-pane>

        <!-- 追问提示测试 -->
        <el-tab-pane label="追问提示" name="followup">
          <template #label>
            <span>❓ 追问提示</span>
          </template>
          <FollowUpTest
            @test-result="handleTestResult"
            ref="followUpRef"
          />
        </el-tab-pane>

        <!-- 学习资源推荐测试 -->
        <el-tab-pane label="学习资源推荐" name="resource">
          <template #label>
            <span>🎓 学习资源推荐</span>
          </template>
          <LearningResourceTest
            @test-result="handleTestResult"
            ref="resourceRef"
          />
        </el-tab-pane>

        <!-- 健康检查 -->
        <el-tab-pane label="健康检查" name="health">
          <template #label>
            <span>🏥 健康检查</span>
          </template>
          <HealthCheck
            @health-update="handleHealthUpdate"
            ref="healthCheckRef"
          />
        </el-tab-pane>

        <!-- 测试历史 -->
        <el-tab-pane label="测试历史" name="history">
          <template #label>
            <span>📋 测试历史</span>
          </template>
          <TestHistory
            :testResults="testResults"
            @clear-history="testResults = []"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import QuestionSearchTest from '@/components/external-test/QuestionSearchTest.vue'
import KnowledgeSearchTest from '@/components/external-test/KnowledgeSearchTest.vue'
import FollowUpTest from '@/components/external-test/FollowUpTest.vue'
import LearningResourceTest from '@/components/external-test/LearningResourceTest.vue'
import HealthCheck from '@/components/external-test/HealthCheck.vue'
import TestHistory from '@/components/external-test/TestHistory.vue'

const activeTab = ref('question')
const externalUrl = ref('http://10.179.224.63:8004')
const serviceStatus = ref({
  type: 'info',
  text: '检查中...'
})

const testResults = ref([])
const loading = ref(false)

const testStats = computed(() => {
  const total = testResults.value.length
  const success = testResults.value.filter(r => r.status === 'success').length
  const failed = testResults.value.filter(r => r.status === 'error').length

  return { total, success, failed }
})

let healthCheckInterval = null

// 检查服务健康状态
const checkServiceHealth = async () => {
  try {
    const response = await fetch('/api/test/question-bank/health')
    const data = await response.json()

    if (data.service_available) {
      serviceStatus.value = {
        type: 'success',
        text: '✅ 服务正常'
      }
      externalUrl.value = data.configuration.service_url
    } else {
      serviceStatus.value = {
        type: 'danger',
        text: '❌ 服务不可用'
      }
    }
  } catch (error) {
    serviceStatus.value = {
      type: 'danger',
      text: '❌ 连接失败'
    }
  }
}

// 处理测试结果
const handleTestResult = (result) => {
  testResults.value.unshift({
    ...result,
    timestamp: new Date().toLocaleString(),
    id: Date.now()
  })
}

// 处理健康更新
const handleHealthUpdate = (healthData) => {
  if (healthData.service_available) {
    serviceStatus.value = {
      type: 'success',
      text: '✅ 服务正常'
    }
    externalUrl.value = healthData.configuration.service_url
  } else {
    serviceStatus.value = {
      type: 'danger',
      text: '❌ 服务不可用'
    }
  }
}

onMounted(() => {
  checkServiceHealth()
  // 每30秒检查一次服务状态
  healthCheckInterval = setInterval(checkServiceHealth, 30000)
})

onUnmounted(() => {
  if (healthCheckInterval) {
    clearInterval(healthCheckInterval)
  }
})
</script>

<style scoped>
.external-module-test {
  padding: 0;
}

.page-title {
  margin: 0 0 20px 0;
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}

.status-row {
  margin-bottom: 20px;
}

.status-card {
  height: 100%;
}

.status-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.status-label {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
}

.status-value {
  display: flex;
  align-items: center;
  min-height: 32px;
}

.url-text {
  font-size: 13px;
  color: var(--text-primary);
  font-family: 'Courier New', monospace;
}

.main-card {
  min-height: 600px;
}

:deep(.el-tabs__header) {
  margin: 0 0 20px 0;
}

:deep(.el-tabs__content) {
  padding: 20px 0;
}

:deep(.el-statistic__head) {
  font-size: 12px;
}

:deep(.el-statistic__content) {
  font-size: 20px;
  font-weight: 600;
}

@media (max-width: 768px) {
  .status-row {
    margin-bottom: 12px;
  }

  .status-card {
    margin-bottom: 12px;
  }

  :deep(.el-statistic-group) {
    flex-direction: column;
    gap: 10px;
  }

  :deep(.el-statistic) {
    text-align: center;
  }
}
</style>
