<template>
  <div class="xunfei-digital-human">
    <iframe
      v-if="renderFrame"
      v-show="!error"
      :key="iframeKey"
      ref="runtimeFrame"
      class="avatar-runtime-frame"
      title="xunfei-digital-human-runtime"
      :srcdoc="iframeSrcdoc"
      allow="autoplay; microphone"
    ></iframe>

    <div v-show="!isVideoReady && !error" class="loading-placeholder">
      <el-icon class="is-loading" :size="60">
        <Loading />
      </el-icon>
      <p>coming...</p>
    </div>

    <div v-if="error" class="error-message">
      <el-alert
        :title="error"
        type="error"
        :closable="false"
        show-icon
        center
      />
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, toRaw, watch } from 'vue'
import { Loading } from '@element-plus/icons-vue'

const props = defineProps({
  sessionId: {
    type: String,
    required: true
  },
  config: {
    type: Object,
    required: true
  },
  autoStart: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['ready', 'error', 'status-change'])

const runtimeFrame = ref(null)
const renderFrame = ref(true)
const iframeReady = ref(false)
const isVideoReady = ref(false)
const error = ref('')
const iframeKey = ref(0)
const runtimeInitialized = ref(false)
const currentFrameToken = ref(0)
const destroyed = ref(false)
const audioUnlocked = ref(false)
const userGestureCaptured = ref(false)

const commandSeq = ref(0)
const pendingCommands = new Map()

const AVATAR_VISUAL_SCALE = 1.32
const MESSAGE_SOURCE_PARENT = 'xunfei-avatar-parent'
const MESSAGE_SOURCE_CHILD = 'xunfei-avatar-iframe'

const iframeSrcdoc = computed(() => `<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
      html, body {
        margin: 0;
        width: 100%;
        height: 100%;
        overflow: hidden;
        background: linear-gradient(180deg, #d7dbe2 0%, #c9ced6 100%);
      }

      #player-root {
        width: 100%;
        height: 100%;
        overflow: hidden;
        transform: scale(${AVATAR_VISUAL_SCALE});
        transform-origin: center bottom;
      }
    </style>
  </head>
  <body>
    <div id="player-root"></div>
    <script type="module">
      import AvatarPlatform from '/avatar-sdk-web_3.2.1.1016/esm/index.js';

      (() => {
        const PCM_SAMPLE_RATE = 16000;
        const AUDIO_FRAME_START = 0;
        const AUDIO_FRAME_INTERMEDIATE = 1;
        const AUDIO_FRAME_END = 2;
        const AUDIO_CHUNK_DURATION_MS = 40;
        const AUDIO_CHUNK_SAMPLES = (PCM_SAMPLE_RATE * AUDIO_CHUNK_DURATION_MS) / 1000;
        const AVATAR_FRAME_WIDTH = 1080;
        const AVATAR_FRAME_HEIGHT = 1920;
        const MESSAGE_SOURCE_PARENT = '${MESSAGE_SOURCE_PARENT}';
        const MESSAGE_SOURCE_CHILD = '${MESSAGE_SOURCE_CHILD}';

        const playerRoot = document.getElementById('player-root');
        let avatarPlatform = null;
        let sharedAudioContext = null;

        function post(type, payload = {}) {
          window.parent.postMessage({
            source: MESSAGE_SOURCE_CHILD,
            type,
            ...payload
          }, '*');
        }

        function resetPlayerRoot() {
          if (playerRoot) {
            playerRoot.replaceChildren();
          }
        }

        function serializeError(err) {
          if (!err) {
            return { message: 'Unknown error' };
          }
          if (typeof err === 'string') {
            return { message: err };
          }
          return {
            message: err.message || 'Unknown error',
            stack: err.stack || ''
          };
        }

        async function getAudioContext() {
          if (!sharedAudioContext) {
            sharedAudioContext = new (window.AudioContext || window.webkitAudioContext)({
              sampleRate: PCM_SAMPLE_RATE
            });
          }

          if (sharedAudioContext.state === 'suspended') {
            await sharedAudioContext.resume();
          }

          return sharedAudioContext;
        }

        async function closeAudioContext() {
          if (!sharedAudioContext) {
            return;
          }
          try {
            await sharedAudioContext.close();
          } catch (err) {
            console.warn('[XunfeiDigitalHumanFrame] AudioContext close failed', err);
          }
          sharedAudioContext = null;
        }

        async function streamPcmAudio(pcmData) {
          const totalChunks = Math.ceil(pcmData.length / AUDIO_CHUNK_SAMPLES);

          for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex += 1) {
            const start = chunkIndex * AUDIO_CHUNK_SAMPLES;
            const end = Math.min(start + AUDIO_CHUNK_SAMPLES, pcmData.length);
            const chunk = pcmData.slice(start, end);

            let frameStatus = AUDIO_FRAME_INTERMEDIATE;
            if (totalChunks === 1) {
              frameStatus = AUDIO_FRAME_END;
            } else if (chunkIndex === 0) {
              frameStatus = AUDIO_FRAME_START;
            } else if (chunkIndex === totalChunks - 1) {
              frameStatus = AUDIO_FRAME_END;
            }

            await avatarPlatform.writeAudio(
              chunk.buffer,
              frameStatus,
              {
                sample_rate: PCM_SAMPLE_RATE,
                audio: {
                  sample_rate: PCM_SAMPLE_RATE,
                  channels: 1,
                  bit_depth: 16
                },
                avatar_dispatch: {
                  audio_mode: 1
                },
                full_duplex: 1
              }
            );

            if (chunkIndex < totalChunks - 1) {
              await new Promise(resolve => window.setTimeout(resolve, AUDIO_CHUNK_DURATION_MS));
            }
          }
        }

        async function destroyRuntime() {
          if (!avatarPlatform) {
            resetPlayerRoot();
            await closeAudioContext();
            return;
          }

          try {
            if (typeof avatarPlatform.interrupt === 'function') {
              await avatarPlatform.interrupt();
            }
          } catch (err) {
            console.warn('[XunfeiDigitalHumanFrame] interrupt before destroy failed', err);
          }

          try {
            if (typeof avatarPlatform.removeAllListeners === 'function') {
              avatarPlatform.removeAllListeners();
            }
          } catch (err) {
            console.warn('[XunfeiDigitalHumanFrame] removeAllListeners failed', err);
          }

          try {
            if (avatarPlatform.player && typeof avatarPlatform.player.stop === 'function') {
              avatarPlatform.player.stop();
            }
          } catch (err) {
            console.warn('[XunfeiDigitalHumanFrame] player stop failed', err);
          }

          try {
            if (typeof avatarPlatform.stop === 'function') {
              await avatarPlatform.stop();
            }
          } catch (err) {
            console.warn('[XunfeiDigitalHumanFrame] stop failed', err);
          }

          try {
            if (typeof avatarPlatform.destroy === 'function') {
              await avatarPlatform.destroy();
            }
          } catch (err) {
            console.warn('[XunfeiDigitalHumanFrame] destroy failed', err);
          }

          avatarPlatform = null;
          resetPlayerRoot();
          await closeAudioContext();
        }

        async function initializeRuntime(payload) {
          const config = payload.config || {};

          await destroyRuntime();
          resetPlayerRoot();

          avatarPlatform = new AvatarPlatform({
            useInlinePlayer: true,
            logLevel: 2
          });

          avatarPlatform.on('connected', () => {
            post('ready');
          });

          avatarPlatform.on('stream_start', () => {
            post('stream-start');
          });

          avatarPlatform.on('frame_start', () => {
            post('status-change', { status: 'SPEAKING' });
          });

          avatarPlatform.on('frame_stop', () => {
            post('status-change', { status: 'LISTENING' });
          });

          avatarPlatform.on('disconnected', () => {
            post('status-change', { status: 'LISTENING' });
          });

          avatarPlatform.on('error', err => {
            post('runtime-error', {
              error: serializeError(err)
            });
          });

          avatarPlatform.setApiInfo({
            appId: config.appId,
            apiKey: config.apiKey,
            apiSecret: config.apiSecret,
            sceneId: config.sceneId || 'default'
          });

          avatarPlatform.setGlobalParams({
            stream: {
              protocol: 'xrtc'
            },
            avatar: {
              avatar_id: config.avatarId || 'xiaofeng',
              width: AVATAR_FRAME_WIDTH,
              height: AVATAR_FRAME_HEIGHT
            },
            tts: {
              vcn: config.vcn || 'xiaofeng',
              speed: 50,
              pitch: 50,
              volume: 50
            },
            audio: {
              sample_rate: PCM_SAMPLE_RATE,
              channels: 1,
              bit_depth: 16
            }
          });

          await avatarPlatform.start({
            wrapper: playerRoot
          });

          try {
            if (avatarPlatform.player) {
              avatarPlatform.player.muted = true;
              avatarPlatform.player.volume = 1;
            }
          } catch (err) {
            console.warn('[XunfeiDigitalHumanFrame] player state sync failed', err);
          }
        }

        async function unlockRuntimeAudio() {
          if (!avatarPlatform) {
            return;
          }

          try {
            await getAudioContext();
          } catch (err) {
            console.warn('[XunfeiDigitalHumanFrame] shared audio context unlock failed', err);
          }

          try {
            if (avatarPlatform.player) {
              avatarPlatform.player.muted = false;
              avatarPlatform.player.volume = 1;
              // Only resume if the player has an active stream
              if (typeof avatarPlatform.player.resume === 'function' &&
                  avatarPlatform.player.srcObject ||
                  avatarPlatform.player.readyState >= 2) { // HAVE_CURRENT_DATA
                try {
                  await avatarPlatform.player.resume();
                } catch (resumeErr) {
                  // Ignore "stream not found" errors - stream may not be ready yet
                  if (!resumeErr?.message?.includes('stream not found')) {
                    console.warn('[XunfeiDigitalHumanFrame] player resume failed', resumeErr);
                  }
                }
              }
            }
          } catch (err) {
            console.warn('[XunfeiDigitalHumanFrame] player unlock failed', err);
            throw err;
          }
        }

        async function speakText(payload) {
          if (!avatarPlatform) {
            throw new Error('Digital human SDK is not initialized');
          }

          const content = String(payload.text || '').trim();
          if (!content) {
            return;
          }

          await avatarPlatform.writeText(content, {
            tts: {
              vcn: payload.vcn || 'xiaofeng',
              audio: {
                sample_rate: payload.sampleRate || PCM_SAMPLE_RATE
              }
            },
            avatar_dispatch: {
              interactive_mode: 1
            }
          });
        }

        async function speakAudio(payload) {
          if (!avatarPlatform) {
            throw new Error('Digital human SDK is not initialized');
          }

          const binaryString = window.atob(payload.audioData);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i += 1) {
            bytes[i] = binaryString.charCodeAt(i);
          }

          const audioContext = await getAudioContext();
          const audioBuffer = await audioContext.decodeAudioData(bytes.buffer);
          const length = audioBuffer.length;
          const numberOfChannels = audioBuffer.numberOfChannels;
          const pcmData = new Int16Array(length);

          if (numberOfChannels === 1) {
            const channelData = audioBuffer.getChannelData(0);
            for (let i = 0; i < length; i += 1) {
              const sample = Math.max(-1, Math.min(1, channelData[i]));
              pcmData[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
            }
          } else {
            for (let i = 0; i < length; i += 1) {
              let mixedSample = 0;
              for (let channel = 0; channel < numberOfChannels; channel += 1) {
                mixedSample += audioBuffer.getChannelData(channel)[i];
              }
              mixedSample /= numberOfChannels;
              const sample = Math.max(-1, Math.min(1, mixedSample));
              pcmData[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
            }
          }

          await streamPcmAudio(pcmData);
        }

        async function interruptRuntime() {
          if (!avatarPlatform) {
            return;
          }
          await avatarPlatform.interrupt();
          post('status-change', { status: 'LISTENING' });
        }

        window.addEventListener('message', async event => {
          if (event.source !== window.parent) {
            return;
          }
          if (!event.data || event.data.source !== MESSAGE_SOURCE_PARENT) {
            return;
          }

          const { command, requestId, payload } = event.data;

          try {
            let result = null;
            if (command === 'init') {
              await initializeRuntime(payload || {});
            } else if (command === 'unlockAudio') {
              await unlockRuntimeAudio();
            } else if (command === 'speakText') {
              await speakText(payload || {});
            } else if (command === 'speakAudio') {
              await speakAudio(payload || {});
            } else if (command === 'interrupt') {
              await interruptRuntime();
            } else if (command === 'destroy') {
              await destroyRuntime();
            } else {
              throw new Error('Unsupported command: ' + command);
            }

            post('command-result', { requestId, result });
          } catch (err) {
            post('command-error', {
              requestId,
              error: serializeError(err)
            });
          }
        });

        window.addEventListener('beforeunload', () => {
          destroyRuntime();
        });

        post('iframe-ready');
      })();
    <\/script>
  </body>
</html>`)

function buildSerializableConfig(config) {
  const rawConfig = toRaw(config || {})
  return {
    appId: rawConfig.appId || '',
    apiKey: rawConfig.apiKey || '',
    apiSecret: rawConfig.apiSecret || '',
    sceneId: rawConfig.sceneId || '',
    avatarId: rawConfig.avatarId || '',
    vcn: rawConfig.vcn || '',
    sampleRate: rawConfig.sampleRate || 16000
  }
}

function rejectPendingCommands(message = 'Digital human runtime reset') {
  for (const { reject, timer } of pendingCommands.values()) {
    window.clearTimeout(timer)
    reject(new Error(message))
  }
  pendingCommands.clear()
}

function isIgnorableRuntimeError(err) {
  const message = String(err?.message || err || '')
  return (
    message.includes('Digital human runtime reset') ||
    message.includes('Digital human runtime iframe is unavailable') ||
    message.includes('Digital human runtime iframe load timed out')
  )
}

function waitForIframeReady(timeoutMs = 30000) { // 从10秒增加到30秒
  if (destroyed.value) {
    return Promise.reject(new Error('Digital human runtime reset'))
  }

  if (iframeReady.value && runtimeFrame.value?.contentWindow) {
    return Promise.resolve()
  }

  return new Promise((resolve, reject) => {
    const startedAt = Date.now()
    const timer = window.setInterval(() => {
      if (iframeReady.value && runtimeFrame.value?.contentWindow) {
        window.clearInterval(timer)
        resolve()
        return
      }

      if (Date.now() - startedAt > timeoutMs) {
        window.clearInterval(timer)
        reject(new Error('Digital human runtime iframe load timed out'))
        return
      }

      if (destroyed.value) {
        window.clearInterval(timer)
        reject(new Error('Digital human runtime reset'))
      }
    }, 50)
  })
}

async function recreateRuntimeFrame() {
  destroyed.value = false
  currentFrameToken.value += 1
  iframeReady.value = false
  isVideoReady.value = false
  runtimeInitialized.value = false
  error.value = ''
  rejectPendingCommands()
  renderFrame.value = false
  runtimeFrame.value = null
  await nextTick()
  await new Promise(resolve => window.setTimeout(resolve, 120))
  renderFrame.value = true
  iframeKey.value += 1
  await nextTick()
  await waitForIframeReady()
}

async function sendCommand(command, payload = {}, timeoutMs = 20000) {
  await waitForIframeReady()

  const frameWindow = runtimeFrame.value?.contentWindow
  if (!frameWindow) {
    throw new Error('Digital human runtime iframe is unavailable')
  }

  const requestId = `${command}-${Date.now()}-${commandSeq.value += 1}`

  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      pendingCommands.delete(requestId)
      reject(new Error(`Digital human command timed out: ${command}`))
    }, timeoutMs)

    pendingCommands.set(requestId, {
      resolve,
      reject,
      timer
    })

    frameWindow.postMessage({
      source: MESSAGE_SOURCE_PARENT,
      command,
      requestId,
      payload
    }, '*')
  })
}

