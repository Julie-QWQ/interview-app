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
            <div class="plugin-icon">
              <el-icon><User /></el-icon>
            </div>
            <h4>{{ plugin.name }}</h4>
            <p class="description">{{ plugin.description }}</p>
            <div class="plugin-meta">
              <el-tag size="small">{{ getStyleLabel(plugin.config?.style) }}</el-tag>
              <el-tag size="small" type="success">{{ getCharacteristicsLabel(plugin) }}</el-tag>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
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

// 加载插件列表
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
    console.error('加载插件失败', error)
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

function getStyleLabel(style) {
  if (!style) return ''
  const styleMap = {
    'deep_technical': '技术深入型',
    'guided': '亲和引导型',
    'behavioral': '行为导向型'
  }
  return styleMap[style?.questioning_style] || style?.questioning_style || '标准'
}

function getCharacteristicsLabel(plugin) {
  const characteristics = plugin.config?.characteristics || []
  if (characteristics.length === 0) return '标准风格'
  return characteristics[0]
}

onMounted(() => {
  loadPlugins()
})

// 暴露刷新方法给父组件
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

    h4 {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0 0 8px 0;
      text-align: center;
    }

    .description {
      font-size: 13px;
      color: var(--text-secondary);
      line-height: 1.5;
      text-align: center;
      min-height: 40px;
      margin-bottom: 12px;
    }

    .plugin-meta {
      display: flex;
      gap: 8px;
      justify-content: center;
      align-items: center;
      flex-wrap: wrap;
    }
  }
}
</style>
