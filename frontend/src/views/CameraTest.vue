<template>
  <div class="camera-test-page">
    <div class="test-header">
      <h1>🎥 摄像头功能测试</h1>
      <p>用于测试 UserCamera 组件的各项功能</p>
    </div>

    <div class="test-content">
      <el-card class="test-card">
        <template #header>
          <div class="card-header">
            <span>摄像头组件</span>
            <el-tag :type="cameraActive ? 'success' : 'info'">
              {{ cameraActive ? '运行中' : '未启动' }}
            </el-tag>
          </div>
        </template>

        <div class="camera-wrapper">
          <UserCamera
            ref="cameraRef"
            :auto-start="false"
            :is-recording="isRecording"
            @camera-started="handleCameraStarted"
            @camera-stopped="handleCameraStopped"
            @camera-error="handleCameraError"
          />
        </div>
      </el-card>

      <el-card class="controls-card">
        <template #header>
          <div class="card-header">
            <span>控制面板</span>
            <el-button
              type="warning"
              size="small"
              @click="runDiagnostics"
            >
              <el-icon><TrendCharts /></el-icon>
              诊断问题
            </el-button>
          </div>
        </template>

        <div class="control-section">
          <h3>基础控制</h3>
          <div class="button-group">
            <el-button
              type="primary"
              @click="startCamera"
              :loading="isStarting"
              :disabled="cameraActive"
            >
              <el-icon><VideoPlay /></el-icon>
              启动摄像头
            </el-button>
            <el-button
              type="danger"
              @click="stopCamera"
              :disabled="!cameraActive"
            >
              <el-icon><SwitchButton /></el-icon>
              停止摄像头
            </el-button>
          </div>
        </div>

        <el-divider />

        <div class="control-section">
          <h3>录制测试</h3>
          <div class="button-group">
            <el-button
              :type="isRecording ? 'danger' : 'success'"
              @click="toggleRecording"
              :disabled="!cameraActive"
            >
              <el-icon><component :is="isRecording ? VideoPause : VideoPlay" /></el-icon>
              {{ isRecording ? '停止录制' : '开始录制' }}
            </el-button>
          </div>
          <p class="hint">录制状态会在摄像头画面上显示红色指示器</p>
        </div>

        <el-divider />

        <div class="control-section">
          <h3>高级功能</h3>
          <div class="button-group">
            <el-button
              @click="toggleMirror"
              :disabled="!cameraActive"
            >
              <el-icon><RefreshLeft /></el-icon>
              切换镜像 ({{ isMirrored ? '开' : '关' }})
            </el-button>
            <el-button
              @click="togglePause"
              :disabled="!cameraActive"
              :type="isPaused ? 'warning' : 'default'"
            >
              <el-icon><component :is="isPaused ? VideoPlay : VideoPause" /></el-icon>
              {{ isPaused ? '继续视频' : '暂停视频' }}
            </el-button>
          </div>
        </div>

        <el-divider />

        <div class="control-section">
          <h3>截图功能</h3>
          <div class="button-group">
            <el-button
              type="success"
              @click="captureSnapshot"
              :disabled="!cameraActive"
            >
              <el-icon><Camera /></el-icon>
              截图
            </el-button>
          </div>
          <p class="hint">点击截图会在下方显示当前画面</p>
        </div>

        <el-divider />

        <div class="control-section">
          <h3>设备信息</h3>
          <div v-if="streamInfo" class="info-list">
            <div class="info-item">
              <span class="label">分辨率:</span>
              <span class="value">{{ streamInfo.width }}x{{ streamInfo.height }}</span>
            </div>
            <div class="info-item">
              <span class="label">帧率:</span>
              <span class="value">{{ streamInfo.frameRate || '默认' }}</span>
            </div>
            <div class="info-item">
              <span class="label">设备ID:</span>
              <span class="value">{{ streamInfo.deviceId?.slice(0, 16) }}...</span>
            </div>
          </div>
          <el-empty v-else description="摄像头未启动" :image-size="80" />
        </div>
      </el-card>

      <el-card v-if="snapshots.length > 0" class="snapshots-card">
        <template #header>
          <div class="card-header">
            <span>截图记录 ({{ snapshots.length }})</span>
            <el-button
              type="danger"
              size="small"
              @click="clearSnapshots"
            >
              清空
            </el-button>
          </div>
        </template>

        <div class="snapshots-grid">
          <div
            v-for="(snapshot, index) in snapshots"
            :key="index"
            class="snapshot-item"
          >
            <img :src="snapshot.data" :alt="'截图 ' + (index + 1)" />
            <div class="snapshot-info">
              <span>{{ snapshot.time }}</span>
              <el-button
                type="primary"
                size="small"
                link
                @click="downloadSnapshot(snapshot)"
              >
                下载
              </el-button>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  VideoPlay,
  VideoPause,
  SwitchButton,
  RefreshLeft,
  Camera,
  TrendCharts
} from '@element-plus/icons-vue'
import UserCamera from '@/components/UserCamera.vue'
import { showCameraDiagnostics } from '@/utils/cameraDiagnostics'

const cameraRef = ref(null)
const cameraActive = ref(false)
const isStarting = ref(false)
const isRecording = ref(false)
const isMirrored = ref(true)
const isPaused = ref(false)
const streamInfo = ref(null)
const snapshots = ref([])