function sendCommandDirect(command, payload = {}, timeoutMs = 8000) {
  const frameWindow = runtimeFrame.value?.contentWindow
  if (!frameWindow) {
    return Promise.reject(new Error('Digital human runtime iframe is unavailable'))
  }

  const requestId = `${command}-${Date.now()}-${commandSeq.value += 1}`

  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      pendingCommands.delete(requestId)
      reject(new Error(`Digital human command timed out: ${command}`))
    }, timeoutMs)

    pendingCommands.set(requestId, {
      resolve,
      reject,
      timer
    })

    frameWindow.postMessage({
      source: MESSAGE_SOURCE_PARENT,
      command,
      requestId,
      payload
    }, '*')
  })
}

async function initialize() {
  if (!props.sessionId) {
    return
  }

  destroyed.value = false
  error.value = ''
  isVideoReady.value = false

  // 增加初始化超时时间到60秒，因为讯飞数字人连接较慢
  await sendCommand('init', {
    sessionId: props.sessionId,
    config: buildSerializableConfig(props.config)
  }, 60000) // 从默认20秒增加到60秒

  runtimeInitialized.value = true
  if (userGestureCaptured.value) {
    await unlockAudio()
  }
}

async function ensureInitialized() {
  if (!runtimeInitialized.value) {
    await initialize()
  }
}

