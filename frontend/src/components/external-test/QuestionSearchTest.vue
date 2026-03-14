<template>
  <div class="question-search-test">
    <el-row :gutter="20">
      <!-- 测试控制面板 -->
      <el-col :xs="24" :md="10">
        <el-card class="control-panel" shadow="never">
          <template #header>
            <div class="panel-header">
              <span>🔍 题目检索配置</span>
            </div>
          </template>

          <el-form :model="searchForm" label-position="top" label-width="100px">
            <el-form-item label="岗位">
              <el-select v-model="searchForm.position" placeholder="选择岗位" style="width: 100%">
                <el-option label="Java后端" value="java_backend" />
                <el-option label="Web前端" value="web_frontend" />
                <el-option label="算法工程师" value="algorithm" />
              </el-select>
            </el-form-item>

            <el-form-item label="题目类型">
              <el-select v-model="searchForm.type" placeholder="选择类型" style="width: 100%">
                <el-option label="技术题" value="technical" />
                <el-option label="行为题" value="behavioral" />
                <el-option label="项目题" value="project" />
                <el-option label="场景题" value="scenario" />
              </el-select>
            </el-form-item>

            <el-form-item label="难度">
              <el-slider v-model="searchForm.difficulty" :min="1" :max="5" show-stops />
            </el-form-item>

            <el-form-item label="标签">
              <el-input v-model="searchForm.tags" placeholder="Spring,Redis (逗号分隔)" />
            </el-form-item>

            <el-form-item label="语义搜索">
              <el-input v-model="searchForm.query" placeholder="输入关键词启用FAISS检索" clearable />
            </el-form-item>

            <el-form-item label="排除ID">
              <el-input v-model="searchForm.excludeIds" placeholder="1,2,3 (已出题目ID)" />
            </el-form-item>

            <el-form-item label="返回数量">
              <el-input-number v-model="searchForm.size" :min="1" :max="20" style="width: 100%" />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="testSearch" :loading="loading" style="width: 100%">
                {{ loading ? '检索中...' : '🚀 开始检索' }}
              </el-button>
              <el-button @click="resetForm" style="width: 100%; margin-top: 10px">
                重置
              </el-button>
            </el-form-item>
          </el-form>

          <el-divider />

          <div class="quick-tests">
            <div class="quick-title">⚡ 快速测试</div>
            <el-space wrap>
              <el-button size="small" @click="quickTest('basic')">基础检索</el-button>
              <el-button size="small" @click="quickTest('semantic')">语义搜索</el-button>
              <el-button size="small" @click="quickTest('advanced')">高级筛选</el-button>
              <el-button size="small" @click="quickTest('exclude')">排除重复</el-button>
            </el-space>
          </div>
        </el-card>
      </el-col>

      <!-- 结果展示面板 -->
      <el-col :xs="24" :md="14">
        <el-card class="result-panel" shadow="never">
          <template #header>
            <div class="panel-header">
              <span>📊 检索结果</span>
              <el-tag v-if="result" :type="result.status === 'success' ? 'success' : 'danger'">
                {{ result.status === 'success' ? '成功' : '失败' }}
              </el-tag>
            </div>
          </template>

          <div v-if="loading" class="loading-container">
            <el-icon class="is-loading"><Loading /></el-icon>
            <p>正在检索题目...</p>
          </div>

          <div v-else-if="result" class="result-container">
            <!-- 检索摘要 -->
            <div class="result-summary">
              <el-descriptions :column="2" border>
                <el-descriptions-item label="状态">
                  <el-tag :type="result.status === 'success' ? 'success' : 'danger'">
                    {{ result.status === 'success' ? '成功' : '失败' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="题目数量">
                  <el-tag type="info">{{ result.count || 0 }} 道</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="响应时间">
                  <el-tag type="warning">{{ result.meta?.latency_ms || 0 }} ms</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="检索类型">
                  <el-tag v-if="searchForm.query" type="success">FAISS语义检索</el-tag>
                  <el-tag v-else type="info">标签筛选</el-tag>
                </el-descriptions-item>
              </el-descriptions>
            </div>

            <el-divider />

            <!-- 题目列表 -->
            <div v-if="result.questions && result.questions.length > 0" class="questions-list">
              <div v-for="(question, index) in result.questions" :key="question.id" class="question-item">
                <div class="question-header">
                  <el-tag type="primary">Q{{ question.id }}</el-tag>
                  <el-tag type="info">{{ question.code }}</el-tag>
                  <el-tag>{{ question.category }}</el-tag>
                  <el-rate v-model="question.difficulty" disabled show-score />
                </div>
                <div class="question-text">
                  <h4>{{ question.text }}</h4>
                </div>
                <div class="question-details">
                  <div class="detail-item">
                    <strong>💡 关键点:</strong>
                    <el-tag v-for="point in question.keyPoints" :key="point" size="small" class="tag-item">
                      {{ point }}
                    </el-tag>
                  </div>
                  <div class="detail-item">
                    <strong>🏷️ 标签:</strong>
                    <el-tag v-for="tag in question.tags" :key="tag" size="small" type="success" class="tag-item">
                      {{ tag }}
                    </el-tag>
                  </div>
                  <div v-if="question.followUpHints && question.followUpHints.length" class="detail-item">
                    <strong>❓ 追问建议:</strong>
                    <ul class="hints-list">
                      <li v-for="hint in question.followUpHints" :key="hint">{{ hint }}</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            <div v-else class="empty-result">
              <el-empty description="未找到相关题目" />
            </div>
          </div>

          <div v-else class="empty-result">
            <el-empty description="请配置检索参数并点击开始检索" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'

const emit = defineEmits(['test-result'])

const searchForm = ref({
  position: 'java_backend',
  type: 'technical',
  difficulty: 3,
  tags: '',
  query: '',
  excludeIds: '',
  size: 5
})

const result = ref(null)
const loading = ref(false)

const testSearch = async () => {
  loading.value = true
  result.value = null

  try {
    const payload = {
      position: searchForm.value.position,
      type: searchForm.value.type,
      difficulty: searchForm.value.difficulty,
      size: searchForm.value.size
    }

    if (searchForm.value.tags) {
      payload.tags = searchForm.value.tags
    }

    if (searchForm.value.query) {
      payload.query = searchForm.value.query
    }

    if (searchForm.value.excludeIds) {
      payload.excludeIds = searchForm.value.excludeIds
    }

    const startTime = Date.now()
    const response = await fetch('/api/test/question-bank/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    const data = await response.json()
    const endTime = Date.now()

    result.value = data

    emit('test-result', {
      type: '题目检索',
      status: data.status,
      duration: endTime - startTime,
      summary: data.summary,
      details: `检索到 ${data.count || 0} 道题目`
    })

    if (data.status === 'success') {
      ElMessage.success(`成功检索到 ${data.count} 道题目`)
    } else {
      ElMessage.error('检索失败: ' + (data.errors?.join(', ') || '未知错误'))
    }
  } catch (error) {
    ElMessage.error('请求失败: ' + error.message)
    emit('test-result', {
      type: '题目检索',
      status: 'error',
      duration: 0,
      summary: '请求失败',
      details: error.message
    })
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  searchForm.value = {
    position: 'java_backend',
    type: 'technical',
    difficulty: 3,
    tags: '',
    query: '',
    excludeIds: '',
    size: 5
  }
  result.value = null
}

const quickTest = (type) => {
  resetForm()

  switch (type) {
    case 'basic':
      searchForm.value = { ...searchForm.value, size: 3 }
      break
    case 'semantic':
      searchForm.value = { ...searchForm.value, query: '分布式', size: 2 }
      break
    case 'advanced':
      searchForm.value = {
        ...searchForm.value,
        tags: 'Spring,Redis',
        difficulty: 4,
        size: 3
      }
      break
    case 'exclude':
      searchForm.value = {
        ...searchForm.value,
        excludeIds: '1,2,3',
        size: 5
      }
      break
  }

  testSearch()
}
</script>

<style scoped>
.question-search-test {
  padding: 10px;
}

.control-panel, .result-panel {
  height: 100%;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: var(--text-primary);
}

.quick-tests {
  margin-top: 20px;
}

.quick-title {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 10px;
  font-weight: 500;
}

.loading-container {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}

.loading-container .el-icon {
  font-size: 48px;
  color: var(--el-color-primary);
}

.result-container {
  max-height: 500px;
  overflow-y: auto;
}

.result-summary {
  margin-bottom: 20px;
}

.questions-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.question-item {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  background: var(--el-bg-color);
  transition: all 0.3s;
}

.question-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-color: var(--el-color-primary);
}

.question-header {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.question-text h4 {
  margin: 0 0 12px 0;
  color: var(--text-primary);
  font-size: 16px;
  line-height: 1.6;
}

.question-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-item {
  font-size: 14px;
  color: var(--text-secondary);
}

.detail-item strong {
  margin-right: 8px;
  color: var(--text-primary);
}

.tag-item {
  margin-right: 4px;
  margin-bottom: 4px;
}

.hints-list {
  margin: 4px 0 0 20px;
  padding: 0;
}

.hints-list li {
  margin-bottom: 4px;
  color: var(--text-secondary);
}

.empty-result {
  text-align: center;
  padding: 40px 20px;
}

@media (max-width: 768px) {
  .question-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
