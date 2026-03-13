/**
 * Pinia状态管理类型定义
 */

import type { Store } from 'pinia'

// ==================== Store状态类型 ====================

export interface InterviewState {
  // 面试数据
  interviews: Interview[]
  currentInterview: Interview | null

  // 消息树结构
  messages: MessageNode[]
  messageTree: Record<string | number, MessageNode>
  currentBranchId: string
  currentMessagePath: (string | number)[]

  // UI状态
  loading: boolean
  error: string | null
  thinking: boolean
  streamingMessage: string

  // 面试进度
  currentStage: StageType | null
  stageProgress: number | null

  // 数字人状态
  isPlaying: boolean
  currentPlayingMessageId: number | string | null
  isMuted: boolean
  digitalHumanReady: boolean
  digitalHumanAvailable: boolean
  digitalHumanError: string
  activeSpeechMode: 'none' | 'tts' | 'digital_human'
  sessionId: string | null
  digitalHumanConfig: Record<string, any> | null
  provider: 'xunfei' | 'did' | 'disabled'
  avatarStatus: 'LISTENING' | 'SPEAKING' | 'THINKING' | 'INTERRUPTED' | 'ERROR'
}

// ==================== Store getters类型 ====================

export interface InterviewGetters {
  // 面试相关
  activeInterviews: Interview[]
  completedInterviews: Interview[]
  interviewById: (id: number) => Interview | undefined
  currentInterviewId: number | null

  // 消息相关
  currentMessage: MessageNode | undefined
  messageTreeDepth: number
  branchCount: number
  isStreaming: boolean

  // 数字人相关
  canPlayAudio: boolean
  isDigitalHumanActive: boolean
  hasDigitalHumanError: boolean

  // UI相关
  isLoading: boolean
  hasError: boolean
  errorMessage: string
}

// ==================== Store actions类型 ====================

export interface InterviewActions {
  // 面试操作
  fetchInterviews: (params?: ListParams) => Promise<Interview[]>
  createInterview: (data: CreateInterviewRequest) => Promise<Interview>
  fetchInterviewDetail: (id: number) => Promise<Interview | null>
  startInterview: (id: number) => Promise<void>
  completeInterview: (id: number) => Promise<void>
  deleteInterview: (id: number) => Promise<boolean>
  clearCurrentInterview: () => void

  // 消息操作
  sendMessage: (interviewId: number, content: string, options?: StreamOptions) => Promise<any>
  switchToMessage: (messageId: number | string) => Promise<void>
  switchToBranch: (nodeId: number | string) => Promise<void>
  createNewBranch: (parentMessageId: number | string) => void
  buildMessageTree: (messages: Message[], currentMessageId?: number | string) => void

  // 数字人操作
  initAvatarSession: (interviewId: number) => Promise<void>
  setAvatarStatus: (status: 'LISTENING' | 'SPEAKING' | 'THINKING' | 'INTERRUPTED' | 'ERROR') => void
  setDigitalHumanReady: (ready: boolean) => void
  setDigitalHumanError: (error: string) => void
  beginAssistantSpeech: (messageId?: number | string) => void
  finishAssistantSpeech: () => void
  interruptAssistant: () => { mode: string }

  // 音频操作
  toggleMute: () => void
  setMute: (muted: boolean) => void
  stopVoice: () => void

  // 工具方法
  generateId: () => string
  mergeStreamingContent: (previous: string, incoming: string) => string
  ensureAvatarState: (node: MessageNode) => AvatarSegment[]
  normalizeAvatarError: (error: string) => string
  resetSpeechState: () => void
  upsertAvatarSegment: (node: MessageNode, segment: Partial<AvatarSegment>) => void
  updateLinearMessages: () => void
}

// ==================== 通用Store类型 ====================

export interface AppState {
  sidebar: {
    opened: boolean
    withoutAnimation: boolean
  }
  device: {
    isMobile: boolean
  }
  settings: {
    theme: string
    language: string
    pageSize: number
  }
  loading: boolean
  error: string | null
}

export interface AppActions {
  toggleSidebar: (withoutAnimation?: boolean) => void
  closeSidebar: (withoutAnimation?: boolean) => void
  toggleDevice: (isMobile: boolean) => void
  setTheme: (theme: string) => void
  setLanguage: (language: string) => void
  setPageSize: (size: number) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

// ==================== 用户状态类型 ====================

export interface UserState {
  token: string
  name: string
  avatar: string
  roles: string[]
  permissions: string[]
  settings: UserSettings
}

export interface UserSettings {
  theme: string
  language: string
  notifications: boolean
  soundEffects: boolean
  autoPlay: boolean
}

export interface UserActions {
  setToken: (token: string) => void
  setName: (name: string) => void
  setAvatar: (avatar: string) => void
  setRoles: (roles: string[]) => void
  setPermissions: (permissions: string[]) => void
  updateSettings: (settings: Partial<UserSettings>) => void
  logout: () => void
}

// ==================== 标签页状态类型 ====================

export interface TagsViewState {
  visitedViews: VisitableView[]
  cachedViews: string[]
  currentView: VisitableView | null
}

export interface VisitableView {
  name: string
  path: string
  title: string
  query?: Record<string, any>
  params?: Record<string, any>
  fullPath: string
}

export interface TagsViewActions {
  addView: (view: VisitableView) => void
  addCachedView: (viewName: string) => void
  removeView: (view: VisitableView) => void
  removeCachedView: (viewName: string) => void
  removeOthersViews: (view: VisitableView) => void
  removeAllViews: () => void
  removeAllCachedViews: () => void
  setCurrentView: (view: VisitableView) => void
}

// ==================== 权限状态类型 ====================

export interface PermissionState {
  routes: AppRoute[]
  dynamicRoutes: AppRoute[]
  permissions: string[]
  roles: string[]
  loaded: boolean
}

export interface PermissionActions {
  setRoutes: (routes: AppRoute[]) => void
  setDynamicRoutes: (routes: AppRoute[]) => void
  setPermissions: (permissions: string[]) => void
  setRoles: (roles: string[]) => void
  hasPermission: (permission: string) => boolean
  hasRole: (role: string) => boolean
  hasAnyPermission: (permissions: string[]) => boolean
  hasAnyRole: (roles: string[]) => boolean
  loadPermissions: () => Promise<void>
}

// ==================== 应用设置状态类型 ====================

export interface SettingsState {
  title: string
  version: string
  debug: boolean
  apiBaseUrl: string
  websocketUrl: string
  uploadUrl: string
  maxFileSize: number
  allowedFileTypes: string[]
}

export interface SettingsActions {
  setTitle: (title: string) => void
  setDebug: (debug: boolean) => void
  updateSettings: (settings: Partial<SettingsState>) => void
  loadSettings: () => Promise<void>
  saveSettings: (settings: Partial<SettingsState>) => Promise<void>
}

// ==================== Store类型定义 ====================

export type InterviewStore = Store<'interview', InterviewState, InterviewGetters, InterviewActions>
export type AppStore = Store<'app', AppState, {}, AppActions>
export type UserStore = Store<'user', UserState, {}, UserActions>
export type TagsViewStore = Store<'tagsView', TagsViewState, {}, TagsViewActions>
export type PermissionStore = Store<'permission', PermissionState, {}, PermissionActions>
export type SettingsStore = Store<'settings', SettingsState, {}, SettingsActions>

// ==================== Pinia插件类型 ====================

export interface PiniaCustomStateProperties {
  interview: InterviewState
  app: AppState
  user: UserState
  tagsView: TagsViewState
  permission: PermissionState
  settings: SettingsState
}

export {};