<template>
  <div class="conversation-graph">
    <el-card shadow="never" class="fullscreen-card">
      <template #header>
        <div class="card-header">
          <span>面试流程可视化</span>
          <div class="header-actions">
            <el-button-group>
              <el-button size="small" @click="fitView">
                <el-icon><FullScreen /></el-icon>
                适应视图
              </el-button>
              <el-button size="small" @click="toggleLayout">
                <el-icon><Refresh /></el-icon>
                切换布局
              </el-button>
            </el-button-group>
          </div>
        </div>
      </template>

      <div class="graph-container" ref="graphContainer">
        <svg ref="svgRef" class="graph-svg"></svg>
        <div v-if="allNodes.length === 0" class="empty-state-overlay">
          <el-empty description="暂无对话数据，开始面试后将显示流程图" :image-size="80" />
        </div>
      </div>

      <!-- 图例 -->
      <div class="graph-legend">
        <div class="legend-item">
          <span class="legend-color user"></span>
          <span>候选人消息</span>
        </div>
        <div class="legend-item">
          <span class="legend-color assistant"></span>
          <span>面试官消息</span>
        </div>
      </div>
    </el-card>

    <!-- 节点详情弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogData?.role === 'user' ? '候选人消息' : '面试官消息'"
      width="500px"
      destroy-on-close
    >
      <div v-if="dialogData" class="node-dialog-content">
        <div class="dialog-message">
          <div class="message-label">消息内容：</div>
          <div class="message-text">{{ dialogData.content }}</div>
        </div>

        <div v-if="dialogData.formattedTime" class="dialog-time">
          <span class="time-label">发送时间：</span>
          <span class="time-value">{{ dialogData.formattedTime }}</span>
        </div>

        <div class="dialog-info">
          <div class="info-item">
            <span class="info-label">角色：</span>
            <el-tag :type="dialogData.role === 'user' ? 'primary' : 'info'" size="small">
              {{ dialogData.role === 'user' ? '候选人' : '面试官' }}
            </el-tag>
          </div>
          <div class="info-item">
            <span class="info-label">层级：</span>
            <span>第 {{ dialogData.level }} 层</span>
          </div>
          <div class="info-item">
            <span class="info-label">状态：</span>
            <el-tag :type="dialogData.inCurrentPath ? 'success' : 'info'" size="small">
              {{ dialogData.inCurrentPath ? '当前路径' : '其他分支' }}
            </el-tag>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="handleDialogAction('close')">关闭</el-button>
          <el-button
            type="info"
            @click="handleDialogAction('locate')"
          >
            <el-icon><Location /></el-icon>
            定位消息
          </el-button>
          <el-button
            v-if="dialogData?.role === 'assistant'"
            type="primary"
            @click="handleDialogAction('jump')"
          >
            <el-icon><Right /></el-icon>
            切换到该分支
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 面试流程可视化组件（树型结构）
 *
 * 重要说明：
 * - messageTree: 树型消息结构 { id: { id, parentId, content, role, children: [] } }
 * - currentPath: 当前活跃路径的消息ID列表
 * - currentMessageIndex: 当前对话位置的线性索引（用于UI显示）
 * - 点击节点可以切换到该节点的分支
 * - 高亮显示当前活跃路径
 */
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { FullScreen, Refresh, Location, Right } from '@element-plus/icons-vue'
import * as d3 from 'd3'

const props = defineProps({
  messageTree: {
    type: Object,
    default: () => ({})
  },
  currentPath: {
    type: Array,
    default: () => ([])
  },
  currentMessageIndex: {
    type: Number,
    default: -1
  }
})

// 计算所有节点（扁平化）
const allNodes = computed(() => {
  try {
    if (!props.messageTree || typeof props.messageTree !== 'object') {
      return []
    }
    return Object.values(props.messageTree)
  } catch (error) {
    return []
  }
})

// 计算根节点（没有parentId的节点）
const rootNodes = computed(() => {
  try {
    return allNodes.value.filter(node => !node.parentId)
  } catch (error) {
    return []
  }
})

const graphContainer = ref(null)
const svgRef = ref(null)
const layoutType = ref('vertical') // vertical | horizontal
const isInitialized = ref(false)
const dialogVisible = ref(false)
const dialogData = ref(null)
let renderScheduled = false // 防止重复渲染
let renderTimer = null // 防抖定时器
const RENDER_DEBOUNCE_TIME = 200 // 增加防抖时间
let isUpdating = false // 防止同时更新