async function unlockAudio() {
  userGestureCaptured.value = true

  if (!runtimeInitialized.value || audioUnlocked.value) {
    return
  }

  try {
    await sendCommand('unlockAudio', {}, 8000)
    audioUnlocked.value = true
  } catch (err) {
    const message = String(err?.message || err || '')
    // Ignore "stream not found" and "NotAllowedError" - stream may not be ready yet
    // The audio will be unlocked when the stream is actually needed
    if (!message.includes('NotAllowedError') && !message.includes('stream not found')) {
      console.warn('[XunfeiDigitalHuman] unlock audio failed', err)
    }
    // Still mark as unlocked to avoid repeated attempts
    audioUnlocked.value = true
  }
}

async function speak(audioData) {
  await ensureInitialized()
  await unlockAudio()
  await sendCommand('speakAudio', {
    audioData
  }, 40000)
}

async function speakText(text) {
  const content = String(text || '').trim()
  if (!content) {
    return
  }

  await ensureInitialized()
  await unlockAudio()
  await sendCommand('speakText', {
    text: content,
    vcn: buildSerializableConfig(props.config).vcn,
    sampleRate: buildSerializableConfig(props.config).sampleRate
  }, 30000)
}

async function interrupt() {
  if (!runtimeInitialized.value) {
    return
  }

  await sendCommand('interrupt')
}

