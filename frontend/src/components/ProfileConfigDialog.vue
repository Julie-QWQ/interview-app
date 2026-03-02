<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑画像' : '创建自定义画像'"
    width="700px"
    destroy-on-close
    @close="handleClose"
  >
    <el-form :model="formData" label-width="120px">
      <!-- 基础信息 -->
      <el-form-item label="画像类型" v-if="!isEdit">
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

      <!-- 岗位画像配置 -->
      <template v-if="formData.type === 'position'">
        <el-divider content-position="left">能力权重配置</el-divider>

        <el-form-item label="技术能力">
          <el-slider
            v-model="formData.config.ability_weights.technical"
            :min="0"
            :max="1"
            :step="0.05"
            :format-tooltip="(val) => (val * 100).toFixed(0) + '%'"
          />
        </el-form-item>

        <el-form-item label="沟通能力">
          <el-slider
            v-model="formData.config.ability_weights.communication"
            :min="0"
            :max="1"
            :step="0.05"
            :format-tooltip="(val) => (val * 100).toFixed(0) + '%'"
          />
        </el-form-item>

        <el-form-item label="问题解决">
          <el-slider
            v-model="formData.config.ability_weights.problem_solving"
            :min="0"
            :max="1"
            :step="0.05"
            :format-tooltip="(val) => (val * 100).toFixed(0) + '%'"
          />
        </el-form-item>

        <el-form-item label="学习潜力">
          <el-slider
            v-model="formData.config.ability_weights.learning_potential"
            :min="0"
            :max="1"
            :step="0.05"
            :format-tooltip="(val) => (val * 100).toFixed(0) + '%'"
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

      <!-- 面试官画像配置 -->
      <template v-if="formData.type === 'interviewer'">
        <el-divider content-position="left">面试风格配置</el-divider>

        <el-form-item label="提问风格">
          <el-select v-model="formData.config.style.questioning_style" style="width: 100%">
            <el-option label="技术深入型 - 注重技术细节和实现深度" value="deep_technical" />
            <el-option label="亲和引导型 - 氛围轻松,善于引导" value="guided" />
            <el-option label="行为导向型 - 关注过往经历和行为模式" value="behavioral" />
          </el-select>
        </el-form-item>

        <el-form-item label="节奏把控">
          <el-radio-group v-model="formData.config.style.pace">
            <el-radio-button label="fast">快节奏</el-radio-button>
            <el-radio-button label="moderate">适中</el-radio-button>
            <el-radio-button label="slow">慢节奏</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="严厉程度">
          <el-slider
            v-model="formData.config.style.strictness"
            :min="0"
            :max="1"
            :step="0.1"
            :format-tooltip="(val) => val.toFixed(1)"
          />
        </el-form-item>

        <el-divider content-position="left">特征标签</el-divider>

        <el-form-item label="标签">
          <el-select
            v-model="formData.config.characteristics"
            multiple
            placeholder="选择特征标签"
            style="width: 100%"
          >
            <el-option label="技术专家型" value="技术专家型" />
            <el-option label="亲和力强" value="亲和力强" />
            <el-option label="注重实战" value="注重实战" />
            <el-option label="逻辑严密" value="逻辑严密" />
            <el-option label="善于引导" value="善于引导" />
            <el-option label="注重经验" value="注重经验" />
            <el-option label="关注细节" value="关注细节" />
          </el-select>
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { profileApi } from '@/api/profile'

const props = defineProps({
  modelValue: Boolean,
  plugin: Object,  // 编辑时传入的插件数据
  pluginType: String  // 创建时指定的画像类型：position | interviewer
})

const emit = defineEmits(['update:modelValue', 'success'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const isEdit = computed(() => !!props.plugin)
const saving = ref(false)

// 如果传入了 pluginType，则预设为该类型
const defaultType = props.pluginType || 'position'

const formData = ref({
  plugin_id: '',
  type: defaultType,
  name: '',
  description: '',
  is_system: false,
  config: {
    // 岗位画像配置
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
    // 面试官画像配置
    style: {
      questioning_style: 'guided',
      pace: 'moderate',
      interaction: 'two_way',
      strictness: 0.5
    },
    characteristics: []
  }
})

// 监听插件数据变化(编辑模式)
watch(() => props.plugin, (plugin) => {
  if (plugin) {
    formData.value = {
      plugin_id: plugin.plugin_id,
      type: plugin.type,
      name: plugin.name,
      description: plugin.description,
      is_system: plugin.is_system,
      config: plugin.config || formData.value.config
    }
  }
}, { immediate: true })

function handleClose() {
  // 重置表单
  if (!isEdit.value) {
    formData.value = {
      plugin_id: '',
      type: 'position',
      name: '',
      description: '',
      is_system: false,
      config: formData.value.config
    }
  }
}

async function handleSave() {
  // 验证
  if (!formData.value.name.trim()) {
    ElMessage.warning('请输入画像名称')
    return
  }

  if (formData.value.type === 'position') {
    const skills = formData.value.config.skill_requirements.core_skills
    if (!skills || skills.length === 0) {
      ElMessage.warning('请选择至少一个核心技能')
      return
    }
  }

  // 权重总和检查
  if (formData.value.type === 'position') {
    const weights = formData.value.config.ability_weights
    const sum = Object.values(weights).reduce((a, b) => a + b, 0)
    if (Math.abs(sum - 1.0) > 0.01) {
      ElMessage.warning(`能力权重总和应为100%,当前为${(sum * 100).toFixed(0)}%`)
      return
    }
  }

  saving.value = true
  try {
    if (isEdit.value) {
      await profileApi.updatePlugin(formData.value.plugin_id, {
        name: formData.value.name,
        description: formData.value.description,
        config: formData.value.config
      })
      ElMessage.success('更新成功')
    } else {
      // 生成插件ID
      formData.value.plugin_id = `${formData.value.type}_${Date.now()}`
      await profileApi.createPlugin(formData.value)
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
