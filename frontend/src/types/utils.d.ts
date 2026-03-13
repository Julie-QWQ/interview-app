/**
 * 工具函数类型定义
 */

// ==================== 音频相关类型 ====================

export interface AudioConfig {
  enabled: boolean
  always_on_enabled: boolean
  noise_floor_sample_ms: number
  speech_start_threshold: number
  min_speech_ms: number
  end_silence_ms: number
  max_segment_ms: number
  pre_roll_ms: number
  barge_in_ms: number
  chunk_retention_ms: number
  min_threshold: number
  timeslice_ms: number
  auto_send_min_chars: number
  typing_grace_ms: number
  short_noise_words: string[]
}

export interface VoiceControllerConfig {
  audioConfig: AudioConfig
  enableTTS: boolean
  enableDigitalHuman: boolean
  debug: boolean
}

export interface AudioSegment {
  index: number
  content: string
  audioData?: ArrayBuffer
  duration?: number
  isPlaying: boolean
  error?: string
}

// ==================== 录音相关类型 ====================

export interface RecordingState {
  isRecording: boolean
  isPaused: boolean
  duration: number
  volume: number
  audioData?: Blob[]
}

export interface RecordingConfig {
  sampleRate: number
  channelCount: number
  bitDepth: number
  format: 'wav' | 'mp3' | 'ogg'
}

export interface SpeechRecognitionConfig {
  language: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
}

export interface RecognitionResult {
  transcript: string
  confidence: number
  isFinal: boolean
  alternatives?: Array<{
    transcript: string
    confidence: number
  }>
}

// ==================== 数字人相关类型 ====================

export interface DigitalHumanConfig {
  provider: 'xunfei' | 'did' | 'disabled'
  appId?: string
  apiKey?: string
  apiSecret?: string
  voiceId?: string
  avatarId?: string
  sessionId?: string
}

export interface DigitalHumanSession {
  sessionId: string
  provider: string
  config: DigitalHumanConfig
  status: 'initializing' | 'ready' | 'error'
  error?: string
}

export interface AvatarRequest {
  content: string
  voiceId?: string
  avatarId?: string
  background?: string
  quality?: 'low' | 'medium' | 'high'
}

export interface AvatarResponse {
  success: boolean
  videoUrl?: string
  sessionId?: string
  error?: string
  generationTime?: number
}

export interface AvatarSegmentResponse {
  segmentIndex: number
  status: 'pending' | 'ready' | 'failed'
  content: string
  videoUrl?: string
  error?: string
  generationTime?: number
}

// ==================== 表情分析相关类型 ====================

export interface ExpressionAnalysisConfig {
  enabled: boolean
  captureInterval: number
  analysisInterval: number
  includeVideo: boolean
  includeAudio: boolean
  includeFacialLandmarks: boolean
  includeEmotions: boolean
  includeHeadPose: boolean
  includeEyeTracking: boolean
}

export interface ExpressionFrame {
  timestamp: number
  emotions: {
    happy: number
    sad: number
    angry: number
    surprised: number
    neutral: number
  }
  facialLandmarks?: number[][]
  headPose?: {
    pitch: number
    yaw: number
    roll: number
  }
  eyeTracking?: {
    gazeDirection: { x: number; y: number; z: number }
    blink: boolean
  }
}

export interface ExpressionAnalysisResult {
  overallScore: number
  confidenceLevel: string
  metrics: Record<string, number>
  dimensionScores: Record<string, number>
  narrative: string
  riskFlags: string[]
}

export interface ExpressionReport {
  interviewId: number
  overallScore: number
  confidenceLevel: string
  confidenceScore: number
  modalityCoverage: Record<string, any>
  metrics: Record<string, any>
  dimensionScores: Record<string, any>
  evidenceSummary: any[]
  riskFlags: any[]
  narrativeSummary: string
}

// ==================== 相机相关类型 ====================

export interface CameraConfig {
  width: number
  height: number
  facingMode: 'user' | 'environment'
  frameRate: number
}

export interface CameraStream {
  id: string
  label: string
  capabilities: MediaTrackCapabilities
}

export interface CameraError {
  name: string
  message: string
  constraint?: string
}

// ==================== 网络相关类型 ====================

export interface NetworkConfig {
  baseUrl: string
  timeout: number
  retryCount: number
  retryDelay: number
}

export interface RequestConfig {
  url: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  params?: Record<string, any>
  data?: any
  headers?: Record<string, string>
  timeout?: number
}

