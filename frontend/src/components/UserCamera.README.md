# UserCamera 组件使用文档

## 功能特性

UserCamera 是一个功能完整的用户摄像头组件,提供以下特性:

### 核心功能
- ✅ 实时摄像头视频流显示
- ✅ 自动检测和列出可用摄像头设备
- ✅ 支持多摄像头切换
- ✅ 视频镜像翻转控制
- ✅ 视频暂停/继续
- ✅ 录制状态指示器
- ✅ 优雅的错误处理和用户提示
- ✅ 完整的生命周期管理

### 用户体验
- 🎨 渐变色占位界面
- 🔄 流畅的加载动画
- ⚠️ 详细的错误提示
- 🎯 直观的控制按钮
- 📱 响应式设计

## 基本用法

### 最简用法

```vue
<template>
  <UserCamera />
</template>

<script setup>
import UserCamera from '@/components/UserCamera.vue'
</script>
```

### 自动启动

```vue
<template>
  <UserCamera :auto-start="true" />
</template>
```

### 录制指示器

```vue
<template>
  <UserCamera :is-recording="isRecording" />
</template>

<script setup>
import { ref } from 'vue'
import UserCamera from '@/components/UserCamera.vue'

const isRecording = ref(false)
</script>
```

## Props

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `autoStart` | Boolean | `false` | 是否在组件加载时自动启动摄像头 |
| `isRecording` | Boolean | `false` | 是否显示录制指示器 |

## Events

| 事件名 | 参数 | 说明 |
|--------|------|------|
| `camera-started` | `stream: MediaStream` | 摄像头启动成功时触发 |
| `camera-stopped` | - | 摄像头停止时触发 |
| `camera-error` | `error: Error` | 摄像头发生错误时触发 |
| `stream-ready` | `stream: MediaStream` | 视频流准备就绪时触发 |

## 方法(通过 ref 调用)

| 方法名 | 参数 | 返回值 | 说明 |
|--------|------|--------|------|
| `startCamera` | `deviceId?: string` | `Promise<void>` | 启动摄像头,可选指定设备ID |
| `stopCamera` | - | `void` | 停止摄像头 |
| `togglePause` | - | `void` | 暂停/继续视频播放 |
| `toggleMirror` | - | `void` | 切换镜像翻转 |
| `getStream` | - | `MediaStream \| null` | 获取当前视频流 |
| `getVideoElement` | - | `HTMLVideoElement \| null` | 获取视频元素 |

## 完整示例

```vue
<template>
  <div>
    <UserCamera
      ref="cameraRef"
      :auto-start="false"
      :is-recording="isRecording"
      @camera-started="handleStarted"
      @camera-stopped="handleStopped"
      @camera-error="handleError"
    />

    <div class="controls">
      <el-button @click="start">启动摄像头</el-button>
      <el-button @click="stop">停止摄像头</el-button>
      <el-button @click="startRecording">开始录制</el-button>
      <el-button @click="stopRecording">停止录制</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import UserCamera from '@/components/UserCamera.vue'

const cameraRef = ref(null)
const isRecording = ref(false)

function start() {
  cameraRef.value?.startCamera()
}

function stop() {
  cameraRef.value?.stopCamera()
}

function startRecording() {
  isRecording.value = true
  ElMessage.success('开始录制')
}

function stopRecording() {
  isRecording.value = false
  ElMessage.info('停止录制')
}

function handleStarted(stream) {
  console.log('摄像头已启动', stream)
  ElMessage.success('摄像头已启动')
}

function handleStopped() {
  console.log('摄像头已停止')
  ElMessage.info('摄像头已停止')
}

function handleError(error) {
  console.error('摄像头错误', error)
  ElMessage.error('摄像头发生错误')
}
</script>
```

## 在面试场景中的使用