let simulation = null
let svg = null
let g = null
let linksGroup = null
let nodesGroup = null
let resizeObserver = null
let cachedData = null // 缓存数据,避免不必要的重算
let zoom = null // 保存 zoom 实例,用于 fitView

onMounted(async () => {
  // 等待 DOM 渲染完成
  await nextTick()
  // 稍微延迟以确保容器有正确的尺寸
  setTimeout(() => {
    initGraph()
    setupResizeObserver()
  }, 200)
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
  if (renderTimer) {
    clearTimeout(renderTimer)
  }
  window.removeEventListener('resize', handleWindowResize)
})

// 防抖渲染函数
function debouncedRender() {
  if (renderTimer) {
    clearTimeout(renderTimer)
  }
  renderTimer = setTimeout(() => {
    requestAnimationFrame(() => {
      renderGraph()
    })
  }, RENDER_DEBOUNCE_TIME)
}

function setupResizeObserver() {
  if (!graphContainer.value) return

  let lastWidth = 0
  resizeObserver = new ResizeObserver((entries) => {
    for (let entry of entries) {
      const { width } = entry.contentRect
      // 只有宽度变化超过 50px 才重新渲染,避免小幅度调整导致的抖动
      if (width > 100 && isInitialized.value && Math.abs(width - lastWidth) > 50) {
        lastWidth = width
        debouncedRender()
      }
    }
  })

  resizeObserver.observe(graphContainer.value)

  // 同时监听窗口 resize 事件作为备用
  window.addEventListener('resize', handleWindowResize)
}

function handleWindowResize() {
  if (isInitialized.value) {
    debouncedRender()
  }
}

// 合并所有 watch,减少重复渲染
watch(
  [() => props.messageTree, () => props.currentPath, () => props.currentMessageIndex],
  () => {
    debouncedRender()
  },
  { deep: true }
)

function initGraph() {
  if (!svgRef.value || !graphContainer.value) {
    return
  }

  const container = graphContainer.value

  // 获取容器宽度，如果太小则等待
  let width = container.clientWidth
  let retries = 0
  const maxRetries = 10

  while (width < 100 && retries < maxRetries) {
    setTimeout(() => {
      width = container.clientWidth
    }, 100)
    retries++
  }

  // 如果仍然太小，使用默认宽度
  if (width < 100) {
    width = 600
  }

  const nodeCount = Object.keys(props.messageTree || {}).length
  const containerHeight = container.clientHeight || 500
  const height = Math.max(containerHeight, (nodeCount + 1) * 100)

  svg = d3.select(svgRef.value)
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', `0 0 ${width} ${height}`)
    // 启用硬件加速,防止模糊
    .style('transform', 'translateZ(0)')
    .style('will-change', 'transform')

  // 添加渐变定义
  const defs = svg.append('defs')

  // 节点阴影
  const shadowFilter = defs.append('filter')
    .attr('id', 'nodeShadow')
    .attr('x', '-50%')
    .attr('y', '-50%')
    .attr('width', '200%')
    .attr('height', '200%')

  shadowFilter.append('feDropShadow')
    .attr('dx', 0)
    .attr('dy', 2)
    .attr('stdDeviation', 3)
    .attr('flood-color', 'rgba(0, 0, 0, 0.08)')

  g = svg.append('g')

  // 添加缩放功能 - 保存到全局变量
  zoom = d3.zoom()
    .scaleExtent([0.1, 3])
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
    })

  svg.call(zoom)

  isInitialized.value = true
  renderGraph()
}

function renderGraph() {
  // 防止重复渲染和并发更新
  if (renderScheduled || isUpdating) {
    return
  }

  renderScheduled = true

  // 使用 requestAnimationFrame 确保在浏览器重绘前执行
  requestAnimationFrame(() => {
    nextTick(() => {
      isUpdating = true
      try {
        doRenderGraph()
      } finally {
        isUpdating = false
        renderScheduled = false
      }
    })
  })
}


