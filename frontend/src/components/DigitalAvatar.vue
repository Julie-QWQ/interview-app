<template>
  <div class="digital-avatar-container">
    <!-- 视频播放器 (为将来集成 HeyGem 预留) -->
    <video
      v-if="currentVideoUrl"
      :key="currentVideoUrl"
      :src="currentVideoUrl"
      autoplay
      muted
      playsinline
      @ended="handleVideoEnd"
      @error="handleVideoError"
      class="avatar-video"
      :class="{ 'video-playing': isPlaying }"
    />

    <!-- 生成中状态 -->
    <div v-else-if="isGenerating" class="loading-state">
      <el-icon class="is-loading" :size="40"><Loading /></el-icon>
      <p class="loading-text">数字人生成中...</p>
      <el-progress :percentage="generationProgress" :show-text="false" />
    </div>

    <!-- 静态头像 (当前使用方案) -->
    <div v-else class="static-avatar-container">
      <!-- 使用 Element Plus 的用户图标作为头像 -->
      <div class="avatar-icon" :class="{ 'speaking': isPlaying }">
        <el-icon :size="80"><User /></el-icon>
      </div>
      <!-- 呼吸动画覆盖层 -->
      <div class="breathing-overlay" v-show="isPlaying"></div>
    </div>

    <!-- 状态标签 -->
    <div class="status-badge" :class="statusClass">
      {{ statusText }}
    </div>

    <!-- 降级提示 -->
    <el-alert
      v-if="videoError"
      type="info"
      :closable="false"
      show-icon
      class="info-alert"
    >
      数字人功能待配置,当前使用语音模式
    </el-alert>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Loading, User } from '@element-plus/icons-vue'

// Props
const props = defineProps({
  isSpeaking: {
    type: Boolean,
    default: false
  },
  isThinking: {
    type: Boolean,
    default: false
  },
  currentText: {
    type: String,
    default: ''
  },
  videoUrl: {
    type: String,
    default: ''
  }
})

// 状态
const currentVideoUrl = ref('')
const isGenerating = ref(false)
const generationProgress = ref(0)
const videoError = ref(false)
const isPlaying = ref(false)

// 计算属性
const statusText = computed(() => {
  if (props.isThinking) return '思考中...'
  if (isGenerating.value) return '生成中'
  if (props.isSpeaking) return '说话中'
  return '倾听中'
})

const statusClass = computed(() => {
  if (props.isThinking || isGenerating.value) return 'status-thinking'
  if (props.isSpeaking) return 'status-speaking'
  return 'status-listening'
})

// 监听视频URL变化 (为将来集成 HeyGem 准备)
watch(() => props.videoUrl, (newUrl) => {
  if (newUrl && newUrl !== currentVideoUrl.value) {
    console.log('收到新的视频URL:', newUrl)
    isGenerating.value = true
    generationProgress.value = 0

    // 模拟加载进度
    const progressInterval = setInterval(() => {
      if (generationProgress.value < 90) {
        generationProgress.value += 10
      }
    }, 200)

    // 加载视频
    const video = document.createElement('video')
    video.src = newUrl
    video.onloadeddata = () => {
      clearInterval(progressInterval)
      generationProgress.value = 100
      setTimeout(() => {
        currentVideoUrl.value = newUrl
        isGenerating.value = false
        isPlaying.value = true
      }, 500)
    }
    video.onerror = () => {
      clearInterval(progressInterval)
      isGenerating.value = false
      videoError.value = true
      console.error('视频加载失败')
    }
  }
})

// 监听说话状态
watch(() => props.isSpeaking, (speaking) => {
  isPlaying.value = speaking
})

// 方法
function handleVideoEnd() {
  isPlaying.value = false
}

function handleVideoError() {
  videoError.value = true
  isPlaying.value = false
  currentVideoUrl.value = ''
}
</script>

<style scoped>
.digital-avatar-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8eaf0 100%);
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  min-width: 280px;
  width: 100%;
}

/* 视频播放器样式 (为将来预留) */
.avatar-video {
  width: 100%;
  max-width: 400px;
  border-radius: 12px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
}

.avatar-video.video-playing {
  box-shadow: 0 8px 16px rgba(76, 175, 80, 0.3);
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 40px 20px;
  width: 100%;
}

.loading-text {
  font-size: 14px;
  color: #666;
  margin: 0;
}

/* 静态头像容器 */
.static-avatar-container {
  position: relative;
  width: 180px;
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 头像图标 */
.avatar-icon {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  transition: all 0.3s ease;
}

.avatar-icon.speaking {
  animation: pulse 1.5s ease-in-out infinite;
  box-shadow: 0 8px 16px rgba(76, 175, 80, 0.4);
}

/* 呼吸动画覆盖层 */
.breathing-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 160px;
  height: 160px;
  background: radial-gradient(circle, rgba(76, 175, 80, 0.15) 0%, transparent 70%);
  border-radius: 50%;
  animation: breathe 3s ease-in-out infinite;
  pointer-events: none;
}

@keyframes breathe {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0.5;
  }
  50% {
    transform: translate(-50%, -50%) scale(1.1);
    opacity: 0.8;
  }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

/* 状态标签 */
.status-badge {
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  text-align: center;
  min-width: 80px;
  transition: all 0.3s ease;
}

.status-listening {
  background: #E3F2FD;
  color: #1976D2;
}

.status-speaking {
  background: #E8F5E9;
  color: #388E3C;
}

.status-thinking {
  background: #FFF3E0;
  color: #F57C00;
}

/* 提示信息 */
.info-alert {
  width: 100%;
  margin-top: 8px;
  font-size: 12px;
}

/* 响应式 */
@media (max-width: 768px) {
  .digital-avatar-container {
    min-width: auto;
    padding: 16px;
  }

  .avatar-video {
    max-width: 100%;
  }

  .static-avatar-container {
    width: 140px;
    height: 140px;
  }

  .avatar-icon {
    width: 100px;
    height: 100px;
  }

  .breathing-overlay {
    width: 120px;
    height: 120px;
  }
}
</style>
