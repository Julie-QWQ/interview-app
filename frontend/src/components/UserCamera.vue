<template>
  <div class="user-camera-container">
    <div class="camera-wrapper">
      <!-- 摄像头视频流 -->
      <video
        ref="videoRef"
        class="camera-video"
        :class="{ 'mirrored': isMirrored }"
        autoplay
        playsinline
        muted
      ></video>

      <!-- 占位提示 -->
      <div v-if="!isCameraActive" class="camera-placeholder">
        <el-icon><Camera /></el-icon>
        <span class="placeholder-label">用户摄像头</span>
        <span class="placeholder-hint">{{ cameraStatus }}</span>
        <el-button
          v-if="shouldShowStartButton"
          type="primary"
          @click="startCamera"
          :loading="isStarting"
          size="small"
          style="margin-top: 12px"
        >
          开启摄像头
        </el-button>
      </div>

      <!-- 加载中状态 -->
      <div v-if="isStarting" class="camera-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>正在启动摄像头...</span>
      </div>

      <!-- 错误提示 -->
      <div v-if="error" class="camera-error">
        <el-icon><WarningFilled /></el-icon>
        <span>{{ error }}</span>
        <el-button
          v-if="error"
          type="primary"
          @click="startCamera"
          size="small"
          link
          style="margin-top: 8px"
        >
          重试
        </el-button>
      </div>

      <!-- 摄像头控制栏 -->
      <div v-if="isCameraActive" class="camera-controls">
        <div class="control-buttons">
          <!-- 镜像切换 -->
          <el-tooltip content="镜像翻转" placement="top">
            <el-button
              :type="isMirrored ? 'primary' : 'default'"
              @click="toggleMirror"
              circle
              size="small"
            >
              <el-icon><RefreshLeft /></el-icon>
            </el-button>
          </el-tooltip>

          <!-- 暂停/继续视频 -->
          <el-tooltip :content="isPaused ? '继续视频' : '暂停视频'" placement="top">
            <el-button
              @click="togglePause"
              :type="isPaused ? 'warning' : 'default'"
              circle
              size="small"
            >
              <el-icon>
                <component :is="isPaused ? VideoPlay : VideoPause" />
              </el-icon>
            </el-button>
          </el-tooltip>

          <!-- 停止摄像头 -->
          <el-tooltip content="关闭摄像头" placement="top">
            <el-button
              type="danger"
              @click="stopCamera"
              circle
              size="small"
            >
              <el-icon><SwitchButton /></el-icon>
            </el-button>
          </el-tooltip>
        </div>

        <!-- 设备信息 -->
        <div class="device-info">
          <el-tag size="small" type="info">
            {{ currentDevice?.label || '默认设备' }}
          </el-tag>
        </div>
      </div>

      <!-- 录制指示器 -->
      <div v-if="isRecording" class="recording-indicator">
        <span class="recording-dot"></span>
        <span>录制中</span>
      </div>
    </div>

    <!-- 设备选择器 -->
    <el-dialog
      v-model="showDeviceDialog"
      title="选择摄像头设备"
      width="400px"
    >
      <el-select
        v-model="selectedDeviceId"
        placeholder="请选择摄像头"
        style="width: 100%"
        @change="switchDevice"
      >
        <el-option
          v-for="device in videoDevices"
          :key="device.deviceId"
          :label="device.label || `摄像头 ${String(device.deviceId || '').slice(0, 8)}`"
          :value="device.deviceId"
        />
      </el-select>
      <template #footer>
        <el-button @click="showDeviceDialog = false">取消</el-button>
        <el-button type="primary" @click="switchDevice">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Camera,
  Loading,
  WarningFilled,
  RefreshLeft,
  VideoPlay,
  VideoPause,
  SwitchButton,
  Setting
} from '@element-plus/icons-vue'

const props = defineProps({
  // 是否自动启动摄像头
  autoStart: {
    type: Boolean,
    default: false
  },
  // 是否显示录制指示器
  isRecording: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'camera-started',
  'camera-stopped',
  'camera-error',
  'stream-ready'
])

// Refs
const videoRef = ref(null)
const streamRef = ref(null)

// 状态
const isStarting = ref(false)
const isCameraActive = ref(false)
const isPaused = ref(false)
const isMirrored = ref(true) // 默认开启镜像
const error = ref('')
const cameraStatus = ref('等待开启...')
const showStartButton = ref(true)

// 设备相关
const videoDevices = ref([])
const currentDevice = ref(null)
const selectedDeviceId = ref('')
const showDeviceDialog = ref(false)

// 计算属性
const shouldShowStartButton = computed(() => {
  return !isCameraActive.value && !isStarting.value
})

// 生命周期
onMounted(async () => {
  // 检查浏览器支持
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    error.value = '当前浏览器不支持摄像头功能'
    cameraStatus.value = '浏览器不支持'
    emit('camera-error', error.value)
    return
  }

  // 请求权限并获取设备列表
  await getVideoDevices()

  // 如果设置了自动启动
  if (props.autoStart) {
    await startCamera()
  }
})

