/**
 * 摄像头测试工具
 * 用于在浏览器控制台测试摄像头功能
 */

export async function testCameraAccess() {
  console.log('开始测试摄像头访问...')

  // 检查浏览器支持
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    console.error('❌ 当前浏览器不支持摄像头访问')
    return false
  }

  console.log('✅ 浏览器支持摄像头访问')

  try {
    // 获取设备列表
    const devices = await navigator.mediaDevices.enumerateDevices()
    const videoDevices = devices.filter(device => device.kind === 'videoinput')

    console.log(`📷 检测到 ${videoDevices.length} 个摄像头设备:`)
    videoDevices.forEach((device, index) => {
      console.log(`  ${index + 1}. ${device.label || `未命名设备 (${device.deviceId.slice(0, 8)})`}`)
    })

    // 尝试获取摄像头流
    console.log('🎥 正在请求摄像头权限...')
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 }
      }
    })

    console.log('✅ 成功获取摄像头流')
    console.log('📊 视频轨道信息:')
    const videoTrack = stream.getVideoTracks()[0]
    const settings = videoTrack.getSettings()
    console.log(`  分辨率: ${settings.width}x${settings.height}`)
    console.log(`  帧率: ${settings.frameRate || '默认'}`)
    console.log(`  设备ID: ${settings.deviceId.slice(0, 8)}...`)

    // 创建视频元素预览
    const video = document.createElement('video')
    video.srcObject = stream
    video.autoplay = true
    video.muted = true
    video.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      width: 320px;
      height: 240px;
      background: #000;
      border: 2px solid #409eff;
      border-radius: 8px;
      z-index: 9999;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `

    // 添加关闭按钮
    const closeBtn = document.createElement('button')
    closeBtn.textContent = '关闭预览'
    closeBtn.style.cssText = `
      position: absolute;
      bottom: 10px;
      left: 50%;
      transform: translateX(-50%);
      padding: 8px 16px;
      background: #f56c6c;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
    `
    closeBtn.onclick = () => {
      stream.getTracks().forEach(track => track.stop())
      document.body.removeChild(video)
      console.log('✅ 摄像头测试完成')
    }

    video.appendChild(closeBtn)
    document.body.appendChild(video)

    console.log('✅ 摄像头测试成功! 预览窗口已显示在右上角')
    console.log('💡 点击预览窗口中的"关闭预览"按钮停止测试')

    return true
  } catch (error) {
    console.error('❌ 摄像头访问失败:', error)

    switch (error.name) {
      case 'NotAllowedError':
        console.error('   原因: 用户拒绝了摄像头权限')
        console.error('   解决: 请在浏览器地址栏左侧点击锁图标,允许摄像头访问')
        break
      case 'NotFoundError':
        console.error('   原因: 未找到摄像头设备')
        console.error('   解决: 请确保已连接摄像头设备')
        break
      case 'NotReadableError':
        console.error('   原因: 摄像头被其他应用占用')
        console.error('   解决: 请关闭其他使用摄像头的应用(如视频会议软件)')
        break
      default:
        console.error('   原因:', error.message)
    }

    return false
  }
}

// 在浏览器控制台快速测试
// 在控制台输入: testCameraAccess()
window.testCameraAccess = testCameraAccess

export default testCameraAccess
