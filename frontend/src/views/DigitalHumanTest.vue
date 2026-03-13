<template>
  <div class="digital-human-test">
    <el-container>
      <el-header>
        <h1>讯飞数字人测试页面</h1>
      </el-header>

      <el-main>
        <el-card class="config-card">
          <template #header>
            <div class="card-header">
              <span>配置信息</span>
              <el-button type="primary" @click="initSession" :loading="loading">
                初始化会话
              </el-button>
            </div>
          </template>

          <el-form label-width="120px">
            <el-form-item label="Session ID">
              <el-input v-model="sessionId" disabled />
            </el-form-item>

            <el-form-item label="Avatar ID">
              <el-input v-model="config.avatarId" disabled />
            </el-form-item>

            <el-form-item label="App ID">
              <el-input v-model="config.appId" show-password />
            </el-form-item>

            <el-form-item label="API Key">
              <el-input v-model="config.apiKey" show-password />
            </el-form-item>

            <el-form-item label="API Secret">
              <el-input v-model="config.apiSecret" show-password />
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="video-card" v-if="sessionId">
          <template #header>
            <div class="card-header">
              <span>数字人视频</span>
              <el-tag :type="isReady ? 'success' : 'info'">
                {{ isReady ? '已就绪' : '未就绪' }}
              </el-tag>
            </div>
          </template>

          <XunfeiDigitalHuman
            :session-id="sessionId"
            :config="config"
            :auto-start="true"
            @ready="handleReady"
            @error="handleError"
            @status-change="handleStatusChange"
            class="digital-human"
          />
        </el-card>

        <el-card class="control-card" v-if="isReady">
          <template #header>
            <span>控制面板</span>
          </template>

          <el-space direction="vertical" style="width: 100%">
            <el-alert
              :title="statusText"
              :type="statusType"
              :closable="false"
              show-icon
            />

            <el-button @click="interrupt" type="warning" :disabled="status !== 'SPEAKING'">
              打断播报
            </el-button>
          </el-space>
        </el-card>

        <el-card class="log-card">
          <template #header>
            <div class="card-header">
              <span>日志</span>
              <el-button size="small" @click="clearLogs">清空</el-button>
            </div>
          </template>

          <div class="log-container">
            <div v-for="(log, index) in logs" :key="index" :class="['log-entry', `log-${log.type}`]">
              <span class="log-time">{{ log.time }}</span>
              <span class="log-message">{{ log.message }}</span>
            </div>
          </div>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import XunfeiDigitalHuman from '@/components/XunfeiDigitalHuman.vue'

const sessionId = ref(null)
const config = ref({
  appId: '',
  apiKey: '',
  apiSecret: '',
  avatarId: 'xiaofeng',
  sampleRate: 16000
})

const loading = ref(false)
const isReady = ref(false)
const status = ref('LISTENING')
const logs = ref([])

function addLog(message, type = 'info') {
  const time = new Date().toLocaleTimeString()
  logs.value.push({ time, message, type })
  console.log(`[DigitalHumanTest] ${message}`)
}

function clearLogs() {
  logs.value = []
}

async function initSession() {
  loading.value = true
  addLog('开始初始化数字人会话...')

  try {
    const response = await fetch('http://localhost:8000/api/test/avatar-session', {
      method: 'POST'
    })

    const data = await response.json()

    if (data.success) {
      sessionId.value = data.session_id
      config.value = {
        ...config.value,
        ...data.config
      }
      addLog(`会话初始化成功: ${data.session_id}`, 'success')
      addLog(`Avatar ID: ${data.avatar_id}`, 'info')
    } else {
      addLog(`会话初始化失败: ${data.error}`, 'error')
    }
  } catch (error) {
    addLog(`请求失败: ${error.message}`, 'error')
  } finally {
    loading.value = false
  }
}

function handleReady() {
  isReady.value = true
  addLog('数字人已就绪', 'success')
}

function handleError(error) {
  addLog(`错误: ${error.message || error}`, 'error')
}

function handleStatusChange(newStatus) {
  status.value = newStatus
  addLog(`状态变化: ${newStatus}`, 'info')
}

async function interrupt() {
  addLog('正在打断播报...', 'warning')
  // 组件的 interrupt 方法会通过 ref 调用
}

const statusText = ref('倾听中')
const statusType = ref('info')

onMounted(() => {
  addLog('测试页面已加载', 'info')
  addLog('点击"初始化会话"按钮开始测试', 'info')
})
</script>

<style scoped>
.digital-human-test {
  min-height: 100vh;
  background: #f5f7fa;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-card,
.video-card,
.control-card,
.log-card {
  margin-bottom: 20px;
}

.digital-human {
  width: 100%;
  height: 400px;
  background: #000;
  border-radius: 4px;
}

.log-container {
  max-height: 300px;
  overflow-y: auto;
  background: #1e1e1e;
  padding: 12px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
}

.log-entry {
  display: flex;
  margin-bottom: 8px;
  line-height: 1.6;
}

.log-time {
  color: #858585;
  margin-right: 12px;
  flex-shrink: 0;
}

.log-message {
  flex: 1;
}

.log-info {
  color: #4fc3f7;
}

.log-success {
  color: #81c784;
}

.log-error {
  color: #e57373;
}

.log-warning {
  color: #ffb74d;
}
</style>
