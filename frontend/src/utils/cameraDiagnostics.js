/**
 * 摄像头诊断工具
 * 用于排查摄像头问题
 */

import { ElMessage } from 'element-plus'

/**
 * 完整的摄像头诊断
 */
export async function runCameraDiagnostics() {
  console.log('===== 开始摄像头诊断 =====')

  const results = {
    browserSupport: false,
    secureContext: false,
    permissionStatus: 'unknown',
    devicesFound: 0,
    devices: [],
    errors: [],
    recommendations: []
  }

  // 1. 检查浏览器支持
  console.log('1. 检查浏览器支持...')
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    results.errors.push('浏览器不支持媒体设备 API')
    results.recommendations.push('请使用 Chrome、Edge、Firefox 或 Safari 浏览器')
    console.error('❌ 浏览器不支持摄像头')
    return results
  }
  results.browserSupport = true
  console.log('✅ 浏览器支持摄像头 API')

  // 2. 检查安全上下文
  console.log('2. 检查安全上下文...')
  const isSecure = window.isSecureContext ||
                   window.location.protocol === 'https:' ||
                   window.location.hostname === 'localhost' ||
                   window.location.hostname === '127.0.0.1'
  if (!isSecure) {
    results.errors.push('非安全上下文')
    results.recommendations.push('摄像头功能需要在 HTTPS 或 localhost 环境下使用')
    console.error('❌ 非 HTTPS 环境')
    return results
  }
  results.secureContext = true
  console.log('✅ 安全上下文检查通过')

  // 3. 检查权限状态
  console.log('3. 检查摄像头权限...')
  try {
    if (navigator.permissions) {
      const permissionStatus = await navigator.permissions.query({ name: 'camera' })
      results.permissionStatus = permissionStatus.state
      console.log(`权限状态: ${permissionStatus.state}`)

      if (permissionStatus.state === 'denied') {
        results.errors.push('摄像头权限被拒绝')
        results.recommendations.push('请在浏览器设置中允许摄像头访问: 点击地址栏左侧的锁图标 → 允许摄像头')
        console.error('❌ 权限被拒绝')
        return results
      }
    }
  } catch (err) {
    console.warn('⚠️ 无法检查权限状态:', err.message)
  }

  // 4. 枚举设备
  console.log('4. 枚举摄像头设备...')
  try {
    // 先请求一次权限以获取完整的设备标签
    let tempStream = null
    try {
      tempStream = await navigator.mediaDevices.getUserMedia({ video: true })
      console.log('✅ 成功获取临时权限')
    } catch (err) {
      console.warn('⚠️ 获取临时权限失败:', err.name, err.message)
      if (err.name === 'NotAllowedError') {
        results.errors.push('用户拒绝了摄像头权限')
        results.recommendations.push('请刷新页面并允许摄像头权限')
        return results
      }
      throw err
    }

    const devices = await navigator.mediaDevices.enumerateDevices()
    const videoDevices = devices.filter(device => device.kind === 'videoinput')

    // 清理临时流
    if (tempStream) {
      tempStream.getTracks().forEach(track => track.stop())
    }

    results.devicesFound = videoDevices.length
    results.devices = videoDevices

    console.log(`✅ 检测到 ${videoDevices.length} 个摄像头:`)
    videoDevices.forEach((device, index) => {
      console.log(`   ${index + 1}. ${device.label || '未命名设备'} (${device.deviceId.slice(0, 8)}...)`)
    })

    if (videoDevices.length === 0) {
      results.errors.push('未检测到摄像头设备')
      results.recommendations.push('请确保摄像头已正确连接到电脑')
      results.recommendations.push('尝试重新插拔摄像头或重启电脑')
      console.error('❌ 没有检测到摄像头设备')
      return results
    }
  } catch (err) {
    results.errors.push(`枚举设备失败: ${err.message}`)
    console.error('❌ 枚举设备失败:', err)
    return results
  }

  // 5. 尝试启动摄像头(使用最小配置)
  console.log('5. 尝试启动摄像头...')

  // 先尝试不指定设备,让系统自动选择
  const testConfigs = [
    { label: '默认配置(自动选择设备)', constraints: { video: true } },
    { label: '用户视角', constraints: { video: { facingMode: 'user' } } },
    { label: '最小分辨率', constraints: { video: { width: 160, height: 120 } } },
    { label: '仅视频', constraints: { video: { width: { ideal: 320 } } } }
  ]

  // 如果有多个设备,尝试每个设备
  if (results.devices.length > 1) {
    console.log(`   将测试 ${results.devices.length} 个摄像头设备`)
    results.devices.forEach((device, index) => {
      const deviceConfig = {
        label: `设备 ${index + 1}: ${device.label || '未命名'}`,
        constraints: { video: { deviceId: { exact: device.deviceId } } }
      }
      // 插入到配置列表前面
      testConfigs.splice(index, 0, deviceConfig)
    })
  }

  let successfulConfig = null
  for (const config of testConfigs) {
    try {
      console.log(`   尝试: ${config.label}`)
      const stream = await navigator.mediaDevices.getUserMedia(config.constraints)

      // 获取实际使用的设备
      const videoTrack = stream.getVideoTracks()[0]
      const settings = videoTrack.getSettings()
      const actualDevice = results.devices.find(d => d.deviceId === settings.deviceId)

      stream.getTracks().forEach(track => track.stop())
      successfulConfig = {
        ...config,
        actualDevice: actualDevice?.label || '默认设备',
        resolution: `${settings.width}x${settings.height}`
      }
      console.log(`   ✅ ${config.label} 成功`)
      console.log(`   实际使用: ${successfulConfig.actualDevice} @ ${successfulConfig.resolution}`)
      break
    } catch (err) {
      console.warn(`   ❌ ${config.label} 失败:`, err.name, err.message)
      if (err.constraint) {
        console.warn(`      失败约束: ${err.constraint}`)
      }
    }
  }

  if (!successfulConfig) {
    results.errors.push('所有配置都无法启动摄像头')
    results.recommendations.push('可能是驱动问题,尝试更新摄像头驱动程序')
    results.recommendations.push('检查摄像头是否被其他应用占用(如 Zoom、Teams、Skype 等)')
    results.recommendations.push('尝试重启浏览器或电脑')
    results.recommendations.push('如果是外接摄像头,尝试更换 USB 接口')
    console.error('❌ 所有配置均失败')
  } else {
    console.log(`✅ 推荐配置: ${successfulConfig.label}`)
    results.recommendations.push(`可以使用 "${successfulConfig.label}" 启动摄像头`)
    if (successfulConfig.actualDevice) {
      results.recommendations.push(`实际使用的设备: ${successfulConfig.actualDevice}`)
    }
  }

  console.log('===== 诊断完成 =====')
  return results
}