async function startCamera() {
  if (!cameraRef.value) return

  isStarting.value = true
  try {
    await cameraRef.value.startCamera()
    ElMessage.success('摄像头启动成功')
  } catch (error) {
    console.error('启动摄像头失败', error)
    ElMessage.error('启动摄像头失败')
  } finally {
    isStarting.value = false
  }
}

function stopCamera() {
  if (!cameraRef.value) return

  cameraRef.value.stopCamera()
  streamInfo.value = null
  ElMessage.info('摄像头已停止')
}

function toggleRecording() {
  isRecording.value = !isRecording.value
  ElMessage.success(isRecording.value ? '开始录制' : '停止录制')
}

function toggleMirror() {
  if (!cameraRef.value) return

  cameraRef.value.toggleMirror()
  isMirrored.value = !isMirrored.value
  ElMessage.success(isMirrored.value ? '镜像已开启' : '镜像已关闭')
}

function togglePause() {
  if (!cameraRef.value) return

  cameraRef.value.togglePause()
  isPaused.value = !isPaused.value
}

function captureSnapshot() {
  const video = cameraRef.value?.getVideoElement()
  if (!video) return

  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const ctx = canvas.getContext('2d')

  // 如果开启了镜像,需要水平翻转绘制
  if (isMirrored.value) {
    ctx.translate(canvas.width, 0)
    ctx.scale(-1, 1)
  }

  ctx.drawImage(video, 0, 0)
  const imageData = canvas.toDataURL('image/png')

  snapshots.value.unshift({
    data: imageData,
    time: new Date().toLocaleTimeString('zh-CN')
  })

  ElMessage.success('截图成功')
}

function downloadSnapshot(snapshot) {
  const link = document.createElement('a')
  link.href = snapshot.data
  link.download = `camera-snapshot-${Date.now()}.png`
  link.click()
}

function clearSnapshots() {
  snapshots.value = []
  ElMessage.success('已清空截图')
}

function handleCameraStarted(stream) {
  cameraActive.value = true

  const videoTrack = stream.getVideoTracks()[0]
  const settings = videoTrack.getSettings()
  streamInfo.value = {
    width: settings.width,
    height: settings.height,
    frameRate: settings.frameRate,
    deviceId: settings.deviceId
  }

  console.log('摄像头已启动', stream)
}

function handleCameraStopped() {
  cameraActive.value = false
  streamInfo.value = null
  console.log('摄像头已停止')
}

function handleCameraError(error) {
  console.error('摄像头错误', error)
  ElMessage.error('摄像头发生错误: ' + error.message)

  // 自动运行诊断
  setTimeout(() => {
    ElMessage.warning('正在运行诊断,请查看控制台...')
    showCameraDiagnostics()
  }, 1000)
}

async function runDiagnostics() {
  ElMessage.info('正在运行摄像头诊断,请查看控制台...')
  const results = await showCameraDiagnostics()

  if (results.errors.length > 0) {
    // 显示详细错误信息
    let errorMsg = '诊断发现以下问题:\n\n'
    results.errors.forEach((err, i) => {
      errorMsg += `${i + 1}. ${err}\n`
    })
    errorMsg += '\n建议:\n\n'
    results.recommendations.forEach((rec, i) => {
      errorMsg += `${i + 1}. ${rec}\n`
    })

    // 使用 alert 显示详细信息(因为在消息框中显示多行文本不太友好)
    alert(errorMsg)
  }
}
</script>

<style scoped lang="scss">
.camera-test-page {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 24px;

  .test-header {
    text-align: center;
    margin-bottom: 32px;

    h1 {
      font-size: 32px;
      font-weight: 600;
      color: #303133;
      margin: 0 0 8px 0;
    }

    p {
      font-size: 16px;
      color: #606266;
      margin: 0;
    }
  }

  .test-content {
    max-width: 1400px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: 1fr 400px;
    gap: 24px;
    align-items: start;
  }

  .test-card {
    .camera-wrapper {
      aspect-ratio: 16 / 9;
      background: #000;
      border-radius: 8px;
      overflow: hidden;
    }
  }

  .controls-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .control-section {
      margin-bottom: 24px;

      &:last-child {
        margin-bottom: 0;
      }

      h3 {
        font-size: 16px;
        font-weight: 600;
        color: #303133;
        margin: 0 0 12px 0;
      }

      .button-group {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .hint {
        font-size: 13px;
        color: #909399;
        margin: 8px 0 0 0;
      }
    }

    .info-list {
      .info-item {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #ebeef5;

        &:last-child {
          border-bottom: none;
        }

        .label {
          font-weight: 500;
          color: #606266;
        }

        .value {
          color: #303133;
          font-family: monospace;
        }
      }
    }
  }

  .snapshots-card {
    grid-column: 1 / -1;

    .snapshots-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 16px;
    }

    .snapshot-item {
      border: 1px solid #ebeef5;
      border-radius: 8px;
      overflow: hidden;

      img {
        width: 100%;
        aspect-ratio: 16 / 9;
        object-fit: cover;
        display: block;
      }

      .snapshot-info {
        padding: 8px 12px;
        background: #fafafa;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 12px;
        color: #606266;
      }
    }
  }
}

@media (max-width: 1024px) {
  .camera-test-page .test-content {
    grid-template-columns: 1fr;
  }
}
</style>
