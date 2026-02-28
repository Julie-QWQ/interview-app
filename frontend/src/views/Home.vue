<template>
  <div class="home">
    <div class="hero-section">
      <h1 class="hero-title">欢迎使用AI面试系统</h1>
      <p class="hero-subtitle">智能化技术面试，提升招聘效率</p>
      <div class="hero-actions">
        <el-button type="primary" size="large" @click="$router.push('/interview/create')">
          <el-icon><Plus /></el-icon>
          创建面试
        </el-button>
        <el-button size="large" @click="$router.push('/interviews')">
          <el-icon><List /></el-icon>
          查看列表
        </el-button>
      </div>
    </div>

    <div class="features">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="8" v-for="feature in features" :key="feature.title">
          <div class="feature-card">
            <div class="feature-icon" :style="{ background: feature.color }">
              <el-icon :size="32">
                <component :is="feature.icon" />
              </el-icon>
            </div>
            <h3>{{ feature.title }}</h3>
            <p>{{ feature.description }}</p>
          </div>
        </el-col>
      </el-row>
    </div>

    <div class="stats-section">
      <el-row :gutter="20">
        <el-col :xs="12" :sm="6" v-for="stat in stats" :key="stat.label">
          <div class="stat-card">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Plus, List, ChatDotRound, DocumentChecked, TrendCharts, Setting } from '@element-plus/icons-vue'
import { useInterviewStore } from '@/stores/interview'

const interviewStore = useInterviewStore()

const features = ref([
  {
    icon: ChatDotRound,
    title: '智能对话',
    description: 'AI驱动的自然对话体验，根据岗位需求智能提问',
    color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
  },
  {
    icon: DocumentChecked,
    title: '自动评估',
    description: '多维度自动评估候选人能力，生成详细报告',
    color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
  },
  {
    icon: TrendCharts,
    title: '数据分析',
    description: '全面的面试数据分析，助力招聘决策',
    color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
  }
])

const stats = ref([
  { label: '总面试数', value: '-' },
  { label: '进行中', value: '-' },
  { label: '已完成', value: '-' },
  { label: '平均分', value: '-' }
])

onMounted(async () => {
  try {
    const interviews = await interviewStore.fetchInterviews()
    const total = interviews.length
    const inProgress = interviews.filter(i => i.status === 'in_progress').length
    const completed = interviews.filter(i => i.status === 'completed').length

    stats.value[0].value = total
    stats.value[1].value = inProgress
    stats.value[2].value = completed
  } catch (error) {
    console.error('获取统计数据失败', error)
  }
})
</script>

<style scoped lang="scss">
.home {
  max-width: 1000px;
  margin: 0 auto;
}

.hero-section {
  text-align: center;
  padding: 60px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 20px;
  color: white;
  margin-bottom: 40px;
}

.hero-title {
  font-size: 42px;
  font-weight: 700;
  margin-bottom: 16px;
}

.hero-subtitle {
  font-size: 20px;
  opacity: 0.9;
  margin-bottom: 32px;
}

.hero-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

.features {
  margin-bottom: 40px;
}

.feature-card {
  background: white;
  padding: 32px;
  border-radius: 16px;
  text-align: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transition: transform 0.3s, box-shadow 0.3s;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  }

  h3 {
    font-size: 20px;
    margin: 16px 0 8px;
  }

  p {
    color: #666;
    font-size: 14px;
    line-height: 1.6;
  }
}

.feature-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto;
  color: white;
}

.stats-section {
  background: white;
  padding: 32px;
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.stat-card {
  text-align: center;
  padding: 16px;

  .stat-value {
    font-size: 36px;
    font-weight: 700;
    color: #667eea;
    margin-bottom: 8px;
  }

  .stat-label {
    color: #666;
    font-size: 14px;
  }
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 32px;
  }

  .hero-subtitle {
    font-size: 16px;
  }
}
</style>
