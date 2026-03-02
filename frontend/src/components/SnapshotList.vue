<template>
  <div class="snapshot-list">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>对话存档</span>
          <el-tag size="small" type="info">{{ snapshots.length }} 个存档</el-tag>
        </div>
      </template>

      <div v-if="loading" v-loading="loading" style="min-height: 200px"></div>

      <div v-else-if="snapshots.length === 0" class="empty-state">
        <el-empty description="暂无存档记录，面试官发言后会自动创建存档" />
      </div>

      <div v-else class="snapshots-content">
        <div
          v-for="snapshot in snapshots"
          :key="snapshot.id"
          class="snapshot-item"
          :class="{ 'is-selected': selectedSnapshotId === snapshot.id }"
          @click="handleSelect(snapshot)"
        >
          <div class="snapshot-header">
            <div class="snapshot-info">
              <el-icon class="snapshot-icon"><FolderOpened /></el-icon>
              <div class="snapshot-text">
                <div class="snapshot-name">{{ snapshot.name }}</div>
                <div class="snapshot-meta">
                  <span>{{ snapshot.message_count }} 条消息</span>
                  <span>{{ formatDate(snapshot.created_at) }}</span>
                </div>
              </div>
            </div>
            <div class="snapshot-actions">
              <el-button
                type="primary"
                size="small"
                @click.stop="handleRestore(snapshot)"
                :loading="restoringId === snapshot.id"
              >
                <el-icon><RefreshLeft /></el-icon>
                恢复
              </el-button>
              <el-button
                type="danger"
                size="small"
                @click.stop="handleDelete(snapshot)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          <div v-if="snapshot.description" class="snapshot-description">
            {{ snapshot.description }}
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { FolderOpened, RefreshLeft, Delete } from '@element-plus/icons-vue'
import { interviewApi } from '@/api/interview'

const props = defineProps({
  interviewId: {
    type: Number,
    required: true
  },
  messages: {
    type: Array,
    default: () => []
  },
  currentStage: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['restore', 'select'])

const loading = ref(false)
const snapshots = ref([])
const selectedSnapshotId = ref(null)
const restoringId = ref(null)
const lastMessageCount = ref(0)
const isCreatingSnapshot = ref(false)

onMounted(() => {
  loadSnapshots()
})

// 监听消息变化,当面试官说完话后自动创建存档
watch(() => props.messages, async (newMessages, oldMessages) => {
  // 只在有新消息且当前不是正在创建存档时处理
  if (newMessages.length > lastMessageCount.value && !isCreatingSnapshot.value) {
    const lastMessage = newMessages[newMessages.length - 1]

    // 只有当最后一条消息是面试官(assistant)的消息时才创建存档
    if (lastMessage && lastMessage.role === 'assistant') {
      await autoCreateSnapshot(newMessages)
    }

    lastMessageCount.value = newMessages.length
  }
}, { deep: true })

async function loadSnapshots() {
  loading.value = true
  try {
    const data = await interviewApi.listSnapshots(props.interviewId)
    snapshots.value = data
    lastMessageCount.value = props.messages.length
  } catch (error) {
    console.error('加载存档失败', error)
  } finally {
    loading.value = false
  }
}

async function autoCreateSnapshot(currentMessages) {
  // 避免重复创建
  if (isCreatingSnapshot.value) return

  isCreatingSnapshot.value = true

  try {
    // 生成存档名称
    const stageNames = {
      'welcome': '开场介绍',
      'technical': '技术问题',
      'scenario': '情景问题',
      'closing': '结束阶段'
    }

    const stageName = stageNames[props.currentStage] || props.currentStage
    const messageNum = currentMessages.length
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

    const snapshotData = {
      name: `${stageName} - 第${Math.ceil(messageNum / 2)}轮 (${timestamp})`,
      description: `面试官发言后的自动存档，当前共${messageNum}条消息`
    }

    await interviewApi.createSnapshot(props.interviewId, snapshotData)

    // 静默成功,不打扰用户
    console.log('自动存档创建成功')

    // 重新加载存档列表
    await loadSnapshots()
  } catch (error) {
    console.error('自动创建存档失败', error)
    // 静默失败,不打扰用户体验
  } finally {
    isCreatingSnapshot.value = false
  }
}

function handleSelect(snapshot) {
  selectedSnapshotId.value = snapshot.id
  emit('select', snapshot)
}

async function handleRestore(snapshot) {
  try {
    await ElMessageBox.confirm(
      `确认恢复到存档"${snapshot.name}"？当前对话进度将被替换。`,
      '确认恢复',
      {
        confirmButtonText: '恢复',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    restoringId.value = snapshot.id
    const data = await interviewApi.loadSnapshot(snapshot.id)
    ElMessage.success('存档加载成功')
    emit('restore', data)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('恢复存档失败', error)
      ElMessage.error('恢复存档失败')
    }
  } finally {
    restoringId.value = null
  }
}

async function handleDelete(snapshot) {
  try {
    await ElMessageBox.confirm(
      `确认删除存档"${snapshot.name}"？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await interviewApi.deleteSnapshot(snapshot.id)
    ElMessage.success('存档已删除')
    await loadSnapshots()

    if (selectedSnapshotId.value === snapshot.id) {
      selectedSnapshotId.value = null
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除存档失败', error)
      ElMessage.error('删除存档失败')
    }
  }
}

function formatDate(dateStr) {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return date.toLocaleDateString('zh-CN')
}

defineExpose({
  loadSnapshots
})
</script>

<style scoped lang="scss">
.snapshot-list {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
  }

  .empty-state {
    padding: 40px 0;
  }

  .snapshots-content {
    max-height: 500px;
    overflow-y: auto;
  }

  .snapshot-item {
    padding: 12px;
    margin-bottom: 8px;
    border: 1px solid #e4e7ed;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s;

    &:hover {
      border-color: #667eea;
      background: #f5f7fa;
    }

    &.is-selected {
      border-color: #667eea;
      background: #ede9fe;
    }

    .snapshot-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .snapshot-info {
      display: flex;
      align-items: center;
      gap: 12px;
      flex: 1;

      .snapshot-icon {
        font-size: 24px;
        color: #667eea;
      }

      .snapshot-text {
        flex: 1;

        .snapshot-name {
          font-weight: 600;
          color: #333;
          margin-bottom: 4px;
        }

        .snapshot-meta {
          display: flex;
          gap: 12px;
          font-size: 12px;
          color: #999;
        }
      }
    }

    .snapshot-actions {
      display: flex;
      gap: 8px;
      opacity: 0;
      transition: opacity 0.3s;
    }

    &:hover .snapshot-actions {
      opacity: 1;
    }

    .snapshot-description {
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid #e4e7ed;
      font-size: 13px;
      color: #666;
      line-height: 1.6;
    }
  }
}
</style>
