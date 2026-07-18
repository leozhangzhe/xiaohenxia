/**
 * PrivacyGuard - 扫描列表页增强脚本
 * 表头翻译 + 统计面板实时更新（主渲染逻辑已移至 spiderfoot.scanlist.js）
 */

(function() {
  'use strict';

  var statusMap = {
    'RUNNING':      { text: '进行中', cls: 'pg-badge-running' },
    'STARTED':      { text: '启动中', cls: 'pg-badge-running' },
    'STARTING':     { text: '启动中', cls: 'pg-badge-running' },
    'INITIALIZING': { text: '初始化', cls: 'pg-badge-running' },
    'CREATED':      { text: '已创建',  cls: 'pg-badge-queued' },
    'FINISHED':     { text: '已完成',  cls: 'pg-badge-finished' },
    'ABORTED':      { text: '已中止',  cls: 'pg-badge-aborted' },
    'ABORT-REQUESTED': { text: '中止中', cls: 'pg-badge-aborted' },
    'ERROR-FAILED': { text: '失败',    cls: 'pg-badge-error' },
  };

  // 顶部栏标题
  var topbarTitle = document.getElementById('page-title');
  if (topbarTitle) topbarTitle.textContent = '扫描任务';

})();
