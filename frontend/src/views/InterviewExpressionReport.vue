<template>
  <div class="report-page">
    <section class="report-header">
      <div>
        <h2>表达分析报告</h2>
        <p>{{ interviewTitle }}</p>
      </div>
      <div class="header-actions">
        <el-button @click="$router.push('/interviews')">返回列表</el-button>
        <el-button type="primary" @click="goInterview">进入面试</el-button>
      </div>
    </section>

    <el-skeleton v-if="loading" :rows="8" animated />

    <template v-else-if="report">
      <section class="score-grid">
        <el-card shadow="never" class="score-card primary">
          <div class="score-label">总体表达评分</div>
          <div class="score-value">{{ report.overall_score }}</div>
          <div class="score-meta">置信度 {{ report.confidence_level }} / {{ report.confidence_score }}</div>
        </el-card>

        <el-card shadow="never" class="score-card">
          <div class="score-label">流利度</div>
          <div class="score-value">{{ report.dimension_scores?.fluency ?? '-' }}</div>
        </el-card>
        <el-card shadow="never" class="score-card">
          <div class="score-label">清晰度</div>
          <div class="score-value">{{ report.dimension_scores?.clarity ?? '-' }}</div>
        </el-card>
        <el-card shadow="never" class="score-card">
          <div class="score-label">自信度</div>
          <div class="score-value">{{ report.dimension_scores?.confidence ?? '-' }}</div>
        </el-card>
        <el-card shadow="never" class="score-card">
          <div class="score-label">沉着度</div>
          <div class="score-value">{{ report.dimension_scores?.composure ?? '-' }}</div>
        </el-card>
      </section>

      <section class="content-grid">
        <el-card shadow="never" class="panel-card">
          <template #header>结论摘要</template>
          <p class="summary-text">{{ report.narrative_summary || '暂无摘要' }}</p>
          <div class="coverage">
            <el-tag size="small" :type="report.modality_coverage?.audio ? 'success' : 'info'">音频</el-tag>
            <el-tag size="small" :type="report.modality_coverage?.video ? 'success' : 'info'">视频</el-tag>
            <el-tag size="small" :type="report.modality_coverage?.text ? 'success' : 'info'">文本</el-tag>
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <template #header>证据摘要</template>
          <ul class="plain-list">
            <li v-for="(item, index) in report.evidence_summary || []" :key="index">{{ item }}</li>
          </ul>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <template #header>风险提示</template>
          <ul class="plain-list">
            <li v-for="(item, index) in report.risk_flags || []" :key="index">{{ item }}</li>
          </ul>
          <div v-if="!report.risk_flags?.length" class="empty-text">未发现明显风险提示</div>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <template #header>关键指标</template>
          <div class="metrics-grid">
            <div class="metric-item">
              <span>语音段数</span>
              <strong>{{ report.metrics?.audio?.segment_count ?? 0 }}</strong>
            </div>
            <div class="metric-item">
              <span>视频窗口数</span>
              <strong>{{ report.metrics?.video?.window_count ?? 0 }}</strong>
            </div>
            <div class="metric-item">
              <span>平均语速</span>
              <strong>{{ formatMetric(report.metrics?.audio?.speech_rate_wpm) }}</strong>
            </div>
            <div class="metric-item">
              <span>停顿占比</span>
              <strong>{{ formatMetric(report.metrics?.audio?.avg_pause_ratio, 2) }}</strong>
            </div>
            <div class="metric-item">
              <span>视线偏移率</span>
              <strong>{{ formatMetric(report.metrics?.video?.gaze_aversion_rate, 2) }}</strong>
            </div>
            <div class="metric-item">
              <span>头部抖动</span>
              <strong>{{ formatMetric(report.metrics?.video?.head_jitter, 3) }}</strong>
            </div>
          </div>
        </el-card>
      </section>
    </template>

    <el-empty v-else description="报告暂不可用" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { interviewApi } from '@/api/interview'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const report = ref(null)
const interview = ref(null)

const interviewId = computed(() => Number(route.params.id))
const interviewTitle = computed(() => {
  if (!interview.value) return '面试报告'
  return `${interview.value.candidate_name} / ${interview.value.position}`
})

onMounted(async () => {
  await loadPage()
})

async function loadPage() {
  loading.value = true
  try {
    interview.value = await interviewApi.getDetail(interviewId.value)
    report.value = await interviewApi.getExpressionReport(interviewId.value)
  } catch (error) {
    console.error('加载表达分析报告失败', error)
    ElMessage.error('加载表达分析报告失败')
  } finally {
    loading.value = false
  }
}

function goInterview() {
  router.push(`/interviews/${interviewId.value}`)
}

function formatMetric(value, digits = 0) {
  if (value === undefined || value === null || Number.isNaN(Number(value))) return '-'
  return Number(value).toFixed(digits)
}
</script>

<style scoped lang="scss">
.report-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 18px 20px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--line-color);
  background: linear-gradient(135deg, #fff9ef 0%, #f6f7fb 100%);

  h2 {
    margin: 0;
    font-size: 24px;
    color: var(--text-primary);
  }

  p {
    margin: 6px 0 0;
    color: var(--text-secondary);
  }
}

.header-actions {
  display: flex;
  gap: 10px;
}

.score-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.score-card {
  border-radius: var(--radius-lg);

  &.primary {
    background: linear-gradient(135deg, #16324f 0%, #235789 100%);
    color: #fff;
  }
}

.score-label {
  font-size: 13px;
  opacity: 0.8;
}

.score-value {
  margin-top: 10px;
  font-size: 36px;
  font-weight: 700;
}

.score-meta {
  margin-top: 8px;
  font-size: 12px;
  opacity: 0.8;
}

.content-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.panel-card {
  border-radius: var(--radius-lg);
}

.summary-text {
  margin: 0;
  line-height: 1.7;
  color: var(--text-primary);
}

.coverage {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.plain-list {
  margin: 0;
  padding-left: 18px;
  color: var(--text-primary);

  li + li {
    margin-top: 8px;
  }
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.metric-item {
  padding: 12px;
  border-radius: 12px;
  background: #f6f7fb;
  display: flex;
  justify-content: space-between;
  gap: 12px;

  span {
    color: var(--text-secondary);
  }

  strong {
    color: var(--text-primary);
  }
}

.empty-text {
  color: var(--text-secondary);
}

@media (max-width: 960px) {
  .score-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>