async function destroy() {
  destroyed.value = true
  try {
    if (!renderFrame.value || !iframeReady.value || !runtimeFrame.value?.contentWindow) {
      return
    }
    await sendCommandDirect('destroy', {}, 8000)
  } catch (destroyError) {
    const message = String(destroyError?.message || '')
    if (
      !message.includes('iframe is unavailable') &&
      !message.includes('Digital human runtime reset')
    ) {
      console.warn('[XunfeiDigitalHuman] destroy command failed', destroyError)
    }
  } finally {
    runtimeInitialized.value = false
    audioUnlocked.value = false
    isVideoReady.value = false
    iframeReady.value = false
    rejectPendingCommands()
  }
}

function handleUserGesture() {
  userGestureCaptured.value = true
  void unlockAudio()
}

function handleFrameMessage(event) {
  const frameWindow = runtimeFrame.value?.contentWindow
  if (!frameWindow || event.source !== frameWindow) {
    return
  }

  const message = event.data
  if (!message || message.source !== MESSAGE_SOURCE_CHILD) {
    return
  }

  if (message.type === 'iframe-ready') {
    iframeReady.value = true
    return
  }

  if (message.type === 'command-result') {
    const pending = pendingCommands.get(message.requestId)
    if (!pending) {
      return
    }
    window.clearTimeout(pending.timer)
    pendingCommands.delete(message.requestId)
    pending.resolve(message.result)
    return
  }

  if (message.type === 'command-error') {
    const pending = pendingCommands.get(message.requestId)
    const err = new Error(message.error?.message || 'Digital human runtime error')
    if (pending) {
      window.clearTimeout(pending.timer)
      pendingCommands.delete(message.requestId)
      pending.reject(err)
    }
    error.value = err.message
    emit('error', err)
    return
  }

  if (message.type === 'ready') {
    emit('ready')
    return
  }

  if (message.type === 'stream-start') {
    isVideoReady.value = true
    return
  }

  if (message.type === 'status-change') {
    emit('status-change', message.status)
    return
  }

  if (message.type === 'runtime-error') {
    const err = new Error(message.error?.message || 'Digital human runtime error')
    error.value = err.message
    emit('error', err)
  }
}

