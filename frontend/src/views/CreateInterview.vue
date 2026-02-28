<template>
  <div class="create-interview">
    <el-page-header @back="$router.back()" title="返回">
      <template #content>
        <h2>创建面试</h2>
      </template>
    </el-page-header>

    <el-card class="form-card" shadow="never">
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
        label-position="top"
      >
        <el-form-item label="候选人姓名" prop="candidate_name">
          <el-input
            v-model="formData.candidate_name"
            placeholder="请输入候选人姓名"
            clearable
          />
        </el-form-item>

        <el-form-item label="面试职位" prop="position">
          <el-input
            v-model="formData.position"
            placeholder="例如：前端工程师、后端工程师"
            clearable
          />
        </el-form-item>

        <el-form-item label="技能领域" prop="skill_domain">
          <el-select
            v-model="formData.skill_domain"
            placeholder="请选择技能领域"
            style="width: 100%"
          >
            <el-option label="前端开发" value="frontend" />
            <el-option label="后端开发" value="backend" />
            <el-option label="全栈开发" value="fullstack" />
            <el-option label="AI/机器学习" value="ai_ml" />
            <el-option label="数据工程" value="data_engineering" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>

        <el-form-item label="技能标签" prop="skills">
          <el-select
            v-model="formData.skills"
            multiple
            filterable
            allow-create
            placeholder="请选择或输入技能标签"
            style="width: 100%"
          >
            <el-option label="JavaScript" value="JavaScript" />
            <el-option label="Python" value="Python" />
            <el-option label="Java" value="Java" />
            <el-option label="Vue.js" value="Vue.js" />
            <el-option label="React" value="React" />
            <el-option label="Node.js" value="Node.js" />
            <el-option label="数据库" value="数据库" />
            <el-option label="系统设计" value="系统设计" />
            <el-option label="算法" value="算法" />
          </el-select>
        </el-form-item>

        <el-form-item label="经验级别" prop="experience_level">
          <el-radio-group v-model="formData.experience_level">
            <el-radio label="初级" />
            <el-radio label="中级" />
            <el-radio label="高级" />
          </el-radio-group>
        </el-form-item>

        <el-form-item label="面试时长" prop="duration_minutes">
          <el-slider
            v-model="formData.duration_minutes"
            :min="15"
            :max="120"
            :step="5"
            show-stops
            :marks="{ 15: '15分钟', 30: '30分钟', 60: '60分钟', 120: '120分钟' }"
          />
          <div class="duration-display">预计时长：{{ formData.duration_minutes }} 分钟</div>
        </el-form-item>

        <el-form-item label="额外要求">
          <el-input
            v-model="formData.additional_requirements"
            type="textarea"
            :rows="4"
            placeholder="请输入额外的面试要求或注意事项（可选）"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading" size="large">
            <el-icon><Check /></el-icon>
            创建面试
          </el-button>
          <el-button @click="handleReset" size="large">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import { useInterviewStore } from '@/stores/interview'

const router = useRouter()
const interviewStore = useInterviewStore()

const formRef = ref(null)
const loading = ref(false)

const formData = reactive({
  candidate_name: '',
  position: '',
  skill_domain: '',
  skills: [],
  experience_level: '中级',
  duration_minutes: 30,
  additional_requirements: ''
})

const formRules = {
  candidate_name: [
    { required: true, message: '请输入候选人姓名', trigger: 'blur' }
  ],
  position: [
    { required: true, message: '请输入面试职位', trigger: 'blur' }
  ],
  skill_domain: [
    { required: true, message: '请选择技能领域', trigger: 'change' }
  ],
  skills: [
    { required: true, message: '请选择至少一个技能标签', trigger: 'change' }
  ]
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    loading.value = true

    await interviewStore.createInterview(formData)

    ElMessage.success('面试创建成功！')
    router.push('/interviews')
  } catch (error) {
    if (error !== false) {
      console.error('创建面试失败', error)
    }
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  formRef.value.resetFields()
}
</script>

<style scoped lang="scss">
.create-interview {
  max-width: 800px;
  margin: 0 auto;
}

h2 {
  margin: 0;
  font-size: 24px;
}

.form-card {
  margin-top: 24px;
}

.duration-display {
  text-align: center;
  color: #667eea;
  font-weight: 600;
  margin-top: 8px;
}

:deep(.el-form-item__label) {
  font-weight: 600;
}
</style>