onBeforeUnmount(() => {
  stopCamera()
})

// 监听录制状态变化
watch(() => props.isRecording, (newVal) => {
  // 可以在这里处理录制相关的逻辑
})

// 获取视频设备列表
async function getVideoDevices() {
  try {
    // 先请求一次权限以获取完整的设备标签
    await navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        stream.getTracks().forEach(track => track.stop())
      })

    const devices = await navigator.mediaDevices.enumerateDevices()
    videoDevices.value = devices.filter(device => device.kind === 'videoinput')

    if (videoDevices.value.length === 0) {
      error.value = '未检测到摄像头设备'
      cameraStatus.value = '未检测到设备'
    }
  } catch (err) {
    console.error('获取设备列表失败:', err)
    if (err.name === 'NotAllowedError') {
      error.value = '摄像头权限被拒绝'
      cameraStatus.value = '权限被拒绝'
    } else if (err.name === 'NotFoundError') {
      error.value = '未找到摄像头设备'
      cameraStatus.value = '未找到设备'
    } else {
      error.value = `摄像头访问失败: ${err.message}`
      cameraStatus.value = '访问失败'
    }
  }
}

// 启动摄像头
async function startCamera(deviceId = null) {
  if (isStarting.value || isCameraActive.value) return

  isStarting.value = true
  error.value = ''

  // 定义多个分辨率配置,按优先级降序
  const resolutionOptions = [
    { width: { ideal: 1280 }, height: { ideal: 720 }, label: '720p' },
    { width: { ideal: 640 }, height: { ideal: 480 }, label: '480p' },
    { width: { ideal: 320 }, height: { ideal: 240 }, label: '240p' },
    { width: { ideal: 160 }, height: { ideal: 120 }, label: '120p' },
    { width: {}, height: {}, label: '默认' } // 最后使用摄像头默认分辨率
  ]

  let lastError = null

  // 先检查是否有可用的摄像头设备
  if (videoDevices.value.length === 0) {
    await getVideoDevices()
  }

  if (videoDevices.value.length === 0) {
    isStarting.value = false
    error.value = '未检测到摄像头设备,请确保已连接摄像头'
    cameraStatus.value = '未检测到设备'
    emit('camera-error', new Error('No camera devices found'))
    ElMessage.error(error.value)
    return
  }

  console.log(`检测到 ${videoDevices.value.length} 个摄像头设备`)

  // 构建设备尝试列表:如果指定了设备,先尝试指定设备,然后尝试其他设备
  const devicesToTry = []
  if (deviceId && typeof deviceId === 'string') {
    const specifiedDevice = videoDevices.value.find(d => d.deviceId === deviceId)
    if (specifiedDevice) {
      devicesToTry.push({ id: deviceId, name: '指定设备' })
    } else {
      console.warn(`指定的设备ID不存在: ${deviceId.slice(0, 8)}...`)
    }
  }
  // 添加其他设备作为备选
  videoDevices.value.forEach(device => {
    if (!deviceId || device.deviceId !== deviceId) {
      devicesToTry.push({ id: device.deviceId, name: device.label || '其他设备' })
    }
  })
  // 最后尝试不指定设备ID
  devicesToTry.push({ id: null, name: '默认设备' })

  console.log(`将按顺序尝试 ${devicesToTry.length} 个设备`)

  // 尝试每个设备和每个分辨率的组合
  for (const device of devicesToTry) {
    for (const resolution of resolutionOptions) {
      const constraints = {
        video: {
          ...resolution,
          facingMode: 'user'
        }
      }

      // 添加设备ID约束(如果不是默认设备)
      if (device.id) {
        constraints.video.deviceId = { exact: device.id }
      }

      try {
        console.log(`尝试: ${device.name} - ${resolution.label}`)

        const stream = await navigator.mediaDevices.getUserMedia(constraints)
        streamRef.value = stream

        if (videoRef.value) {
          videoRef.value.srcObject = stream
          await videoRef.value.play()
        }

        // 获取当前使用的设备信息
        const videoTrack = stream.getVideoTracks()[0]
        const settings = videoTrack.getSettings()
        currentDevice.value = videoDevices.value.find(
          d => d.deviceId === settings.deviceId
        ) || { label: '默认设备' }

        isCameraActive.value = true
        isStarting.value = false
        cameraStatus.value = '运行中'

        emit('camera-started', stream)
        emit('stream-ready', stream)

        const deviceName = currentDevice.value?.label || '默认设备'
        ElMessage.success(`摄像头已启动 (${deviceName}, ${settings.width}x${settings.height})`)
        return
      } catch (err) {
        console.warn(`${device.name} - ${resolution.label} 失败:`, {
          name: err.name,
          message: err.message,
          constraint: err.constraint
        })
        lastError = err
        // 继续尝试下一个组合
      }
    }
  }

  // 所有分辨率都失败了
  console.error('启动摄像头失败,所有分辨率尝试均失败', {
    devicesCount: videoDevices.value.length,
    lastError: lastError?.name,
    errorMessage: lastError?.message,
    constraint: lastError?.constraint
  })

  isStarting.value = false

  // 提供更详细的错误信息
  if (lastError?.name === 'NotAllowedError') {
    error.value = '摄像头权限被拒绝,请点击浏览器地址栏左侧的锁图标,允许访问摄像头'
  } else if (lastError?.name === 'NotFoundError') {
    error.value = '未找到摄像头设备,请确保摄像头已连接并正常工作'
  } else if (lastError?.name === 'NotReadableError') {
    error.value = '摄像头被其他应用占用(如视频会议软件),请关闭其他应用后重试'
  } else if (lastError?.name === 'OverconstrainedError') {
    // 特殊处理 deviceId 约束错误
    if (lastError?.constraint === 'deviceId') {
      error.value = '指定的摄像头设备不可用,已自动切换到默认设备。请点击"开启摄像头"重试'
    } else {
      error.value = `摄像头配置不兼容: ${lastError.constraint || '未知约束'}`
    }
  } else if (lastError?.name === 'TypeError') {
    error.value = '摄像头参数配置错误,请刷新页面重试'
  } else {
    error.value = `摄像头启动失败: ${lastError?.message || '未知错误'} (${lastError?.name || 'Unknown'})`
  }

  cameraStatus.value = '启动失败'

  emit('camera-error', lastError)
  ElMessage.error({
    message: error.value,
    duration: 5000,
    showClose: true
  })
}