async function bootstrapRuntime() {
  await recreateRuntimeFrame()
  if (props.autoStart && props.sessionId) {
    await initialize()
  }
}

onMounted(async () => {
  window.addEventListener('message', handleFrameMessage)
  window.addEventListener('pointerdown', handleUserGesture, { passive: true })
  window.addEventListener('keydown', handleUserGesture)
  try {
    await bootstrapRuntime()
  } catch (err) {
    if (!isIgnorableRuntimeError(err)) {
      console.error('[XunfeiDigitalHuman] bootstrap failed', err)
      error.value = String(err?.message || err || 'Initialization failed')
      emit('error', err)
    }
  }
})

onBeforeUnmount(async () => {
  window.removeEventListener('message', handleFrameMessage)
  window.removeEventListener('pointerdown', handleUserGesture)
  window.removeEventListener('keydown', handleUserGesture)
  await destroy()
})

watch(
  () => props.sessionId,
  async newSessionId => {
    if (!newSessionId) {
      await destroy()
      return
    }

    try {
      await bootstrapRuntime()
    } catch (err) {
      if (!isIgnorableRuntimeError(err)) {
        console.error('[XunfeiDigitalHuman] session switch bootstrap failed', err)
        error.value = String(err?.message || err || 'Initialization failed')
        emit('error', err)
      }
    }
  }
)

watch(
  () => props.config,
  async (newConfig, oldConfig) => {
    if (!props.autoStart || !props.sessionId) {
      return
    }

    if (JSON.stringify(newConfig || {}) === JSON.stringify(oldConfig || {})) {
      return
    }

    try {
      await bootstrapRuntime()
    } catch (err) {
      if (!isIgnorableRuntimeError(err)) {
        console.error('[XunfeiDigitalHuman] config switch bootstrap failed', err)
        error.value = String(err?.message || err || 'Initialization failed')
        emit('error', err)
      }
    }
  },
  { deep: true }
)

defineExpose({
  initialize,
  unlockAudio,
  speak,
  speakText,
  interrupt,
  destroy
})
</script>

<style scoped>
.xunfei-digital-human {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #d7dbe2 0%, #c9ced6 100%);
}

.avatar-runtime-frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  background: transparent;
}

.loading-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 40px 20px;
  color: #5b6472;
}

.loading-placeholder p {
  margin: 0;
  font-size: 14px;
}

.error-message {
  position: absolute;
  left: 50%;
  top: 50%;
  width: min(260px, calc(100% - 24px));
  transform: translate(-50%, -50%);
  z-index: 2;
}
</style>