// 只更新高亮状态,不重绘整个图
function updateHighlightsOnly() {
  if (!g) return

  // 更新链接的高亮
  g.selectAll('.graph-link')
    .transition()
    .duration(150)
    .ease(d3.easeLinear)
    .attr('stroke', d => d.inCurrentPath ? '#2563eb' : '#e5e7eb')
    .attr('stroke-width', d => d.inCurrentPath ? 2 : 1.5)
    .attr('opacity', d => d.inCurrentPath ? 0.8 : 0.4)

  // 更新节点的高亮
  g.selectAll('.graph-node rect')
    .transition()
    .duration(150)
    .ease(d3.easeLinear)
    .attr('fill', function() {
      const node = d3.select(this.parentNode).datum()
      if (node.type === 'start') return '#2563eb'
      if (!node.inCurrentPath) return '#f3f4f6'
      return getNodeColor(node)
    })
    .attr('stroke', function() {
      const node = d3.select(this.parentNode).datum()
      if (node.type === 'start') return 'none'
      if (!node.inCurrentPath) return '#d1d5db'
      return getStrokeColor(node)
    })
    .attr('stroke-width', function() {
      const node = d3.select(this.parentNode).datum()
      if (node.type === 'start') return 0
      return node.inCurrentPath ? 2.5 : 1.5
    })
    .attr('opacity', function() {
      const node = d3.select(this.parentNode).datum()
      if (node.type === 'start') return 1
      return node.inCurrentPath ? 1 : 0.5
    })

  // 更新节点文本颜色
  g.selectAll('.graph-node text')
    .transition()
    .duration(150)
    .ease(d3.easeLinear)
    .attr('fill', function() {
      const node = d3.select(this.parentNode).datum()
      if (node.type === 'start') return '#fff'
      if (!node.inCurrentPath) return '#9ca3af'
      return '#1f2937'
    })
}


function getNodeColor(node) {
  if (node.type === 'start') return '#2563eb'
  if (node.role === 'user') return '#eff6ff'
  return '#f9fafb'
}

function getStrokeColor(node) {
  if (node.role === 'user') return '#3b82f6'
  return '#94a3b8'
}

