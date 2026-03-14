import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue')
  },
  {
    path: '/interviews',
    name: 'InterviewList',
    component: () => import('@/views/InterviewList.vue')
  },
  {
    path: '/interviews/:id',
    name: 'InterviewDetail',
    component: () => import('@/views/InterviewDetail.vue')
  },
  {
    path: '/interviews/:id/report',
    name: 'InterviewExpressionReport',
    component: () => import('@/views/InterviewExpressionReport.vue')
  },
  {
    path: '/interview/create',
    name: 'CreateInterview',
    component: () => import('@/views/CreateInterview.vue')
  },
  {
    path: '/admin/prompts',
    name: 'PromptConfig',
    component: () => import('@/views/prompts/PromptConfigLayout.vue'),
    redirect: '/admin/prompts/interviewer',
    children: [
      {
        path: 'interviewer',
        name: 'InterviewerPromptConfig',
        component: () => import('@/views/prompts/InterviewerPromptConfig.vue')
      }
    ]
  },
  {
    path: '/admin/tools',
    name: 'ToolConfig',
    component: () => import('@/views/ToolConfig.vue')
  },
  {
    path: '/admin/smart-reply',
    name: 'SmartReplyConfig',
    component: () => import('@/views/SmartReplyConfig.vue')
  },
  {
    path: '/admin/stages',
    name: 'StageConfig',
    component: () => import('@/views/StageConfig.vue')
  },
  {
    path: '/admin/voice',
    name: 'VoiceConfig',
    component: () => import('@/views/VoiceConfig.vue')
  },
  {
    path: '/admin/profiles',
    name: 'ProfileManagement',
    component: () => import('@/views/ProfileManagement.vue')
  },
  {
    path: '/test/camera',
    name: 'CameraTest',
    component: () => import('@/views/CameraTest.vue')
  },
  {
    path: '/test/digital-human',
    name: 'TestDigitalHuman',
    component: () => import('@/views/TestDigitalHuman.vue')
  },
  {
    path: '/test/xunfei-digital-human',
    name: 'XunfeiDigitalHumanTest',
    component: () => import('@/views/DigitalHumanTest.vue')
  },
  {
    path: '/test/external-module',
    name: 'ExternalModuleTest',
    component: () => import('@/views/ExternalModuleTest.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
