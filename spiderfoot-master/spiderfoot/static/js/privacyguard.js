/**
 * PrivacyGuard - 全局 JS
 * 初始化、通用工具、隐私保护功能
 */

(function() {
  'use strict';

  // 确保 docroot 变量在运行时可用
  var _docroot = (typeof docroot !== 'undefined' ? docroot : '');

  // =========================================
  // 通用工具
  // =========================================

  // 关闭下拉菜单（点击外部）
  document.addEventListener('click', function(e) {
    if (!e.target.closest('.pg-dropdown')) {
      document.querySelectorAll('.pg-dropdown-menu.show').forEach(function(m) {
        m.classList.remove('show');
      });
    }
  });

  // 顶部栏页面标题映射
  var pageTitles = {
    'NEWSCAN': '新建扫描',
    'SCANLIST': '扫描任务',
    'SETTINGS': '系统设置',
  };

  // =========================================
  // 侧边栏导航绑定
  // =========================================

  var navPrivacy = document.getElementById('nav-privacy');
  if (navPrivacy) {
    navPrivacy.addEventListener('click', function(e) {
      e.preventDefault();
      showPrivacyCenter();
    });
  }

  var navSmartMask = document.getElementById('nav-smartmask');
  if (navSmartMask) {
    navSmartMask.addEventListener('click', function(e) {
      e.preventDefault();
      showSmartPrivacyModule();
    });
  }

  var navAlerts = document.getElementById('nav-alerts');
  if (navAlerts) {
    navAlerts.addEventListener('click', function(e) {
      e.preventDefault();
      showAlertsPanel();
    });
  }

  var navServices = document.getElementById('nav-services');
  if (navServices) {
    navServices.addEventListener('click', function(e) {
      e.preventDefault();
      showServicesPanel();
    });
  }

  var navDataViz = document.getElementById('nav-dataviz');
  if (navDataViz) {
    navDataViz.addEventListener('click', function(e) {
      e.preventDefault();
      showDataInsightDashboard();
    });
  }

  // =========================================
  // 隐私保护中心（真实数据驱动）
  // =========================================

  function showPrivacyCenter() {
    var content = document.querySelector('.pg-content');
    if (!content) return;

    content.innerHTML = '<div class="pg-page-header pg-fade-in">' +
      '<h1 class="pg-page-title">隐私保护中心</h1>' +
      '<p class="pg-page-subtitle">通过扫描结果分析您的数字痕迹风险，发现敏感信息泄露</p>' +
      '<button class="pg-btn pg-btn-primary pg-btn-sm" onclick="window.location.href=\'' + _docroot + '/newscan\'" style="margin-top:8px;">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
        ' 开始扫描' +
      '</button>' +
    '</div>' +

    '<div class="pg-stats-grid pg-fade-in" id="pg-stats-container">' +
      '<div class="pg-stat-card red">' +
        '<div class="pg-stat-icon red">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>' +
        '</div>' +
        '<div class="pg-stat-value" id="pg-high-count" style="color:var(--accent-red)">--</div>' +
        '<div class="pg-stat-label">高风险关联</div>' +
      '</div>' +
      '<div class="pg-stat-card yellow">' +
        '<div class="pg-stat-icon yellow">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>' +
        '</div>' +
        '<div class="pg-stat-value" id="pg-medium-count" style="color:var(--accent-yellow)">--</div>' +
        '<div class="pg-stat-label">中风险关联</div>' +
      '</div>' +
      '<div class="pg-stat-card green">' +
        '<div class="pg-stat-icon green">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><polyline points="20 6 9 17 4 12"/></svg>' +
        '</div>' +
        '<div class="pg-stat-value" id="pg-finished-count" style="color:var(--accent-green)">--</div>' +
        '<div class="pg-stat-label">已完成扫描</div>' +
      '</div>' +
      '<div class="pg-stat-card purple">' +
        '<div class="pg-stat-icon purple">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>' +
        '</div>' +
        '<div class="pg-stat-value" id="pg-total-count">--</div>' +
        '<div class="pg-stat-label">历史扫描总数</div>' +
      '</div>' +
    '</div>' +

    '<div class="pg-card pg-fade-in" style="margin-top:16px;">' +
      '<div class="pg-card-header">' +
        '<div class="pg-card-title">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" stroke-width="2" width="16" height="16"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>' +
          ' 如何使用隐私保护中心' +
        '</div>' +
      '</div>' +
      '<div class="pg-card-body">' +
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;">' +
          '<div style="display:flex;align-items:flex-start;gap:12px;">' +
            '<div style="flex-shrink:0;width:28px;height:28px;border-radius:50%;background:rgba(239,68,68,0.15);color:var(--accent-red);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;">1</div>' +
            '<div>' +
              '<div style="font-weight:600;font-size:13px;margin-bottom:4px;">发起扫描</div>' +
              '<div style="font-size:12px;color:var(--text-secondary);line-height:1.5;">在「新建扫描」中输入目标（域名、IP、邮箱等），选择模块后启动扫描。</div>' +
            '</div>' +
          '</div>' +
          '<div style="display:flex;align-items:flex-start;gap:12px;">' +
            '<div style="flex-shrink:0;width:28px;height:28px;border-radius:50%;background:rgba(245,158,11,0.15);color:var(--accent-yellow);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;">2</div>' +
            '<div>' +
              '<div style="font-weight:600;font-size:13px;margin-bottom:4px;">等待完成</div>' +
              '<div style="font-size:12px;color:var(--text-secondary);line-height:1.5;">扫描完成后，风险数据将自动汇总至此处，中高风险项会突出显示。</div>' +
            '</div>' +
          '</div>' +
          '<div style="display:flex;align-items:flex-start;gap:12px;">' +
            '<div style="flex-shrink:0;width:28px;height:28px;border-radius:50%;background:rgba(34,197,94,0.15);color:var(--accent-green);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;">3</div>' +
            '<div>' +
              '<div style="font-weight:600;font-size:13px;margin-bottom:4px;">查看详情</div>' +
              '<div style="font-size:12px;color:var(--text-secondary);line-height:1.5;">点击风险项可跳转至对应扫描详情，查看数据来源和完整关联路径。</div>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>' +
    '</div>' +

    '<div id="pg-risk-list" class="pg-fade-in" style="margin-top:16px;">' +
      '<div class="pg-card">' +
        '<div class="pg-card-header">' +
          '<div class="pg-card-title">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="var(--accent-red)" stroke-width="2" width="16" height="16"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>' +
            ' 扫描结果中的风险关联' +
          '</div>' +
          '<a href="' + _docroot + '/scanlist" class="pg-btn pg-btn-ghost pg-btn-sm">全部扫描</a>' +
        '</div>' +
        '<div class="pg-card-body" id="pg-risk-body">' +
          '<div style="text-align:center;padding:40px 0;">' +
            '<span class="pg-loader" style="width:28px;height:28px;border-width:3px;"></span>' +
            '<div style="margin-top:12px;color:var(--text-secondary);font-size:13px;">正在从扫描结果中分析风险...</div>' +
          '</div>' +
        '</div>' +
      '</div>' +
    '</div>';

    loadPrivacyStats();
  }

  function loadPrivacyStats() {
    // 并行加载扫描列表和风险告警
    Promise.all([
      fetch(_docroot + '/scanlist').then(function(r) { return r.json(); }).catch(function() { return []; }),
      fetch(_docroot + '/riskalerts').then(function(r) { return r.json(); }).catch(function() { return []; })
    ]).then(function(results) {
      var scanList = results[0];
      var alerts = results[1];

      var total = scanList.length;
      var finished = 0, running = 0;
      for (var i = 0; i < scanList.length; i++) {
        var s = scanList[i][6];
        if (s === 'FINISHED') finished++;
        else if (['RUNNING','STARTING','STARTED','INITIALIZING'].indexOf(s) >= 0) running++;
      }

      var high = alerts.filter(function(a) { return a.risk === 'HIGH'; }).length;
      var medium = alerts.filter(function(a) { return a.risk === 'MEDIUM'; }).length;

      updateStat('pg-total-count', total);
      updateStat('pg-finished-count', finished);
      updateStat('pg-high-count', high);
      updateStat('pg-medium-count', medium);

      renderRiskList(alerts);
    });
  }

  function updateStat(id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = val || 0;
  }

  function renderRiskList(alerts) {
    var body = document.getElementById('pg-risk-body');
    if (!body) return;

    if (!alerts || alerts.length === 0) {
      body.innerHTML = '<div style="text-align:center;padding:40px 0;">' +
        '<div style="font-size:40px;margin-bottom:12px;">🛡️</div>' +
        '<div style="font-weight:600;margin-bottom:6px;">暂无风险数据</div>' +
        '<div style="font-size:13px;color:var(--text-secondary);">请先完成至少一次扫描任务</div>' +
        '<a href="' + _docroot + '/newscan" class="pg-btn pg-btn-primary" style="margin-top:16px;">新建扫描</a>' +
        '</div>';
      return;
    }

    var html = '';
    for (var i = 0; i < alerts.length; i++) {
      var a = alerts[i];
      var isHigh = a.risk === 'HIGH';
      var borderColor = isHigh ? 'var(--accent-red)' : 'var(--accent-yellow)';
      var bgColor = isHigh ? 'rgba(239,68,68,0.06)' : 'rgba(245,158,11,0.06)';
      var iconBg = isHigh ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)';
      var iconColor = isHigh ? 'var(--accent-red)' : 'var(--accent-yellow)';
      var scanLink = _docroot + '/scaninfo?id=' + (a.scanId || '');

      html += '<div class="pg-leak-item" style="border-left:2px solid ' + borderColor + ';background:' + bgColor + ';border-radius:8px;padding:14px;margin-bottom:8px;">' +
        '<div style="display:flex;align-items:flex-start;gap:12px;">' +
          '<div style="flex-shrink:0;width:32px;height:32px;border-radius:8px;background:' + iconBg + ';color:' + iconColor + ';display:flex;align-items:center;justify-content:center;font-size:16px;">' +
            (isHigh ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>' : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><circle cx="12" cy="12" r="10"/></svg>') +
          '</div>' +
          '<div style="flex:1;min-width:0;">' +
            '<div style="font-weight:600;font-size:13px;margin-bottom:4px;">' + escHtml(a.title || a.ruleName || '风险关联') + '</div>' +
            '<div style="font-size:12px;color:var(--text-secondary);margin-bottom:6px;">' +
              escHtml(a.ruleDescr || a.detail || '') + ' ' +
              (a.eventCount ? '（出现 ' + a.eventCount + ' 次）' : '') +
            '</div>' +
            '<div style="font-size:11px;color:var(--text-muted);">' +
              '来自: <a href="' + scanLink + '" style="color:var(--accent-blue);text-decoration:none;">' + escHtml(a.scanName) + '</a> · ' +
              '<code style="font-size:10px;background:rgba(255,255,255,0.05);padding:1px 4px;border-radius:3px;">' + escHtml(a.scanTarget) + '</code>' +
            '</div>' +
          '</div>' +
          '<div style="flex-shrink:0;">' +
            '<span class="pg-badge ' + (isHigh ? 'pg-badge-high' : 'pg-badge-medium') + '">' + (isHigh ? '高' : '中') + '</span>' +
            '<a href="' + scanLink + '" class="pg-btn pg-btn-primary pg-btn-sm" style="display:block;margin-top:8px;">查看详情</a>' +
          '</div>' +
        '</div>' +
      '</div>';
    }

    body.innerHTML = html;
  }

  // =========================================
  // 风险告警面板（从真实 API 获取）
  // =========================================

  // 本地存储：已关闭的告警
  function getDismissedAlerts() {
    try {
      return JSON.parse(localStorage.getItem('sf_dismissed_alerts') || '[]');
    } catch (e) { return []; }
  }
  function saveDismissedAlert(alertId) {
    var dismissed = getDismissedAlerts();
    if (dismissed.indexOf(alertId) < 0) {
      dismissed.push(alertId);
      localStorage.setItem('sf_dismissed_alerts', JSON.stringify(dismissed));
    }
  }

  function showAlertsPanel() {
    var content = document.querySelector('.pg-content');
    if (!content) return;

    content.innerHTML = '<div class="pg-page-header pg-fade-in">' +
      '<h1 class="pg-page-title">风险告警</h1>' +
      '<p class="pg-page-subtitle">从已完成扫描中提取的高风险关联与敏感数据发现</p>' +
      '<div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;">' +
        '<button class="pg-btn pg-btn-primary pg-btn-sm" onclick="window.location.href=\'' + _docroot + '/newscan\'">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>' +
          ' 新建扫描任务' +
        '</button>' +
        '<button class="pg-btn pg-btn-ghost pg-btn-sm" onclick="autoFixRisk(\'__batch_high__\')">一键处理全部高风险</button>' +
        '<button class="pg-btn pg-btn-ghost pg-btn-sm" onclick="showRiskCompareReport()">对比报告</button>' +
      '</div>' +
    '</div>' +
    '<div class="pg-stats-grid pg-fade-in" style="margin-bottom:14px;">' +
      '<div class="pg-stat-card blue"><div class="pg-stat-value" id="risk-stat-total">--</div><div class="pg-stat-label">告警总数</div></div>' +
      '<div class="pg-stat-card yellow"><div class="pg-stat-value" id="risk-stat-todo">--</div><div class="pg-stat-label">待处理</div></div>' +
      '<div class="pg-stat-card purple"><div class="pg-stat-value" id="risk-stat-progress">--</div><div class="pg-stat-label">处理中</div></div>' +
      '<div class="pg-stat-card green"><div class="pg-stat-value" id="risk-stat-resolved">--</div><div class="pg-stat-label">已处置</div></div>' +
      '<div class="pg-stat-card red"><div class="pg-stat-value" id="risk-stat-retest">--</div><div class="pg-stat-label">待复检</div></div>' +
    '</div>' +
    '<div class="pg-card pg-fade-in" style="margin-bottom:14px;">' +
      '<div class="pg-card-body" style="padding:10px 14px;">' +
        '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">' +
          '<span style="font-size:12px;color:var(--text-muted);">筛选状态:</span>' +
          '<button class="pg-btn pg-btn-ghost pg-btn-sm risk-filter-btn active" data-filter="all">全部</button>' +
          '<button class="pg-btn pg-btn-ghost pg-btn-sm risk-filter-btn" data-filter="todo">待处理</button>' +
          '<button class="pg-btn pg-btn-ghost pg-btn-sm risk-filter-btn" data-filter="in_progress">处理中</button>' +
          '<button class="pg-btn pg-btn-ghost pg-btn-sm risk-filter-btn" data-filter="resolved">已处置</button>' +
          '<button class="pg-btn pg-btn-ghost pg-btn-sm risk-filter-btn" data-filter="retest">待复检</button>' +
        '</div>' +
      '</div>' +
    '</div>' +

    '<div id="risk-alerts-container" class="pg-fade-in">' +
      '<div class="pg-empty" style="padding:80px 0;">' +
        '<div class="pg-empty-icon">' +
          '<span class="pg-loader" style="width:32px;height:32px;border-width:3px;"></span>' +
        '</div>' +
        '<div class="pg-empty-title" style="margin-top:16px;">正在加载风险告警...</div>' +
        '<div class="pg-empty-desc">正在从扫描结果中分析风险数据</div>' +
      '</div>' +
    '</div>';

    fetchRiskAlerts();
    bindRiskFilterEvents();
  }

  var currentRiskStatusFilter = 'all';

  function fetchRiskAlerts() {
    fetch(_docroot + '/riskalerts')
      .then(function(res) { return res.json(); })
      .then(function(alerts) {
        var dismissed = getDismissedAlerts();
        var activeAlerts = alerts.filter(function(a) { return dismissed.indexOf(a.alertId) < 0; });
        renderRiskAlerts(alerts);
        updateRiskBadgeCount(activeAlerts.length);
      })
      .catch(function(err) {
        var container = document.getElementById('risk-alerts-container');
        if (container) {
          container.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);">' +
            '<div style="font-size:32px;margin-bottom:12px;">⚠️</div>' +
            '<div style="color:var(--text-secondary);">加载告警失败: ' + err.message + '</div>' +
            '<div style="font-size:12px;margin-top:8px;">请确保已运行过至少一次扫描任务</div>' +
            '</div>';
        }
      });
  }

  function renderRiskAlerts(alerts) {
    var container = document.getElementById('risk-alerts-container');
    if (!container) return;

    var dismissed = getDismissedAlerts();
    var activeAlerts = alerts.filter(function(a) {
      return dismissed.indexOf(a.alertId) < 0;
    });
    updateRiskStats(activeAlerts);

    if (currentRiskStatusFilter !== 'all') {
      activeAlerts = activeAlerts.filter(function(a) {
        return (a.actionStatus || 'todo') === currentRiskStatusFilter;
      });
    }

    if (activeAlerts.length === 0) {
      container.innerHTML = '<div style="text-align:center;padding:60px 0;">' +
        '<div style="font-size:48px;margin-bottom:16px;">🛡️</div>' +
        '<div style="font-size:18px;font-weight:600;color:var(--text-primary);margin-bottom:8px;">暂无风险告警</div>' +
        '<div style="color:var(--text-secondary);font-size:13px;">您已完成的所有扫描均未检测到高风险数据泄露。<br>点击上方"新建扫描任务"启动新的检测。</div>' +
        '<a href="' + _docroot + '/newscan" class="pg-btn pg-btn-primary" style="margin-top:20px;">开始新扫描</a>' +
        '</div>';
      return;
    }

    var highAlerts = activeAlerts.filter(function(a) { return a.risk === 'HIGH'; });
    var mediumAlerts = activeAlerts.filter(function(a) { return a.risk === 'MEDIUM'; });

    var html = '';

    if (highAlerts.length > 0) {
      html += '<div style="margin-bottom:20px;">' +
        '<div style="font-size:12px;font-weight:600;color:var(--accent-red);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px;">' +
        '🔴 高风险 (' + highAlerts.length + ')</div>';
      highAlerts.forEach(function(alert) { html += renderAlertCard(alert, 'high'); });
      html += '</div>';
    }

    if (mediumAlerts.length > 0) {
      html += '<div>' +
        '<div style="font-size:12px;font-weight:600;color:var(--accent-yellow);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px;">' +
        '🟡 中风险 (' + mediumAlerts.length + ')</div>';
      mediumAlerts.forEach(function(alert) { html += renderAlertCard(alert, 'medium'); });
      html += '</div>';
    }

    container.innerHTML = html;
  }

  function updateRiskStats(alerts) {
    var counts = { total: 0, todo: 0, in_progress: 0, resolved: 0, retest: 0 };
    counts.total = alerts.length;
    for (var i = 0; i < alerts.length; i++) {
      var s = alerts[i].actionStatus || 'todo';
      if (counts[s] === undefined) continue;
      counts[s]++;
    }
    setText('risk-stat-total', counts.total);
    setText('risk-stat-todo', counts.todo);
    setText('risk-stat-progress', counts.in_progress);
    setText('risk-stat-resolved', counts.resolved);
    setText('risk-stat-retest', counts.retest);
  }

  function setText(id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function bindRiskFilterEvents() {
    var buttons = document.querySelectorAll('.risk-filter-btn');
    buttons.forEach(function(btn) {
      btn.addEventListener('click', function() {
        currentRiskStatusFilter = btn.getAttribute('data-filter') || 'all';
        buttons.forEach(function(b) { b.classList.remove('active'); });
        btn.classList.add('active');
        fetchRiskAlerts();
      });
    });
  }

  function renderAlertCard(alert, riskClass) {
    var iconBg = riskClass === 'high' ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)';
    var iconColor = riskClass === 'high' ? 'var(--accent-red)' : 'var(--accent-yellow)';

    var icon = alert.type === 'correlation'
      ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>'
      : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><circle cx="12" cy="12" r="10"/></svg>';

    var human = toHumanAlertText(alert);
    var btnLabel = alert.type === 'correlation' ? '查看关联' : '查看详情';
    var detailText = human.detail;

    var link = _docroot + '/scaninfo?id=' + (alert.scanId || '');
    var actionStatus = alert.actionStatus || 'todo';
    var statusLabelMap = {
      todo: '待处理',
      in_progress: '处理中',
      resolved: '已处置',
      retest: '待复检'
    };
    var planList = (alert.playbook || []).map(function(item) {
      return '<li style="margin:2px 0;">' + escHtml(item) + '</li>';
    }).join('');

    return '<div class="pg-alert-card ' + riskClass + '" id="alert-' + alert.alertId + '" style="margin-bottom:8px;">' +
      '<div style="flex-shrink:0;width:36px;height:36px;border-radius:8px;background:' + iconBg + ';color:' + iconColor + ';display:flex;align-items:center;justify-content:center;">' + icon + '</div>' +
      '<div style="flex:1;min-width:0;">' +
        '<div style="font-weight:600;font-size:13px;margin-bottom:4px;">' + escHtml(human.title) + '</div>' +
        '<div style="font-size:12px;color:var(--text-secondary);margin-bottom:6px;">' + escHtml(detailText) + '</div>' +
        '<div style="font-size:11px;color:var(--text-muted);">' +
          '来自: <a href="' + link + '" style="color:var(--accent-blue);text-decoration:none;">' + escHtml(alert.scanName) + '</a> · ' +
          '<code style="font-size:10px;background:rgba(255,255,255,0.05);padding:1px 4px;border-radius:3px;">' + escHtml(alert.scanTarget) + '</code>' +
          (alert.eventCount ? ' · ' + alert.eventCount + ' 次出现' : '') +
        '</div>' +
        '<div style="margin-top:8px;padding:8px 10px;border:1px solid var(--border-color);border-radius:8px;background:rgba(255,255,255,0.02);">' +
          '<div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;">处置建议</div>' +
          '<ul style="font-size:12px;color:var(--text-secondary);padding-left:18px;margin:0;">' + planList + '</ul>' +
        '</div>' +
        (alert.actionMethod ? (
          '<div style="margin-top:8px;padding:8px 10px;border:1px dashed rgba(79,142,247,0.45);border-radius:8px;background:rgba(79,142,247,0.06);">' +
          '<div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;">系统处理方法</div>' +
          '<div style="font-size:12px;color:var(--text-secondary);">' + escHtml(alert.actionMethod) + '</div>' +
          '</div>'
        ) : '') +
        '<div style="margin-top:8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;">' +
          '<span class="pg-badge pg-badge-gray" id="alert-status-text-' + alert.alertId + '">状态: ' + (statusLabelMap[actionStatus] || '待处理') + '</span>' +
          '<select id="alert-status-' + alert.alertId + '" class="pg-input" style="height:30px;padding:4px 8px;font-size:12px;min-width:120px;">' +
            '<option value="todo"' + (actionStatus === 'todo' ? ' selected' : '') + '>待处理</option>' +
            '<option value="in_progress"' + (actionStatus === 'in_progress' ? ' selected' : '') + '>处理中</option>' +
            '<option value="resolved"' + (actionStatus === 'resolved' ? ' selected' : '') + '>已处置</option>' +
            '<option value="retest"' + (actionStatus === 'retest' ? ' selected' : '') + '>待复检</option>' +
          '</select>' +
          '<button class="pg-btn pg-btn-primary pg-btn-sm" onclick="autoFixRisk(\'' + alert.alertId + '\')">一键处理</button>' +
          '<button class="pg-btn pg-btn-ghost pg-btn-sm" onclick="updateRiskAction(\'' + alert.alertId + '\')">保存状态</button>' +
        '</div>' +
      '</div>' +
      '<div style="display:flex;flex-direction:column;gap:6px;flex-shrink:0;min-width:80px;">' +
        '<a href="' + link + '" class="pg-btn pg-btn-primary pg-btn-sm">' + btnLabel + '</a>' +
        '<button class="pg-btn pg-btn-ghost pg-btn-sm" onclick="dismissAlert(\'' + alert.alertId + '\')" style="color:var(--text-muted);">关闭</button>' +
      '</div>' +
    '</div>';
  }

  function toHumanAlertText(alert) {
    var rawTitle = (alert && alert.title) ? String(alert.title) : '';
    var rawRule = (alert && alert.ruleDescr) ? String(alert.ruleDescr) : '';
    var rawDetail = (alert && alert.detail) ? String(alert.detail) : '';
    var source = (rawDetail || rawRule || rawTitle).toLowerCase();

    // 默认值
    var title = rawTitle || '检测到风险项';
    var detail = rawDetail || rawRule || '检测到可疑信息，建议尽快处理。';

    // 规则类常见英文文案翻译成“人话”
    if (source.indexOf('entity considered malicious by multiple sources') >= 0 || source.indexOf('considered malicious') >= 0) {
      title = '该 IP/账号被多个安全源判定为高风险';
      detail = '该对象在多个威胁情报源被标记为恶意，建议优先核查并限制访问。';
    } else if (source.indexOf('leak') >= 0 || source.indexOf('breach') >= 0) {
      title = '疑似存在信息泄露风险';
      detail = '检测到与泄露数据相关线索，建议立即改密并开启二次验证。';
    } else if (source.indexOf('tor') >= 0 || source.indexOf('proxy') >= 0 || source.indexOf('vpn') >= 0) {
      title = '发现匿名网络/代理相关风险';
      detail = '检测到目标与代理或匿名网络有关联，建议进一步核查来源与用途。';
    } else if (source.indexOf('credit') >= 0 || source.indexOf('iban') >= 0 || source.indexOf('bank') >= 0) {
      title = '发现金融敏感信息风险';
      detail = '检测到疑似银行卡或账户类敏感数据，请尽快脱敏和下线公开内容。';
    } else if (source.indexOf('email') >= 0 || source.indexOf('phone') >= 0 || source.indexOf('name') >= 0) {
      title = '发现个人隐私信息暴露';
      detail = '检测到邮箱/手机号/姓名等个人信息，建议先做脱敏并清理公开页面。';
    } else if (alert && alert.type === 'event' && rawTitle.indexOf('发现敏感数据:') === 0) {
      title = rawTitle.replace('发现敏感数据:', '发现敏感信息：');
      detail = rawDetail || '该类敏感信息已被检出，建议优先处置并复检。';
    }

    // 控制长度，避免英文大段挤压布局
    if (title.length > 40) title = title.slice(0, 40) + '...';
    if (detail.length > 90) detail = detail.slice(0, 90) + '...';
    return { title: title, detail: detail };
  }

  window.dismissAlert = function(alertId) {
    saveDismissedAlert(alertId);
    var card = document.getElementById('alert-' + alertId);
    if (card) {
      card.style.transition = 'all 0.3s ease';
      card.style.opacity = '0';
      card.style.transform = 'translateX(20px)';
      setTimeout(function() {
        card.remove();
        var container = document.getElementById('risk-alerts-container');
        if (container && container.querySelectorAll('.pg-alert-card').length === 0) {
          container.innerHTML = '<div style="text-align:center;padding:60px 0;">' +
            '<div style="font-size:48px;margin-bottom:16px;">🛡️</div>' +
            '<div style="font-size:18px;font-weight:600;color:var(--text-primary);margin-bottom:8px;">暂无风险告警</div>' +
            '<div style="color:var(--text-secondary);font-size:13px;">所有告警已处理完毕</div>' +
            '</div>';
        }
        // 重新计算活跃（未关闭）告警数，精确更新徽章
        var remaining = container ? container.querySelectorAll('.pg-alert-card').length : 0;
        updateRiskBadgeCount(remaining);
      }, 300);
    }
  };

  window.updateRiskAction = function(alertId) {
    var select = document.getElementById('alert-status-' + alertId);
    if (!select) return;
    var status = select.value;
    var payload = 'alertId=' + encodeURIComponent(alertId) + '&status=' + encodeURIComponent(status);
    fetch(_docroot + '/riskactionupdate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' },
      body: payload
    }).then(function(res) { return res.json(); })
      .then(function(ret) {
        if (ret && ret.error) {
          showNotification('warning', '状态保存失败: ' + (ret.error.message || '未知错误'));
          return;
        }
        var labelMap = {
          todo: '待处理',
          in_progress: '处理中',
          resolved: '已处置',
          retest: '待复检'
        };
        var statusEl = document.getElementById('alert-status-text-' + alertId);
        if (statusEl) statusEl.textContent = '状态: ' + (labelMap[status] || status);
        showNotification('success', '风险状态已更新');
        fetchRiskAlerts();
      })
      .catch(function(err) {
        showNotification('warning', '状态保存失败: ' + err.message);
      });
  };

  window.autoFixRisk = function(alertId) {
    var isBatchHigh = alertId === '__batch_high__';
    var payload = isBatchHigh
      ? 'scope=high'
      : ('scope=single&alertId=' + encodeURIComponent(alertId));
    fetch(_docroot + '/riskactionautofix', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' },
      body: payload
    }).then(function(res) {
      var contentType = (res.headers.get('content-type') || '').toLowerCase();
      if (contentType.indexOf('application/json') >= 0) {
        return res.json();
      }
      return res.text().then(function(txt) {
        return { error: { message: '服务器返回非JSON响应（可能未登录或服务未重启）' }, raw: txt };
      });
    })
      .then(function(ret) {
        if (ret && ret.error) {
          showAutoFixPermissionDialog(ret.error.message || '权限不足或会话失效');
          return;
        }
        var rerunInfo = (ret && ret.rerunScanIds && ret.rerunScanIds.length)
          ? ('，已触发复检: ' + ret.rerunScanIds.join(','))
          : '';
        if (isBatchHigh) {
          showNotification('success', '已一键处理高风险项：' + (ret.updatedCount || 0) + ' 条' + rerunInfo);
        } else {
          showNotification('success', '该风险项已一键处理并同步状态' + rerunInfo);
        }
        fetchRiskAlerts();
      })
      .catch(function(err) {
        showAutoFixPermissionDialog(err && err.message ? err.message : '权限不足或服务未就绪');
      });
  };

  function showAutoFixPermissionDialog(reason) {
    var msg = String(reason || '').toLowerCase();
    var hint = '当前会话缺少一键处理所需权限。请按以下项检查后重试。';
    if (msg.indexOf('nonjson') >= 0 || msg.indexOf('登录') >= 0 || msg.indexOf('login') >= 0 || msg.indexOf('401') >= 0) {
      hint = '当前登录状态无效或会话已过期，请先重新登录。';
    } else if (msg.indexOf('403') >= 0 || msg.indexOf('forbidden') >= 0 || msg.indexOf('denied') >= 0 || msg.indexOf('permission') >= 0) {
      hint = '系统拒绝执行一键处理，通常是处理权限未开启。';
    }

    var html =
      '<div style="text-align:left;line-height:1.8;">' +
      '<div style="margin-bottom:8px;">' + escHtml(hint) + '</div>' +
      '<div style="font-size:12px;color:var(--text-secondary);">需要开启的权限/条件：</div>' +
      '<ul style="margin:6px 0 0 18px;padding:0;font-size:12px;color:var(--text-secondary);">' +
      '<li>登录会话有效（未过期）</li>' +
      '<li>后端已重启到最新版本（包含一键处理接口）</li>' +
      '<li>数据库可写（用于脱敏写回、状态同步、报告记录）</li>' +
      '<li>允许触发复检任务（可创建扫描实例）</li>' +
      '</ul>' +
      '<div style="margin-top:8px;font-size:11px;color:var(--text-muted);">详细原因：' + escHtml(reason || '未知') + '</div>' +
      '</div>';

    if (typeof alertify !== 'undefined' && alertify.alert) {
      alertify.alert('一键处理未执行', html);
    } else {
      window.alert('一键处理未执行。请检查登录、服务版本、数据库写权限与复检任务权限。');
    }
  }

  window.showRiskCompareReport = function() {
    var content = document.querySelector('.pg-content');
    if (!content) return;
    content.innerHTML = '<div class="pg-page-header pg-fade-in">' +
      '<h1 class="pg-page-title">处置对比报告</h1>' +
      '<p class="pg-page-subtitle">展示一键处理后的复检结果与风险变化趋势</p>' +
      '</div>' +
      '<div id="risk-compare-summary" class="pg-stats-grid pg-fade-in" style="margin-bottom:14px;">' +
        '<div class="pg-stat-card blue"><div class="pg-stat-value" id="rc-total">--</div><div class="pg-stat-label">报告总数</div></div>' +
        '<div class="pg-stat-card red"><div class="pg-stat-value" id="rc-high-drop">--</div><div class="pg-stat-label">高风险下降率</div></div>' +
        '<div class="pg-stat-card yellow"><div class="pg-stat-value" id="rc-medium-drop">--</div><div class="pg-stat-label">中风险下降率</div></div>' +
        '<div class="pg-stat-card green"><div class="pg-stat-value" id="rc-done">--</div><div class="pg-stat-label">已完成复检</div></div>' +
      '</div>' +
      '<div class="pg-card pg-fade-in" style="margin-bottom:14px;">' +
        '<div class="pg-card-body" style="display:flex;gap:8px;flex-wrap:wrap;">' +
          '<button class="pg-btn pg-btn-primary pg-btn-sm" onclick="exportRiskCompareCsv()">导出 CSV</button>' +
          '<button class="pg-btn pg-btn-ghost pg-btn-sm" onclick="copyRiskComparePitch()">复制答辩摘要</button>' +
          '<span id="rc-summary-tip" style="font-size:12px;color:var(--text-muted);align-self:center;"></span>' +
        '</div>' +
      '</div>' +
      '<div id="risk-compare-container" class="pg-card pg-fade-in">' +
      '<div class="pg-card-body"><div style="text-align:center;padding:40px 0;"><span class="pg-loader" style="width:28px;height:28px;border-width:3px;"></span><div style="margin-top:10px;color:var(--text-secondary);font-size:13px;">正在加载对比报告...</div></div></div>' +
      '</div>';

    fetch(_docroot + '/riskactionreport')
      .then(function(res) { return res.json(); })
      .then(function(rows) {
        var wrap = document.getElementById('risk-compare-container');
        if (!wrap) return;
        window.__riskCompareRows = rows || [];
        renderRiskCompareSummary(rows || []);
        if (!rows || !rows.length) {
          wrap.innerHTML = '<div class="pg-card-body" style="text-align:center;padding:50px 0;color:var(--text-muted);">暂无对比报告，请先执行一键处理并等待复检。</div>';
          return;
        }
        var html = '<div class="pg-card-body"><div class="pg-table-wrap"><table class="pg-table"><thead><tr>' +
          '<th>原扫描</th><th>复检扫描</th><th>处理前(H/M)</th><th>处理后(H/M)</th><th>变化(H/M)</th><th>状态</th><th>更新时间</th>' +
          '</tr></thead><tbody>';
        rows.forEach(function(r) {
          var before = (r.baseline && r.baseline.HIGH !== undefined) ? (r.baseline.HIGH + '/' + r.baseline.MEDIUM) : '-';
          var after = (r.after && r.after.HIGH !== null && r.after.HIGH !== undefined) ? (r.after.HIGH + '/' + r.after.MEDIUM) : '待复检';
          var delta = (r.delta && r.delta.HIGH !== null && r.delta.HIGH !== undefined)
            ? ((r.delta.HIGH > 0 ? '+' : '') + r.delta.HIGH + '/' + (r.delta.MEDIUM > 0 ? '+' : '') + r.delta.MEDIUM)
            : '--';
          var statusText = r.status === 'DONE' ? '已完成' : '复检中';
          var statusCls = r.status === 'DONE' ? 'pg-badge-green' : 'pg-badge-yellow';
          html += '<tr>' +
            '<td><div style="font-weight:600;">' + escHtml(r.scanName || r.scanId) + '</div><div style="font-size:11px;color:var(--text-muted);">' + escHtml(r.scanTarget || '') + '</div></td>' +
            '<td><a href="' + _docroot + '/scaninfo?id=' + escHtml(r.rerunScanId || '') + '" style="color:var(--accent-blue);text-decoration:none;">' + escHtml(r.rerunScanId || '-') + '</a><div style="font-size:11px;color:var(--text-muted);">' + escHtml(r.rerunStatus || '-') + '</div></td>' +
            '<td>' + before + '</td>' +
            '<td>' + after + '</td>' +
            '<td>' + delta + '</td>' +
            '<td><span class="pg-badge ' + statusCls + '">' + statusText + '</span></td>' +
            '<td style="font-size:11px;color:var(--text-muted);">' + escHtml(r.updatedAt || '-') + '</td>' +
            '</tr>';
        });
        html += '</tbody></table></div></div>';
        wrap.innerHTML = html;
      })
      .catch(function(err) {
        var wrap = document.getElementById('risk-compare-container');
        if (wrap) wrap.innerHTML = '<div class="pg-card-body" style="text-align:center;padding:50px 0;color:var(--text-muted);">加载失败：' + escHtml(err.message) + '</div>';
      });
  };

  function renderRiskCompareSummary(rows) {
    var total = rows.length;
    var done = rows.filter(function(r) { return r.status === 'DONE'; }).length;
    var baseHigh = 0, afterHigh = 0, baseMed = 0, afterMed = 0;
    rows.forEach(function(r) {
      baseHigh += (r.baseline && r.baseline.HIGH) ? r.baseline.HIGH : 0;
      baseMed += (r.baseline && r.baseline.MEDIUM) ? r.baseline.MEDIUM : 0;
      if (r.after && r.after.HIGH !== null && r.after.HIGH !== undefined) afterHigh += r.after.HIGH;
      if (r.after && r.after.MEDIUM !== null && r.after.MEDIUM !== undefined) afterMed += r.after.MEDIUM;
    });
    var highDrop = baseHigh > 0 ? (((baseHigh - afterHigh) / baseHigh) * 100).toFixed(1) + '%' : '--';
    var medDrop = baseMed > 0 ? (((baseMed - afterMed) / baseMed) * 100).toFixed(1) + '%' : '--';
    setText('rc-total', total);
    setText('rc-done', done);
    setText('rc-high-drop', highDrop);
    setText('rc-medium-drop', medDrop);
    var tip = document.getElementById('rc-summary-tip');
    if (tip) {
      tip.textContent = '当前基线 H/M: ' + baseHigh + '/' + baseMed + ' -> 复检后 H/M: ' + afterHigh + '/' + afterMed;
    }
  }

  window.exportRiskCompareCsv = function() {
    var rows = window.__riskCompareRows || [];
    if (!rows.length) {
      showNotification('warning', '暂无可导出的对比报告');
      return;
    }
    var header = ['scan_id','scan_name','scan_target','rerun_scan_id','rerun_status','before_high','before_medium','after_high','after_medium','delta_high','delta_medium','status','updated_at'];
    var lines = [header.join(',')];
    rows.forEach(function(r) {
      var vals = [
        r.scanId || '',
        r.scanName || '',
        r.scanTarget || '',
        r.rerunScanId || '',
        r.rerunStatus || '',
        (r.baseline && r.baseline.HIGH !== undefined) ? r.baseline.HIGH : '',
        (r.baseline && r.baseline.MEDIUM !== undefined) ? r.baseline.MEDIUM : '',
        (r.after && r.after.HIGH !== undefined && r.after.HIGH !== null) ? r.after.HIGH : '',
        (r.after && r.after.MEDIUM !== undefined && r.after.MEDIUM !== null) ? r.after.MEDIUM : '',
        (r.delta && r.delta.HIGH !== undefined && r.delta.HIGH !== null) ? r.delta.HIGH : '',
        (r.delta && r.delta.MEDIUM !== undefined && r.delta.MEDIUM !== null) ? r.delta.MEDIUM : '',
        r.status || '',
        r.updatedAt || ''
      ].map(function(v) {
        var s = String(v).replace(/"/g, '""');
        return '"' + s + '"';
      });
      lines.push(vals.join(','));
    });
    var blob = new Blob(["\ufeff" + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'risk_compare_report.csv';
    a.click();
    URL.revokeObjectURL(a.href);
    showNotification('success', '对比报告 CSV 已导出');
  };

  window.copyRiskComparePitch = function() {
    var rows = window.__riskCompareRows || [];
    if (!rows.length) {
      showNotification('warning', '暂无报告数据，无法生成摘要');
      return;
    }
    var done = rows.filter(function(r) { return r.status === 'DONE'; }).length;
    var baseHigh = 0, afterHigh = 0, baseMed = 0, afterMed = 0;
    rows.forEach(function(r) {
      baseHigh += (r.baseline && r.baseline.HIGH) ? r.baseline.HIGH : 0;
      baseMed += (r.baseline && r.baseline.MEDIUM) ? r.baseline.MEDIUM : 0;
      if (r.after && r.after.HIGH !== null && r.after.HIGH !== undefined) afterHigh += r.after.HIGH;
      if (r.after && r.after.MEDIUM !== null && r.after.MEDIUM !== undefined) afterMed += r.after.MEDIUM;
    });
    var highDrop = baseHigh > 0 ? (((baseHigh - afterHigh) / baseHigh) * 100).toFixed(1) : '0.0';
    var medDrop = baseMed > 0 ? (((baseMed - afterMed) / baseMed) * 100).toFixed(1) : '0.0';
    var text = '本次系统共生成 ' + rows.length + ' 条自动处置对比报告，已完成复检 ' + done + ' 条。' +
      '高风险由 ' + baseHigh + ' 降至 ' + afterHigh + '（下降 ' + highDrop + '%），' +
      '中风险由 ' + baseMed + ' 降至 ' + afterMed + '（下降 ' + medDrop + '%）。' +
      '说明一键处理在隐私风险收敛上有效，并具备可追踪、可复检的闭环能力。';
    navigator.clipboard.writeText(text).then(function() {
      showNotification('success', '答辩摘要已复制');
    }).catch(function() {
      showNotification('warning', '复制失败，请手动复制摘要');
    });
  };

  function updateRiskBadgeCount(count) {
    var badge = document.getElementById('nav-alert-badge');
    if (!badge) return;
    if (count <= 0) {
      badge.style.display = 'none';
    } else {
      badge.textContent = count > 99 ? '99+' : count;
      badge.style.display = 'inline-block';
    }
  }

  // =========================================
  // 服务监控面板（显示系统状态，无假数据）
  // =========================================

  function showServicesPanel() {
    var content = document.querySelector('.pg-content');
    if (!content) return;

    content.innerHTML = '<div class="pg-page-header pg-fade-in">' +
      '<h1 class="pg-page-title">服务监控</h1>' +
      '<p class="pg-page-subtitle">SpiderFoot 核心模块与数据库运行状态</p>' +
    '</div>' +
    '<div id="services-content" class="pg-fade-in">' +
      '<div style="text-align:center;padding:60px 0;">' +
        '<span class="pg-loader" style="width:28px;height:28px;border-width:3px;"></span>' +
        '<div style="margin-top:12px;color:var(--text-secondary);font-size:13px;">正在加载服务状态...</div>' +
      '</div>' +
    '</div>';

    // 从 scanlist API 推断系统状态
    fetch(_docroot + '/scanlist').then(function(r) { return r.json(); }).then(function(data) {
      var running = 0, finished = 0, error = 0;
      for (var i = 0; i < data.length; i++) {
        var s = data[i][6];
        if (['RUNNING','STARTING','STARTED','INITIALIZING'].indexOf(s) >= 0) running++;
        else if (s === 'FINISHED') finished++;
        else if ((s || '').indexOf('ABORT') >= 0 || (s || '').indexOf('FAILED') >= 0) error++;
      }

      var uptime = data.length > 0 ? getUptime(data) : '首次使用';

      document.getElementById('services-content').innerHTML = '<div class="pg-stats-grid">' +
        '<div class="pg-stat-card blue">' +
          '<div class="pg-stat-icon blue">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>' +
          '</div>' +
          '<div class="pg-stat-value">' + data.length + '</div>' +
          '<div class="pg-stat-label">历史扫描总数</div>' +
          '<div class="pg-stat-trend">运行时长：' + uptime + '</div>' +
        '</div>' +
        '<div class="pg-stat-card yellow">' +
          '<div class="pg-stat-icon yellow">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>' +
          '</div>' +
          '<div class="pg-stat-value" style="color:var(--accent-yellow);">' + running + '</div>' +
          '<div class="pg-stat-label">进行中扫描</div>' +
        '</div>' +
        '<div class="pg-stat-card green">' +
          '<div class="pg-stat-icon green">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><polyline points="20 6 9 17 4 12"/></svg>' +
          '</div>' +
          '<div class="pg-stat-value" style="color:var(--accent-green);">' + finished + '</div>' +
          '<div class="pg-stat-label">已完成扫描</div>' +
        '</div>' +
        '<div class="pg-stat-card red">' +
          '<div class="pg-stat-icon red">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>' +
          '</div>' +
          '<div class="pg-stat-value" style="color:var(--accent-red);">' + error + '</div>' +
          '<div class="pg-stat-label">失败/中止</div>' +
        '</div>' +
      '</div>' +
      '<div class="pg-card" style="margin-top:16px;">' +
        '<div class="pg-card-header">' +
          '<div class="pg-card-title">模块状态</div>' +
        '</div>' +
        '<div class="pg-card-body">' +
          '<div style="font-size:13px;color:var(--text-secondary);line-height:2;">' +
            '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">' +
              '<span class="pg-dot-green" style="width:8px;height:8px;border-radius:50%;background:var(--accent-green);display:inline-block;"></span>' +
              '<strong>sfwebui</strong> — Web 服务正常运行' +
            '</div>' +
            '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">' +
              '<span class="pg-dot-green" style="width:8px;height:8px;border-radius:50%;background:var(--accent-green);display:inline-block;"></span>' +
              '<strong>spiderfoot.db</strong> — 数据库连接正常' +
            '</div>' +
            '<div style="display:flex;align-items:center;gap:8px;">' +
              '<span class="' + (running > 0 ? 'pg-dot-yellow' : 'pg-dot-green') + '" style="width:8px;height:8px;border-radius:50%;background:' + (running > 0 ? 'var(--accent-yellow)' : 'var(--accent-green)') + ';display:inline-block;"></span>' +
              '<strong>scanner</strong> — ' + (running > 0 ? running + ' 个扫描任务执行中' : '无运行中的扫描任务') +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div style="margin-top:16px;font-size:12px;color:var(--text-muted);text-align:center;">' +
        '服务监控数据来源于实际系统状态，无模拟数据。如需查看详细扫描日志，请访问「扫描任务」页面。' +
      '</div>';
    }).catch(function() {
      document.getElementById('services-content').innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);">加载失败，请刷新重试</div>';
    });
  }

  // =========================================
  // 数据洞察看板（大数据可视化）
  // =========================================
  function showDataInsightDashboard() {
    var content = document.querySelector('.pg-content');
    if (!content) return;

    content.innerHTML = '<div class="pg-page-header pg-fade-in">' +
      '<h1 class="pg-page-title">数据洞察看板</h1>' +
      '<p class="pg-page-subtitle">把复杂扫描结果翻译成“看得懂、做得到”的隐私风险建议</p>' +
    '</div>' +
    '<div class="pg-stats-grid pg-fade-in" style="margin-bottom:14px;">' +
      '<div class="pg-stat-card blue"><div class="pg-stat-value" id="dv-total-scans">--</div><div class="pg-stat-label">累计扫描任务</div></div>' +
      '<div class="pg-stat-card green"><div class="pg-stat-value" id="dv-finished-scans">--</div><div class="pg-stat-label">已完成扫描</div></div>' +
      '<div class="pg-stat-card red"><div class="pg-stat-value" id="dv-high-risks">--</div><div class="pg-stat-label">高风险告警</div></div>' +
      '<div class="pg-stat-card yellow"><div class="pg-stat-value" id="dv-medium-risks">--</div><div class="pg-stat-label">中风险告警</div></div>' +
    '</div>' +
    '<div style="display:grid;grid-template-columns:1.4fr 1fr;gap:14px;margin-bottom:14px;">' +
      '<div class="pg-card"><div class="pg-card-header"><div class="pg-card-title">最近 14 天扫描趋势</div></div><div class="pg-card-body">' +
      '<div id="dv-trend-tip" style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;">解读：扫描次数越稳定，越容易持续发现新风险。</div>' +
      '<svg id="dv-trend-chart" style="width:100%;height:260px;"></svg></div></div>' +
      '<div class="pg-card"><div class="pg-card-header"><div class="pg-card-title">风险结构（红=高风险，黄=中风险）</div></div><div class="pg-card-body">' +
      '<div id="dv-risk-tip" style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;">解读：红色越多，越需要优先处理账号、联系方式等泄露问题。</div>' +
      '<svg id="dv-risk-donut" style="width:100%;height:260px;"></svg></div></div>' +
    '</div>' +
    '<div style="display:grid;grid-template-columns:1.2fr 1fr;gap:14px;margin-bottom:14px;">' +
      '<div class="pg-card"><div class="pg-card-header"><div class="pg-card-title">最常见风险类型（Top 8）</div></div><div class="pg-card-body">' +
      '<div id="dv-types-tip" style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;">解读：条越长，代表这类问题出现越多，建议优先治理。</div>' +
      '<svg id="dv-top-types" style="width:100%;height:300px;"></svg></div></div>' +
      '<div class="pg-card"><div class="pg-card-header"><div class="pg-card-title">处理进度（从发现到复检）</div></div><div class="pg-card-body">' +
      '<div id="dv-funnel-tip" style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;">解读：绿色“已处置”越多，说明隐私风险正在下降。</div>' +
      '<svg id="dv-action-funnel" style="width:100%;height:300px;"></svg></div></div>' +
    '</div>' +
    '<div class="pg-card pg-fade-in">' +
      '<div class="pg-card-header"><div class="pg-card-title">给普通用户的下一步建议</div></div>' +
      '<div class="pg-card-body" id="dv-action-advice" style="font-size:13px;color:var(--text-secondary);line-height:1.8;">正在生成建议...</div>' +
    '</div>';

    Promise.all([
      fetch(_docroot + '/scanlist').then(function(r) { return r.json(); }).catch(function() { return []; }),
      fetch(_docroot + '/riskalerts').then(function(r) { return r.json(); }).catch(function() { return []; })
    ]).then(function(results) {
      var scanList = results[0] || [];
      var alerts = results[1] || [];
      renderDataInsightDashboard(scanList, alerts);
    });
  }

  function renderDataInsightDashboard(scanList, alerts) {
    var finished = scanList.filter(function(s) { return s[6] === 'FINISHED'; }).length;
    var high = alerts.filter(function(a) { return a.risk === 'HIGH'; }).length;
    var medium = alerts.filter(function(a) { return a.risk === 'MEDIUM'; }).length;
    setText('dv-total-scans', scanList.length);
    setText('dv-finished-scans', finished);
    setText('dv-high-risks', high);
    setText('dv-medium-risks', medium);

    renderScanTrendChart(scanList);
    renderRiskDonutChart(alerts);
    renderTopRiskTypeChart(alerts);
    renderActionFunnelChart(alerts);
    renderPlainAdvice(scanList, alerts);
  }

  function renderPlainAdvice(scanList, alerts) {
    var adviceEl = document.getElementById('dv-action-advice');
    if (!adviceEl) return;
    var high = alerts.filter(function(a) { return a.risk === 'HIGH'; }).length;
    var medium = alerts.filter(function(a) { return a.risk === 'MEDIUM'; }).length;
    var resolved = alerts.filter(function(a) { return (a.actionStatus || 'todo') === 'resolved'; }).length;
    var retest = alerts.filter(function(a) { return (a.actionStatus || 'todo') === 'retest'; }).length;

    var levelText = high >= 5 ? '当前风险偏高，建议优先处理高风险项。' :
      (high > 0 ? '存在少量高风险，建议本周内完成处置。' : '当前未发现高风险，整体情况较好。');
    var firstAction = high > 0
      ? '第一步：进入“风险告警”，按“高风险”筛选，先处理账号泄露/联系方式暴露。'
      : '第一步：继续保持每周扫描 1-2 次，持续监控是否出现新暴露。';
    var secondAction = medium > 3
      ? '第二步：处理中风险较多，建议批量做信息脱敏（手机号、邮箱、历史帖子）。'
      : '第二步：处理中风险较少，可按优先级逐条关闭。';
    var thirdAction = retest > 0
      ? '第三步：你有待复检任务，处置完成后请立即发起复扫确认是否生效。'
      : '第三步：处置后记得把状态改为“待复检”，形成闭环。';

    adviceEl.innerHTML =
      '<div style="margin-bottom:8px;"><strong>一句话结论：</strong>' + levelText + '</div>' +
      '<ul style="padding-left:18px;margin:0;">' +
      '<li style="margin:4px 0;">' + firstAction + '</li>' +
      '<li style="margin:4px 0;">' + secondAction + '</li>' +
      '<li style="margin:4px 0;">' + thirdAction + '</li>' +
      '<li style="margin:4px 0;">当前已处置 <strong>' + resolved + '</strong> 项，建议目标：本周至少新增处置 3 项。</li>' +
      '</ul>';
  }

  function renderScanTrendChart(scanList) {
    var svg = document.getElementById('dv-trend-chart');
    if (!svg) return;
    var rect = svg.getBoundingClientRect();
    var width = Math.max(420, Math.floor(rect.width || 640));
    var height = 260;
    svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
    var margin = { top: 14, right: 24, bottom: 28, left: 34 };
    var innerW = width - margin.left - margin.right;
    var innerH = height - margin.top - margin.bottom;

    var days = [];
    var now = new Date();
    for (var i = 13; i >= 0; i--) {
      var d = new Date(now.getTime() - i * 86400000);
      days.push({
        key: d.toISOString().slice(0, 10),
        label: (d.getMonth() + 1) + '/' + d.getDate(),
        value: 0
      });
    }
    var dayMap = {};
    days.forEach(function(d) { dayMap[d.key] = d; });
    scanList.forEach(function(row) {
      var created = row[3];
      var dateObj = typeof created === 'string' ? new Date(created.replace(' ', 'T')) : null;
      if (!dateObj || isNaN(dateObj.getTime())) return;
      var key = dateObj.toISOString().slice(0, 10);
      if (dayMap[key]) dayMap[key].value += 1;
    });

    var yMax = 2;
    for (var m = 0; m < days.length; m++) yMax = Math.max(yMax, days[m].value);
    var points = [];
    for (var i = 0; i < days.length; i++) {
      var px = margin.left + (innerW * i / Math.max(1, days.length - 1));
      var py = margin.top + innerH - (days[i].value / yMax) * innerH;
      points.push({ x: px, y: py, label: days[i].label, value: days[i].value });
    }

    var lines = '';
    for (var gy = 0; gy <= 4; gy++) {
      var yv = margin.top + (innerH * gy / 4);
      lines += '<line x1="' + margin.left + '" y1="' + yv + '" x2="' + (margin.left + innerW) + '" y2="' + yv + '" stroke="#1e293b" stroke-width="1"/>';
    }
    var path = '';
    for (var p = 0; p < points.length; p++) {
      path += (p === 0 ? 'M' : 'L') + points[p].x + ',' + points[p].y + ' ';
    }
    var dots = points.map(function(pt) {
      return '<circle cx="' + pt.x + '" cy="' + pt.y + '" r="3.5" fill="#4f8ef7"></circle>';
    }).join('');
    var xlabels = points.filter(function(_, idx) { return idx % 2 === 0; }).map(function(pt) {
      return '<text x="' + pt.x + '" y="' + (height - 8) + '" fill="#94a3b8" font-size="10" text-anchor="middle">' + pt.label + '</text>';
    }).join('');
    svg.innerHTML = lines +
      '<line x1="' + margin.left + '" y1="' + (margin.top + innerH) + '" x2="' + (margin.left + innerW) + '" y2="' + (margin.top + innerH) + '" stroke="#475569" stroke-width="1"/>' +
      '<line x1="' + margin.left + '" y1="' + margin.top + '" x2="' + margin.left + '" y2="' + (margin.top + innerH) + '" stroke="#475569" stroke-width="1"/>' +
      '<path d="' + path + '" fill="none" stroke="#4f8ef7" stroke-width="2.2"></path>' + dots + xlabels;
  }

  function renderRiskDonutChart(alerts) {
    var svg = document.getElementById('dv-risk-donut');
    if (!svg) return;
    var width = 320, height = 260;
    svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
    var high = alerts.filter(function(a) { return a.risk === 'HIGH'; }).length;
    var medium = alerts.filter(function(a) { return a.risk === 'MEDIUM'; }).length;
    var other = Math.max(0, alerts.length - high - medium);
    var data = [
      { name: 'HIGH', value: high, color: '#ef4444' },
      { name: 'MEDIUM', value: medium, color: '#f59e0b' },
      { name: 'OTHER', value: other, color: '#64748b' }
    ].filter(function(d) { return d.value > 0; });
    if (!data.length) data = [{ name: 'NO DATA', value: 1, color: '#64748b' }];

    var total = data.reduce(function(s, d) { return s + d.value; }, 0);
    var barX = 24, barY = 98, barW = 272, barH = 24;
    var labelY = 160;
    var stacked = '';
    var offset = 0;
    for (var i = 0; i < data.length; i++) {
      var segW = (data[i].value / total) * barW;
      stacked += '<rect x="' + (barX + offset) + '" y="' + barY + '" width="' + segW + '" height="' + barH + '" rx="4" fill="' + data[i].color + '"></rect>';
      offset += segW;
    }

    var legend = data.map(function(d, i) {
      var pct = ((d.value / total) * 100).toFixed(1) + '%';
      var cn = d.name === 'HIGH' ? '高风险' : (d.name === 'MEDIUM' ? '中风险' : '其他');
      return '<rect x="24" y="' + (labelY + i * 24) + '" width="10" height="10" rx="2" fill="' + d.color + '"></rect>' +
        '<text x="40" y="' + (labelY + 9 + i * 24) + '" fill="#cbd5e1" font-size="11">' + cn + '</text>' +
        '<text x="296" y="' + (labelY + 9 + i * 24) + '" fill="#94a3b8" font-size="11" text-anchor="end">' + d.value + ' / ' + total + '（' + pct + '）</text>';
    }).join('');

    svg.innerHTML =
      '<text x="24" y="42" fill="#e2e8f0" font-size="20" font-weight="700">总告警 ' + alerts.length + '</text>' +
      '<text x="24" y="62" fill="#94a3b8" font-size="11">每种颜色占比越大，说明该风险类型越需要优先处理</text>' +
      '<rect x="' + barX + '" y="' + barY + '" width="' + barW + '" height="' + barH + '" rx="6" fill="#0f172a" stroke="#334155" stroke-width="1"></rect>' +
      stacked +
      legend;
  }

  function renderTopRiskTypeChart(alerts) {
    var svg = document.getElementById('dv-top-types');
    if (!svg) return;
    var rect = svg.getBoundingClientRect();
    var width = Math.max(420, rect.width || 620);
    var height = 300;
    svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
    var margin = { top: 12, right: 90, bottom: 16, left: 190 };
    var innerW = width - margin.left - margin.right;
    var innerH = height - margin.top - margin.bottom;

    var counter = {};
    alerts.forEach(function(a) {
      var key = getRiskTypeLabel(a);
      counter[key] = (counter[key] || 0) + 1;
    });
    var data = Object.keys(counter).map(function(k) { return { key: k, value: counter[k] }; })
      .sort(function(a, b) { return b.value - a.value; })
      .slice(0, 8);
    if (!data.length) {
      svg.innerHTML = '<text x="' + (width / 2) + '" y="' + (height / 2) + '" fill="#94a3b8" font-size="13" text-anchor="middle">暂无可视化数据</text>';
      return;
    }

    var total = data.reduce(function(s, d) { return s + d.value; }, 0);
    var maxV = Math.max(1, data.reduce(function(m, d) { return Math.max(m, d.value); }, 0));
    // 固定条形高度，避免只有 1 条数据时被拉成整块色块
    var barH = 20;
    var rowGap = 12;
    var startY = 36;
    var neededH = startY + data.length * (barH + rowGap) + 12;
    var dynamicH = Math.max(height, neededH);
    svg.setAttribute('viewBox', '0 0 ' + width + ' ' + dynamicH);
    var bars = '';
    var palette = ['#22c55e', '#16a34a', '#3b82f6', '#6366f1', '#f59e0b', '#ef4444', '#14b8a6', '#94a3b8'];
    for (var i = 0; i < data.length; i++) {
      var y = startY + i * (barH + rowGap);
      var w = (data[i].value / maxV) * innerW;
      var label = data[i].key.length > 20 ? data[i].key.slice(0, 20) + '…' : data[i].key;
      var pct = ((data[i].value / Math.max(1, total)) * 100).toFixed(1) + '%';
      var color = palette[i % palette.length];
      var rank = i + 1;
      bars +=
        '<text x="' + (margin.left - 165) + '" y="' + (y + barH / 2 + 4) + '" fill="#cbd5e1" font-size="11" text-anchor="start">TOP ' + rank + '</text>' +
        '<text x="' + (margin.left - 95) + '" y="' + (y + barH / 2 + 4) + '" fill="#94a3b8" font-size="11" text-anchor="start">' + label + '</text>' +
        '<rect x="' + margin.left + '" y="' + y + '" width="' + w + '" height="' + barH + '" rx="6" fill="' + color + '" opacity="0.9"></rect>' +
        '<text x="' + (margin.left + w + 8) + '" y="' + (y + barH / 2 + 4) + '" fill="#cbd5e1" font-size="11">' + data[i].value + ' (' + pct + ')</text>';
    }
    svg.innerHTML = '<text x="8" y="14" fill="#94a3b8" font-size="11">越靠前表示该风险类型出现越频繁，建议优先治理</text>' + bars;
  }

  function getRiskTypeLabel(alert) {
    if (!alert) return '未知类型';
    if (alert.type === 'event') {
      if (alert.title && alert.title.indexOf('发现敏感数据:') === 0) {
        return alert.title.replace('发现敏感数据:', '').trim();
      }
      return alert.eventType || '事件风险';
    }
    return alert.ruleName || alert.title || '关联风险';
  }

  function renderActionFunnelChart(alerts) {
    var svg = document.getElementById('dv-action-funnel');
    if (!svg) return;
    var width = 420, height = 300;
    svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
    var counts = { todo: 0, in_progress: 0, resolved: 0, retest: 0 };
    alerts.forEach(function(a) {
      var s = a.actionStatus || 'todo';
      if (counts[s] === undefined) counts.todo += 1;
      else counts[s] += 1;
    });
    var data = [
      { key: '待处理', v: counts.todo, color: '#f59e0b' },
      { key: '处理中', v: counts.in_progress, color: '#3b82f6' },
      { key: '已处置', v: counts.resolved, color: '#22c55e' },
      { key: '待复检', v: counts.retest, color: '#ef4444' }
    ];
    var maxV = Math.max(1, data.reduce(function(m, d) { return Math.max(m, d.v); }, 0));
    var html = '';
    for (var i = 0; i < data.length; i++) {
      var w = 320 * (data[i].v / maxV);
      var y = 20 + i * 62;
      html += '<rect x="18" y="' + y + '" width="' + w + '" height="36" rx="6" fill="' + data[i].color + '" opacity="0.85"></rect>' +
        '<text x="28" y="' + (y + 23) + '" fill="#0f172a" font-size="12" font-weight="700">' + data[i].key + '</text>' +
        '<text x="' + (28 + w) + '" y="' + (y + 23) + '" fill="#cbd5e1" font-size="12">' + data[i].v + '</text>';
    }
    svg.innerHTML = html;
  }

  // =========================================
  // 智能脱敏与隐藏模块
  // =========================================
  function showSmartPrivacyModule() {
    var content = document.querySelector('.pg-content');
    if (!content) return;

    content.innerHTML = '<div class="pg-page-header pg-fade-in">' +
      '<h1 class="pg-page-title">智能脱敏与隐藏</h1>' +
      '<p class="pg-page-subtitle">手机号/邮箱掩码、关键词屏蔽、照片隐私化与公开痕迹一键隐藏助手</p>' +
    '</div>' +
    '<div class="pg-card pg-fade-in" style="margin-bottom:16px;">' +
      '<div class="pg-card-header"><div class="pg-card-title">1) 敏感信息掩码处理</div></div>' +
      '<div class="pg-card-body">' +
        '<textarea id="smart-mask-input" class="pg-input" style="min-height:110px;" placeholder="粘贴待处理文本，例如手机号、邮箱、身份证号、银行卡号等"></textarea>' +
        '<div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">' +
          '<button class="pg-btn pg-btn-primary pg-btn-sm" id="btn-run-mask">一键脱敏</button>' +
          '<button class="pg-btn pg-btn-ghost pg-btn-sm" id="btn-copy-mask">复制结果</button>' +
        '</div>' +
        '<textarea id="smart-mask-output" class="pg-input" style="margin-top:10px;min-height:110px;" placeholder="脱敏结果将显示在这里"></textarea>' +
      '</div>' +
    '</div>' +
    '<div class="pg-card pg-fade-in" style="margin-bottom:16px;">' +
      '<div class="pg-card-header"><div class="pg-card-title">2) 发帖关键词屏蔽</div></div>' +
      '<div class="pg-card-body">' +
        '<input id="smart-keywords" class="pg-input" placeholder="输入关键词，逗号分隔，例如：身份证,手机号,住址">' +
        '<textarea id="smart-post-input" class="pg-input" style="margin-top:10px;min-height:100px;" placeholder="输入发帖内容"></textarea>' +
        '<div style="margin-top:10px;"><button class="pg-btn pg-btn-primary pg-btn-sm" id="btn-run-keyword-shield">执行关键词屏蔽</button></div>' +
        '<textarea id="smart-post-output" class="pg-input" style="margin-top:10px;min-height:100px;" placeholder="屏蔽后的发帖内容"></textarea>' +
      '</div>' +
    '</div>' +
    '<div class="pg-card pg-fade-in" style="margin-bottom:16px;">' +
      '<div class="pg-card-header"><div class="pg-card-title">3) 关联照片隐私化处理</div></div>' +
      '<div class="pg-card-body">' +
        '<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">' +
          '<input type="file" id="smart-image-file" accept="image/*">' +
          '<button class="pg-btn pg-btn-primary pg-btn-sm" id="btn-run-image-privacy">照片隐私化处理</button>' +
          '<button class="pg-btn pg-btn-ghost pg-btn-sm" id="btn-download-image">下载隐私化图片</button>' +
        '</div>' +
        '<div style="font-size:12px;color:var(--text-muted);margin-top:6px;">默认进行像素化处理，降低照片被识别和关联检索概率。</div>' +
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px;">' +
          '<div><div style="font-size:12px;margin-bottom:6px;">原图预览</div><canvas id="smart-image-origin" style="width:100%;background:#0f172a;border-radius:8px;"></canvas></div>' +
          '<div><div style="font-size:12px;margin-bottom:6px;">隐私化预览</div><canvas id="smart-image-output" style="width:100%;background:#0f172a;border-radius:8px;"></canvas></div>' +
        '</div>' +
      '</div>' +
    '</div>' +
    '<div class="pg-card pg-fade-in">' +
      '<div class="pg-card-header"><div class="pg-card-title">4) 公开痕迹一键隐藏助手</div></div>' +
      '<div class="pg-card-body">' +
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px;">' +
          '<label><input type="checkbox" class="smart-hide-item" value="搜索引擎快照"> 搜索引擎快照删除申请</label>' +
          '<label><input type="checkbox" class="smart-hide-item" value="社交平台历史帖子"> 社交平台历史帖子清理</label>' +
          '<label><input type="checkbox" class="smart-hide-item" value="招聘/论坛公开资料"> 招聘/论坛公开资料下线</label>' +
          '<label><input type="checkbox" class="smart-hide-item" value="公开联系方式"> 公开联系方式替换为联系表单</label>' +
          '<label><input type="checkbox" class="smart-hide-item" value="图片平台EXIF"> 图片平台 EXIF 清除后重传</label>' +
          '<label><input type="checkbox" class="smart-hide-item" value="第三方数据聚合站"> 第三方聚合站数据删除申诉</label>' +
        '</div>' +
        '<div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">' +
          '<button class="pg-btn pg-btn-primary pg-btn-sm" id="btn-generate-hide-plan">生成一键隐藏方案</button>' +
          '<button class="pg-btn pg-btn-ghost pg-btn-sm" id="btn-mark-hide-done">标记全部已执行</button>' +
        '</div>' +
        '<div id="smart-hide-plan" style="margin-top:10px;font-size:13px;color:var(--text-secondary);"></div>' +
      '</div>' +
    '</div>';

    bindSmartPrivacyEvents();
  }

  function bindSmartPrivacyEvents() {
    var hideStateKey = 'sf_hide_tasks_done';
    var imageState = { image: null };

    var btnRunMask = document.getElementById('btn-run-mask');
    if (btnRunMask) {
      btnRunMask.addEventListener('click', function() {
        var input = document.getElementById('smart-mask-input');
        var output = document.getElementById('smart-mask-output');
        if (!input || !output) return;
        output.value = maskSensitiveText(input.value || '');
      });
    }

    var btnCopyMask = document.getElementById('btn-copy-mask');
    if (btnCopyMask) {
      btnCopyMask.addEventListener('click', function() {
        var output = document.getElementById('smart-mask-output');
        if (!output || !output.value) {
          showNotification('warning', '暂无可复制的脱敏结果');
          return;
        }
        navigator.clipboard.writeText(output.value).then(function() {
          showNotification('success', '脱敏结果已复制');
        }).catch(function() {
          showNotification('warning', '复制失败，请手动复制');
        });
      });
    }

    var btnRunKeyword = document.getElementById('btn-run-keyword-shield');
    if (btnRunKeyword) {
      btnRunKeyword.addEventListener('click', function() {
        var kwInput = document.getElementById('smart-keywords');
        var postInput = document.getElementById('smart-post-input');
        var postOutput = document.getElementById('smart-post-output');
        if (!kwInput || !postInput || !postOutput) return;
        var keywords = (kwInput.value || '').split(',').map(function(k) { return k.trim(); }).filter(Boolean);
        postOutput.value = shieldKeywords(postInput.value || '', keywords);
      });
    }

    var fileInput = document.getElementById('smart-image-file');
    if (fileInput) {
      fileInput.addEventListener('change', function() {
        if (!fileInput.files || !fileInput.files[0]) return;
        var reader = new FileReader();
        reader.onload = function(ev) {
          var img = new Image();
          img.onload = function() {
            imageState.image = img;
            renderImagePreview('smart-image-origin', img);
          };
          img.src = ev.target.result;
        };
        reader.readAsDataURL(fileInput.files[0]);
      });
    }

    var btnRunImage = document.getElementById('btn-run-image-privacy');
    if (btnRunImage) {
      btnRunImage.addEventListener('click', function() {
        if (!imageState.image) {
          showNotification('warning', '请先上传图片');
          return;
        }
        pixelateImage(imageState.image, 'smart-image-output', 0.08);
        showNotification('success', '照片已完成隐私化处理');
      });
    }

    var btnDownload = document.getElementById('btn-download-image');
    if (btnDownload) {
      btnDownload.addEventListener('click', function() {
        var canvas = document.getElementById('smart-image-output');
        if (!canvas || !canvas.width) {
          showNotification('warning', '暂无可下载的隐私化图片');
          return;
        }
        var a = document.createElement('a');
        a.href = canvas.toDataURL('image/png');
        a.download = 'privacy-protected.png';
        a.click();
      });
    }

    var btnPlan = document.getElementById('btn-generate-hide-plan');
    if (btnPlan) {
      btnPlan.addEventListener('click', function() {
        var checked = Array.prototype.slice.call(document.querySelectorAll('.smart-hide-item:checked')).map(function(el) {
          return el.value;
        });
        var planEl = document.getElementById('smart-hide-plan');
        if (!planEl) return;
        if (!checked.length) {
          planEl.innerHTML = '<div class="pg-empty-desc">请至少选择一项公开痕迹处理目标。</div>';
          return;
        }
        var html = '<div style="padding:10px;border:1px solid var(--border-color);border-radius:8px;">' +
          '<div style="font-weight:600;margin-bottom:6px;">自动生成处置清单（建议 24 小时内完成）</div><ol style="margin:0;padding-left:18px;">';
        checked.forEach(function(item) {
          html += '<li style="margin:4px 0;">' + escHtml(item) + '：提交删除/隐藏申请并保留工单截图</li>';
        });
        html += '</ol></div>';
        planEl.innerHTML = html;
        localStorage.setItem(hideStateKey, JSON.stringify({ tasks: checked, updatedAt: new Date().toISOString(), done: false }));
      });
    }

    var btnDone = document.getElementById('btn-mark-hide-done');
    if (btnDone) {
      btnDone.addEventListener('click', function() {
        var state = {};
        try { state = JSON.parse(localStorage.getItem(hideStateKey) || '{}'); } catch (e) { state = {}; }
        state.done = true;
        state.doneAt = new Date().toISOString();
        localStorage.setItem(hideStateKey, JSON.stringify(state));
        showNotification('success', '已标记为全部执行完成，请重新发起扫描复检');
      });
    }
  }

  function maskSensitiveText(text) {
    if (!text) return '';
    var ret = String(text);
    ret = ret.replace(/\b1[3-9]\d{9}\b/g, function(m) { return m.substring(0, 3) + '****' + m.substring(7); });
    ret = ret.replace(/\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b/g, function(m, domain) {
      var name = m.split('@')[0];
      return name.substring(0, Math.min(2, name.length)) + '***@' + domain;
    });
    ret = ret.replace(/\b\d{17}[\dXx]\b/g, function(m) { return m.substring(0, 4) + '**********' + m.substring(14); });
    ret = ret.replace(/\b\d{15,19}\b/g, function(m) {
      if (m.length < 15) return m;
      return m.substring(0, 4) + '****' + m.substring(m.length - 4);
    });
    return ret;
  }

  function shieldKeywords(text, keywords) {
    var ret = String(text || '');
    if (!keywords || !keywords.length) return ret;
    keywords.forEach(function(kw) {
      var safe = kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      ret = ret.replace(new RegExp(safe, 'gi'), function(m) { return '*'.repeat(Math.max(2, m.length)); });
    });
    return ret;
  }

  function renderImagePreview(canvasId, image) {
    var canvas = document.getElementById(canvasId);
    if (!canvas || !image) return;
    var maxW = 480;
    var scale = image.width > maxW ? maxW / image.width : 1;
    canvas.width = Math.round(image.width * scale);
    canvas.height = Math.round(image.height * scale);
    var ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
  }

  function pixelateImage(image, outputCanvasId, ratio) {
    var canvas = document.getElementById(outputCanvasId);
    if (!canvas || !image) return;
    var maxW = 480;
    var scale = image.width > maxW ? maxW / image.width : 1;
    var width = Math.round(image.width * scale);
    var height = Math.round(image.height * scale);
    canvas.width = width;
    canvas.height = height;
    var ctx = canvas.getContext('2d');
    var tmp = document.createElement('canvas');
    tmp.width = Math.max(1, Math.floor(width * ratio));
    tmp.height = Math.max(1, Math.floor(height * ratio));
    var tctx = tmp.getContext('2d');
    tctx.drawImage(image, 0, 0, tmp.width, tmp.height);
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, width, height);
    ctx.drawImage(tmp, 0, 0, tmp.width, tmp.height, 0, 0, width, height);
    ctx.imageSmoothingEnabled = true;
  }

  function getUptime(scans) {
    if (!scans || scans.length === 0) return '未知';
    var oldest = null;
    for (var i = 0; i < scans.length; i++) {
      var t = scans[i][3]; // created timestamp
      if (t && (!oldest || t < oldest)) oldest = t;
    }
    if (!oldest) return '未知';
    var now = Date.now();
    var diff = now - (typeof oldest === 'number' ? oldest * 1000 : Date.parse(oldest));
    var hours = Math.floor(diff / 3600000);
    var mins = Math.floor((diff % 3600000) / 60000);
    if (hours > 24) return Math.floor(hours / 24) + ' 天';
    return hours + ' 小时 ' + mins + ' 分钟';
  }

  // =========================================
  // 通知提示
  // =========================================

  function showNotification(type, message) {
    var notif = document.createElement('div');
    notif.style.cssText = 'position:fixed;top:80px;right:24px;z-index:9999;max-width:400px;padding:14px 18px;border-radius:10px;font-size:13px;color:#fff;box-shadow:0 8px 32px rgba(0,0,0,0.4);animation:slideInRight 0.3s ease;';

    if (type === 'success') {
      notif.style.background = 'linear-gradient(135deg,#22c55e,#16a34a)';
    } else if (type === 'warning') {
      notif.style.background = 'linear-gradient(135deg,#f59e0b,#d97706)';
    } else {
      notif.style.background = 'linear-gradient(135deg,#4f8ef7,#2563eb)';
    }
    notif.textContent = message;

    var style = document.createElement('style');
    style.textContent = '@keyframes slideInRight{from{opacity:0;transform:translateX(20px)}to{opacity:1;transform:translateX(0)}}';
    document.head.appendChild(style);
    document.body.appendChild(notif);
    setTimeout(function() {
      notif.style.transition = 'all 0.3s ease';
      notif.style.opacity = '0';
      notif.style.transform = 'translateX(20px)';
      setTimeout(function() { notif.remove(); }, 300);
    }, 3500);
  }

  // =========================================
  // 通用 HTML 转义
  // =========================================

  function escHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // =========================================
  // 设置页 Tab 切换（覆盖原版）
  // =========================================

  window.switchTab = function(tabId) {
    document.querySelectorAll('[id^=optsect_]').forEach(function(el) {
      el.style.display = 'none';
    });
    var target = document.getElementById('optsect_' + tabId);
    if (target) target.style.display = 'block';

    document.querySelectorAll('[id^=tab_]').forEach(function(el) {
      el.style.borderLeftColor = 'transparent';
      el.style.background = '';
    });
    var activeTab = document.getElementById('tab_' + tabId);
    if (activeTab) {
      activeTab.style.borderLeftColor = 'var(--accent-blue)';
      activeTab.style.background = 'rgba(59,130,246,0.08)';
    }
  };

})();
