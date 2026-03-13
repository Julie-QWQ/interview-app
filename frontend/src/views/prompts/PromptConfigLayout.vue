<template>
  <div class="prompt-layout">
    <div class="prompt-layout__header">
      <div>
        <h2>Prompt 配置管理</h2>
        <p>这里维护面试过程中使用的系统提示、主 Prompt 模板和对话参数。</p>
      </div>
    </div>

    <router-view />
  </div>
</template>

<style scoped lang="scss">
.prompt-layout {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.prompt-layout__header {
  h2 {
    margin: 0;
    font-size: 24px;
    line-height: 1.25;
  }

  p {
    margin: 8px 0 0;
    color: #667085;
    line-height: 1.7;
  }
}
</style>
