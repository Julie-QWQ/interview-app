/**
 * 高级音频预处理工具
 * 用于提高ASR识别准确率
 */

export interface AudioProcessingOptions {
  noiseReduction?: boolean      // 降噪
  normalizeVolume?: boolean     // 音量归一化
  highPassFilter?: boolean      // 高通滤波(去除低频噪音)
  targetSampleRate?: number     // 目标采样率
  vadAggressive?: number        // VAD激进程度 (0-3)
}

/**
 * 应用高通滤波器,去除低频噪音
 */
function applyHighPassFilter(
  audioBuffer: AudioBuffer,
  cutoffFrequency: number = 80
): AudioBuffer {
  const audioContext = new AudioContext()
  const offlineContext = new OfflineAudioContext(
    audioBuffer.numberOfChannels,
    audioBuffer.length,
    audioBuffer.sampleRate
  )

  const source = offlineContext.createBufferSource()
  source.buffer = audioBuffer

  const highPass = offlineContext.createBiquadFilter()
  highPass.type = 'highpass'
  highPass.frequency.value = cutoffFrequency
  highPass.Q.value = 0.7

  source.connect(highPass)
  highPass.connect(offlineContext.destination)
  source.start(0)

  return offlineContext.startRendering()
}

/**
 * 音量归一化
 */
function applyVolumeNormalization(audioBuffer: AudioBuffer, targetDB: number = -3): AudioBuffer {
  const numberOfChannels = audioBuffer.numberOfChannels
  const length = audioBuffer.length
  const offlineContext = new OfflineAudioContext(
    numberOfChannels,
    length,
    audioBuffer.sampleRate
  )

  // 计算RMS
  let maxRMS = 0
  for (let channel = 0; channel < numberOfChannels; channel++) {
    const data = audioBuffer.getChannelData(channel)
    let sum = 0
    for (let i = 0; i < length; i++) {
      sum += data[i] * data[i]
    }
    const rms = Math.sqrt(sum / length)
    if (rms > maxRMS) maxRMS = rms
  }

  // 计算增益
  const targetRMS = Math.pow(10, targetDB / 20)
  const gain = maxRMS > 0 ? targetRMS / maxRMS : 1

  // 应用增益
  const source = offlineContext.createBufferSource()
  source.buffer = audioBuffer

  const gainNode = offlineContext.createGain()
  gainNode.gain.value = gain

  source.connect(gainNode)
  gainNode.connect(offlineContext.destination)
  source.start(0)

  return offlineContext.startRendering()
}

/**
 * 简单的噪声门限处理
 */
function applyNoiseGate(
  audioBuffer: AudioBuffer,
  threshold: number = 0.02,
  ratio: number = 0.1
): AudioBuffer {
  const numberOfChannels = audioBuffer.numberOfChannels
  const length = audioBuffer.length
  const offlineContext = new OfflineAudioContext(
    numberOfChannels,
    length,
    audioBuffer.sampleRate
  )

  const processedBuffer = offlineContext.createBuffer(
    numberOfChannels,
    length,
    audioBuffer.sampleRate
  )

  for (let channel = 0; channel < numberOfChannels; channel++) {
    const inputData = audioBuffer.getChannelData(channel)
    const outputData = processedBuffer.getChannelData(channel)

    for (let i = 0; i < length; i++) {
      const sample = inputData[i]
      const amplitude = Math.abs(sample)

      if (amplitude < threshold) {
        outputData[i] = sample * ratio
      } else {
        outputData[i] = sample
      }
    }
  }

  return processedBuffer
}

/**
 * 合并单声道
 */
function interleaveToMono(audioBuffer: AudioBuffer): Float32Array {
  const numberOfChannels = audioBuffer.numberOfChannels
  const length = audioBuffer.length

  if (numberOfChannels === 1) {
    return audioBuffer.getChannelData(0)
  }

  const mono = new Float32Array(length)
  for (let channel = 0; channel < numberOfChannels; channel++) {
    const channelData = audioBuffer.getChannelData(channel)
    for (let i = 0; i < length; i++) {
      mono[i] += channelData[i] / numberOfChannels
    }
  }

  return mono
}

/**
 * 线性重采样
 */
function resampleLinear(
  input: Float32Array,
  inputSampleRate: number,
  outputSampleRate: number
): Float32Array {
  if (inputSampleRate === outputSampleRate) {
    return input
  }

  const ratio = inputSampleRate / outputSampleRate
  const outputLength = Math.max(1, Math.round(input.length / ratio))
  const output = new Float32Array(outputLength)

  for (let i = 0; i < outputLength; i++) {
    const position = i * ratio
    const leftIndex = Math.floor(position)
    const rightIndex = Math.min(leftIndex + 1, input.length - 1)
    const weight = position - leftIndex
    output[i] = input[leftIndex] * (1 - weight) + input[rightIndex] * weight
  }

  return output
}