export interface ResponseData<T = any> {
  code: number
  message: string
  data: T
}

export interface ErrorResponse {
  code: number
  message: string
  error: string
  details?: any
}

// ==================== 日志相关类型 ====================

export interface LogConfig {
  level: 'debug' | 'info' | 'warn' | 'error'
  enableConsole: boolean
  enableStorage: boolean
  maxStorageSize: number
  storageDays: number
}

export interface LogEntry {
  timestamp: string
  level: string
  message: string
  context?: string
  data?: any
}

// ==================== 存储相关类型 ====================

export interface StorageConfig {
  prefix: string
  version: string
  maxSize: number
}

export interface StorageItem {
  key: string
  value: any
  expiry?: number
}

// ==================== 缓存相关类型 ====================

export interface CacheConfig {
  maxSize: number
  defaultTTL: number
  storage: 'memory' | 'localStorage' | 'sessionStorage'
}

export interface CacheItem {
  key: string
  value: any
  ttl: number
  timestamp: number
}

// ==================== 加密相关类型 ====================

export interface EncryptionConfig {
  algorithm: 'AES' | 'RSA'
  keySize: number
  mode: 'CBC' | 'GCM'
}

export interface EncryptedData {
  data: string
  iv: string
  salt: string
}

// ==================== 压缩相关类型 ====================

export interface CompressionConfig {
  algorithm: 'gzip' | 'deflate' | 'brotli'
  level: number
}

// ==================== 文件处理相关类型 ====================

export interface FileUploadConfig {
  maxSize: number
  allowedTypes: string[]
  maxFiles: number
  autoUpload: boolean
}

export interface FileProgress {
  loaded: number
  total: number
  percentage: number
}

export interface UploadedFile {
  id: string
  name: string
  size: number
  type: string
  url: string
  thumbnailUrl?: string
  uploadTime: string
}

// ==================== 图表相关类型 ====================

export interface ChartData {
  labels: string[]
  datasets: ChartDataset[]
}

export interface ChartDataset {
  label: string
  data: number[]
  backgroundColor?: string | string[]
  borderColor?: string | string[]
  borderWidth?: number
  tension?: number
}

export interface ChartOptions {
  responsive: boolean
  maintainAspectRatio: boolean
  plugins: ChartPlugins
  scales: ChartScales
}

export interface ChartPlugins {
  legend: {
    display: boolean
    position: 'top' | 'bottom' | 'left' | 'right'
  }
  tooltip: {
    enabled: boolean
    mode: 'index' | 'nearest'
  }
}

export interface ChartScales {
  x: {
    display: boolean
    title?: string
  }
  y: {
    display: boolean
    title?: string
    beginAtZero?: boolean
  }
}

// ==================== 表单相关类型 ====================

export interface FormConfig {
  validateOnChange: boolean
  showErrors: boolean
  scrollToError: boolean
  focusOnError: boolean
}

export interface FormValidationRule {
  type: 'required' | 'email' | 'phone' | 'url' | 'number' | 'pattern' | 'custom'
  value?: any
  message: string
  trigger?: 'blur' | 'change'
  validator?: (value: any) => boolean | string
}

export interface FormFieldConfig {
  name: string
  type: 'text' | 'number' | 'email' | 'password' | 'textarea' | 'select' | 'checkbox' | 'radio' | 'date' | 'file'
  label?: string
  placeholder?: string
  defaultValue?: any
  rules?: FormValidationRule[]
  options?: Array<{ label: string; value: any }>
  disabled?: boolean
  readonly?: boolean
  hidden?: boolean
}

// ==================== 表格相关类型 ====================

export interface TableColumn {
  prop: string
  label: string
  width?: number
  minWidth?: number
  maxWidth?: number
  align?: 'left' | 'center' | 'right'
  fixed?: boolean | 'left' | 'right'
  sortable?: boolean
  filterable?: boolean
  formatter?: (row: any, column: any, cellValue: any, index: number) => any
}

export interface TableConfig {
  stripe: boolean
  border: boolean
  size: 'large' | 'default' | 'small'
  showHeader: boolean
  highlightCurrentRow: boolean
  fit: boolean
}

// ==================== 分页相关类型 ====================

export interface PaginationConfig {
  pageSize: number
  pageSizes: number[]
  layout: string[]
  background: boolean
  autoScroll: boolean
}

