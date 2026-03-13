/**
 * API接口类型定义
 * 定义所有与后端API交互的数据结构
 */

// ==================== 基础类型 ====================

export type MessageRole = 'user' | 'assistant' | 'system'

export type InterviewStatus = 'created' | 'in_progress' | 'completed' | 'cancelled'

export type SkillDomain = 'frontend' | 'backend' | 'fullstack' | 'ai' | 'data' | 'other'

export type ExperienceLevel = '初级' | '中级' | '高级' | '专家'

export type StageType = 'welcome' | 'technical' | 'scenario' | 'closing'

// ==================== 消息相关类型 ====================

export interface Message {
  id: number | string
  interview_id: number
  role: MessageRole
  content: string
  timestamp: string
  parent_id: number | string | null
  branch_id: string
  tree_path: (number | string)[]
  is_active: boolean
}

export interface MessageNode extends Message {
  children: (number | string)[]
  avatarSegments: AvatarSegment[]
  avatarError: string
  isStreaming?: boolean
  error?: boolean
}

export interface AvatarSegment {
  segmentIndex: number
  status: 'pending' | 'ready' | 'failed'
  content: string
  videoUrl: string
  error: string
  generationTime: number | null
}

export interface MessageResponse {
  id: number
  role: MessageRole
  content: string
  timestamp: string
  parent_id?: number | string | null
  branch_id?: string
  tree_path?: (number | string)[]
  is_active?: boolean
}

export interface ChatMessage {
  content: string
}

// ==================== 面试相关类型 ====================

export interface Interview {
  id: number
  candidate_name: string
  position: string
  skill_domain: SkillDomain
  skills: string[]
  experience_level: ExperienceLevel
  duration_minutes: number
  additional_requirements: string | null
  resume_file_id: string | null
  resume_text: string | null
  status: InterviewStatus
  current_stage: StageType | null
  current_message_id: number | null
  created_at: string
  updated_at: string | null
  completed_at: string | null
  expression_report_ready: boolean
}

export interface CreateInterviewRequest {
  candidate_name: string
  position: string
  skill_domain: SkillDomain
  skills: string[]
  experience_level?: ExperienceLevel
  duration_minutes?: number
  additional_requirements?: string
  resume_file_id?: string
  resume_text?: string
}

export interface InterviewResponse extends Interview {
  messages?: Message[]
  stage_progress?: number
  current_stage?: StageType
}

export interface InterviewProgress {
  current_stage: StageType
  progress: number
  time_spent: number
  time_remaining: number
}

// ==================== API响应类型 ====================

export interface ApiResponse<T = any> {
  data: T
  message: string
  code: number
}

export interface ApiError {
  error: string
  message: string
  status: number
}

// ==================== 流式响应类型 ====================

export interface StreamEvent {
  type: 'text_chunk' | 'avatar_segment_pending' | 'avatar_segment_ready' | 'avatar_segment_failed' | 'done'
  content?: string
  segment_index?: number
  video_url?: string
  audio?: string | null
  error?: string
  generation_time?: number
  message_id?: number
  user_message_id?: number
  current_stage?: StageType
  progress?: number
  done?: boolean
}

export interface StreamOptions {
  parentId?: number | string | null
  branchId?: string
  source?: 'text_input' | 'voice_input'
}

// ==================== 分页相关类型 ====================

export interface ListParams {
  limit?: number
  offset?: number
  status?: InterviewStatus
  skill_domain?: SkillDomain
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

// ==================== 文件上传类型 ====================

export interface FileUploadResponse {
  file_id: string
  filename: string
  size: number
  upload_time: string
}

export interface ResumeUploadRequest {
  interview_id: number
  file: File
}

// ==================== 表情分析类型 ====================

export interface ExpressionReport {
  id: number
  interview_id: number
  overall_score: number
  confidence_level: string
  confidence_score: number
  modality_coverage: Record<string, any>
  metrics: Record<string, any>
  dimension_scores: Record<string, any>
  evidence_summary: any[]
  risk_flags: any[]
  narrative_summary: string
  created_at: string
  updated_at: string
}

// ==================== Prompt配置类型 ====================

export interface PromptConfig {
  id: number
  config_type: string
  config_data: Record<string, any>
  updated_at: string
}

export interface PromptConfigData {
  base_system_prompt: string
  interviewer_prompt: string
  evaluation_prompt: string
  stages: Record<string, StageConfig>
}

export interface StageConfig {
  name: string
  description: string
  duration_minutes: number
  focus_areas: string[]
}

// ==================== 快照类型 ====================

export interface Snapshot {
  id: number
  interview_id: number
  name: string
  description: string
  snapshot_data: SnapshotData
  created_at: string
}

export interface SnapshotData {
  messages: Message[]
  current_message_id: number | string | null
  current_stage: StageType | null
  progress: number
  metadata: Record<string, any>
}

// ==================== 画像插件类型 ====================

export interface ProfilePlugin {
  id: number
  plugin_id: string
  type: 'position' | 'interviewer'
  name: string
  description: string
  is_system: boolean
  config: ProfileConfig
  created_at: string
  updated_at: string
}

export interface ProfileConfig {
  ability_weights: Record<string, number>
  skill_requirements: {
    core_skills: string[]
    weights: Record<string, number>
  }
  interview_strategy: {
    stages: Array<{
      stage: StageType
      time_allocation: number
      focus: string
    }>
  }
}

export interface InterviewProfile {
  id: number
  interview_id: number
  position_plugin_id: string | null
  interviewer_plugin_id: string | null
  custom_config: Record<string, any> | null
  created_at: string
  updated_at: string
}

// ==================== 工具调用类型 ====================

export interface ToolInvocation {
  id: number
  trace_id: string | null
  interview_id: number
  stage: string
  trigger: string
  tool_name: string
  request_payload: Record<string, any> | null
  response_payload: Record<string, any> | null
  status: string
  latency_ms: number
  cache_hit: boolean
  created_at: string
}

// ==================== 数字人相关类型 ====================

export interface DigitalHumanConfig {
  provider: 'xunfei' | 'did' | 'disabled'
  session_id: string | null
  config: Record<string, any> | null
}

export interface DigitalHumanSession {
  success: boolean
  provider: string
  session_id: string
  config: Record<string, any>
  error?: string
}

export interface AvatarStatus {
  status: 'LISTENING' | 'SPEAKING' | 'THINKING' | 'INTERRUPTED' | 'ERROR'
  ready: boolean
  available: boolean
  error: string
}