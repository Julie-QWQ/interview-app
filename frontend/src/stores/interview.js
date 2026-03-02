import { defineStore } from 'pinia'
import { ref, nextTick } from 'vue'
import { interviewApi } from '@/api/interview'
import voiceController from '@/utils/voiceController'

export const useInterviewStore = defineStore('interview', () => {
  const interviews = ref([])
  const currentInterview = ref(null)
  const messages = ref([]) // 线性消息列表（用于显示）
  const messageTree = ref({}) // 树型消息结构 { id: { id, parentId, content, role, timestamp, branchId, children: [] } }
  const currentBranchId = ref('main') // 当前活跃的分支ID
  const currentMessagePath = ref([]) // 当前活跃路径的消息ID列表
  const loading = ref(false)
  const currentStage = ref(null)
  const stageProgress = ref(null)
  const thinking = ref(false) // AI 思考状态
  const streamingMessage = ref('') // 正在流式输出的消息

  // 语音相关状态
  const isPlaying = ref(false) // 是否正在播放语音
  const currentPlayingMessageId = ref(null) // 当前播放的消息ID
  const isMuted = ref(false) // 是否静音

  // 生成唯一ID
  function generateId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  // Merge stream fragments safely:
  // - supports normal delta chunks
  // - tolerates duplicated/snapshotted chunks from server
  function mergeStreamingContent(previous = '', incoming = '') {
    if (!incoming) return previous
    if (!previous) return incoming
    if (incoming === previous) return previous
    if (previous.endsWith(incoming)) return previous
    if (incoming.endsWith(previous)) return incoming

    const maxOverlap = Math.min(previous.length, incoming.length)
    for (let i = maxOverlap; i > 0; i--) {
      if (previous.slice(-i) === incoming.slice(0, i)) {
        return previous + incoming.slice(i)
      }
    }
    return previous + incoming
  }

  // 获取面试列表
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

  // 创建面试
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

  // 获取面试详情
  async function fetchInterviewDetail(id) {
    loading.value = true
    try {
      const data = await interviewApi.getDetail(id)
      currentInterview.value = data

      // 转换消息为树型结构
      if (data.messages && data.messages.length > 0) {
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

  // 构建消息树（从后端返回的树形数据）
  function buildMessageTree(msgs, currentMessageId = null) {
    const tree = {}
    const linearMessages = []

    // 第一遍：创建所有节点，直接使用后端ID
    msgs.forEach((msg) => {
      const id = msg.id  // 直接使用后端的数字ID

      const node = {
        id,
        parentId: msg.parent_id,  // 直接使用后端的parent_id
        content: msg.content,
        role: msg.role,
        timestamp: msg.timestamp,
        branchId: msg.branch_id || 'main',
        is_active: msg.is_active,
        children: []
      }

      tree[id] = node
      linearMessages.push(node)
    })

    // 第二遍：建立父子关系(建立children数组)
    linearMessages.forEach((node) => {
      if (node.parentId && tree[node.parentId]) {
        if (!tree[node.parentId].children.includes(node.id)) {
          tree[node.parentId].children.push(node.id)
        }
      }
    })

    // 构建当前路径
    const currentPath = []
    const activeMessages = []

    // 如果指定了当前消息ID,则从该消息节点向上追溯到根节点
    if (currentMessageId && tree[currentMessageId]) {
      const reversePath = []
      let currentNode = tree[currentMessageId]

      // 向上追溯到根节点
      while (currentNode) {
        reversePath.push(currentNode)
        if (currentNode.parentId && tree[currentNode.parentId]) {
          currentNode = tree[currentNode.parentId]
        } else {
          break
        }
      }

      // 反转路径,得到从根到当前节点的正确顺序
      for (let i = reversePath.length - 1; i >= 0; i--) {
        const node = reversePath[i]
        currentPath.push(node.id)
        activeMessages.push(node)
      }
    } else {
      // 如果没有指定当前消息ID,则使用默认行为(沿着第一个子节点遍历到叶子节点)
      const rootNode = linearMessages.find(node => !node.parentId)
      if (rootNode) {
        let currentNode = rootNode
        while (currentNode) {
          currentPath.push(currentNode.id)
          activeMessages.push(currentNode)

          // 获取子节点
          const childrenIds = tree[currentNode.id]?.children || []
          if (childrenIds.length > 0) {
            // 选择第一个子节点继续遍历
            currentNode = tree[childrenIds[0]]
          } else {
            // 到达叶子节点
            break
          }
        }
      }
    }

    messageTree.value = tree
    messages.value = activeMessages
    currentBranchId.value = 'main'
    currentMessagePath.value = currentPath
  }

  // 开始面试
  async function startInterview(id) {
    loading.value = true
    try {
      const data = await interviewApi.start(id)
      await fetchInterviewDetail(id)

      // 如果返回了TTS音频,播放欢迎消息的语音
      if (data.welcome_audio && data.welcome_message && !isMuted.value) {
        // 使用 voiceController 播放欢迎消息
        voiceController.enqueue(data.welcome_audio, data.message_id)
        console.log('播放欢迎消息TTS')
      }

      return data
    } finally {
      loading.value = false
    }
  }

  // 添加消息到树
  function addMessageToTree(content, role, parentId = null) {
    const id = generateId()
    const lastNode = currentMessagePath.value.length > 0
      ? messageTree.value[currentMessagePath.value[currentMessagePath.value.length - 1]]
      : null

    // 如果没有指定 parentId，使用当前路径的最后一个节点
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

    // 建立父子关系
    if (actualParentId && messageTree.value[actualParentId]) {
      if (!messageTree.value[actualParentId].children) {
        messageTree.value[actualParentId].children = []
      }
      messageTree.value[actualParentId].children.push(id)
    }

    // 更新当前路径
    if (actualParentId) {
      const parentIndex = currentMessagePath.value.indexOf(actualParentId)
      if (parentIndex >= 0) {
        // 父节点在当前路径中，添加到路径末尾
        currentMessagePath.value = [...currentMessagePath.value.slice(0, parentIndex + 1), id]
      } else {
        // 父节点不在当前路径中（切换了分支）
        currentMessagePath.value.push(id)
      }
    } else {
      currentMessagePath.value = [id]
    }

    // 更新线性消息列表（显示当前路径）
    updateLinearMessages()

    return id
  }

  // 更新线性消息列表（显示当前活跃路径）
  function updateLinearMessages() {
    const linearMessages = currentMessagePath.value.map(id => messageTree.value[id]).filter(Boolean)
    // 使用 nextTick 确保响应式更新
    messages.value = linearMessages
  }

  // 发送消息（流式）
  async function sendMessage(id, content) {
    // 获取当前路径的最后一个节点作为父节点
    const lastNodeId = currentMessagePath.value.length > 0
      ? currentMessagePath.value[currentMessagePath.value.length - 1]
      : null

    // 停止当前语音播放（用户输入时）
    voiceController.stop()
    isPlaying.value = false
    currentPlayingMessageId.value = null

    // 添加用户消息到树
    const userId = addMessageToTree(content, 'user')

    // 添加一个临时的AI消息占位符
    const assistantId = generateId()
    const tempNode = {
      id: assistantId,
      parentId: userId,
      content: '',
      role: 'assistant',
      timestamp: new Date().toISOString(),
      branchId: currentBranchId.value,
      children: [],
      isStreaming: true
    }

    messageTree.value[assistantId] = tempNode

    // 建立父子关系
    if (!messageTree.value[userId].children) {
      messageTree.value[userId].children = []
    }
    messageTree.value[userId].children.push(assistantId)

    // 更新当前路径和线性显示
    currentMessagePath.value.push(assistantId)
    updateLinearMessages()

    thinking.value = true
    streamingMessage.value = ''

    return new Promise((resolve, reject) => {
      interviewApi.chatStream(
        id,
        content,
        // onChunk
        (chunk, audio) => {
          streamingMessage.value = mergeStreamingContent(streamingMessage.value, chunk)
          tempNode.content = streamingMessage.value

          // 如果有音频数据,播放语音
          if (audio && !isMuted.value) {
            voiceController.enqueue(audio, assistantId)
            isPlaying.value = voiceController.isPlaying
            currentPlayingMessageId.value = voiceController.currentMessageId
          }

          // 更新线性显示
          updateLinearMessages()
        },
        // onError
        (error) => {
          thinking.value = false
          tempNode.isStreaming = false
          tempNode.error = true
          voiceController.stop()
          isPlaying.value = false
          currentPlayingMessageId.value = null
          reject(error)
        },
        // onComplete
        (finalData) => {
          thinking.value = false
          tempNode.isStreaming = false
          tempNode.timestamp = new Date().toISOString()

          // 更新阶段和进度
          if (finalData.current_stage) {
            currentStage.value = finalData.current_stage
          }
          if (finalData.progress) {
            stageProgress.value = finalData.progress
          }

          // 监听语音播放结束
          if (voiceController.queue.length === 0) {
            isPlaying.value = false
            currentPlayingMessageId.value = null
          }

          resolve(finalData)
        },
        // options: 传递 parent_id 和 branch_id
        {
          // 只有当 lastNodeId 是纯数字且在合理范围内时才传递给后端
          parentId: (() => {
            if (!lastNodeId) return null
            // 检查是否为纯数字字符串
            if (/^\d+$/.test(lastNodeId)) {
              const num = parseInt(lastNodeId)
              // 检查是否在 INTEGER 范围内（-2147483648 到 2147483647）
              if (num >= -2147483648 && num <= 2147483647) {
                return num
              }
            }
            // 如果是临时 ID（包含横杠）或超出范围，返回 null
            return null
          })(),
          branchId: currentBranchId.value
        }
      )
    })
  }

  // 完成面试
  async function completeInterview(id) {
    loading.value = true
    try {
      const data = await interviewApi.complete(id)
      await fetchInterviewDetail(id)
      return data
    } finally {
      loading.value = false
    }
  }

  // 删除面试
  async function deleteInterview(id) {
    loading.value = true
    try {
      await interviewApi.delete(id)
      interviews.value = interviews.value.filter(i => i.id !== id)
      return true
    } finally {
      loading.value = false
    }
  }

  // 切换到指定消息节点（用于回溯或切换分支）
  async function switchToMessage(messageId) {
    const node = messageTree.value[messageId]
    if (!node) {
      console.error('Message not found:', messageId)
      return
    }

    // 计算从根到该节点的路径
    const path = []
    let currentNode = node
    while (currentNode) {
      path.unshift(currentNode.id)
      currentNode = currentNode.parentId ? messageTree.value[currentNode.parentId] : null
    }

    currentMessagePath.value = path

    // 如果该节点属于不同的分支，创建新分支
    if (node.branchId !== currentBranchId.value) {
      currentBranchId.value = `${currentBranchId.value}-${Date.now()}`
    }

    // 更新线性显示
    updateLinearMessages()

    // 如果是后端的消息ID（纯数字），更新数据库中的当前节点
    if (/^\d+$/.test(messageId)) {
      try {
        await interviewApi.updateCurrentMessage(currentInterview.value?.id, messageId)
        console.log('已更新当前消息节点:', messageId)
      } catch (error) {
        console.error('更新当前消息节点失败:', error)
      }
    }
  }

  // 创建新分支（回溯后发送消息时调用）
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

    // 停止语音播放
    voiceController.stop()
    isPlaying.value = false
    currentPlayingMessageId.value = null
    isMuted.value = false
  }

  // 语音控制函数
  function toggleMute() {
    isMuted.value = voiceController.toggleMute()
    if (isMuted.value) {
      isPlaying.value = false
      currentPlayingMessageId.value = null
    }
  }

  function setMute(muted) {
    isMuted.value = voiceController.setMute(muted)
    if (isMuted.value) {
      isPlaying.value = false
      currentPlayingMessageId.value = null
    }
  }

  function stopVoice() {
    voiceController.stop()
    isPlaying.value = false
    currentPlayingMessageId.value = null
  }

  // 截断消息到指定索引（已弃用，保留兼容性）
  function truncateMessages(index) {
    // 在树型结构中，这个方法不再需要
    console.warn('truncateMessages is deprecated in tree structure')
  }

  // 切换到指定节点的分支
  async function switchToBranch(nodeId) {
    console.log('switchToBranch: switching to node', nodeId)

    // 检查节点是否存在
    if (!messageTree.value[nodeId]) {
      console.error('Node not found:', nodeId)
      return
    }

    // 第一步：从该节点往上追溯到根节点，构建完整路径（反向）
    const reversePath = []
    let currentNode = messageTree.value[nodeId]

    while (currentNode) {
      reversePath.push(currentNode)

      // 如果有父节点，继续往上追溯
      if (currentNode.parentId && messageTree.value[currentNode.parentId]) {
        currentNode = messageTree.value[currentNode.parentId]
      } else {
        // 到达根节点
        break
      }
    }

    // 第二步：反转路径，得到从根到该节点的正确顺序
    const newPath = []
    const newMessages = []

    for (let i = reversePath.length - 1; i >= 0; i--) {
      const node = reversePath[i]
      newPath.push(node.id)
      newMessages.push(node)
    }

    // 更新当前路径和消息显示
    currentMessagePath.value = newPath
    messages.value = newMessages

    console.log('switchToBranch: new path', newPath)
    console.log('switchToBranch: new messages count', newMessages.length)
    console.log('switchToBranch: messages', newMessages.map(m => ({ id: m.id, role: m.role, content: m.content.substring(0, 30) })))

    // 如果是后端的消息ID（纯数字），更新数据库中的当前节点
    if (/^\d+$/.test(nodeId) && currentInterview.value?.id) {
      try {
        await interviewApi.updateCurrentMessage(currentInterview.value.id, nodeId)
        console.log('已更新当前消息节点:', nodeId)
      } catch (error) {
        console.error('更新当前消息节点失败:', error)
      }
    }
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
    // 语音相关状态
    isPlaying,
    currentPlayingMessageId,
    isMuted,
    fetchInterviews,
    createInterview,
    fetchInterviewDetail,
    startInterview,
    sendMessage,
    completeInterview,
    deleteInterview,
    clearCurrentInterview,
    switchToMessage,
    createNewBranch,
    truncateMessages,
    switchToBranch,
    // 语音控制函数
    toggleMute,
    setMute,
    stopVoice
  }
})
