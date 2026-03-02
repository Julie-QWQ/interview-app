/**
 * 摄像头工具函数集合
 */

/**
 * 检查浏览器是否支持摄像头访问
 * @returns {boolean}
 */
export function isCameraSupported() {
  return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
}

/**
 * 获取所有摄像头设备列表
 * @returns {Promise<MediaDeviceInfo[]>}
 */
export async function getCameraDevices() {
  if (!isCameraSupported()) {
    throw new Error('浏览器不支持摄像头访问')
  }

  // 先请求一次权限以获取完整的设备标签
  try {
    await navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        stream.getTracks().forEach(track => track.stop())
      })
  } catch (error) {
    // 忽略权限错误,继续获取设备列表
  }

  const devices = await navigator.mediaDevices.enumerateDevices()
  return devices.filter(device => device.kind === 'videoinput')
}

/**
 * 请求摄像头权限
 * @returns {Promise<boolean>}
 */
export async function requestCameraPermission() {
  if (!isCameraSupported()) {
    return false
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true })
    stream.getTracks().forEach(track => track.stop())
    return true
  } catch (error) {
    console.error('请求摄像头权限失败:', error)
    return false
  }
}

/**
 * 检查摄像头权限状态
 * @returns {Promise<string>} 'granted' | 'denied' | 'prompt'
 */
export async function checkCameraPermission() {
  if (!navigator.permissions) {
    return 'prompt'
  }

  try {
    const permissionStatus = await navigator.permissions.query({ name: 'camera' })
    return permissionStatus.state
  } catch (error) {
    return 'prompt'
  }
}

/**
 * 获取摄像头流的最佳配置
 * @param {Object} options
 * @param {number} options.width - 期望的宽度
 * @param {number} options.height - 期望的高度
 * @param {string} options.deviceId - 设备ID
 * @returns {Object}
 */
export function getCameraConstraints(options = {}) {
  const {
    width = 1280,
    height = 720,
    deviceId = null
  } = options

  const constraints = {
    video: {
      width: { ideal: width },
      height: { ideal: height },
      facingMode: 'user'
    }
  }

  if (deviceId) {
    constraints.video.deviceId = { exact: deviceId }
  }

  return constraints
}

/**
 * 启动摄像头
 * @param {Object} options - 配置选项
 * @returns {Promise<MediaStream>}
 */
export async function startCamera(options = {}) {
  if (!isCameraSupported()) {
    throw new Error('浏览器不支持摄像头访问')
  }

  const constraints = getCameraConstraints(options)
  const stream = await navigator.mediaDevices.getUserMedia(constraints)
  return stream
}

/**
 * 停止摄像头流
 * @param {MediaStream} stream
 */
export function stopCamera(stream) {
  if (stream) {
    stream.getTracks().forEach(track => {
      track.stop()
    })
  }
}

/**
 * 从视频流中截取图片
 * @param {HTMLVideoElement} videoElement
 * @param {boolean} mirrored - 是否镜像翻转
 * @returns {string} base64 图片数据
 */
export function captureFrame(videoElement, mirrored = false) {
  const canvas = document.createElement('canvas')
  canvas.width = videoElement.videoWidth
  canvas.height = videoElement.videoHeight

  const ctx = canvas.getContext('2d')

  if (mirrored) {
    ctx.translate(canvas.width, 0)
    ctx.scale(-1, 1)
  }

  ctx.drawImage(videoElement, 0, 0)
  return canvas.toDataURL('image/png')
}

/**
 * 下载图片
 * @param {string} dataUrl - base64 图片数据
 * @param {string} filename - 文件名
 */
export function downloadImage(dataUrl, filename = 'camera-capture.png') {
  const link = document.createElement('a')
  link.href = dataUrl
  link.download = filename
  link.click()
}

/**
 * 获取视频流的详细信息
 * @param {MediaStream} stream
 * @returns {Object}
 */
export function getStreamInfo(stream) {
  const videoTrack = stream.getVideoTracks()[0]
  if (!videoTrack) {
    return null
  }

  const settings = videoTrack.getSettings()
  const capabilities = videoTrack.getCapabilities()

  return {
    width: settings.width,
    height: settings.height,
    frameRate: settings.frameRate,
    deviceId: settings.deviceId,
    aspectRatio: settings.width / settings.height,
    capabilities: {
      minWidth: capabilities?.width?.min,
      maxWidth: capabilities?.width?.max,
      minHeight: capabilities?.height?.min,
      maxHeight: capabilities?.height?.max,
      minFrameRate: capabilities?.frameRate?.min,
      maxFrameRate: capabilities?.frameRate?.max
    }
  }
}

/**
 * 格式化错误信息
 * @param {Error} error
 * @returns {string}
 */
export function formatCameraError(error) {
  const errorMessages = {
    'NotAllowedError': '摄像头权限被拒绝，请在浏览器设置中允许访问摄像头',
    'NotFoundError': '未找到摄像头设备，请确保已连接摄像头',
    'NotReadableError': '摄像头被其他应用占用，请关闭其他使用摄像头的应用',
    'OverconstrainedError': '摄像头配置不兼容，系统会自动尝试其他分辨率',
    'TypeError': '摄像头参数配置错误',
    'SecurityError': '安全限制：只能在 HTTPS 或 localhost 环境下访问摄像头',
    'NotSupportedError': '浏览器不支持摄像头功能'
  }

  return errorMessages[error.name] || `摄像头访问失败: ${error.message}`
}

/**
 * 创建视频预览元素
 * @param {MediaStream} stream
 * @param {Object} options
 * @returns {HTMLVideoElement}
 */
export function createVideoPreview(stream, options = {}) {
  const {
    width = 320,
    height = 240,
    autoplay = true,
    muted = true,
    className = 'camera-preview'
  } = options

  const video = document.createElement('video')
  video.srcObject = stream
  video.autoplay = autoplay
  video.muted = muted
  video.width = width
  video.height = height
  video.className = className

  return video
}

/**
 * 检查是否在安全上下文中(HTTPS 或 localhost)
 * @returns {boolean}
 */
export function isSecureContext() {
  return window.isSecureContext ||
         window.location.protocol === 'https:' ||
         window.location.hostname === 'localhost' ||
         window.location.hostname === '127.0.0.1'
}

/**
 * 摄像头诊断工具
 * @returns {Promise<Object>}
 */
export async function diagnoseCamera() {
  const result = {
    supported: false,
    permission: 'unknown',
    devices: [],
    error: null
  }

  // 检查浏览器支持
  if (!isCameraSupported()) {
    result.error = '浏览器不支持摄像头访问'
    return result
  }
  result.supported = true

  // 检查安全上下文
  if (!isSecureContext()) {
    result.error = '非安全上下文，摄像头功能只能在 HTTPS 或 localhost 环境下使用'
    return result
  }

  // 检查权限
  try {
    result.permission = await checkCameraPermission()
  } catch (error) {
    result.permission = 'unknown'
  }

  // 获取设备列表
  try {
    result.devices = await getCameraDevices()
  } catch (error) {
    result.error = error.message
  }

  return result
}

export default {
  isCameraSupported,
  getCameraDevices,
  requestCameraPermission,
  checkCameraPermission,
  getCameraConstraints,
  startCamera,
  stopCamera,
  captureFrame,
  downloadImage,
  getStreamInfo,
  formatCameraError,
  createVideoPreview,
  isSecureContext,
  diagnoseCamera
}
