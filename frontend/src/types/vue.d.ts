/**
 * Vue组件类型声明
 * 为Vue组件提供TypeScript支持
 */

import type { DefineComponent } from 'vue'

// ==================== 全局组件类型声明 ====================

declare module '@vue/runtime-core' {
  export interface GlobalComponents {
    // Element Plus 组件
    ElButton: DefineComponent
    ElInput: DefineComponent
    ElForm: DefineComponent
    ElFormItem: DefineComponent
    ElDialog: DefineComponent
    ElTable: DefineComponent
    ElTableColumn: DefineComponent
    ElPagination: DefineComponent
    ElSelect: DefineComponent
    ElOption: DefineComponent
    ElRadio: DefineComponent
    ElRadioGroup: DefineComponent
    ElCheckbox: DefineComponent
    ElCheckboxGroup: DefineComponent
    ElSwitch: DefineComponent
    ElSlider: DefineComponent
    ElDatePicker: DefineComponent
    ElTimePicker: DefineComponent
    ElUpload: DefineComponent
    ElProgress: DefineComponent
    ElCard: DefineComponent
    ElContainer: DefineComponent
    ElHeader: DefineComponent
    ElMain: DefineComponent
    ElAside: DefineComponent
    ElFooter: DefineComponent
    ElMenu: DefineComponent
    ElMenuItem: DefineComponent
    ElSubMenu: DefineComponent
    ElBreadcrumb: DefineComponent
    ElBreadcrumbItem: DefineComponent
    ElDropdown: DefineComponent
    ElDropdownItem: DefineComponent
    ElTabs: DefineComponent
    ElTabPane: DefineComponent
    ElTag: DefineComponent
    ElIcon: DefineComponent
    ElRow: DefineComponent
    ElCol: DefineComponent
    ElDivider: DefineComponent
    ElAlert: DefineComponent
    ElMessage: DefineComponent
    ElNotification: DefineComponent
    ElMessageBox: DefineComponent
    ElLoading: DefineComponent
    ElTooltip: DefineComponent
    ElPopover: DefineComponent
    ElCascader: DefineComponent
    ElTransfer: DefineComponent
    ElTree: DefineComponent
  }

  export interface ComponentCustomProperties {
    // 全局属性
    $api: any
    $store: any
    $router: import('vue-router').RouterInstance
    $route: import('vue-router').RouteLocationNormalized
  }
}

// ==================== 环境变量类型声明 ====================

declare interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_APP_TITLE: string
  readonly VITE_APP_VERSION: string
  readonly VITE_ENABLE_MOCK: string
}

declare interface ImportMeta {
  readonly env: ImportMetaEnv
}

// ==================== 窗口对象扩展 ====================

declare global {
  interface Window {
    // 音频上下文
    webkitAudioContext: typeof AudioContext
    AudioContext: typeof AudioContext

    // 媒体流
    MediaStream: typeof MediaStream

    // 其他浏览器API
    SpeechRecognition: any
    webkitSpeechRecognition: any
  }
}

export {}