/**
 * 编码WAV文件
 */
function encodeWavFromMonoPcm(samples: Float32Array, sampleRate: number): Blob {
  const bytesPerSample = 2
  const blockAlign = bytesPerSample
  const buffer = new ArrayBuffer(44 + samples.length * bytesPerSample)
  const view = new DataView(buffer)

  const writeString = (offset: number, value: string): void => {
    for (let i = 0; i < value.length; i++) {
      view.setUint8(offset + i, value.charCodeAt(i))
    }
  }

  writeString(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * bytesPerSample, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * blockAlign, true)
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, 16, true)
  writeString(36, 'data')
  view.setUint32(40, samples.length * bytesPerSample, true)

  let offset = 44
  for (let i = 0; i < samples.length; i++) {
    const normalized = Math.max(-1, Math.min(1, samples[i]))
    const pcm = normalized < 0 ? normalized * 0x8000 : normalized * 0x7fff
    view.setInt16(offset, pcm, true)
    offset += bytesPerSample
  }

  return new Blob([buffer], { type: 'audio/wav' })
}

/**
 * 高级音频预处理主函数
 */
export async function processAudioForASR(
  audioBlob: Blob,
  options: AudioProcessingOptions = {}
): Promise<Blob> {
  const {
    noiseReduction = true,   // 启用降噪
    normalizeVolume = true,  // 启用音量归一化
    highPassFilter = true,   // 启用高通滤波
    targetSampleRate = 16000,
  } = options

  console.log('processAudioForASR: Processing audio blob', {
    size: audioBlob.size,
    type: audioBlob.type,
    options
  })

  const AudioContextCtor = window.AudioContext || (window as any).webkitAudioContext
  if (!AudioContextCtor) {
    console.warn('AudioContext 不可用,返回原始音频')
    return audioBlob
  }

  const audioContext = new AudioContextCtor()

  try {
    // 1. 解码音频
    const arrayBuffer = await audioBlob.arrayBuffer()
    let audioBuffer = await audioContext.decodeAudioData(arrayBuffer.slice(0))
    console.log('Audio decoded:', {
      sampleRate: audioBuffer.sampleRate,
      channels: audioBuffer.numberOfChannels,
      duration: audioBuffer.duration
    })

    // 2. 应用高通滤波器(去除低频噪音)
    if (highPassFilter) {
      console.log('Applying high-pass filter...')
      audioBuffer = await applyHighPassFilter(audioBuffer)
    }

    // 3. 应用噪声门限
    if (noiseReduction) {
      console.log('Applying noise gate...')
      audioBuffer = await applyNoiseGate(audioBuffer)
    }

    // 4. 音量归一化
    if (normalizeVolume) {
      console.log('Applying volume normalization...')
      audioBuffer = await applyVolumeNormalization(audioBuffer)
    }

    // 5. 转换为单声道
    const mono = interleaveToMono(audioBuffer)
    console.log('Converted to mono, length:', mono.length)

    // 6. 重采样到目标采样率
    const resampled = resampleLinear(mono, audioBuffer.sampleRate, targetSampleRate)
    console.log('Resampled to', targetSampleRate, 'Hz, length:', resampled.length)

    // 7. 编码为WAV
    const result = encodeWavFromMonoPcm(resampled, targetSampleRate)
    console.log('Encoded to WAV, size:', result.size)
    return result
  } catch (error) {
    console.error('Audio processing failed:', error)
    throw error
  } finally {
    await audioContext.close()
  }
}

/**
 * 检测音频片段是否有效(包含足够的人声)
 */
export async function detectValidVoice(audioBlob: Blob): Promise<boolean> {
  const AudioContextCtor = window.AudioContext || (window as any).webkitAudioContext
  if (!AudioContextCtor) {
    return true // 无法检测时默认有效
  }

  const audioContext = new AudioContextCtor()

  try {
    const arrayBuffer = await audioBlob.arrayBuffer()
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer.slice(0))
    const data = audioBuffer.getChannelData(0)

    // 计算能量
    let energy = 0
    for (let i = 0; i < data.length; i++) {
      energy += data[i] * data[i]
    }
    const rms = Math.sqrt(energy / data.length)

    // RMS > 0.01 认为是有效语音
    return rms > 0.01
  } finally {
    await audioContext.close()
  }
}
