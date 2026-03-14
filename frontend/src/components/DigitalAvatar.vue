<template>
  <div class="digital-avatar-container">
    <div class="avatar-stage">
      <XunfeiDigitalHuman
        v-if="provider === 'xunfei' && sessionId"
        ref="xunfeiDigitalHumanRef"
        :session-id="sessionId"
        :config="digitalHumanConfig"
        :auto-start="true"
        class="avatar-video"
        @ready="handleDigitalHumanReady"
        @error="handleDigitalHumanError"
        @status-change="handleStatusChange"
      />

      <div v-else-if="showErrorState" class="avatar-state">
        <div class="avatar-icon">
          <el-icon :size="80"><User /></el-icon>
        </div>
        <el-alert
          :title="displayErrorMessage"
          type="info"
          :closable="false"
          show-icon
          center
          class="center-error-alert"
        />
      </div>

      <div v-else class="avatar-state">
        <div class="avatar-icon" :class="{ speaking: isSpeakingVisual }">
          <el-icon :size="80"><User /></el-icon>
        </div>
        <div v-show="isSpeakingVisual" class="breathing-overlay"></div>
      </div>
    </div>

    <div class="status-badge" :class="statusClass">
      {{ statusText }}
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { User } from '@element-plus/icons-vue'
import XunfeiDigitalHuman from './XunfeiDigitalHuman.vue'

const emit = defineEmits(['ready', 'error', 'status-change'])

const props = defineProps({
  sessionId: {
    type: String,
    default: null
  },
  digitalHumanConfig: {
    type: Object,
    default: null
  },
  provider: {
    type: String,
    default: 'xunfei'
  },
  isSpeaking: {
    type: Boolean,
    default: false
  },
  isThinking: {
    type: Boolean,
    default: false
  },
  errorMessage: {
    type: String,
    default: ''
  }
})

const videoError = ref(false)
const isVideoPlaying = ref(false)
const xunfeiDigitalHumanRef = ref(null)

const displayErrorMessage = computed(() => {
  return props.errorMessage || (videoError.value ? '数字人连接失败，请检查配置' : '')
})

const showErrorState = computed(() => Boolean(displayErrorMessage.value))
const isSpeakingVisual = computed(() => isVideoPlaying.value || props.isSpeaking)

const statusText = computed(() => {
  if (showErrorState.value) return '数字人异常'
  if (props.isThinking) return 'thinking...'
  if (isVideoPlaying.value) return 'speaking...'
  if (props.isSpeaking) return 'speaking...'
  return 'listening...'
})

const statusClass = computed(() => {
  if (showErrorState.value || props.isThinking) return 'status-thinking'
  if (isVideoPlaying.value || props.isSpeaking) return 'status-speaking'
  return 'status-listening'
})

function handleDigitalHumanReady() {
  isVideoPlaying.value = false
  videoError.value = false
  emit('ready')
}

function handleDigitalHumanError(error) {
  console.error('[DigitalAvatar] xunfei digital human error:', error)
  videoError.value = true
  emit('error', error)
}

function handleStatusChange(status) {
  if (status === 'SPEAKING') {
    isVideoPlaying.value = true
  } else if (status === 'LISTENING') {
    isVideoPlaying.value = false
  }
  emit('status-change', status)
}

async function destroy() {
  if (!xunfeiDigitalHumanRef.value) {
    return
  }

  await xunfeiDigitalHumanRef.value.destroy()
  isVideoPlaying.value = false
}

async function speakWithAudio(audioBase64) {
  if (!xunfeiDigitalHumanRef.value) {
    return
  }

  if (typeof xunfeiDigitalHumanRef.value.unlockAudio === 'function') {
    await xunfeiDigitalHumanRef.value.unlockAudio()
  }
  await xunfeiDigitalHumanRef.value.speak(audioBase64)
  isVideoPlaying.value = true
}

async function speakText(text) {
  if (!xunfeiDigitalHumanRef.value) {
    return
  }

  if (typeof xunfeiDigitalHumanRef.value.unlockAudio === 'function') {
    await xunfeiDigitalHumanRef.value.unlockAudio()
  }
  await xunfeiDigitalHumanRef.value.speakText(text)
  isVideoPlaying.value = true
}

async function interrupt() {
  if (!xunfeiDigitalHumanRef.value) {
    return
  }

  await xunfeiDigitalHumanRef.value.interrupt()
  isVideoPlaying.value = false
}

async function unlockAudio() {
  if (!xunfeiDigitalHumanRef.value?.unlockAudio) {
    return
  }

  await xunfeiDigitalHumanRef.value.unlockAudio()
}

defineExpose({
  destroy,
  speakWithAudio,
  speakText,
  interrupt,
  unlockAudio
})

watch(() => props.sessionId, newSessionId => {
  console.log('[DigitalAvatar] sessionId changed:', newSessionId)
})

watch(() => props.provider, newProvider => {
  console.log('[DigitalAvatar] provider changed:', newProvider)
})
</script>

<style scoped>
.digital-avatar-container {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
}

.avatar-stage {
  position: relative;
  flex: 1;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: linear-gradient(180deg, #d7dbe2 0%, #c9ced6 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.35);
}

.avatar-video {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  background: linear-gradient(180deg, #d7dbe2 0%, #c9ced6 100%);
  transition: all 0.3s ease;
}

.avatar-state {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-icon {
  display: grid;
  place-items: center;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  color: #475569;
  background: rgba(255, 255, 255, 0.35);
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.16);
  z-index: 1;
}

.avatar-icon.speaking {
  animation: pulse 1.2s ease-in-out infinite;
}

.breathing-overlay {
  position: absolute;
  inset: 18% 22%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(14, 165, 233, 0.24) 0%, rgba(14, 165, 233, 0) 70%);
  animation: breathe 2.4s ease-in-out infinite;
}

.center-error-alert {
  position: absolute;
  left: 50%;
  bottom: 24px;
  width: min(420px, calc(100% - 32px));
  transform: translateX(-50%);
}

.status-badge {
  position: absolute;
  top: 18px;
  right: 18px;
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  backdrop-filter: blur(8px);
}

.status-speaking {
  color: #92400e;
  background: rgba(254, 243, 199, 0.88);
}

.status-thinking {
  color: #1d4ed8;
  background: rgba(219, 234, 254, 0.88);
}

.status-listening {
  color: #166534;
  background: rgba(220, 252, 231, 0.88);
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.04);
  }
}

@keyframes breathe {
  0%,
  100% {
    opacity: 0.35;
    transform: scale(0.96);
  }
  50% {
    opacity: 0.75;
    transform: scale(1.04);
  }
}
</style>