```vue
<template>
  <div class="interview-view">
    <UserCamera
      ref="userCameraRef"
      :auto-start="false"
      :is-recording="isListening"
      @camera-started="handleCameraStarted"
      @camera-stopped="handleCameraStopped"
      @camera-error="handleCameraError"
    />

    <el-button @click="startInterview">开始面试</el-button>
    <el-button @click="endInterview">结束面试</el-button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import UserCamera from '@/components/UserCamera.vue'

const userCameraRef = ref(null)
const isListening = ref(false)

async function startInterview() {
  // ... 开始面试逻辑

  // 自动启动摄像头
  if (userCameraRef.value) {
    try {
      await userCameraRef.value.startCamera()
      ElMessage.success('面试开始,摄像头已启动')
    } catch (error) {
      console.error('启动摄像头失败', error)
      ElMessage.warning('摄像头启动失败,但面试可以继续')
    }
  }
}

async function endInterview() {
  // 停止摄像头
  if (userCameraRef.value) {
    await userCameraRef.value.stopCamera()
  }

  // ... 结束面试逻辑
}

function handleCameraStarted(stream) {
  console.log('摄像头已就绪', stream)
}

function handleCameraStopped() {
  console.log('摄像头已关闭')
}

function handleCameraError(error) {
  console.error('摄像头错误:', error)
}
</script>
```

## 浏览器兼容性

| 浏览器 | 支持情况 |
|--------|----------|
| Chrome | ✅ 完全支持 |
| Edge | ✅ 完全支持 |
| Firefox | ✅ 完全支持 |
| Safari | ✅ 完全支持 (需要 iOS 11+) |
| Opera | ✅ 完全支持 |

## 权限处理

### 首次使用
浏览器会弹出摄像头权限请求,用户需要点击"允许"。

### 权限被拒绝
如果用户拒绝了权限,组件会显示友好的错误提示,引导用户:
1. 点击地址栏左侧的锁图标
2. 找到"摄像头"权限
3. 更改为"允许"

### 权限检查
```javascript
// 检查权限状态
const permissionStatus = await navigator.permissions.query({ name: 'camera' })
console.log('摄像头权限状态:', permissionStatus.state)
// 'granted' - 已授权
// 'denied' - 已拒绝
// 'prompt' - 未询问
```

## 设备切换

组件会自动检测所有可用的摄像头设备,用户可以通过设备选择对话框切换:

```vue
<script setup>
import { ref } from 'vue'
import UserCamera from '@/components/UserCamera.vue'

const cameraRef = ref(null)

async function switchToSpecificDevice(deviceId) {
  await cameraRef.value?.startCamera(deviceId)
}
</script>
```

## 错误处理

组件会处理各种常见错误:

| 错误类型 | 原因 | 解决方案 |
|----------|------|----------|
| `NotAllowedError` | 用户拒绝权限 | 引导用户允许摄像头访问 |
| `NotFoundError` | 未找到摄像头 | 提示用户连接摄像头 |
| `NotReadableError` | 摄像头被占用 | 提示关闭其他应用 |
| `OverconstrainedError` | 分辨率不支持 | 自动降级分辨率 |

## 性能优化

1. **自动资源释放**: 组件卸载时自动停止摄像头
2. **暂停优化**: 不使用时可以暂停视频播放
3. **分辨率适配**: 自动选择最佳分辨率
4. **硬件加速**: 使用 CSS transform 启用硬件加速

## 样式定制

组件使用 scoped 样式,可以通过以下方式定制:

```vue
<style>
/* 修改容器样式 */
.user-camera-container {
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* 修改控制按钮样式 */
.camera-controls .control-buttons button {
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.2);
}
</style>
```

## 常见问题

### Q: 摄像头画面是倒的?
A: 可以通过镜像翻转功能解决,组件默认开启镜像。

### Q: 如何在移动端使用?
A: 组件已完全支持移动端,会自动使用前置摄像头。

### Q: 能否同时使用多个摄像头?
A: 可以,创建多个组件实例即可。

### Q: 如何保存摄像头截图?
A: 可以通过 `getVideoElement()` 获取视频元素,然后使用 canvas 截图:

```javascript
const video = cameraRef.value?.getVideoElement()
const canvas = document.createElement('canvas')
canvas.width = video.videoWidth
canvas.height = video.videoHeight
const ctx = canvas.getContext('2d')
ctx.drawImage(video, 0, 0)
const imageData = canvas.toDataURL('image/png')
```

## 更新日志

### v1.0.0 (2025-03-02)
- ✨ 初始版本
- ✅ 支持基础摄像头功能
- ✅ 设备切换
- ✅ 镜像控制
- ✅ 录制指示器
- ✅ 完整错误处理