function truncateText(text, maxLength) {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

function showTooltip(event, d) {
  // 简单的 tooltip 实现
  const tooltip = d3.select('body')
    .append('div')
    .attr('class', 'graph-tooltip')
    .style('position', 'absolute')
    .style('background', 'rgba(0, 0, 0, 0.8)')
    .style('color', '#fff')
    .style('padding', '8px 12px')
    .style('border-radius', '6px')
    .style('font-size', '12px')
    .style('max-width', '300px')
    .style('word-wrap', 'break-word')
    .style('pointer-events', 'none')
    .style('z-index', '1000')

  let content = ''
  if (d.type === 'start') {
    content = '面试开始'
  } else {
    // 安全地格式化时间戳
    let timeStr = ''
    try {
      if (d.timestamp) {
        const date = new Date(d.timestamp)
        if (!isNaN(date.getTime())) {
          timeStr = date.toLocaleString('zh-CN')
        }
      }
    } catch (e) {
      // 忽略无效时间戳
    }

    const roleText = d.role === 'user' ? '候选人' : '面试官'
    content = `<strong>${roleText}</strong><br>${d.content}`

    // 只有当时间字符串有效时才添加时间
    if (timeStr) {
      content += `<br><small>${timeStr}</small>`
    }
  }

  tooltip.html(content)
    .style('left', (event.pageX + 10) + 'px')
    .style('top', (event.pageY - 10) + 'px')
}

function hideTooltip() {
  d3.selectAll('.graph-tooltip').remove()
}

function showNodeDialog(nodeData) {
  dialogData.value = {
    ...nodeData,
    // 安全地格式化时间戳
    formattedTime: formatTimestamp(nodeData.timestamp)
  }
  dialogVisible.value = true
}

function formatTimestamp(timestamp) {
  if (!timestamp) return ''
  try {
    const date = new Date(timestamp)
    if (!isNaN(date.getTime())) {
      return date.toLocaleString('zh-CN')
    }
  } catch (e) {
    // 忽略无效时间戳
  }
  return ''
}

function handleDialogAction(action) {
  if (!dialogData.value) return

  switch (action) {
    case 'jump':
      // 切换到该节点的分支
      emit('switchToBranch', dialogData.value.nodeId)
      break
    case 'locate':
      // 定位消息（只滚动，不切换分支）
      emit('locateMessage', dialogData.value.nodeId)
      break
    case 'close':
      dialogVisible.value = false
      break
  }

  if (action !== 'close') {
    dialogVisible.value = false
  }
}

function fitView() {
  if (!svg || !g || !zoom) return

  // 先重置变换,获取正确的边界框
  const currentTransform = d3.zoomTransform(svg.node())
  g.attr('transform', null)

  const bounds = g.node().getBBox()
  const parent = graphContainer.value
  const width = parent.clientWidth
  const height = parent.clientHeight

  // 计算合适的缩放比例,留出 40px 的边距
  const padding = 40
  const scale = Math.min(
    (width - padding) / bounds.width,
    (height - padding) / bounds.height,
    1 // 最大缩放为 1
  )

  // 居中显示
  const translateX = (width - bounds.width * scale) / 2 - bounds.x * scale
  const translateY = (height - bounds.height * scale) / 2 - bounds.y * scale

  // 应用缩放和平移
  svg.transition()
    .duration(300)
    .ease(d3.easeCubicOut)
    .call(
      zoom.transform,
      d3.zoomIdentity.translate(translateX, translateY).scale(scale)
    )
}

// 实际的渲染函数（避免重复渲染）
function doRenderGraph() {
  // 确保 svg 和 g 已经初始化
  if (!svgRef.value || !g) {
    return
  }

  const container = graphContainer.value
  let width = container.clientWidth

  // 如果宽度太小，使用默认宽度或从 SVG 属性获取
  if (!width || width < 100) {
    width = svg.attr('width') ? parseInt(svg.attr('width')) : 600
  }

  const containerHeight = container.clientHeight || 500
  const height = Math.max(containerHeight, (Object.keys(props.messageTree).length + 1) * 100)

  // 生成数据签名,检查是否需要重新渲染
  const dataSignature = JSON.stringify({
    nodeCount: allNodes.value.length,
    currentPath: props.currentPath,
    currentIndex: props.currentMessageIndex
  })

  // 如果数据未变化,只更新高亮而不重绘整个图
  if (cachedData === dataSignature) {
    updateHighlightsOnly()
    return
  }

  cachedData = dataSignature

  // 清空现有内容
  g.selectAll('*').remove()

  if (allNodes.value.length === 0) {
    // 显示空状态提示
    g.append('text')
      .attr('x', width / 2)
      .attr('y', height / 2)
      .attr('text-anchor', 'middle')
      .attr('fill', '#9ca3af')
      .attr('font-size', '16px')
      .text('开始面试后将显示流程图')
    return
  }

  // 更新 SVG 尺寸 - 使用 requestAnimationFrame 避免强制同步布局
  requestAnimationFrame(() => {
    svg.attr('width', width).attr('height', height)
  })

  // 构建树型结构的节点和链接
  const nodes = []
  const links = []

  // 真正的树形布局：根据父子关系构建节点和链接
  const nodeWidth = 180
  const nodeHeight = 60
  const levelSpacing = 140 // 垂直布局时的层级间距(增加)
  const levelSpacingH = 250 // 水平布局时的层级间距(大幅增加)
  const siblingSpacing = 220 // 同一层级的节点间距(增加)
  const margin = 80 // 边距

  // 先计算最大层级数和每层最大节点数
  let maxLevel = 0
  let maxNodesInLevel = 0

  if (allNodes.value.length > 0) {
    // 构建树的层级结构
    const treeLevels = [] // 每一层包含的节点
    const nodeLevelMap = new Map() // 节点ID -> 层级
    const nodeChildrenMap = new Map() // 父节点ID -> 子节点数组

    // 初始化根节点
    const rootNodes = allNodes.value.filter(node => !node.parentId)

    // 使用 BFS 构建层级结构
    const queue = rootNodes.map(node => ({ node, level: 1 }))
    const visited = new Set()

    while (queue.length > 0) {
      const { node, level } = queue.shift()
      if (visited.has(node.id)) continue
      visited.add(node.id)

      // 添加到层级
      if (!treeLevels[level]) treeLevels[level] = []
      treeLevels[level].push(node)
      nodeLevelMap.set(node.id, level)

      // 获取子节点
      const children = node.children || []
      nodeChildrenMap.set(node.id, children)

      // 将子节点加入队列
      children.forEach(childId => {
        const childNode = allNodes.value.find(n => n.id === childId)
        if (childNode && !visited.has(childId)) {
          queue.push({ node: childNode, level: level + 1 })
        }
      })
    }

    // 计算每个节点的位置 - 根据布局类型
    const isVertical = layoutType.value === 'vertical'

    // 先遍历一次获取层级信息
    treeLevels.forEach((levelNodes, level) => {
      if (!levelNodes || levelNodes.length === 0) return
      maxLevel = Math.max(maxLevel, level)
      maxNodesInLevel = Math.max(maxNodesInLevel, levelNodes.length)
    })

    // 动态调整 SVG 尺寸以适应布局
    let requiredHeight = height
    let requiredWidth = width

    if (!isVertical) {
      // 水平布局: 需要更大的宽度和高度
      requiredHeight = Math.max(
        500,
        maxNodesInLevel * siblingSpacing + margin * 2 + nodeHeight
      )
      // 计算公式: 左边距 + 开始节点宽度 + 层间距 + (maxLevel-1)*层间距 + 最后节点宽度 + 右边距
      requiredWidth = Math.max(
        width,
        margin + nodeWidth + levelSpacingH + (maxLevel - 1) * levelSpacingH + nodeWidth + margin
      )
    }

    requestAnimationFrame(() => {
      svg.attr('width', requiredWidth).attr('height', requiredHeight)
    })

    // 添加开始节点 - 在计算完尺寸后再添加
    const startNode = {
      id: 'start',
      type: 'start',
      role: 'system',
      content: '面试开始',
      level: 0,
      x: isVertical ? requiredWidth / 2 : margin + nodeWidth / 2,
      y: isVertical ? 50 + nodeHeight / 2 : requiredHeight / 2
    }
    nodes.push(startNode)

    // 第二次遍历: 计算位置
    treeLevels.forEach((levelNodes, level) => {
      if (!levelNodes || levelNodes.length === 0) return

      if (isVertical) {
        // 垂直布局: 从上到下
        const totalWidth = (levelNodes.length - 1) * siblingSpacing
        const startX = (width - totalWidth) / 2

        levelNodes.forEach((node, index) => {
          const x = startX + index * siblingSpacing
          const y = 50 + level * levelSpacing

          nodes.push({
            id: node.id,
            type: 'message',
            role: node.role,
            content: node.content,
            level: level,
            x: x,
            y: y,
            nodeId: node.id,
            parentId: node.parentId,
            inCurrentPath: props.currentPath.includes(node.id)
          })
        })
      } else {
        // 水平布局: 从左到右
        const totalHeight = (levelNodes.length - 1) * siblingSpacing
        const availableHeight = maxNodesInLevel * siblingSpacing + margin * 2
        const startY = (availableHeight - totalHeight) / 2 + margin

        levelNodes.forEach((node, index) => {
          // 计算水平位置: 开始节点后留一个间距,然后每层递增
          // 开始节点中心: margin + nodeWidth / 2
          // 第一层节点中心: margin + nodeWidth + levelSpacingH + nodeWidth / 2
          const x = margin + nodeWidth + levelSpacingH + (level - 1) * levelSpacingH + nodeWidth / 2
          const y = startY + index * siblingSpacing

          nodes.push({
            id: node.id,
            type: 'message',
            role: node.role,
            content: node.content,
            level: level,
            x: x,
            y: y,
            nodeId: node.id,
            parentId: node.parentId,
            inCurrentPath: props.currentPath.includes(node.id)
          })
        })
      }
    })

    // 添加链接：从开始到根节点
    rootNodes.forEach(rootNode => {
      links.push({
        source: 'start',
        target: rootNode.id,
        inCurrentPath: props.currentPath.includes(rootNode.id)
      })
    })

    // 添加链接：从父节点到子节点
    allNodes.value.forEach(node => {
      if (node.parentId && nodeChildrenMap.has(node.parentId)) {
        links.push({
          source: node.parentId,
          target: node.id,
          inCurrentPath: props.currentPath.includes(node.id)
        })
      }
    })
  }

  // 绘制链接
  const link = g.append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('class', 'graph-link')
    .attr('x1', d => {
      const sourceNode = nodes.find(n => n.id === d.source)
      return Math.round(sourceNode?.x || 0)
    })
    .attr('y1', d => {
      const sourceNode = nodes.find(n => n.id === d.source)
      return Math.round(sourceNode?.y || 0)
    })
    .attr('x2', d => {
      const targetNode = nodes.find(n => n.id === d.target)
      return Math.round(targetNode?.x || 0)
    })
    .attr('y2', d => {
      const targetNode = nodes.find(n => n.id === d.target)
      return Math.round(targetNode?.y || 0)
    })
    .attr('stroke', d => d.inCurrentPath ? '#2563eb' : '#e5e7eb')
    .attr('stroke-width', d => d.inCurrentPath ? 2 : 1.5)
    .attr('opacity', d => d.inCurrentPath ? 0.8 : 0.4)
    // 优化渲染质量
    .attr('shape-rendering', 'geometricPrecision')

  // 绘制节点
  const nodeGroups = g.append('g')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .attr('class', 'graph-node')
    .attr('transform', d => `translate(${Math.round(d.x)},${Math.round(d.y)})`)
    .style('cursor', d => d.type !== 'start' ? 'pointer' : 'default')
    // 优化渲染质量
    .attr('shape-rendering', 'geometricPrecision')
    .attr('text-rendering', 'optimizeLegibility')

  // 节点矩形
  nodeGroups.append('rect')
    .attr('width', nodeWidth)
    .attr('height', nodeHeight)
    .attr('x', -nodeWidth / 2)
    .attr('y', -nodeHeight / 2)
    .attr('rx', 6)
    .attr('fill', d => {
      if (d.type === 'start') return '#2563eb'
      if (!d.inCurrentPath) return '#f3f4f6' // 非当前路径的节点使用灰色
      return getNodeColor(d)
    })
    .attr('stroke', d => {
      if (d.type === 'start') return 'none'
      if (!d.inCurrentPath) return '#d1d5db'
      return getStrokeColor(d)
    })
    .attr('stroke-width', d => {
      if (d.type === 'start') return 0
      return d.inCurrentPath ? 2.5 : 1.5
    })
    .attr('opacity', d => {
      if (d.type === 'start') return 1
      return d.inCurrentPath ? 1 : 0.5
    })
    .attr('filter', 'url(#nodeShadow)')
    // 优化渲染质量
    .attr('vector-effect', 'non-scaling-stroke')

  // 节点文本
  nodeGroups.append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', '0.35em')
    .attr('fill', d => {
      if (d.type === 'start') return '#fff'
      if (!d.inCurrentPath) return '#9ca3af'
      return '#1f2937'
    })
    .attr('font-size', '13px')
    .attr('font-weight', d => d.type === 'start' ? '600' : '500')
    .style('text-shadow', d => d.type === 'start' ? '0 2px 4px rgba(0,0,0,0.3)' : 'none')
    // 优化文字渲染
    .style('text-rendering', 'optimizeLegibility')
    .style('font-smooth', 'always')
    .style('-webkit-font-smoothing', 'antialiased')
    .style('-moz-osx-font-smoothing', 'grayscale')
    .text(d => {
      if (d.type === 'start') return '开始'
      return truncateText(d.content, 15)
    })

  // 高亮当前路径的最后一个节点
  if (props.currentPath.length > 0) {
    const lastNodeId = props.currentPath[props.currentPath.length - 1]
    const currentNode = nodeGroups.filter(d => d.nodeId === lastNodeId)

    currentNode.select('rect')
      .attr('stroke', '#2563eb')  // 主色边框
      .attr('stroke-width', 3)     // 加粗边框
  }


  // 添加交互
  nodeGroups
    .on('mouseover', function(event, d) {
      d3.select(this).select('rect')
        .attr('filter', 'drop-shadow(4px 4px 8px rgba(0,0,0,0.2))')
    })
    .on('mouseout', function() {
      d3.select(this).select('rect')
        .attr('filter', 'drop-shadow(2px 2px 4px rgba(0,0,0,0.1))')
    })
    .on('click', function(event, d) {
      if (d.type === 'message' && d.nodeId) {
        // 显示弹窗
        showNodeDialog(d)
      }
    })
}

function toggleLayout() {
  layoutType.value = layoutType.value === 'vertical' ? 'horizontal' : 'vertical'
  // 清除缓存,强制重新渲染
  cachedData = null
  renderGraph()

  // 切换布局后自动适应视图
  setTimeout(() => {
    fitView()
  }, 100)
}

const emit = defineEmits(['switchToBranch', 'locateMessage'])

defineExpose({
  fitView,
  renderGraph
})
</script>

<style scoped lang="scss">
.conversation-graph {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;

  :deep(.el-card) {
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--border-color);
  }

  .fullscreen-card {
    flex: 1;
    height: 100%;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  :deep(.el-card__body) {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    padding: 12px 16px 16px;
  }

  :deep(.el-card__header) {
    background: var(--bg-white);
    padding: 14px 16px;
    border-bottom: 1px solid var(--border-color);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 500;
    color: var(--text-primary);
    font-size: 14px;

    .header-actions {
      :deep(.el-button-group) {
        .el-button {
          background: var(--bg-white);
          border-color: var(--border-color);
          color: var(--text-secondary);
          transition: all 0.15s ease;

          &:hover {
            border-color: var(--primary-color);
            color: var(--primary-color);
          }

          &.el-button--small {
            padding: 5px 10px;
            font-size: 12px;
          }
        }
      }
    }
  }

  .empty-state {
    padding: 60px 0;
  }

  .graph-container {
    width: 100%;
    flex: 1;
    min-height: 0;
    height: 100%;
    max-height: none;
    overflow: hidden;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    background: var(--bg-white);
    position: relative;
  }

  .graph-svg {
    display: block;
    // 启用硬件加速,防止模糊
    will-change: transform;
    // 确保清晰的渲染
    shape-rendering: geometricPrecision;
    text-rendering: optimizeLegibility;
  }

  .empty-state-overlay {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 100%;
    text-align: center;
    padding: 40px 20px;

    :deep(.el-empty) {
      .el-empty__description {
        color: var(--text-tertiary);
        font-size: 13px;
        margin-top: 12px;
      }
    }
  }

  .graph-legend {
    flex-shrink: 0;
    display: flex;
    gap: 24px;
    padding: 12px 16px;
    border-top: 1px solid var(--border-color);
    margin-top: 16px;
    background: var(--bg-gray);

    .legend-item {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: var(--text-secondary);

      .legend-color {
        width: 16px;
        height: 16px;
        border-radius: var(--radius-sm);
        border: 1px solid;

        &.user {
          background: #eff6ff;
          border-color: #3b82f6;
        }

        &.assistant {
          background: var(--bg-white);
          border-color: var(--border-color);
        }
      }
    }
  }
}

:deep(.graph-node) {
  // 优化过渡性能,只对需要的属性使用过渡
  cursor: pointer;
  will-change: opacity, fill, stroke;

  rect {
    // 只对颜色相关属性使用过渡,避免布局抖动
    transition: fill 0.15s ease, stroke 0.15s ease, stroke-width 0.15s ease, opacity 0.15s ease;
    will-change: fill, stroke, stroke-width, opacity;
  }

  text {
    // 只对颜色使用过渡
    transition: fill 0.15s ease;
    pointer-events: none;
    will-change: fill;
  }

  &:hover {
    rect {
      filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.1));
    }
  }
}

