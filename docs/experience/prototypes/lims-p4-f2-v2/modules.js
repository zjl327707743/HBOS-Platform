/* LIMS 静态视觉原型：领域页面只读内容，所有数据均为演示。 */
window.LimsModules = (() => {
  const esc = value => String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const tag = (label, tone = 'blue') => `<span class="tag ${tone}">${esc(label)}</span>`;
  const detail = (title, kind, label = '查看详情') => `<button class="btn quiet" data-detail="${esc(title)}" data-kind="${kind}">${esc(label)}</button>`;
  const next = (page, label) => `<button class="btn quiet" data-page="${page}">${esc(label)} <span aria-hidden="true">→</span></button>`;
  const tabLink = (tab, label) => `<button class="btn quiet" data-tab="${tab}">${esc(label)} <span aria-hidden="true">→</span></button>`;
  const tabs = (items, current) => `<nav class="section-tabs" aria-label="页面内容分类">${items.map(([key, label]) => `<button class="${key === current ? 'active' : ''}" data-tab="${key}" aria-current="${key === current ? 'page' : 'false'}">${label}</button>`).join('')}</nav>`;
  const panel = (title, sub, body, action = '') => `<section class="panel"><div class="panel-head"><div><h2>${title}</h2>${sub ? `<p class="muted">${sub}</p>` : ''}</div>${action}</div>${body}</section>`;
  const stats = items => `<div class="mini-stats">${items.map(([label, value, sub]) => `<div class="stat"><span class="muted">${label}</span><strong>${value}</strong><span class="muted">${sub}</span></div>`).join('')}</div>`;
  const table = (headers, rows, caption) => `<div class="table-wrap"><table class="data-table" aria-label="${esc(caption)}"><thead><tr>${headers.map(title => `<th scope="col">${title}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  const identity = (name, code) => `<strong>${name}</strong><div class="muted">${code}</div>`;
  const note = text => `<p class="note">${text}</p>`;
  const pick = (current, options) => options.some(([key]) => key === current) ? current : options[0][0];

  function reports(tab) {
    const items = [['all', '全部报告'], ['pending', '待审核与发布'], ['published', '已发布']];
    const current = pick(tab, items);
    const rows = [
      [identity('原料药 A', '报告 2026-0929-01 · 样品 0929-008'), 'A260920', '第 3 版', tag('草稿', 'amber'), '检验员甲', detail('原料药 A · 检验报告 2026-0929-01', 'reports', '预览报告')],
      [identity('注射用粉针 B', '报告 2026-0928-03 · 样品 0928-021'), 'B260918', '第 2 版', tag('已审核'), '审核员乙', detail('注射用粉针 B · 检验报告 2026-0928-03', 'reports', '预览报告')],
      [identity('包材 C', '报告 2026-0927-02 · 样品 0927-006'), 'C260916', '第 1 版', tag('已发布', 'green'), '批准人丙', detail('包材 C · 检验报告 2026-0927-02', 'reports', '查看正式报告')]
    ];
    const selected = current === 'published' ? rows.slice(2) : current === 'pending' ? rows.slice(0, 2) : rows;
    return stats([['待审核', '1 份', '结果已批准，报告待审核'], ['待发布', '1 份', '已完成质量审核'], ['已发布', '1 份', '可查看正式报告']]) +
      tabs(items, current) + panel('检验报告清单', '报告内容关联样品、批号、标准版本与已批准结果', table(['物料 / 报告编号', '批号', '标准版本', '报告状态', '当前经办人', '操作'], selected, '检验报告清单')) +
      `<div class="detail-grid">${panel('从结果到报告', '每一步都有可追溯依据', '<ol class="timeline"><li><strong>检验完成</strong><p class="muted">核对全部必检项目与判定。</p></li><li><strong>结果全部批准</strong><p class="muted">形成报告候选样品。</p></li><li><strong>起草 → 审核 → 发布</strong><p class="muted">报告保留检验人、审核人和发布人。</p></li></ol>', next('ledger', '查看结果台账'))}${panel('报告预览重点', '检验人员快速核对三项内容', '<div class="note"><strong>样品身份</strong><p>物料名称、样品编号、批号一致。</p><strong>检验依据</strong><p>标准版本、项目、限度与结果匹配。</p><strong>签署信息</strong><p>检验、审核与批准记录完整。</p></div>', detail('原料药 A · 检验报告 2026-0929-01', 'reports', '打开报告预览'))}</div>`;
  }

  function specs(tab) {
    const items = [['effective', '现行标准'], ['draft', '修订草稿'], ['history', '历史版本']];
    const current = pick(tab, items);
    const versions = {
      effective: [['原料药 A 质量标准', '标准 A-001', '第 3 版', '2026-09-01', '8 项', tag('已生效', 'green')], ['注射用粉针 B 质量标准', '标准 B-002', '第 2 版', '2026-08-15', '12 项', tag('已生效', 'green')]],
      draft: [['原料药 A 质量标准', '标准 A-001', '第 4 版', '待确认', '8 项', tag('草稿', 'amber')]],
      history: [['原料药 A 质量标准', '标准 A-001', '第 2 版', '2026-03-01', '8 项', tag('已废止')]]
    };
    return stats([['现行标准', '2 份', '按生效版本执行检验'], ['待修订', '1 份', '修订后保留版本链'], ['检验依据', '项目 · 方法 · 限度', '查看同一标准的完整定义']]) +
      tabs(items, current) + panel(current === 'effective' ? '可用质量标准' : current === 'draft' ? '待确认的修订草稿' : '可追溯的历史标准', '检验记录固定引用当时的标准版本', table(['标准名称 / 编号', '版本', '生效日期', '检验项目', '状态', '操作'], versions[current].map(row => [identity(row[0], row[1]), row[2], row[3], row[4], row[5], detail(`${row[0]} · ${row[2]}`, 'specs', '查看项目与限度')]), '质量标准版本清单')) +
      panel('原料药 A · 现行标准速览', '标准 A-001 / 第 3 版', table(['检验项目', '方法文件', '限度形式', '标准限度', '单位'], [['性状', '性状检查法', '文本', '白色或类白色结晶性粉末', '—'], ['水分', '水分测定法', '上限', '≤ 1.0', '%'], ['含量', '高效液相色谱法', '范围', '98.0～102.0', '%']], '质量标准项目速览'), detail('原料药 A 质量标准 · 第 3 版', 'specs', '查看完整标准'));
  }

  function retention(tab) {
    const items = [['overview', '工作台'], ['samples', '登记与台账'], ['products', '留样产品'], ['observations', '观察任务'], ['usage', '使用申请'], ['disposal', '处理申请']];
    const current = pick(tab, items);
    const summary = stats([['待观察', '2 项', '含今天计划 1 项'], ['使用申请', '1 单', '当前待质量控制批准'], ['到期关注', '1 批', '留样期至 10 月 15 日'], ['在库留样', '18 批', '结存与预占分开显示']]);
    const pages = {
      overview: () => `<div class="detail-grid">${panel('今天先处理', '按计划日期安排留样工作', '<ol class="timeline"><li><strong>原料药 A · 第 6 个月观察</strong><p class="muted">今天计划 · 位置 R-02 / 03 层 · 观察外观与包装。</p>' + tabLink('observations', '查看观察任务') + '</li><li><strong>使用申请 · 待质量控制批准</strong><p class="muted">申请 10 g，结存 80 g，已预占 10 g。</p>' + tabLink('usage', '查看使用申请') + '</li><li><strong>包材 C · 留样临近到期</strong><p class="muted">2026-10-15 到期，先核对处理依据。</p>' + tabLink('disposal', '查看处理申请') + '</li></ol>')}${panel('按位置找到样品', '留样信息卡', '<div class="note"><span class="tag green">在库</span><h3>原料药 A</h3><p>批号 A260301 · 留样 2026-0301-01</p><div class="detail-grid"><div><span class="muted">储存位置</span><h3>R-02 / 03 层</h3></div><div><span class="muted">当前结存</span><h3>80 g</h3></div><div><span class="muted">已预占</span><h3>10 g</h3></div><div><span class="muted">可用量</span><h3>70 g</h3></div></div><p class="muted">密闭保存 · 容器 01 · 留样期至 2028-03-01</p></div>', detail('原料药 A · 留样 2026-0301-01', 'retention', '查看留样及流水'))}</div>`,
      samples: () => panel('留样登记与台账', '识别样品、找到位置、核对结存与预占量', table(['样品 / 批号', '容器 / 储存位置', '结存 / 预占 / 可用', '留样期至', '状态', '操作'], [[identity('原料药 A', 'A260301 · 留样 0301-01'), '01 · R-02 / 03 层', '80 / 10 / 70 g', '2028-03-01', tag('在库', 'green'), detail('原料药 A · 留样 2026-0301-01', 'retention')], [identity('注射用粉针 B', 'B260615 · 留样 0615-02'), '02 · R-03 / 02 层', '60 / 0 / 60 瓶', '2028-06-15', tag('在库', 'green'), detail('注射用粉针 B · 留样 2026-0615-02', 'retention')], [identity('包材 C', 'C241015 · 留样 1015-03'), '01 · R-05 / 01 层', '30 / 0 / 30 个', '2026-10-15', tag('临近到期', 'amber'), detail('包材 C · 留样 2024-1015-03', 'retention')]], '留样台账')) + note('登记信息包含留样产品、批号、容器、数量及单位、包装、留样期限、储存位置和关联检验样品；详情保留库存操作流水。'),
      products: () => panel('留样产品规则', '默认计量单位、全检量、储存与观察规则保持一致', table(['产品', '类别', '全检量', '默认单位', '储存条件', '观察规则', '操作'], [[identity('原料药 A', '产品 A-001'), '原料', '50 g', 'g', '密闭保存', '按批准规则生成', detail('原料药 A · 留样产品规则', 'retention', '查看规则')], [identity('注射用粉针 B', '产品 B-002'), '成品', '30 瓶', '瓶', '遮光保存', '按批准规则生成', detail('注射用粉针 B · 留样产品规则', 'retention', '查看规则')]], '留样产品规则')),
      observations: () => panel('观察任务', '先确认位置与时间点，再核对外观及包装记录', table(['样品 / 批号', '观察时间点', '计划日期', '观察状态', '观察结果', '操作'], [[identity('原料药 A', 'A260301 · R-02 / 03 层'), '第 6 个月', '2026-09-29', tag('今天待观察', 'amber'), '尚未记录', detail('原料药 A · 第 6 个月观察', 'retention', '查看观察记录')], [identity('注射用粉针 B', 'B260615 · R-03 / 02 层'), '第 3 个月', '2026-09-30', tag('待观察'), '尚未记录', detail('注射用粉针 B · 第 3 个月观察', 'retention', '查看观察记录')], [identity('原料药 A', 'A260301 · R-02 / 03 层'), '初始观察', '2026-03-01', tag('已完成', 'green'), '无异常', detail('原料药 A · 初始观察记录', 'retention', '查看历史')]], '留样观察任务')),
      usage: () => panel('使用申请', '申请、审批与领用记录关联到同一留样批次', table(['申请单 / 留样', '触发场景', '申请数量', '申请部门', '状态', '操作'], [[identity('使用 2026-0929-01', '原料药 A · A260301'), '检验结果分析', '10 g', '质量检验', tag('待质量控制批准', 'amber'), detail('原料药 A · 使用申请 2026-0929-01', 'retention')], [identity('使用 2026-0922-02', '注射用粉针 B · B260615'), '检验结果分析', '6 瓶', '质量检验', tag('已完成', 'green'), detail('注射用粉针 B · 使用申请 2026-0922-02', 'retention')]], '留样使用申请')) + note('详情显示申请原因、审批过程与实际使用记录。数量始终携带留样产品定义的计量单位。'),
      disposal: () => panel('处理申请', '核对留样期限、处理方式和审批进度', table(['处理单 / 留样', '处理类型', '处理数量', '留样期至', '当前状态', '操作'], [[identity('处理 2026-0929-01', '包材 C · C241015'), '留样期满继续留样', '30 个', '2026-10-15', tag('草稿', 'amber'), detail('包材 C · 留样期满继续留样申请', 'retention')], [identity('处理 2026-0920-02', '原料药 A · A240901'), '留样期满销毁', '40 g', '2026-09-01', tag('待质量控制主管审核'), detail('原料药 A · 留样销毁申请', 'retention')]], '留样处理申请')) + note('处理详情展示原因、地点、方式、所需审批层级和执行记录；继续留样另核对新的留样期至，销毁执行保留双人签署。')
    };
    return summary + tabs(items, current) + pages[current]();
  }

  function stability(tab) {
    const items = [['study', '考察申请与方案'], ['samples', '样品入箱与台账'], ['schedule', '取样与检测计划'], ['results', '结果与趋势'], ['reports', '报告与有效期'], ['ops', '变更与环境设备']];
    const current = pick(tab, items);
    const summary = stats([['进行中考察', '6 项', '2 个产品 · 3 类条件'], ['近期取样', '2 个时间点', '下次取样 09-30'], ['检测中', '1 个时间点', '按截止日期安排'], ['待审核', '1 份方案', '通知与方案保持关联']]);
    const pages = {
      study: () => panel('考察申请与方案', '通知单 → 批准方案 → 样品入箱 → 时间点执行', table(['考察 / 产品', '条件', '时间点', '关联通知', '状态', '操作'], [[identity('原料药 A · 长期考察', '方案 2026-001'), '25 ± 2 °C / 60 ± 5 % RH', '0、3、6、9、12 月', '通知 2026-001', tag('已生效', 'green'), detail('原料药 A · 稳定性方案 2026-001', 'stability')], [identity('注射用粉针 B · 加速考察', '方案 2026-006'), '40 ± 2 °C / 75 ± 5 % RH', '0、1、2、3、6 月', '通知 2026-006', tag('待审核', 'amber'), detail('注射用粉针 B · 稳定性方案 2026-006', 'stability')]], '稳定性考察方案')) + `<div class="module-grid"><article class="module-card"><h3>产品规则</h3><p class="muted">考察分类、剂型、默认单位、有效期和长期条件。</p>${detail('稳定性产品规则 · 原料药 A', 'stability', '查看产品规则')}</article><article class="module-card"><h3>条件与检验项目</h3><p class="muted">温湿度范围、关键项目、显著变化规则与业务项目关联。</p>${detail('原料药 A · 条件与检验项目', 'stability', '查看条件与项目')}</article></div>`,
      samples: () => panel('稳定性样品台账', '入箱条件与位置一眼可见；数量变化可回溯', table(['产品 / 批号', '条件 / 储存位置', '入箱日期', '结存 / 初始', '状态', '操作'], [[identity('原料药 A', 'A260330 · 稳定性样品 0330-01'), '长期 · ST-01 / 02 层', '2026-03-30', '120 / 180 g', tag('考察中', 'green'), detail('原料药 A · 稳定性样品 2026-0330-01', 'stability')], [identity('注射用粉针 B', 'B260601 · 稳定性样品 0601-02'), '加速 · ST-02 / 03 层', '2026-06-01', '48 / 72 瓶', tag('考察中', 'green'), detail('注射用粉针 B · 稳定性样品 2026-0601-02', 'stability')]], '稳定性样品台账')) + note('入箱记录包含包装、放置方向、储存人与复核人；详情关联标签、库存流水及强制评估记录。'),
      schedule: () => panel('近期取样与检测', '同时显示计划日、有效截止日和延期状态', table(['产品 / 时间点', '考察条件', '计划取样日', '检测截止日', '进度', '操作'], [[identity('原料药 A · 6 月', 'A260330 · 时间点 0930-01'), '长期', '2026-09-30', '2026-10-30', tag('待取样', 'amber'), detail('原料药 A · 长期 6 月取样计划', 'stability', '查看时间点')], [identity('注射用粉针 B · 3 月', 'B260601 · 时间点 0901-02'), '加速', '2026-09-01', '2026-10-01', tag('检测中'), detail('注射用粉针 B · 加速 3 月检测计划', 'stability', '查看检测进度')]], '稳定性取样与检测计划')) + panel('延期记录', '保留原计划、申请日期、批准日期及原因', table(['时间点', '延期类型', '原计划日', '批准日期', '状态', '操作'], [['原料药 A · 长期 3 月', '取样延期', '2026-06-30', '2026-07-02', tag('已批准', 'green'), detail('原料药 A · 长期 3 月延期记录', 'stability')]], '延期历史')),
      results: () => `<div class="detail-grid">${panel('本次检验结果', '注射用粉针 B · 加速 3 月 · 检测中', table(['检验项目', '结果', '来源', '状态'], [['性状', '符合规定', '自检', tag('已批准', 'green')], ['水分', '0.6 %', '自检', tag('已复核')], ['含量', '99.2 %', '业务检验同步', tag('已批准', 'green')]], '稳定性结果'), detail('注射用粉针 B · 加速 3 月结果', 'stability', '查看结果与修订'))}${panel('含量变化趋势', '注射用粉针 B · 加速考察 · 当前生效值', '<svg viewBox="0 0 430 200" role="img" aria-label="含量从初始100.0%、1个月99.8%、2个月99.5%到3个月99.2%" style="display:block;width:100%;max-height:220px"><g stroke="#e6eeec" stroke-width="1"><path d="M45 30H410M45 85H410M45 140H410"/></g><g fill="#6c817b" font-size="12"><text x="4" y="34">100.0</text><text x="4" y="89">99.5</text><text x="4" y="144">99.0</text><text x="40" y="180">初始</text><text x="156" y="180">1 月</text><text x="273" y="180">2 月</text><text x="390" y="180">3 月</text></g><path d="M55 30L170 52L285 85L400 118" fill="none" stroke="#0b8c72" stroke-width="3"/><g fill="#fff" stroke="#0b8c72" stroke-width="3"><circle cx="55" cy="30" r="5"/><circle cx="170" cy="52" r="5"/><circle cx="285" cy="85" r="5"/><circle cx="400" cy="118" r="5"/></g></svg>' + note('初始 100.0 % → 3 月 99.2 %。显著变化判定应结合批准规则与完整结果评估。'))}</div>`,
      reports: () => panel('稳定性报告', '报告审核、版本链与有效期判定', table(['报告 / 产品', '类型', '考察周期', '外推建议', '质量部门判定', '状态', '操作'], [[identity('稳定性报告 2026-003', '原料药 A'), '阶段报告', '2026-03～2026-09', '待评估', '待批准', tag('草稿', 'amber'), detail('原料药 A · 稳定性阶段报告', 'stability', '查看报告')], [identity('稳定性报告 2026-001', '注射用粉针 B'), '年度报告', '2025-01～2025-12', '24 个月', '24 个月', tag('已批准', 'green'), detail('注射用粉针 B · 年度稳定性报告', 'stability', '查看报告')]], '稳定性报告')) + note('有效期外推仅提供辅助建议；最终有效期由获授权的质量人员判定，审核人与批准人按现有职责分离要求执行。'),
      ops: () => `<div class="detail-grid">${panel('稳定性室环境', '2026-09-29 · 早班记录', table(['位置', '温度', '湿度', '判定'], [['ST-01 长期室', '25.1 °C', '60.2 % RH', tag('范围内', 'green')], ['ST-02 加速室', '40.0 °C', '75.3 % RH', tag('范围内', 'green')]], '稳定性室温湿度'), detail('稳定性室 · 2026-09-29 早班记录', 'stability', '查看环境记录'))}${panel('设备与故障记录', '设备状态与关联样品', table(['设备', '状态', '最近记录'], [['稳定性箱 01', tag('运行中', 'green'), '09-29 巡检正常'], ['稳定性箱 02', tag('运行中', 'green'), '09-29 巡检正常']], '稳定性设备状态'), detail('稳定性箱 01 · 设备与故障记录', 'stability', '查看设备档案'))}</div>` + panel('变更记录', '从申请、实施到后评估完整留痕', table(['变更单', '变更对象', '内容摘要', '状态', '操作'], [['变更 2026-009', '稳定性箱 01', '储存位置调整', tag('待后评估', 'amber'), detail('变更 2026-009 · 储存位置调整', 'stability', '查看变更过程')]], '稳定性变更记录'))
    };
    return summary + tabs(items, current) + pages[current]();
  }

  function audit(tab) {
    const items = [['trail', '结果修订追踪'], ['logs', '合规审计日志']];
    const current = pick(tab, items);
    const body = current === 'trail'
      ? table(['结果 / 修订', '修改时间', '操作人', '变更内容', '修订原因', '操作'], [[identity('结果 2026-0928-08', '修订 02 · 原料药 A / 水分'), '09-29 09:18', '检验员甲', '备注：补充称量记录页码', '补充原始记录引用', detail('结果 2026-0928-08 · 修订 02', 'audit', '比较修订')], [identity('结果 2026-0927-03', '修订 01 · 包材 C / 外观'), '09-28 15:42', '检验员乙', '结果描述：补充观察条件', '使记录描述完整', detail('结果 2026-0927-03 · 修订 01', 'audit', '比较修订')]], '结果修订追踪')
      : table(['时间', '操作人', '事件', '对象', '动作摘要', '操作'], [['09-29 10:06', '复核员乙', tag('复核', 'blue'), '结果 2026-0928-08', '完成结果复核', detail('审计记录 · 09-29 10:06 结果复核', 'audit')], ['09-29 09:18', '检验员甲', tag('修订', 'amber'), '结果 2026-0928-08', '补充称量记录页码', detail('审计记录 · 09-29 09:18 结果修订', 'audit')], ['09-29 08:36', '留样员丙', tag('登记', 'green'), '留样 2026-0929-01', '登记入库 100 g', detail('审计记录 · 09-29 08:36 留样登记', 'audit')]], '合规审计日志');
    return note('按授权范围查阅原始记录及其变化：谁在何时，对哪条记录做了什么，为什么修改。') + tabs(items, current) + panel(current === 'trail' ? '结果修订记录' : '业务事件记录', current === 'trail' ? '保留修改前后内容及修订原因' : '记录动作、原因、变更内容与记录指纹', body) + panel('关联查询', '从检验结果进入其完整上下文', '<div class="module-grid"><article class="module-card"><h3>检验结果台账</h3><p class="muted">定位批号、项目与当前生效结果。</p>' + next('ledger', '查看结果台账') + '</article><article class="module-card"><h3>检验报告</h3><p class="muted">核对报告引用的标准版本和批准结果。</p>' + next('reports', '查看检验报告') + '</article></div>');
  }

  function modules(tab) {
    const groups = [
      ['检验业务', '从样品到批准结果，围绕检验员每天的工作展开。', [['tasks', '我的待办与待检任务', '按到期、状态、优先级组织检验。'], ['samples', '样品登记与台账', '样品信息、批号、标准和检验进度。'], ['results', '检验结果录入', '项目结果、原始记录和提交反馈。'], ['ledger', '检验结果台账', '受控结果查询、当前版本与修订。']]],
      ['质量与报告', '用相同的样品身份和标准版本串起证据。', [['reports', '检验报告', '报告起草、审核、发布与报告预览。'], ['specs', '质量标准库', '检验项目、方法、限度与标准版本。']]],
      ['留样管理', '样品有位置，使用有依据，数量有流水。', [['retention', '留样工作台', '登记与台账、产品规则、观察任务、使用申请、处理申请。']]],
      ['稳定性管理', '围绕考察方案与时间点推进长期工作。', [['stability', '稳定性工作台', '申请与方案、入箱台账、取样检测、结果趋势、报告有效期、变更与环境设备。']]],
      ['合规审计', '查看记录的来源与变化。', [['audit', '审计追踪与日志', '结果修订前后对比、操作时间、原因和记录指纹。']]]
    ];
    const items = [['all', '全部功能'], ['daily', '检验员常用']];
    const current = pick(tab, items);
    return tabs(items, current) + (current === 'daily' ? groups.slice(0, 2) : groups).map(([title, desc, entries]) => panel(title, desc, `<div class="module-grid">${entries.map(([page, label, text]) => `<article class="module-card"><h3>${label}</h3><p class="muted">${text}</p>${next(page, '进入查看')}</article>`).join('')}</div>`)).join('') + note('系统配置与管理后台仅向具备相应管理授权的人员开放；普通检验人员从业务工作区完成日常操作。');
  }

  const views = { reports, specs, retention, stability, audit, modules };
  return { render: (page, tab = '') => views[page] ? views[page](tab) : '' };
})();
