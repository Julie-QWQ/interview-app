<template>
  <div class="report-page">
    <section class="report-card">
      <h1>面试报告</h1>
      <p>当前页面仅提供历史对话导出能力。</p>

      <el-button type="primary" :loading="exporting" @click="handleExport">
        导出对话
      </el-button>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { interviewApi } from '@/api/interview'

const route = useRoute()
const exporting = ref(false)
const interviewId = computed(() => Number(route.params.id))

function downloadHistoryExport(historyExport) {
  const exportedAt = (historyExport.exported_at || new Date().toISOString()).replace(/[:]/g, '-')
  const filename = `interview-history-${historyExport.interview_id || interviewId.value}-${exportedAt}.json`
  const content = JSON.stringify(historyExport, null, 2)
  const blob = new Blob([content], { type: 'application/json;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

async function handleExport() {
  exporting.value = true
  try {
    const data = await interviewApi.exportHistory(interviewId.value)
    downloadHistoryExport(data)
    ElMessage.success('对话导出成功')
  } catch (error) {
    console.error('导出对话失败', error)
  } finally {
    exporting.value = false
  }
}
</script>

<style scoped lang="scss">
.report-page {
  padding: 16px;
}

.report-card {
  max-width: 520px;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 12px;
  padding: 20px;

  h1 {
    margin: 0 0 10px;
    font-size: 22px;
  }

  p {
    margin: 0 0 16px;
    color: #606266;
  }
}
</style>