export interface PaginationState {
  currentPage: number
  pageSize: number
  total: number
}

// ==================== 搜索相关类型 ====================

export interface SearchConfig {
  fields: string[]
  placeholder: string
  debounceTime: number
  minChars: number
  maxResults: number
}

export interface SearchResult {
  id: string | number
  title: string
  description: string
  url?: string
  score: number
}

// ==================== 排序相关类型 ====================

export interface SortConfig {
  field: string
  order: 'ascending' | 'descending' | null
  sortable: boolean
}

export interface SortState {
  prop: string
  order: 'ascending' | 'descending'
}

// ==================== 过滤相关类型 ====================

export interface FilterConfig {
  field: string
  operator: 'eq' | 'ne' | 'gt' | 'lt' | 'gte' | 'lte' | 'like' | 'in'
  value: any
  options?: Array<{ label: string; value: any }>
}

export interface FilterState {
  [field: string]: {
    value: any
    operator: string
  }
}

// ==================== 导出相关类型 ====================

export interface ExportConfig {
  format: 'csv' | 'excel' | 'json' | 'xml'
  filename: string
  fields: string[]
  headers?: string[]
  data: any[]
}

export interface ExportProgress {
  current: number
  total: number
  percentage: number
}

// ==================== 导入相关类型 ====================

export interface ImportConfig {
  format: 'csv' | 'excel' | 'json'
  maxSize: number
  allowedTypes: string[]
  validateData: boolean
  skipDuplicates: boolean
}

export interface ImportResult {
  success: number
  failed: number
  total: number
  errors: ImportError[]
}

export interface ImportError {
  row: number
  field: string
  message: string
  value: any
}

// ==================== 权限相关类型 ====================

export interface PermissionConfig {
  permissions: string[]
  roles: string[]
  superAdmin: boolean
}

export interface UserPermission {
  id: number | string
  username: string
  roles: string[]
  permissions: string[]
  isAdmin: boolean
}

export interface AccessControl {
  resource: string
  action: string
  conditions?: Record<string, any>
}

// ==================== 主题相关类型 ====================

export interface ThemeConfig {
  mode: 'light' | 'dark' | 'auto'
  primaryColor: string
  fontSize: 'small' | 'medium' | 'large'
  borderRadius: number
  boxShadow: boolean
}

export interface ThemeColors {
  primary: string
  success: string
  warning: string
  danger: string
  info: string
}

// ==================== 国际化相关类型 ====================

export interface I18nConfig {
  language: 'zh-CN' | 'en-US' | 'ja-JP' | 'ko-KR'
  fallbackLanguage: string
  messages: Record<string, Record<string, string>>
}

export interface TranslationFunction {
  (key: string, params?: Record<string, any>): string
}

// ==================== 性能监控相关类型 ====================

export interface PerformanceConfig {
  enableMetrics: boolean
  sampleRate: number
  reportUrl: string
  reportInterval: number
}

export interface PerformanceMetrics {
  fps: number
  memory: number
  timing: {
    domContentLoaded: number
    loadComplete: number
    firstPaint: number
    firstContentfulPaint: number
  }
  resources: PerformanceResource[]
}

export interface PerformanceResource {
  name: string
  duration: number
  size: number
  type: string
}

// ==================== 错误处理相关类型 ====================

export interface ErrorConfig {
  showNotification: boolean
  logToServer: boolean
  logToConsole: boolean
  retryOnError: boolean
  retryCount: number
}

export interface ErrorInfo {
  message: string
  stack?: string
  code?: string
  statusCode?: number
  url?: string
  method?: string
  params?: any
}

export interface ErrorHandler {
  (error: ErrorInfo): void
}

// ==================== 调试相关类型 ====================

export interface DebugConfig {
  enabled: boolean
  showLogs: boolean
  showTimings: boolean
  showComponentUpdates: boolean
  showPerformance: boolean
}

export interface DebugInfo {
  componentName: string
  props: any
  state: any
  timing: number
  renderCount: number
}

// ==================== WebSocket相关类型 ====================

export interface WebSocketConfig {
  url: string
  reconnect: boolean
  reconnectInterval: number
  maxReconnectAttempts: number
  heartbeat: boolean
  heartbeatInterval: number
}

export interface WebSocketMessage {
  type: string
  data: any
  timestamp: string
}

export interface WebSocketState {
  connected: boolean
  connecting: boolean
  error: boolean
  reconnectAttempts: number
}

export {};