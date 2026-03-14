<template>
  <div class="learning-resource-test">
    <el-row :gutter="30">
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>📚 学习资源推荐测试</span>
            </div>
          </template>

          <el-form :model="searchForm" label-width="100px">
            <el-form-item label="岗位">
              <el-select v-model="searchForm.position">
                <el-option label="Java后端" value="java_backend" />
                <el-option label="Web前端" value="web_frontend" />
                <el-option label="算法工程师" value="algorithm" />
              </el-select>
            </el-form-item>

            <el-form-item label="用户ID">
              <el-input-number
                v-model="searchForm.user_id"
                :min="1"
                placeholder="可选，按薄弱技能推荐"
              />
            </el-form-item>

            <el-form-item label="标签">
              <el-input v-model="searchForm.tags" placeholder="Redis,分布式" />
            </el-form-item>

            <el-form-item label="资源类型">
              <el-select v-model="searchForm.resource_type" placeholder="不限">
                <el-option label="全部" value="" />
                <el-option label="文章" value="article" />
                <el-option label="视频" value="video" />
                <el-option label="书籍" value="book" />
                <el-option label="项目" value="project" />
              </el-select>
            </el-form-item>

            <el-form-item label="返回数量">
              <el-input-number v-model="searchForm.size" :min="1" :max="10" />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="testRecommend" :loading="loading" size="large">
                {{ loading ? '推荐中...' : '🎯 获取推荐' }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            title="推荐优先级"
            type="info"
            :closable="false"
            show-icon
          >
            ① userId 薄弱技能 → ② tags 标签 → ③ position 兜底
          </el-alert>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>🎖️ 推荐资源</span>
              <el-tag v-if="result" type="success">
                {{ result.resources?.length || 0 }} 个资源
              </el-tag>
            </div>
          </template>

          <div v-if="loading" class="loading-container">
            <el-icon class="is-loading"><Loading /></el-icon>
            <p>正在生成个性化推荐...</p>
          </div>

          <div v-else-if="result && result.resources?.length > 0">
            <div class="resources-grid">
              <div
                v-for="resource in result.resources"
                :key="resource.id"
                class="resource-card"
              >
                <div class="resource-header">
                  <el-tag :type="getTypeColor(resource.type)">
                    {{ getTypeLabel(resource.type) }}
                  </el-tag>
                  <el-rate v-model="resource.difficulty" disabled size="small" />
                </div>

                <h3 class="resource-title">{{ resource.title }}</h3>

                <div class="resource-meta">
                  <el-space wrap>
                    <el-tag
                      v-for="tag in resource.tags"
                      :key="tag"
                      size="small"
                      type="success"
                    >
                      {{ tag }}
                    </el-tag>
                  </el-space>
                </div>

                <p class="resource-description">{{ resource.description }}</p>

                <div class="resource-platform">
                  <el-tag type="info" size="small">{{ resource.platform }}</el-tag>
                </div>

                <div class="resource-actions">
                  <el-button type="primary" size="small" @click="openResource(resource)">
                    🔗 打开链接
                  </el-button>
                  <el-button size="small" @click="copyLink(resource)">
                    📋 复制链接
                  </el-button>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="empty-result">
            <el-empty description="请配置推荐参数并获取推荐" />
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

const searchForm = ref({
  position: 'java_backend',
  user_id: null,
  tags: '',
  resource_type: '',
  size: 5
})

const result = ref(null)
const loading = ref(false)

const testRecommend = async () => {
  loading.value = true

  try {
    const params = new URLSearchParams({
      position: searchForm.value.position,
      size: searchForm.value.size
    })

    if (searchForm.value.user_id) {
      params.append('user_id', searchForm.value.user_id)
    }

    if (searchForm.value.tags && !searchForm.value.user_id) {
      params.append('tags', searchForm.value.tags)
    }

    if (searchForm.value.resource_type) {
      params.append('type', searchForm.value.resource_type)
    }

    const startTime = Date.now()
    const response = await fetch(`/api/test/learning-resource/recommend?${params}`)
    const data = await response.json()
    const endTime = Date.now()

    result.value = data

    addTestResult({
      type: '学习资源推荐',
      status: data.status,
      duration: endTime - startTime,
      summary: data.status === 'success' ? `推荐 ${data.count} 个资源` : '推荐失败',
      details: `岗位: ${searchForm.value.position}`
    })

    if (data.status === 'success') {
      ElMessage.success(`成功推荐 ${data.count} 个学习资源`)
    } else {
      ElMessage.error('推荐失败: ' + (data.message || '未知错误'))
    }
  } catch (error) {
    ElMessage.error('请求失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const getTypeColor = (type) => {
  const colors = {
    video: 'success',
    book: 'warning',
    article: 'primary',
    project: 'danger'
  }
  return colors[type] || 'info'
}

const getTypeLabel = (type) => {
  const labels = {
    video: '视频',
    book: '书籍',
    article: '文章',
    project: '项目'
  }
  return labels[type] || type
}

const openResource = (resource) => {
  window.open(resource.url, '_blank')
}

const copyLink = async (resource) => {
  try {
    await navigator.clipboard.writeText(resource.url)
    ElMessage.success('链接已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}
</script>

<style scoped>
.learning-resource-test {
  padding: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.loading-container {
  text-align: center;
  padding: 40px;
  color: #909399;
}

.resources-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  max-height: 500px;
  overflow-y: auto;
  padding: 10px;
}

.resource-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 20px;
  background: white;
  transition: all 0.3s;
}

.resource-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.resource-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.resource-title {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #303133;
  line-height: 1.4;
  min-height: 44px;
}

.resource-meta {
  margin-bottom: 10px;
  min-height: 30px;
}

.resource-description {
  margin: 10px 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
  min-height: 40px;
}

.resource-platform {
  margin-bottom: 15px;
}

.resource-actions {
  display: flex;
  gap: 10px;
}

.resource-actions .el-button {
  flex: 1;
}

.empty-result {
  text-align: center;
  padding: 60px 20px;
}
</style>
