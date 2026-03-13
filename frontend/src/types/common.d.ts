/**
 * 通用类型定义
 * 定义项目中通用的工具类型和辅助类型
 */

// ==================== 路由相关类型 ====================

export interface RouteMeta {
  title?: string
  requiresAuth?: boolean
  icon?: string
  hideInMenu?: boolean
}

// ==================== 组件Props类型 ====================

export interface BaseComponentProps {
  class?: string
  style?: string | Record<string, any>
}

export interface DialogProps extends BaseComponentProps {
  modelValue: boolean
  title?: string
  width?: string | number
  fullscreen?: boolean
}

// ==================== 表单相关类型 ====================

export interface FormRule {
  required?: boolean
  message?: string
  trigger?: 'blur' | 'change' | ['blur', 'change']
  min?: number
  max?: number
  pattern?: RegExp
  validator?: (rule: any, value: any, callback: any) => void
}

export interface FormRules {
  [key: string]: FormRule | FormRule[]
}

// ==================== 表格相关类型 ====================

export interface TableColumn {
  prop: string
  label: string
  width?: string | number
  minWidth?: string | number
  align?: 'left' | 'center' | 'right'
  fixed?: boolean | 'left' | 'right'
  sortable?: boolean
  formatter?: (row: any, column: any, cellValue: any, index: number) => any
}

// ==================== 状态管理类型 ====================

export interface LoadingState {
  loading: boolean
  error: string | null
}

export interface PaginationState {
  page: number
  pageSize: number
  total: number
}

// ==================== 工具类型 ====================

export type Nullable<T> = T | null

export type Optional<T> = T | undefined

export type Dict<T = any> = Record<string, T>

export type ArrayElement<T> = T extends (infer U)[] ? U : never

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P]
}

export type DeepReadonly<T> = {
  readonly [P in keyof T]: T[P] extends object ? DeepReadonly<T[P]> : T[P]
}

// ==================== 事件处理器类型 ====================

export type EventHandler<T = Event> = (event: T) => void

export type AsyncEventHandler<T = Event> = (event: T) => Promise<void>

// ==================== Promise类型 ====================

export type MaybePromise<T> = T | Promise<T>

export type PromiseResult<T, E = Error> = Promise<{ success: true; data: T } | { success: false; error: E }>

// ==================== 函数类型 ====================

export type Fn = () => void

export type FnT<T> = (arg: T) => void

export type FnTR<T, R> = (arg: T) => R

export type FnAsync = () => Promise<void>

export type FnTAsync<T> = (arg: T) => Promise<void>

// ==================== 时间日期类型 ====================

export type TimeString = string // 格式: 'HH:mm:ss'

export type DateString = string // 格式: 'YYYY-MM-DD'

export type DateTimeString = string // 格式: 'YYYY-MM-DD HH:mm:ss'

// ==================== ID类型 ====================

export type ID = number | string

export type NewRecord = ID | null

// ==================== HTTP相关类型 ====================

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'

export type HttpResponse<T = any> = {
  data: T
  status: number
  statusText: string
  headers: Record<string, string>
}

export type HttpError = {
  message: string
  status: number
  code: string
  response?: HttpResponse
}

// ==================== 树形结构类型 ====================

export interface TreeNode<T = any> {
  id: ID
  label: string
  children?: TreeNode<T>[]
  data?: T
  expanded?: boolean
  disabled?: boolean
}

export type TreeData<T = any> = TreeNode<T>[]

// ==================== 选择器类型 ====================

export interface SelectOption {
  label: string
  value: any
  disabled?: boolean
  children?: SelectOption[]
}

// ==================== 上传文件类型 ====================

export interface UploadFile {
  name: string
  url?: string
  status: 'ready' | 'uploading' | 'success' | 'error'
  percentage?: number
  response?: any
  error?: Error
}

// ==================== 验证结果类型 ====================

export type ValidationResult = {
  valid: boolean
  message?: string
  field?: string
}

export type ValidateResult = ValidationResult | ValidationResult[]

// ==================== 主题样式类型 ====================

export type ThemeType = 'light' | 'dark'

export type ColorType = 'primary' | 'success' | 'warning' | 'danger' | 'info'