/**
 * 显示诊断结果
 */
export async function showCameraDiagnostics() {
  const results = await runCameraDiagnostics()

  let message = '摄像头诊断结果:\n\n'

  if (results.errors.length === 0) {
    message += '✅ 未发现问题\n'
    message += `检测到 ${results.devicesFound} 个摄像头设备\n`
    ElMessage.success({
      message: '摄像头诊断通过,一切正常!',
      duration: 3000
    })
  } else {
    message += '❌ 发现以下问题:\n\n'
    results.errors.forEach((err, i) => {
      message += `${i + 1}. ${err}\n`
    })

    message += '\n💡 建议:\n\n'
    results.recommendations.forEach((rec, i) => {
      message += `${i + 1}. ${rec}\n`
    })

    console.error(message)
    ElMessage.error({
      message: '摄像头诊断发现问题,请查看控制台详情',
      duration: 5000
    })
  }

  return results
}

/**
 * 在浏览器控制台显示详细的诊断信息
 */
export async function logDetailedDiagnostics() {
  const results = await runCameraDiagnostics()

  console.group('🔍 摄像头详细诊断报告')
  console.log('浏览器支持:', results.browserSupport ? '✅' : '❌')
  console.log('安全上下文:', results.secureContext ? '✅' : '❌')
  console.log('权限状态:', results.permissionStatus)
  console.log('设备数量:', results.devicesFound)
  console.log('设备列表:', results.devices)
  console.log('错误列表:', results.errors)
  console.log('建议列表:', results.recommendations)
  console.groupEnd()

  // 显示更多信息
  console.group('📊 环境信息')
  console.log('User Agent:', navigator.userAgent)
  console.log('Protocol:', window.location.protocol)
  console.log('Hostname:', window.location.hostname)
  console.log('Secure Context:', window.isSecureContext)
  console.log('MediaDevices Support:', !!(navigator.mediaDevices))
  console.log('getUserMedia Support:', !!(navigator.mediaDevices?.getUserMedia))
  console.groupEnd()

  return results
}

// 导出到 window 对象,方便在控制台调用
if (typeof window !== 'undefined') {
  window.cameraDiagnostics = {
    run: runCameraDiagnostics,
    show: showCameraDiagnostics,
    log: logDetailedDiagnostics
  }
  console.log('💡 摄像头诊断工具已加载,在控制台输入:')
  console.log('   - cameraDiagnostics.show()  // 显示诊断结果')
  console.log('   - cameraDiagnostics.log()   // 查看详细报告')
  console.log('   - cameraDiagnostics.run()   // 返回诊断数据')
}

export default {
  runCameraDiagnostics,
  showCameraDiagnostics,
  logDetailedDiagnostics
}