:deep(.graph-link) {
  // 只对颜色相关属性使用过渡
  transition: stroke 0.15s ease, stroke-width 0.15s ease, opacity 0.15s ease;
  stroke-linecap: round;
  will-change: stroke, stroke-width, opacity;
}

// 弹窗样式
.node-dialog-content {
  .dialog-message {
    margin-bottom: 16px;
    padding: 14px;
    background: var(--bg-gray);
    border-radius: var(--radius-md);
    border-left: 3px solid var(--primary-color);

    .message-label {
      font-weight: 500;
      color: var(--text-primary);
      margin-bottom: 8px;
      font-size: 13px;
    }

    .message-text {
      color: var(--text-secondary);
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 13px;
    }
  }

  .dialog-time {
    margin-bottom: 12px;
    padding: 10px;
    background: var(--bg-gray);
    border-radius: var(--radius-md);
    color: var(--text-secondary);
    font-size: 12px;

    .time-label {
      font-weight: 500;
      color: var(--primary-color);
      margin-right: 8px;
    }

    .time-value {
      color: var(--text-secondary);
    }
  }

  .dialog-info {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 14px;
    background: var(--bg-gray);
    border-radius: var(--radius-md);

    .info-item {
      display: flex;
      align-items: center;
      font-size: 13px;

      .info-label {
        font-weight: 500;
        color: var(--text-primary);
        margin-right: 8px;
        min-width: 60px;
      }
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
