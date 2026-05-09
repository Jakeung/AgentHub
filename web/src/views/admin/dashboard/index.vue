<template>
  <div class="dashboard-page">
    <el-empty description="管理员仪表盘（开发中）">
      <template #image>
        <el-icon :size="64" color="var(--text-muted)"><DataLine /></el-icon>
      </template>
    </el-empty>
  </div>
</template>

<style scoped>
.dashboard-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}
</style>
