<template>
  <div class="profile-selector">
    <el-tabs v-model="activeTab" class="selector-tabs">
      <el-tab-pane label="岗位画像" name="position">
        <div v-loading="loading" class="plugin-grid">
          <div
            v-for="plugin in positionPlugins"
            :key="plugin.plugin_id"
            :class="['plugin-card', { active: modelValue.position?.plugin_id === plugin.plugin_id }]"
            @click="selectPosition(plugin)"
          >
            <div class="plugin-icon">
              <el-icon><Briefcase /></el-icon>
            </div>
            <h4>{{ plugin.name }}</h4>
            <p class="description">{{ plugin.description }}</p>
            <div class="plugin-meta">
              <el-tag v-if="plugin.is_system" size="small" type="info">系统预设</el-tag>
              <el-tag v-else size="small">自定义</el-tag>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="面试官画像" name="interviewer">
        <div v-loading="loading" class="plugin-grid">
          <div
            v-for="plugin in interviewerPlugins"
            :key="plugin.plugin_id"
            :class="['plugin-card', { active: modelValue.interviewer?.plugin_id === plugin.plugin_id }]"
            @click="selectInterviewer(plugin)"
          >
            <div v-if="plugin.config?.display_image_url" class="interviewer-visual">
              <img :src="plugin.config.display_image_url" :alt="plugin.name" class="interviewer-image" />
            </div>
            <div class="plugin-icon">
              <el-icon><User /></el-icon>
            </div>
            <h4>{{ plugin.name }}</h4>
            <p class="description">{{ plugin.description }}</p>
            <p class="prompt-preview">{{ getPromptPreview(plugin.config?.prompt) }}</p>
            <div class="plugin-meta">
              <el-tag size="small">{{ getToneLabel(plugin.config?.style_tone) }}</el-tag>
              <el-tag size="small" type="warning">{{ getDifficultyLabel(plugin.config?.difficulty) }}</el-tag>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Briefcase, User } from '@element-plus/icons-vue'
import { profileApi } from '@/api/profile'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({ position: null, interviewer: null })
  }
})

const emit = defineEmits(['update:modelValue'])

const activeTab = ref('position')
const loading = ref(false)
const positionPlugins = ref([])
const interviewerPlugins = ref([])

async function loadPlugins() {
  loading.value = true
  try {
    const [positionRes, interviewerRes] = await Promise.all([
      profileApi.listPlugins({ type: 'position' }),
      profileApi.listPlugins({ type: 'interviewer' })
    ])

    if (positionRes.success) {
      positionPlugins.value = positionRes.data
    }
    if (interviewerRes.success) {
      interviewerPlugins.value = interviewerRes.data
    }
  } catch (error) {
    console.error('加载画像列表失败', error)
  } finally {
    loading.value = false
  }
}

function selectPosition(plugin) {
  emit('update:modelValue', {
    ...props.modelValue,
    position: plugin
  })
}

function selectInterviewer(plugin) {
  emit('update:modelValue', {
    ...props.modelValue,
    interviewer: plugin
  })
}

function getPromptPreview(prompt) {
  const text = String(prompt || '').trim()
  if (!text) return '未配置面试官风格'
  return text.length > 48 ? `${text.slice(0, 48)}...` : text
}

function getToneLabel(tone) {
  const toneMap = {
    gentle: '平和',
    balanced: '平衡',
    strict: '严格'
  }
  return toneMap[tone] || '平衡'
}

function getDifficultyLabel(difficulty) {
  const difficultyMap = {
    basic: '低难度',
    standard: '中难度',
    challenging: '高难度'
  }
  return difficultyMap[difficulty] || '中难度'
}

onMounted(() => {
  loadPlugins()
})

defineExpose({
  refresh: loadPlugins
})
</script>

<style scoped lang="scss">
.profile-selector {
  .selector-tabs {
    :deep(.el-tabs__header) {
      margin-bottom: 20px;
    }
  }

  .plugin-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
    min-height: 200px;
  }

  .plugin-card {
    background: var(--bg-white);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    padding: 20px;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      border-color: var(--primary-color);
      box-shadow: var(--shadow-md);
    }

    &.active {
      border-color: var(--primary-color);
      background: var(--primary-light);

      .plugin-icon {
        background: var(--primary-color);
        color: white;
      }
    }
  }

  .plugin-icon {
    width: 48px;
    height: 48px;
    border-radius: var(--radius-lg);
    background: var(--bg-gray);
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 12px;
    color: var(--primary-color);
    font-size: 20px;
    transition: all 0.2s ease;
  }

  .interviewer-visual {
    width: 100%;
    aspect-ratio: 16 / 10;
    border-radius: 16px;
    overflow: hidden;
    margin-bottom: 12px;
    background: #f3f4f6;
  }

  .interviewer-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  h4 {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 8px 0;
    text-align: center;
  }

  .description,
  .prompt-preview {
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.5;
    text-align: center;
    margin-bottom: 12px;
  }

  .description {
    min-height: 40px;
  }

  .prompt-preview {
    min-height: 40px;
  }

  .plugin-meta {
    display: flex;
    gap: 8px;
    justify-content: center;
    align-items: center;
    flex-wrap: wrap;
  }
}
</style>
