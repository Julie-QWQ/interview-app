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
    path: '/interview/create',
    name: 'CreateInterview',
    component: () => import('@/views/CreateInterview.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
