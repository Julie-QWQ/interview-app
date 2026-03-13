import { nextTick, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

export function useConversationNavigation({ interviewStore, messages, messagesContainer, scrollToBottom }) {
  const currentMessageIndex = ref(-1)

  function handleRestoreAllMessages() {
    currentMessageIndex.value = -1
    ElMessage.success('已恢复显示所有消息')
  }

  function handleLocateMessage(messageId) {
    const index = messages.value.findIndex(message => message.id === messageId)
    if (index < 0) {
      ElMessage.warning('消息不在当前显示的分支中')
      return
    }

    nextTick(() => {
      const messageElements = messagesContainer.value?.querySelectorAll('.message-wrapper')
      if (!messageElements?.[index]) {
        return
      }

      messageElements[index].scrollIntoView({ behavior: 'smooth', block: 'center' })
      messageElements[index].classList.add('highlight')
      window.setTimeout(() => {
        messageElements[index]?.classList.remove('highlight')
      }, 2000)
    })
  }

  async function handleSwitchToBranch(messageId) {
    try {
      await interviewStore.switchToBranch(messageId)
      ElMessage.success('已切换到该分支')
    } catch (error) {
      console.error('切换分支失败', error)
      ElMessage.error('切换分支失败')
    }
  }

  async function handleRewindToMessage(messageIndex) {
    try {
      const targetMessage = messages.value[messageIndex]
      await ElMessageBox.confirm(
        `确认回溯到第 ${messageIndex + 1} 条消息？这将把对话状态回溯到“${targetMessage.content.substring(0, 30)}...”，后续消息会被隐藏。从该位置继续发送会创建新的对话分支。`,
        '确认回溯',
        {
          confirmButtonText: '回溯',
          cancelButtonText: '取消',
          type: 'warning',
          dangerouslyUseHTMLString: false
        }
      )

      await interviewStore.switchToMessage(targetMessage.id)
      currentMessageIndex.value = messageIndex

      ElMessage.success(`已回溯到第 ${messageIndex + 1} 条消息，后续消息已隐藏`)
      scrollToBottom()
    } catch (error) {
      if (error !== 'cancel') {
        console.error('回溯失败', error)
        ElMessage.error('回溯失败')
      }
    }
  }

  return {
    currentMessageIndex,
    handleRestoreAllMessages,
    handleLocateMessage,
    handleSwitchToBranch,
    handleRewindToMessage
  }
}
