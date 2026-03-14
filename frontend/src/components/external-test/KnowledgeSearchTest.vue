<template>
  <div class="knowledge-search-test">
    <el-row :gutter="30">
      <!-- 搜索控制面板 -->
      <el-col :span="8">
        <el-card class="control-panel">
          <template #header>
            <div class="card-header">
              <span>📚 知识检索测试 (RAG)</span>
            </div>
          </template>

          <el-form :model="searchForm" label-width="100px">
            <el-form-item label="搜索关键词">
              <el-input
                v-model="searchForm.query"
                placeholder="输入知识点关键词"
                clearable
              />
            </el-form-item>

            <el-form-item label="岗位">
              <el-select v-model="searchForm.position" placeholder="选择岗位">
                <el-option label="Java后端" value="java_backend" />
                <el-option label="Web前端" value="web_frontend" />
                <el-option label="算法工程师" value="algorithm" />
              </el-select>
            </el-form-item>

            <el-form-item label="返回数量">
              <el-input-number v-model="searchForm.size" :min="1" :max="10" />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="testSearch" :loading="loading" size="large">
                {{ loading ? '检索中...' : '🔍 开始检索' }}
              </el-button>
              <el-button @click="resetForm" size="large">重置</el-button>
            </el-form-item>
          </el-form>

          <el-divider />

          <div class="quick-tests">
            <div class="quick-title">⚡ 快速测试</div>
            <el-space wrap>
              <el-button size="small" @click="quickTest('spring')">Spring框架</el-button>
              <el-button size="small" @click="quickTest('redis')">Redis缓存</el-button>
              <el-button size="small" @click="quickTest('jvm')">JVM调优</el-button>
              <el-button size="small" @click="quickTest('distributed')">分布式</el-button>
            </el-space>
          </div>

          <el-divider />

          <div class="info-box">
            <el-alert
              title="RAG知识检索"
              type="info"
              :closable="false"
              show-icon
            >
              <p>知识检索(RAG)用于获取技术知识文档，为LLM提供上下文背景信息。</p>
              <p>• 检索结果包含完整的Markdown内容</p>
              <p>• 支持按岗位限定知识范围</p>
              <p>• 返回相关度最高的文档</p>
            </el-alert>
          </div>
        </el-card>
      </el-col>

      <!-- 结果展示面板 -->
      <el-col :span="16">
        <el-card class="result-panel">
          <template #header>
            <div class="card-header">
              <span>📖 检索结果</span>
              <el-tag v-if="result" :type="result.count > 0 ? 'success' : 'info'">
                {{ result.count }} 个文档
              </el-tag>
            </div>
          </template>

          <div v-if="loading" class="loading-container">
            <el-icon class="is-loading"><Loading /></el-icon>
            <p>正在检索知识文档...</p>
          </div>

          <div v-else-if="result && result.documents && result.documents.length > 0" class="result-container">
            <!-- 检索摘要 -->
            <div class="result-summary">
              <el-descriptions :column="3" border>
                <el-descriptions-item label="查询词">{{ result.query }}</el-descriptions-item>
                <el-descriptions-item label="文档数量">
                  <el-tag type="success">{{ result.count }} 个</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="岗位限定">
                  <el-tag type="info">{{ searchForm.position }}</el-tag>
                </el-descriptions-item>
              </el-descriptions>
            </div>

            <el-divider />

            <!-- 文档列表 -->
            <div class="documents-list">
              <div v-for="(doc, index) in result.documents" :key="doc.id" class="document-item">
                <div class="document-header">
                  <el-tag type="primary">文档 {{ index + 1 }}</el-tag>
                  <h3>{{ doc.title }}</h3>
                </div>

                <div class="document-meta">
                  <el-space>
                    <el-tag v-for="tag in doc.tags" :key="tag" size="small" type="success">
                      {{ tag }}
                    </el-tag>
                  </el-space>
                </div>

                <div class="document-content">
                  <div class="content-preview">
                    <pre>{{ doc.content?.substring(0, 500) }}{{ doc.content?.length > 500 ? '...' : '' }}</pre>
                  </div>
                  <el-button
                    type="primary"
                    size="small"
                    @click="showFullContent(doc)"
                    text
                  >
                    查看完整内容
                  </el-button>
                </div>

                <div class="document-actions">
                  <el-space>
                    <el-button size="small" @click="copyContent(doc)">
                      📋 复制内容
                    </el-button>
                    <el-button size="small" type="success" @click="useForRAG(doc)">
                      🤖 用于RAG上下文
                    </el-button>
                  </el-space>
                </div>
              </div>
            </div>
          </div>

          <div v-else-if="result && result.count === 0" class="empty-result">
            <el-empty description="未找到相关知识文档">
              <template #image>
                <el-icon :size="100"><DocumentDelete /></el-icon>
              </template>
              <p>请尝试其他关键词或联系管理员添加相关知识文档</p>
            </el-empty>
          </div>

          <div v-else class="empty-result">
            <el-empty description="请输入关键词并开始检索" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 完整内容对话框 -->
    <el-dialog v-model="dialogVisible" title="完整文档内容" width="60%" top="5vh">
      <div class="full-content">
        <pre>{{ currentDocument?.content }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, inject } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, DocumentDelete } from '@element-plus/icons-vue'