// 停止摄像头
function stopCamera() {
  if (streamRef.value) {
    streamRef.value.getTracks().forEach(track => {
      track.stop()
    })
    streamRef.value = null
  }

  if (videoRef.value) {
    videoRef.value.srcObject = null
  }

  isCameraActive.value = false
  isPaused.value = false
  cameraStatus.value = '已停止'

  emit('camera-stopped')
}

// 暂停/继续视频
function togglePause() {
  if (!videoRef.value) return

  if (isPaused.value) {
    videoRef.value.play()
    isPaused.value = false
  } else {
    videoRef.value.pause()
    isPaused.value = true
  }
}

// 切换镜像
function toggleMirror() {
  isMirrored.value = !isMirrored.value
}

// 切换设备
async function switchDevice() {
  if (selectedDeviceId.value) {
    showDeviceDialog.value = false
    await startCamera(selectedDeviceId.value)
  }
}

// 显示设备选择对话框
function showDeviceSelector() {
  showDeviceDialog.value = true
}

// 错误信息处理
function getErrorMessage(err) {
  switch (err.name) {
    case 'NotAllowedError':
      return '摄像头权限被拒绝，请在浏览器设置中允许访问摄像头'
    case 'NotFoundError':
      return '未找到摄像头设备，请确保已连接摄像头'
    case 'NotReadableError':
      return '摄像头被其他应用占用，请关闭其他使用摄像头的应用'
    case 'OverconstrainedError':
      return '摄像头配置不兼容，已自动尝试其他分辨率'
    case 'TypeError':
      return '摄像头参数配置错误'
    default:
      return `摄像头访问失败: ${err.message || '未知错误'}`
  }
}

// 监听设备插拔
navigator.mediaDevices?.addEventListener('devicechange', async () => {
  await getVideoDevices()
})

// 暴露方法给父组件
defineExpose({
  startCamera,
  stopCamera,
  togglePause,
  toggleMirror,
  getStream: () => streamRef.value,
  getVideoElement: () => videoRef.value
})
</script>

<style scoped lang="scss">
.user-camera-container {
  width: 100%;
  height: 100%;
  background: #000;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.camera-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  background: #000;

  &.mirrored {
    transform: scaleX(-1);
  }
}

.camera-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  padding: 20px;

  .el-icon {
    font-size: 48px;
    margin-bottom: 12px;
    opacity: 0.9;
  }

  .placeholder-label {
    font-weight: 600;
    font-size: 16px;
    margin-bottom: 8px;
  }

  .placeholder-hint {
    font-size: 13px;
    opacity: 0.8;
  }
}

.camera-loading,
.camera-error {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 20px;
  text-align: center;

  .el-icon {
    font-size: 32px;
    margin-bottom: 12px;
  }

  span {
    font-size: 14px;
    line-height: 1.5;
  }
}

.camera-error {
  .el-icon {
    color: #f56c6c;
  }
}

.camera-controls {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.8), transparent);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;

  .control-buttons {
    display: flex;
    justify-content: center;
    gap: 8px;
  }

  .device-info {
    display: flex;
    justify-content: center;
  }
}

.recording-indicator {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(245, 108, 108, 0.9);
  color: white;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  animation: pulse-recording 1.5s ease-in-out infinite;

  .recording-dot {
    width: 8px;
    height: 8px;
    background: white;
    border-radius: 50%;
  }
}

@keyframes pulse-recording {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}
</style>
