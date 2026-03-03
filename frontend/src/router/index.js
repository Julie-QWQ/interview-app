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
    name: 'InterviewReport',
    component: () => import('@/views/InterviewReport.vue')
  },
  {
    path: '/interview/create',
    name: 'CreateInterview',
    component: () => import('@/views/CreateInterview.vue')
  },
  {
    path: '/admin/prompts',
    name: 'PromptConfig',
    component: () => import('@/views/PromptConfig.vue')
  },
  {
    path: '/admin/stages',
    name: 'StageConfig',
    component: () => import('@/views/StageConfig.vue')
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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