const addTestResult = inject('addTestResult')

const searchForm = ref({
  query: '',
  position: 'java_backend',
  size: 3
})

const result = ref(null)
const loading = ref(false)
const dialogVisible = ref(false)
const currentDocument = ref(null)

const testSearch = async () => {
  if (!searchForm.value.query.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }

  loading.value = true
  result.value = null

  try {
    const params = new URLSearchParams({
      query: searchForm.value.query,
      position: searchForm.value.position,
      size: searchForm.value.size
    })

    const startTime = Date.now()
    const response = await fetch(`/api/test/question-bank/knowledge/search?${params}`)
    const data = await response.json()
    const endTime = Date.now()

    result.value = data

    // 添加到测试历史
    addTestResult({
      type: '知识检索',
      status: data.status,
      duration: endTime - startTime,
      summary: data.status === 'success' ? `检索到 ${data.count} 个文档` : '检索失败',
      details: `关键词: ${searchForm.value.query}`
    })

    if (data.status === 'success') {
      if (data.count > 0) {
        ElMessage.success(`成功检索到 ${data.count} 个知识文档`)
      } else {
        ElMessage.info('未找到相关知识文档')
      }
    } else {
      ElMessage.error('检索失败: ' + (data.message || '未知错误'))
    }
  } catch (error) {
    ElMessage.error('请求失败: ' + error.message)
    addTestResult({
      type: '知识检索',
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
    query: '',
    position: 'java_backend',
    size: 3
  }
  result.value = null
}

const quickTest = (keyword) => {
  searchForm.value.query = keyword
  testSearch()
}

const showFullContent = (doc) => {
  currentDocument.value = doc
  dialogVisible.value = true
}

const copyContent = async (doc) => {
  try {
    await navigator.clipboard.writeText(doc.content)
    ElMessage.success('内容已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败: ' + error.message)
  }
}

const useForRAG = (doc) => {
  ElMessage.success(`已将文档"${doc.title}"添加到RAG上下文`)
  // 这里可以触发实际的RAG上下文更新逻辑
}
</script>

<style scoped>
.knowledge-search-test {
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

.info-box {
  margin-top: 20px;
}

.info-box p {
  margin: 5px 0;
  font-size: 13px;
  color: #606266;
}

.loading-container {
  text-align: center;
  padding: 40px;
  color: #909399;
}

.loading-container .el-icon {
  font-size: 48px;
  color: #409eff;
}

.result-container {
  max-height: 600px;
  overflow-y: auto;
}

.result-summary {
  margin-bottom: 20px;
}

.documents-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.document-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 20px;
  background: #fafafa;
  transition: all 0.3s;
}

.document-item:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.document-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
}

.document-header h3 {
  margin: 0;
  color: #303133;
  font-size: 16px;
}

.document-meta {
  margin-bottom: 15px;
}

.document-content {
  margin-bottom: 15px;
}

.content-preview {
  background: white;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 15px;
  margin-bottom: 10px;
}

.content-preview pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #606266;
}

.document-actions {
  display: flex;
  justify-content: flex-end;
}

.full-content {
  max-height: 70vh;
  overflow-y: auto;
}

.full-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #303133;
}

.empty-result {
  text-align: center;
  padding: 60px 20px;
}
</style>
