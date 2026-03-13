import { defineStore } from 'pinia'
import { ref } from 'vue'
import { interviewApi } from '@/api/interview'

function normalizeAvatarError(error = '') {
  const text = String(error || '').trim()
  if (!text) return ''

  const lower = text.toLowerCase()
  if (lower.includes('not enough credits') || lower.includes('http 402')) {
    return '数字人额度不足'
  }
  if (lower.includes('unauthorized') || lower.includes('http 401')) {
    return '数字人鉴权失败，请检查 D-ID 配置'
  }
  if (lower.includes('timeout') || lower.includes('超时')) {
    return '数字人生超时'
  }
  return text
}

export const useInterviewStore = defineStore('interview', () => {
  const interviews = ref([])
  const currentInterview = ref(null)
  const messages = ref([])
  const messageTree = ref({})
  const currentBranchId = ref('main')
  const currentMessagePath = ref([])
  const loading = ref(false)
  const currentStage = ref(null)
  const stageProgress = ref(null)
  const thinking = ref(false)
  const streamingMessage = ref('')
  const isPlaying = ref(false)
  const currentPlayingMessageId = ref(null)
  const isMuted = ref(false)
  const digitalHumanReady = ref(false)
  const digitalHumanAvailable = ref(false)
  const digitalHumanError = ref('')
  const activeSpeechMode = ref('none')
  const sessionId = ref(null)
  const digitalHumanConfig = ref(null)
  const provider = ref('xunfei')
  const avatarStatus = ref('LISTENING')

  function generateId() {
    return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
  }

  function mergeStreamingContent(previous = '', incoming = '') {
    if (!incoming) return previous
    if (!previous) return incoming
    if (incoming === previous) return previous
    if (previous.endsWith(incoming)) return previous
    if (incoming.endsWith(previous)) return incoming

    const maxOverlap = Math.min(previous.length, incoming.length)
    for (let i = maxOverlap; i > 0; i -= 1) {
      if (previous.slice(-i) === incoming.slice(0, i)) {
        return previous + incoming.slice(i)
      }
    }
    return previous + incoming
  }

  function ensureAvatarState(node) {
    if (!node.avatarSegments) {
      node.avatarSegments = []
    }
    if (!Object.prototype.hasOwnProperty.call(node, 'avatarError')) {
      node.avatarError = ''
    }
    return node.avatarSegments
  }

  function upsertAvatarSegment(node, segment) {
    const segments = ensureAvatarState(node)
    const existingIndex = segments.findIndex(item => item.segmentIndex === segment.segmentIndex)
    const normalizedSegment = {
      segmentIndex: segment.segmentIndex,
      status: segment.status || 'pending',
      content: segment.content || '',
      videoUrl: segment.videoUrl || '',
      error: segment.error || '',
      generationTime: segment.generationTime ?? null
    }

    if (existingIndex >= 0) {
      segments.splice(existingIndex, 1, {
        ...segments[existingIndex],
        ...normalizedSegment
      })
    } else {
      segments.push(normalizedSegment)
    }

    segments.sort((a, b) => a.segmentIndex - b.segmentIndex)
  }

  function resetSpeechState() {
    activeSpeechMode.value = 'none'
    isPlaying.value = false
    currentPlayingMessageId.value = null
    if (!thinking.value) {
      avatarStatus.value = 'LISTENING'
    }
  }

  function setDigitalHumanReady(ready) {
    digitalHumanReady.value = Boolean(ready)
    if (digitalHumanReady.value) {
      digitalHumanAvailable.value = true
      digitalHumanError.value = ''
      if (activeSpeechMode.value === 'none' && !thinking.value) {
        avatarStatus.value = 'LISTENING'
      }
    }
  }

  function setDigitalHumanError(error = '') {
    digitalHumanError.value = normalizeAvatarError(error)
    digitalHumanReady.value = false
    digitalHumanAvailable.value = false
  }

  function setAvatarStatus(status) {
    avatarStatus.value = status
    if (status === 'SPEAKING') {
      activeSpeechMode.value = 'digital_human'
      isPlaying.value = true
      return
    }

    if (status === 'LISTENING' && activeSpeechMode.value === 'digital_human') {
      resetSpeechState()
    }
  }

  function beginAssistantSpeech(messageId = null) {
    activeSpeechMode.value = 'digital_human'
    currentPlayingMessageId.value = messageId || null
    isPlaying.value = true
    avatarStatus.value = 'THINKING'
  }

  function finishAssistantSpeech() {
    resetSpeechState()
  }

  function interruptAssistant() {
    const mode = activeSpeechMode.value
    activeSpeechMode.value = 'none'
    isPlaying.value = false
    currentPlayingMessageId.value = null
    avatarStatus.value = 'INTERRUPTED'
    return { mode }
  }

  async function fetchInterviews(params = {}) {
    loading.value = true
    try {
      const data = await interviewApi.list(params)
      interviews.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  async function createInterview(data) {
    loading.value = true
    try {
      const result = await interviewApi.create(data)
      await fetchInterviews()
      return result
    } finally {
      loading.value = false
    }
  }

  async function fetchInterviewDetail(id) {
    loading.value = true
    try {
      const data = await interviewApi.getDetail(id)
      currentInterview.value = data

      if (Array.isArray(data.messages) && data.messages.length > 0) {
        buildMessageTree(data.messages, data.current_message_id)
      } else {
        messages.value = []
        messageTree.value = {}
        currentBranchId.value = 'main'
        currentMessagePath.value = []
      }

      currentStage.value = data.current_stage || null
      stageProgress.value = data.stage_progress || null
      return data
    } finally {
      loading.value = false
    }
  }

  function buildMessageTree(msgs, currentMessageId = null) {
    const tree = {}
    const linearMessages = []

    msgs.forEach((msg) => {
      const node = {
        id: msg.id,
        parentId: msg.parent_id,
        content: msg.content,
        role: msg.role,
        timestamp: msg.timestamp,
        branchId: msg.branch_id || 'main',
        is_active: msg.is_active,
        children: [],
        avatarSegments: [],
        avatarError: ''
      }

      tree[node.id] = node
      linearMessages.push(node)
    })

    linearMessages.forEach((node) => {
      if (node.parentId && tree[node.parentId] && !tree[node.parentId].children.includes(node.id)) {
        tree[node.parentId].children.push(node.id)
      }
    })

    const currentPath = []
    const activeMessages = []

    if (currentMessageId && tree[currentMessageId]) {
      const reversePath = []
      let currentNode = tree[currentMessageId]

      while (currentNode) {
        reversePath.push(currentNode)
        currentNode = currentNode.parentId ? tree[currentNode.parentId] : null
      }

      for (let i = reversePath.length - 1; i >= 0; i -= 1) {
        const node = reversePath[i]
        currentPath.push(node.id)
        activeMessages.push(node)
      }
    } else {
      const rootNode = linearMessages.find(node => !node.parentId)
      let currentNode = rootNode || null

      while (currentNode) {
        currentPath.push(currentNode.id)
        activeMessages.push(currentNode)

        const childId = tree[currentNode.id]?.children?.[0]
        currentNode = childId ? tree[childId] : null
      }
    }

    messageTree.value = tree
    messages.value = activeMessages
    currentBranchId.value = 'main'
    currentMessagePath.value = currentPath
  }

  async function startInterview(id) {
    loading.value = true
    try {
      const data = await interviewApi.start(id)
      await fetchInterviewDetail(id)

      const welcomeMessage = messages.value.find(message => message.role === 'assistant')
      if (welcomeMessage) {
        const welcomeSegments = Array.isArray(data.welcome_avatar_segments)
          ? data.welcome_avatar_segments
          : []

        if (welcomeSegments.length > 0) {
          welcomeSegments.forEach(segment => {
            upsertAvatarSegment(welcomeMessage, {
              segmentIndex: segment.segment_index ?? 0,
              status: segment.status || 'ready',
              content: segment.content || data.welcome_message || '',
              videoUrl: segment.video_url || '',
              error: segment.error || '',
              generationTime: segment.generation_time ?? null
            })
          })
        } else if (data.welcome_video) {
          upsertAvatarSegment(welcomeMessage, {
            segmentIndex: 0,
            status: 'ready',
            content: data.welcome_message || '',
            videoUrl: data.welcome_video
          })
        }

        if (data.welcome_avatar_error) {
          welcomeMessage.avatarError = normalizeAvatarError(data.welcome_avatar_error)
        }
      }

      return data
    } finally {
      loading.value = false
    }
  }

  async function initAvatarSession(interviewId) {
    try {
      const response = await interviewApi.createAvatarSession(interviewId)
      if (response.success) {
        provider.value = response.provider || 'xunfei'
        sessionId.value = response.session_id
        digitalHumanConfig.value = response.config
        avatarStatus.value = 'LISTENING'
        return response
      }

      provider.value = 'disabled'
      sessionId.value = null
      digitalHumanConfig.value = null
      return response
    } catch (error) {
      provider.value = 'disabled'
      sessionId.value = null
      digitalHumanConfig.value = null
      throw error
    }
  }

  function addMessageToTree(content, role, parentId = null) {
    const id = generateId()
    const lastNode = currentMessagePath.value.length > 0
      ? messageTree.value[currentMessagePath.value[currentMessagePath.value.length - 1]]
      : null
    const actualParentId = parentId || (lastNode ? lastNode.id : null)

    const node = {
      id,
      parentId: actualParentId,
      content,
      role,
      timestamp: new Date().toISOString(),
      branchId: currentBranchId.value,
      children: []
    }

    messageTree.value[id] = node

    if (actualParentId && messageTree.value[actualParentId]) {
      if (!messageTree.value[actualParentId].children) {
        messageTree.value[actualParentId].children = []
      }
      messageTree.value[actualParentId].children.push(id)
    }

    if (actualParentId) {
      const parentIndex = currentMessagePath.value.indexOf(actualParentId)
      if (parentIndex >= 0) {
        currentMessagePath.value = [...currentMessagePath.value.slice(0, parentIndex + 1), id]
      } else {
        currentMessagePath.value = [...currentMessagePath.value, id]
      }
    } else {
      currentMessagePath.value = [id]
    }

    updateLinearMessages()
    return id
  }

  function updateLinearMessages() {
    messages.value = currentMessagePath.value
      .map(id => messageTree.value[id])
      .filter(Boolean)
  }

  async function sendMessage(id, content, options = {}) {
    const lastNodeId = currentMessagePath.value.length > 0
      ? currentMessagePath.value[currentMessagePath.value.length - 1]
      : null

    const userId = addMessageToTree(content, 'user')
    const assistantId = generateId()
    const tempNode = {
      id: assistantId,
      parentId: userId,
      content: '',
      role: 'assistant',
      timestamp: new Date().toISOString(),
      branchId: currentBranchId.value,
      children: [],
      isStreaming: true,
      avatarSegments: [],
      avatarError: ''
    }

    messageTree.value[assistantId] = tempNode

    if (!messageTree.value[userId].children) {
      messageTree.value[userId].children = []
    }
    messageTree.value[userId].children.push(assistantId)

    currentMessagePath.value.push(assistantId)
    updateLinearMessages()

    thinking.value = true
    streamingMessage.value = ''

    return new Promise((resolve, reject) => {
      interviewApi.chatStream(
        id,
        content,
        (chunk, audio, event = {}) => {
          void audio

          if (event.type === 'text_chunk' || (!event.type && chunk)) {
            streamingMessage.value = mergeStreamingContent(streamingMessage.value, chunk)
            tempNode.content = streamingMessage.value
          }

          if (event.type === 'avatar_segment_pending') {
            tempNode.avatarError = ''
            upsertAvatarSegment(tempNode, {
              segmentIndex: event.segment_index,
              status: 'pending',
              content: event.content || ''
            })
          }

          if (event.type === 'avatar_segment_ready') {
            tempNode.avatarError = ''
            upsertAvatarSegment(tempNode, {
              segmentIndex: event.segment_index,
              status: 'ready',
              content: event.content || '',
              videoUrl: event.video_url || '',
              generationTime: event.generation_time ?? null
            })
          }

          if (event.type === 'avatar_segment_failed') {
            tempNode.avatarError = normalizeAvatarError(event.error || '')
            upsertAvatarSegment(tempNode, {
              segmentIndex: event.segment_index,
              status: 'failed',
              content: event.content || '',
              error: normalizeAvatarError(event.error || '')
            })
          }

          updateLinearMessages()
        },
        (error) => {
          thinking.value = false
          tempNode.isStreaming = false
          tempNode.error = true
          reject(error)
        },
        (finalData) => {
          thinking.value = false
          tempNode.isStreaming = false
          tempNode.timestamp = new Date().toISOString()

          if (finalData?.current_stage) {
            currentStage.value = finalData.current_stage
          }
          if (finalData?.progress) {
            stageProgress.value = finalData.progress
          }

          resolve({
            ...finalData,
            reply: tempNode.content || streamingMessage.value || '',
            message_id: finalData?.message_id ?? assistantId,
            user_message_id: finalData?.user_message_id ?? userId
          })
        },
        {
          parentId: (() => {
            if (!lastNodeId) return null
            if (/^\d+$/.test(lastNodeId)) {
              const num = parseInt(lastNodeId, 10)
              if (num >= -2147483648 && num <= 2147483647) {
                return num
              }
            }
            return null
          })(),
          branchId: currentBranchId.value,
          source: options.source || 'text_input'
        }
      )
    })
  }

  async function completeInterview(id) {
    loading.value = true
    try {
      const data = await interviewApi.complete(id)

      if (currentInterview.value?.id === id) {
        currentInterview.value = {
          ...currentInterview.value,
          status: 'completed'
        }
      }
      interviews.value = interviews.value.map((item) =>
        item.id === id ? { ...item, status: 'completed' } : item
      )

      await fetchInterviewDetail(id)
      return data
    } finally {
      loading.value = false
    }
  }

  async function deleteInterview(id) {
    loading.value = true
    try {
      await interviewApi.delete(id)
      interviews.value = interviews.value.filter(item => item.id !== id)
      return true
    } finally {
      loading.value = false
    }
  }

  async function switchToMessage(messageId) {
    const node = messageTree.value[messageId]
    if (!node) {
      console.error('Message not found:', messageId)
      return
    }

    const path = []
    let currentNode = node
    while (currentNode) {
      path.unshift(currentNode.id)
      currentNode = currentNode.parentId ? messageTree.value[currentNode.parentId] : null
    }

    currentMessagePath.value = path

    if (node.branchId !== currentBranchId.value) {
      currentBranchId.value = `${currentBranchId.value}-${Date.now()}`
    }

    updateLinearMessages()

    if (/^\d+$/.test(String(messageId))) {
      try {
        await interviewApi.updateCurrentMessage(currentInterview.value?.id, messageId)
      } catch (error) {
        console.error('Failed to update current message:', error)
      }
    }
  }

  function createNewBranch(parentMessageId) {
    currentBranchId.value = `branch-${Date.now()}`
    switchToMessage(parentMessageId)
  }

  function clearCurrentInterview() {
    currentInterview.value = null
    messages.value = []
    messageTree.value = {}
    currentBranchId.value = 'main'
    currentMessagePath.value = []
    currentStage.value = null
    stageProgress.value = null
    thinking.value = false
    streamingMessage.value = ''
    activeSpeechMode.value = 'none'
    isPlaying.value = false
    currentPlayingMessageId.value = null
    isMuted.value = false
    sessionId.value = null
    digitalHumanConfig.value = null
    provider.value = 'xunfei'
    avatarStatus.value = 'LISTENING'
    digitalHumanReady.value = false
    digitalHumanAvailable.value = false
    digitalHumanError.value = ''
  }

  function truncateMessages() {
    console.warn('truncateMessages is deprecated in tree structure')
  }

  async function switchToBranch(nodeId) {
    if (!messageTree.value[nodeId]) {
      console.error('Node not found:', nodeId)
      return
    }

    const reversePath = []
    let currentNode = messageTree.value[nodeId]
    while (currentNode) {
      reversePath.push(currentNode)
      currentNode = currentNode.parentId ? messageTree.value[currentNode.parentId] : null
    }

    currentMessagePath.value = reversePath
      .slice()
      .reverse()
      .map(node => node.id)
    messages.value = reversePath
      .slice()
      .reverse()

    if (/^\d+$/.test(String(nodeId)) && currentInterview.value?.id) {
      try {
        await interviewApi.updateCurrentMessage(currentInterview.value.id, nodeId)
      } catch (error) {
        console.error('Failed to update current message:', error)
      }
    }
  }

  function toggleMute() {
    isMuted.value = !isMuted.value
    if (isMuted.value) {
      isPlaying.value = false
      currentPlayingMessageId.value = null
    }
  }

  function setMute(muted) {
    isMuted.value = Boolean(muted)
    if (isMuted.value) {
      isPlaying.value = false
      currentPlayingMessageId.value = null
    }
  }

  function stopVoice() {
    activeSpeechMode.value = 'none'
    isPlaying.value = false
    currentPlayingMessageId.value = null
  }

  return {
    interviews,
    currentInterview,
    messages,
    messageTree,
    currentBranchId,
    currentMessagePath,
    loading,
    currentStage,
    stageProgress,
    thinking,
    streamingMessage,
    isPlaying,
    currentPlayingMessageId,
    isMuted,
    digitalHumanReady,
    digitalHumanAvailable,
    digitalHumanError,
    sessionId,
    digitalHumanConfig,
    provider,
    avatarStatus,
    fetchInterviews,
    createInterview,
    fetchInterviewDetail,
    startInterview,
    initAvatarSession,
    sendMessage,
    completeInterview,
    deleteInterview,
    clearCurrentInterview,
    switchToMessage,
    createNewBranch,
    truncateMessages,
    switchToBranch,
    setAvatarStatus,
    setDigitalHumanReady,
    setDigitalHumanError,
    beginAssistantSpeech,
    finishAssistantSpeech,
    interruptAssistant,
    toggleMute,
    setMute,
    stopVoice
  }
})
