<template>
  <div id="app">
    <el-container class="admin-shell">
      <el-aside v-if="!isMainInterviewView" class="sidebar">
        <div class="brand">
          <h1>AI 面试系统</h1>
          <p>后台管理</p>
        </div>

        <nav class="sidebar-nav">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="nav-item"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.label }}</span>
          </router-link>
        </nav>
      </el-aside>

      <el-main :class="['main-content', { 'main-content--interview': isMainInterviewView }]">
        <section :class="['content-body', { 'content-body--interview': isMainInterviewView, 'content-body--plain': !isMainInterviewView }]">
          <router-view />
        </section>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { DataLine, ChatLineRound, Collection, User, Camera } from '@element-plus/icons-vue'

const route = useRoute()

const navItems = [
  { label: '仪表盘', path: '/', icon: DataLine },
  { label: '面试管理', path: '/interviews', icon: ChatLineRound },
  { label: 'Prompt 配置', path: '/admin/prompts', icon: Collection },
  { label: '阶段配置', path: '/admin/stages', icon: DataLine },
  { label: '画像管理', path: '/admin/profiles', icon: User },
  { label: '摄像头测试', path: '/test/camera', icon: Camera }
]

const isMainInterviewView = computed(() => route.path.startsWith('/interviews/'))
</script>

<style scoped>
.admin-shell {
  min-height: 100vh;
  background: var(--layout-bg);
}

.sidebar {
  width: 252px;
  background: #f6f7f9;
  border-right: 1px solid var(--line-color);
  padding: 20px 14px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.brand {
  padding: 8px 8px 4px;
}

.brand h1 {
  font-size: 26px;
  line-height: 1.2;
  font-weight: 800;
  margin: 0;
  color: #161a22;
}

.brand p {
  margin: 6px 0 0;
  font-size: 13px;
  color: #8a93a3;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-item {
  height: 44px;
  padding: 0 12px;
  border-radius: 12px;
  color: #5a6372;
  font-weight: 600;
  font-size: 15px;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.16s ease;
}

.nav-item:hover {
  background: #eceef2;
  color: #1f2937;
}

.nav-item.router-link-active {
  background: #111318;
  color: #ffffff;
}

.main-content {
  padding: 20px 24px 24px;
  overflow: auto;
}

.main-content--interview {
  padding: 0;
}

.content-body {
  margin-top: 14px;
}

.content-body--interview {
  margin-top: 0;
}

.content-body--plain {
  margin-top: 0;
}

@media (max-width: 860px) {
  .admin-shell {
    display: block;
  }

  .sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid var(--line-color);
  }

  .sidebar-nav {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .main-content {
    padding: 14px;
  }
}
</style>
