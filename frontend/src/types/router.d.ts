/**
 * 路由类型定义
 */

import type { RouteRecordRaw } from 'vue-router'

// ==================== 路由配置类型 ====================

export interface AppRoute extends Omit<RouteRecordRaw, 'children'> {
  children?: AppRoute[]
  meta?: RouteMeta
}

export interface RouteMeta {
  title?: string
  icon?: string
  requiresAuth?: boolean
  roles?: string[]
  permissions?: string[]
  hideInMenu?: boolean
  hideInBreadcrumb?: boolean
  activeMenu?: string
  keepAlive?: boolean
  fullscreen?: boolean
}

// ==================== 导航项类型 ====================

export interface NavItem {
  path: string
  label: string
  icon: string | object
  children?: NavItem[]
  external?: boolean
  badge?: string | number
}

// ==================== 面包屑类型 ====================

export interface BreadcrumbItem {
  title: string
  path: string
  query?: Record<string, any>
}

// ==================== 标签页类型 ====================

export interface TabItem {
  title: string
  path: string
  query?: Record<string, any>
  params?: Record<string, any>
  closable: boolean
}

// ==================== 菜单类型 ====================

export interface MenuItem {
  id: string
  label: string
  icon?: string | object
  path: string
  children?: MenuItem[]
  external?: boolean
  badge?: string | number
  expanded?: boolean
  disabled?: boolean
}

// ==================== 权限路由类型 ====================

export interface PermissionRoute {
  path: string
  name: string
  component: any
  meta: {
    title: string
    icon?: string
    roles?: string[]
    permissions?: string[]
  }
  children?: PermissionRoute[]
}

// ==================== 路由守卫类型 ====================

export type NavigationGuard = (
  to: import('vue-router').RouteLocationNormalized,
  from: import('vue-router').RouteLocationNormalized,
  next: (to?: string | false | void) => void
) => void | boolean | Promise<void | boolean>

export type AsyncNavigationGuard = (
  to: import('vue-router').RouteLocationNormalized,
  from: import('vue-router').RouteLocationNormalized,
  next: (to?: string | false | void) => void
) => Promise<void>

// ==================== 路由状态类型 ====================

export interface RouterState {
  currentRoute: import('vue-router').RouteLocationNormalized
  routes: AppRoute[]
  permissions: string[]
  roles: string[]
}

// ==================== 页面配置类型 ====================

export interface PageConfig {
  title: string
  description?: string
  keywords?: string[]
  fullscreen?: boolean
  cache?: boolean
  loading?: boolean
  breadcrumbs?: boolean
  tabs?: boolean
}

export {};