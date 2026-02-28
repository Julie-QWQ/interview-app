import { defineStore } from 'pinia'
import { ref } from 'vue'
import { interviewApi } from '@/api/interview'

export const useInterviewStore = defineStore('interview', () => {
  const interviews = ref([])
  const currentInterview = ref(null)
  const messages = ref([])
  const loading = ref(false)
  const currentStage = ref(null)
  const stageProgress = ref(null)

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
      messages.value = data.messages || []
      currentStage.value = data.current_stage || null
      stageProgress.value = data.stage_progress || null
      return data
    } finally {
      loading.value = false
    }
  }

  // 开始面试
  async function startInterview(id) {
    loading.value = true
    try {
      const data = await interviewApi.start(id)
      // 添加欢迎消息
      if (data.welcome_message) {
        messages.value.push({
          role: 'assistant',
          content: data.welcome_message,
          timestamp: new Date().toISOString()
        })
      }
      await fetchInterviewDetail(id)
      return data
    } finally {
      loading.value = false
    }
  }

  // 发送消息
  async function sendMessage(id, content) {
    loading.value = true
    try {
      // 先添加用户消息
      messages.value.push({
        role: 'user',
        content,
        timestamp: new Date().toISOString()
      })

      const data = await interviewApi.chat(id, content)
      // 添加AI回复
      messages.value.push({
        role: 'assistant',
        content: data.content,
        timestamp: new Date().toISOString()
      })
      // 更新阶段和进度
      if (data.current_stage) {
        currentStage.value = data.current_stage
      }
      if (data.progress) {
        stageProgress.value = data.progress
      }
      return data
    } finally {
      loading.value = false
    }
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

  function clearCurrentInterview() {
    currentInterview.value = null
    messages.value = []
    currentStage.value = null
    stageProgress.value = null
  }

  return {
    interviews,
    currentInterview,
    messages,
    loading,
    currentStage,
    stageProgress,
    fetchInterviews,
    createInterview,
    fetchInterviewDetail,
    startInterview,
    sendMessage,
    completeInterview,
    deleteInterview,
    clearCurrentInterview
  }
})
