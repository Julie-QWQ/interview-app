/**
 * 唇形同步工具
 * 基于文本生成嘴部动画帧,实现唇形同步效果
 */

/**
 * 元音列表 (包括中文拼音)
 * 用于判断字符发音时嘴部是否张开
 */
const VOWELS = /[aeiouāáǎàēéěèīíǐìōóǒòūúǔùüǖǘǚǜ]/i

/**
 * 生成唇形同步动画帧
 * @param {string} text - 要同步的文本
 * @param {number} duration - 音频时长(毫秒)
 * @returns {Array} 动画帧数组
 */
export function generateLipSyncFrames(text, duration) {
  if (!text || !duration) {
    return []
  }

  // 移除多余空格
  const cleanText = text.trim().replace(/\s+/g, ' ')
  const chars = cleanText.split('')
  const frames = []

  // 计算每个字符的时长
  const msPerChar = duration / chars.length

  chars.forEach((char, index) => {
    // 判断是否为元音(嘴部张开)
    const isOpen = VOWELS.test(char)

    frames.push({
      time: index * msPerChar,
      openness: isOpen ? 1 : 0.2, // 0-1, 1为完全张开, 0.2为微张
      duration: msPerChar,
      char: char
    })
  })

  return frames
}

/**
 * 根据时间获取当前嘴部开合度
 * @param {Array} frames - 动画帧数组
 * @param {number} currentTime - 当前时间(毫秒)
 * @returns {number} 嘴部开合度 (0-1)
 */
export function getMouthOpenness(frames, currentTime) {
  if (!frames || frames.length === 0) {
    return 0.2 // 默认微张状态
  }

  // 查找当前时间对应的帧
  const frame = frames.find(f =>
    currentTime >= f.time && currentTime < f.time + f.duration
  )

  return frame ? frame.openness : 0.2
}

/**
 * 简化版唇形同步 - 基于句子生成动画参数
 * 适用于不需要精确到字符的场景
 * @param {string} text - 文本内容
 * @returns {Object} 动画参数
 */
export function generateSimpleLipSync(text) {
  if (!text) {
    return {
      totalDuration: 0,
      speaking: false,
      intensity: 0
    }
  }

  // 估算阅读时长 (假设每分钟200字)
  const estimatedDuration = (text.length / 200) * 60 * 1000

  // 计算元音比例(用于判断嘴部动作强度)
  const vowelCount = (text.match(VOWELS) || []).length
  const intensity = Math.min(vowelCount / text.length, 1)

  return {
    totalDuration: estimatedDuration,
    speaking: true,
    intensity: intensity
  }
}

/**
 * 实时更新嘴部动画
 * @param {string} text - 当前说话内容
 * @param {number} progress - 播放进度 (0-1)
 * @returns {number} 嘴部开合度 (0-1)
 */
export function updateMouthAnimation(text, progress) {
  if (!text || progress <= 0 || progress >= 1) {
    return 0.2
  }

  // 使用正弦波模拟说话节奏
  const baseOpenness = 0.3
  const variation = 0.5

  // 结合文本长度和进度生成自然的说话节奏
  const frequency = 10 + (text.length % 5) // 变化的频率
  const openness = baseOpenness + variation * Math.sin(progress * frequency * Math.PI)

  return Math.max(0.1, Math.min(1, openness))
}

/**
 * 获取表情对应的嘴部基础状态
 * @param {string} mood - 表情类型
 * @returns {Object} 嘴部基础状态
 */
export function getMoodMouthState(mood = 'neutral') {
  const moodStates = {
    neutral: {
      baseOpenness: 0.2,
      cornerUp: 0,
      width: 1
    },
    happy: {
      baseOpenness: 0.3,
      cornerUp: 0.5,
      width: 1.2
    },
    thinking: {
      baseOpenness: 0.15,
      cornerUp: -0.1,
      width: 0.9
    },
    serious: {
      baseOpenness: 0.1,
      cornerUp: 0,
      width: 0.95
    },
    surprised: {
      baseOpenness: 0.6,
      cornerUp: 0.2,
      width: 1.1
    }
  }

  return moodStates[mood] || moodStates.neutral
}
