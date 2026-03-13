<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑画像' : '创建自定义画像'"
    width="720px"
    destroy-on-close
    @close="handleClose"
  >
    <el-form :model="formData" label-width="120px">
      <el-form-item v-if="!isEdit" label="画像类型">
        <el-radio-group v-model="formData.type">
          <el-radio-button label="position">岗位画像</el-radio-button>
          <el-radio-button label="interviewer">面试官画像</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="画像名称" required>
        <el-input v-model="formData.name" placeholder="请输入画像名称" />
      </el-form-item>

      <el-form-item label="描述">
        <el-input
          v-model="formData.description"
          type="textarea"
          :rows="2"
          placeholder="请输入画像描述"
        />
      </el-form-item>

      <template v-if="formData.type === 'position'">
        <el-divider content-position="left">能力权重配置</el-divider>

        <el-form-item label="技术能力">
          <el-slider
            v-model="formData.config.ability_weights.technical"
            :min="0"
            :max="1"
            :step="0.05"
            :format-tooltip="formatPercent"
          />
        </el-form-item>

        <el-form-item label="沟通能力">
          <el-slider
            v-model="formData.config.ability_weights.communication"
            :min="0"
            :max="1"
            :step="0.05"
            :format-tooltip="formatPercent"
          />
        </el-form-item>

        <el-form-item label="问题解决">
          <el-slider
            v-model="formData.config.ability_weights.problem_solving"
            :min="0"
            :max="1"
            :step="0.05"
            :format-tooltip="formatPercent"
          />
        </el-form-item>

        <el-form-item label="学习潜力">
          <el-slider
            v-model="formData.config.ability_weights.learning_potential"
            :min="0"
            :max="1"
            :step="0.05"
            :format-tooltip="formatPercent"
          />
        </el-form-item>

        <el-divider content-position="left">技能要求</el-divider>

        <el-form-item label="核心技能">
          <el-select
            v-model="formData.config.skill_requirements.core_skills"
            multiple
            placeholder="选择核心技能"
            style="width: 100%"
          >
            <el-option label="JavaScript" value="JavaScript" />
            <el-option label="TypeScript" value="TypeScript" />
            <el-option label="Vue.js" value="Vue.js" />
            <el-option label="React" value="React" />
            <el-option label="Node.js" value="Node.js" />
            <el-option label="Python" value="Python" />
            <el-option label="Java" value="Java" />
            <el-option label="Go" value="Go" />
          </el-select>
        </el-form-item>
      </template>

      <template v-if="formData.type === 'interviewer'">
        <el-divider content-position="left">面试官风格</el-divider>

        <el-form-item label="面试官风格" required>
          <el-input
            v-model="formData.config.prompt"
            type="textarea"
            :rows="8"
            placeholder="请输入该面试官的风格、人设、提问重点、说话方式和追问倾向"
          />
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { profileApi } from '@/api/profile'

const props = defineProps({
  modelValue: Boolean,
  plugin: Object,
  pluginType: String
})

const emit = defineEmits(['update:modelValue', 'success'])

const visible = computed({
  get: () => props.modelValue,
  set: value => emit('update:modelValue', value)
})

const isEdit = computed(() => !!props.plugin)
const saving = ref(false)

function createDefaultConfig() {
  return {
    ability_weights: {
      technical: 0.5,
      communication: 0.2,
      problem_solving: 0.2,
      learning_potential: 0.1
    },
    skill_requirements: {
      core_skills: [],
      weights: {}
    },
    prompt: ''
  }
}

function createDefaultFormData(type = 'position') {
  return {
    plugin_id: '',
    type,
    name: '',
    description: '',
    is_system: false,
    config: createDefaultConfig()
  }
}

function normalizeConfig(config = {}) {
  const base = createDefaultConfig()
  return {
    ...base,
    ...config,
    ability_weights: {
      ...base.ability_weights,
      ...(config.ability_weights || {})
    },
    skill_requirements: {
      ...base.skill_requirements,
      ...(config.skill_requirements || {})
    },
    prompt: config.prompt || config.prompt_template || ''
  }
}

const formData = ref(createDefaultFormData(props.pluginType || 'position'))

watch(
  () => props.plugin,
  plugin => {
    if (plugin) {
      formData.value = {
        plugin_id: plugin.plugin_id,
        type: plugin.type,
        name: plugin.name,
        description: plugin.description,
        is_system: plugin.is_system,
        config: normalizeConfig(plugin.config || {})
      }
      return
    }

    formData.value = createDefaultFormData(props.pluginType || 'position')
  },
  { immediate: true }
)

watch(
  () => props.pluginType,
  pluginType => {
    if (!props.plugin && pluginType) {
      formData.value = createDefaultFormData(pluginType)
    }
  }
)

function handleClose() {
  if (!isEdit.value) {
    formData.value = createDefaultFormData(props.pluginType || 'position')
  }
}

function formatPercent(value) {
  return `${(value * 100).toFixed(0)}%`
}

async function handleSave() {
  if (!formData.value.name.trim()) {
    ElMessage.warning('请输入画像名称')
    return
  }

  if (formData.value.type === 'position') {
    const skills = formData.value.config.skill_requirements.core_skills
    if (!skills || skills.length === 0) {
      ElMessage.warning('请至少选择一个核心技能')
      return
    }

    const weights = formData.value.config.ability_weights
    const sum = Object.values(weights).reduce((total, current) => total + current, 0)
    if (Math.abs(sum - 1) > 0.01) {
      ElMessage.warning(`能力权重总和应为 100%，当前为 ${(sum * 100).toFixed(0)}%`)
      return
    }
  }

  if (formData.value.type === 'interviewer' && !formData.value.config.prompt.trim()) {
    ElMessage.warning('请填写面试官风格')
    return
  }

  saving.value = true
  try {
    const payload = {
      name: formData.value.name,
      description: formData.value.description,
      config: formData.value.config
    }

    if (isEdit.value) {
      await profileApi.updatePlugin(formData.value.plugin_id, payload)
      ElMessage.success('更新成功')
    } else {
      formData.value.plugin_id = `${formData.value.type}_${Date.now()}`
      await profileApi.createPlugin({
        ...payload,
        plugin_id: formData.value.plugin_id,
        type: formData.value.type,
        is_system: false
      })
      ElMessage.success('创建成功')
    }

    emit('success', {
      type: formData.value.type,
      plugin_id: formData.value.plugin_id,
      name: formData.value.name
    })
    visible.value = false
  } catch (error) {
    console.error('保存画像失败', error)
    ElMessage.error(error.response?.data?.error || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped lang="scss">
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
