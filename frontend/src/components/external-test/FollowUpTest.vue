<template>
  <div class="follow-up-test">
    <el-row :gutter="30">
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>❓ 追问提示测试</span>
            </div>
          </template>

          <el-form label-width="100px">
            <el-form-item label="题目ID">
              <el-input-number
                v-model="questionId"
                :min="1"
                :max="1000"
                placeholder="输入题目ID"
              />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="testFollowUp" :loading="loading" size="large">
                {{ loading ? '获取中...' : '🔍 获取追问建议' }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-divider />

          <div class="quick-tests">
            <div class="quick-title">⚡ 快速测试</div>
            <el-space wrap>
              <el-button size="small" @click="testId(1)">题目 #1</el-button>
              <el-button size="small" @click="testId(5)">题目 #5</el-button>
              <el-button size="small" @click="testId(14)">题目 #14</el-button>
              <el-button size="small" @click="testId(27)">题目 #27</el-button>
            </el-space>
          </div>

          <el-alert
            title="追问提示说明"
            type="info"
            :closable="false"
            show-icon
            style="margin-top: 20px"
          >
            追问提示基于题目ID获取，用于引导面试官进行深入提问，挖掘候选人的技术深度。
          </el-alert>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>💡 追问建议</span>
              <el-tag v-if="result" type="success">
                {{ result.hints?.length || 0 }} 个建议
              </el-tag>
            </div>
          </template>

          <div v-if="loading" class="loading-container">
            <el-icon class="is-loading"><Loading /></el-icon>
            <p>正在获取追问建议...</p>
          </div>

          <div v-else-if="result && result.hints && result.hints.length > 0" class="hints-container">
            <div class="result-summary">
              <el-descriptions :column="2" border>
                <el-descriptions-item label="题目ID">
                  <el-tag type="primary">{{ result.question_id }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="建议数量">
                  <el-tag type="success">{{ result.hints.length }} 个</el-tag>
                </el-descriptions-item>
              </el-descriptions>
            </div>

            <el-divider />

            <div class="hints-list">
              <div
                v-for="(hint, index) in result.hints"
                :key="index"
                class="hint-item"
              >
                <div class="hint-number">{{ index + 1 }}</div>
                <div class="hint-content">{{ hint }}</div>
              </div>
            </div>

            <div class="actions">
              <el-space>
                <el-button type="primary" @click="copyHints">
                  📋 复制所有建议
                </el-button>
                <el-button @click="useForInterview">
                  🎯 用于面试指导
                </el-button>
              </el-space>
            </div>
          </div>

          <div v-else-if="result && result.hints?.length === 0" class="empty-result">
            <el-empty description="该题目暂无追问建议" />
          </div>

          <div v-else class="empty-result">
            <el-empty description="请输入题目ID获取追问建议" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, inject } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'

const addTestResult = inject('addTestResult')

const questionId = ref(1)
const result = ref(null)
const loading = ref(false)

const testFollowUp = async () => {
  loading.value = true
  result.value = null

  try {
    const startTime = Date.now()
    const response = await fetch(`/api/test/question-bank/followup/${questionId.value}`)
    const data = await response.json()
    const endTime = Date.now()

    result.value = data

    addTestResult({
      type: '追问提示',
      status: data.status,
      duration: endTime - startTime,
      summary: data.status === 'success' ? `获取到 ${data.count} 个追问建议` : '获取失败',
      details: `题目ID: ${questionId.value}`
    })

    if (data.status === 'success') {
      ElMessage.success(`成功获取 ${data.count} 个追问建议`)
    } else {
      ElMessage.error('获取失败: ' + (data.message || '未知错误'))
    }
  } catch (error) {
    ElMessage.error('请求失败: ' + error.message)
    addTestResult({
      type: '追问提示',
      status: 'error',
      duration: 0,
      summary: '请求失败',
      details: error.message
    })
  } finally {
    loading.value = false
  }
}

const testId = (id) => {
  questionId.value = id
  testFollowUp()
}

const copyHints = () => {
  if (result.value?.hints) {
    const text = result.value.hints.map((h, i) => `${i + 1}. ${h}`).join('\n')
    navigator.clipboard.writeText(text)
    ElMessage.success('已复制所有追问建议')
  }
}

const useForInterview = () => {
  ElMessage.success('追问建议已添加到面试指导')
}
</script>

<style scoped>
.follow-up-test {
  padding: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.quick-tests {
  margin-top: 20px;
}

.quick-title {
  font-size: 14px;
  color: #606266;
  margin-bottom: 10px;
  font-weight: bold;
}

.loading-container {
  text-align: center;
  padding: 40px;
  color: #909399;
}

.hints-container {
  max-height: 500px;
  overflow-y: auto;
}

.result-summary {
  margin-bottom: 20px;
}

.hints-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 20px;
}

.hint-item {
  display: flex;
  align-items: flex-start;
  gap: 15px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 6px;
  border-left: 4px solid #409eff;
}

.hint-number {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  background: #409eff;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

.hint-content {
  flex: 1;
  color: #303133;
  line-height: 1.6;
}

.actions {
  display: flex;
  justify-content: center;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.empty-result {
  text-align: center;
  padding: 60px 20px;
}
</style>