// ==================== 语言类型 ====================

export type Language = 'zh-CN' | 'en-US'

// ==================== 权限相关类型 ====================

export type Permission = string

export type Role = string

export type UserPermissions = {
  roles: Role[]
  permissions: Permission[]
}

// ==================== 音频相关类型 ====================

export interface AudioConfig {
  enabled: boolean
  volume: number
  autoPlay: boolean
  loop: boolean
}

export interface VoiceState {
  isPlaying: boolean
  isMuted: boolean
  currentPlayingId: ID | null
  volume: number
}

// ==================== 视频相关类型 ====================

export interface VideoConfig {
  autoplay: boolean
  controls: boolean
  muted: boolean
  loop: boolean
  playsinline: boolean
}

// ==================== 地理位置类型 ====================

export interface Geolocation {
  latitude: number
  longitude: number
  accuracy: number
  altitude?: number
  altitudeAccuracy?: number
  heading?: number
  speed?: number
}

// ==================== 浏览器信息类型 ====================

export interface BrowserInfo {
  name: string
  version: string
  os: string
  isMobile: boolean
  language: string
}

// ==================== 设备信息类型 ====================

export interface DeviceInfo {
  userAgent: string
  platform: string
  vendor: string
  screen: {
    width: number
    height: number
    availWidth: number
    availHeight: number
    colorDepth: number
    pixelDepth: number
  }
}

// ==================== 网络状态类型 ====================

export interface NetworkStatus {
  online: boolean
  effectiveType: string
  downlink: number
  rtt: number
  saveData: boolean
}

// ==================== 性能指标类型 ====================

export interface PerformanceMetrics {
  fps: number
  memory: number
  timing: {
    domContentLoaded: number
    loadComplete: number
    firstPaint: number
    firstContentfulPaint: number
  }
}

// ==================== 键盘事件类型 ====================

export interface KeyboardEvent {
  key: string
  code: string
  ctrlKey: boolean
  shiftKey: boolean
  altKey: boolean
  metaKey: boolean
}

// ==================== 鼠标事件类型 ====================

export interface MouseEvent {
  x: number
  y: number
  clientX: number
  clientY: number
  screenX: number
  screenY: number
  button: number
  buttons: number
  ctrlKey: boolean
  shiftKey: boolean
  altKey: boolean
  metaKey: boolean
}

// ==================== 触摸事件类型 ====================

export interface TouchEvent {
  touches: Touch[]
  changedTouches: Touch[]
  targetTouches: Touch[]
  ctrlKey: boolean
  shiftKey: boolean
  altKey: boolean
  metaKey: boolean
}

export interface Touch {
  identifier: number
  clientX: number
  clientY: number
  screenX: number
  screenY: number
  pageX: number
  pageY: number
}

// ==================== 滚动事件类型 ====================

export interface ScrollEvent {
  scrollTop: number
  scrollLeft: number
  scrollWidth: number
  scrollHeight: number
  clientWidth: number
  clientHeight: number
}

// ==================== 拖拽事件类型 ====================

export interface DragEvent {
  type: 'start' | 'move' | 'end'
  data: any
  source: any
  target: any
}

// ==================== 动画相关类型 ====================

export interface AnimationConfig {
  duration: number
  easing: string
  delay?: number
  fillMode?: 'forwards' | 'backwards' | 'both' | 'none'
}

export type AnimationStatus = 'idle' | 'running' | 'paused' | 'finished'

// ==================== 过渡相关类型 ====================

export interface TransitionConfig {
  name: string
  duration?: number | { enter: number; leave: number }
  easing?: string
  mode?: 'in-out' | 'out-in' | 'default'?
}

// ==================== 样式相关类型 ====================

export type StyleValue = string | number | boolean | null | undefined

export type StyleObject = Record<string, StyleValue>

export interface ClassObject {
  [key: string]: boolean
}

// ==================== 插槽类型 ====================

export type Slot = () => any

export type ScopedSlot = (props: any) => any

// ==================== 生命周期钩子类型 ====================

export type LifecycleHook = () => void

export type AsyncLifecycleHook = () => Promise<void>

export type CleanupHook = () => void | (() => void)