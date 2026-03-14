<template>
  <div class="health-check">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>🏥 服务健康检查</span>
          <el-button type="primary" @click="checkHealth" :loading="loading">
            {{ loading ? '检查中...' : '🔄 重新检查' }}
          </el-button>
        </div>
      </template>

      <div v-if="healthData">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="适配器状态">
            <el-tag :type="healthData.adapter_status === 'ok' ? 'success' : 'danger'">
              {{ healthData.adapter_status === 'ok' ? '正常' : '异常' }}
            </el-tag>
          </el-descriptions-item>

          <el-descriptions-item label="服务可用性">
            <el-tag :type="healthData.service_available ? 'success' : 'danger'">
              {{ healthData.service_available ? '可用' : '不可用' }}
            </el-tag>
          </el-descriptions-item>

          <el-descriptions-item label="工具名称">
            {{ healthData.configuration?.tool_name }}
          </el-descriptions-item>

          <el-descriptions-item label="缓存时间">
            {{ healthData.configuration?.default_ttl_seconds }} 秒
          </el-descriptions-item>

          <el-descriptions-item label="服务地址" :span="2">
            <el-tag type="info">{{ healthData.configuration?.service_url }}</el-tag>
          </el-descriptions-item>

          <el-descriptions-item label="支持阶段" :span="2">
            <el-space wrap>
              <el-tag
                v-for="stage in healthData.supported_stages"
                :key="stage"
                type="success"
              >
                {{ stage }}
              </el-tag>
            </el-space>
          </el-descriptions-item>

          <el-descriptions-item label="支持触发器" :span="2">
            <el-space wrap>
              <el-tag
                v-for="trigger in healthData.supported_triggers"
                :key="trigger"
                type="warning"
              >
                {{ trigger }}
              </el-tag>
            </el-space>
          </el-descriptions-item>
        </el-descriptions>

        <el-divider />

        <div class="provider-status">
          <h4>提供商配置</h4>
          <pre>{{ JSON.stringify(healthData.provider_status, null, 2) }}</pre>
        </div>
      </div>

      <div v-else class="empty-result">
        <el-empty description="点击上方按钮进行健康检查" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, inject, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const healthData = ref(null)
const loading = ref(false)

const checkHealth = async () => {
  loading.value = true

  try {
    const response = await fetch('/api/test/question-bank/health')
    const data = await response.json()

    healthData.value = data

    if (data.service_available) {
      ElMessage.success('服务健康检查通过')
    } else {
      ElMessage.warning('服务可能存在问题')
    }
  } catch (error) {
    ElMessage.error('健康检查失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  checkHealth()
})
</script>

<style scoped>
.health-check {
  padding: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.provider-status {
  margin-top: 20px;
}

.provider-status h4 {
  margin: 0 0 10px 0;
  color: #303133;
}

.provider-status pre {
  background: #f5f7fa;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 15px;
  font-size: 12px;
  overflow-x: auto;
}

.empty-result {
  text-align: center;
  padding: 60px 20px;
}
</style>
