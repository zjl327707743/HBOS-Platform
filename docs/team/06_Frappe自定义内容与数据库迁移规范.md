# 06 Frappe 自定义内容与数据库迁移规范

> **读者对象**：HBOS 项目组全体开发成员  
> **前置知识**：了解 Frappe 框架基本概念（DocType、Workspace 等），会使用 `bench` 命令行  
> **目标**：所有 Frappe 自定义内容都纳入 Git 版本控制，确保任何开发者在任意环境都能完整还原系统配置

---

## 1. 核心原则：数据库不能作为唯一的代码来源

### 1.1 问题的本质

Frappe 框架有两类"代码"：

| 类型 | 存放位置 | 举例 |
|------|---------|------|
| 文件代码 | 硬盘上的文件，由 Git 管理 | Python 文件、DocType JSON、Report JSON |
| 数据库配置 | MariaDB 数据库中的记录，不在 Git 中 | 通过 UI 创建的自定义字段、属性修改、Workflow |

**危险场景**：你在 Frappe 界面上点了几下，给 Employee DocType 加了一个自定义字段 `emergency_contact`，功能正常工作。但这段配置只存在于你的开发数据库里。如果：

- 数据库损坏，字段定义丢失
- 新人 clone 了代码，`bench migrate` 后字段不出现
- 生产环境部署后，字段不存在，功能报错

**这就是"界面配置已生效，但 Git 中无法还原"的问题。**

### 1.2 黄金法则

> **任何改变系统行为的配置，都必须以文件形式提交到 Git。数据库是运行时状态，不是源码。**

```
正确：修改 → 导出为 JSON 文件 → 提交 Git → 其他环境通过 migrate 加载
错误：修改 → 只在数据库中生效 → 自认为"搞定了"
```

---

## 2. DocType 管理

### 2.1 自定义 DocType 的存放位置

自定义 DocType 必须放在 App 的 `doctype` 目录下，遵循 Frappe 的标准目录结构：

```
apps/hb_attendance_app/hb_attendance_app/
└── hbos_attendance/
    └── doctype/
        └── hbos_attendance_import_log/      # 一个 DocType 一个目录
            ├── hbos_attendance_import_log.json   # DocType 定义（核心）
            ├── hbos_attendance_import_log.py     # Python 逻辑（控制器）
            ├── hbos_attendance_import_log.js     # 前端脚本（可选）
            ├── hbos_attendance_import_log_list.js # 列表视图脚本（可选）
            ├── test_hbos_attendance_import_log.py # 单元测试（推荐）
            └── hbos_attendance_import_log_dashboard.py  # Dashboard（可选）
```

### 2.2 DocType JSON 文件结构

DocType JSON 是 DocType 的完整定义，包含字段、权限、表单布局等。下面是核心字段说明：

```json
{
  "name": "HBOS Attendance Import Log",
  "module": "HBOS Attendance",
  "istable": 0,
  "fields": [
    {
      "fieldname": "import_date",
      "fieldtype": "Date",
      "label": "导入日期",
      "reqd": 1
    }
  ],
  "permissions": [
    {
      "role": "System Manager",
      "read": 1, "write": 1, "create": 1, "delete": 1
    }
  ]
}
```

### 2.3 修改已有 DocType

当你在 Frappe UI 中修改 DocType 后（加字段、改属性、调布局），**必须**将修改同步到 JSON 文件：

```bash
# 导出指定 DocType 的最新 JSON（覆盖本地文件）
bench --site 你的站点名 export-doc hb_attendance_app "HBOS Attendance Import Log"

# 或导出整个 Module 下所有 DocType
bench --site 你的站点名 export-doc hb_attendance_app hb_attendance_app
```

### 2.4 多人同时修改 DocType 如何避免冲突

DocType JSON 文件较大且结构嵌套深，多人同时修改极易冲突。遵循以下规则：

1. **修改前先 pull**：确保本地代码是最新的
2. **锁定式修改**：口头或群内告知"我要改 XX DocType，其他人先别动"
3. **导出后仔细检查 diff**：`git diff` 逐条确认变更
4. **冲突时手动合并**：不要直接选"用我的"或"用对方的"，逐字段对比合并
5. **合并后重新 migrate 验证**：`bench migrate` 确认无报错

### 2.5 不要手动创建 DocType JSON

如果你用 `bench new-docType` 创建了 DocType，Frappe 会自动生成目录和文件。**不要手动从头写 DocType JSON**——结构太复杂，容易出错。

---

## 3. Custom Field 管理

### 3.1 什么是 Custom Field

Custom Field 是在**不修改原始 DocType 代码**的前提下，给现有 DocType 添加额外字段的机制。

例如：Employee 是 HRMS App 自带的 DocType，你需要在 Employee 上增加一个 `emergency_contact` 字段。你不能直接改 HRMS 的源码（升级会被覆盖），应该创建一条 Custom Field 记录。

### 3.2 Custom Field 如何导出到 App

Custom Field 通过 **Fixture** 机制导出：

```bash
# 导出所有 Custom Field 到 App 的 fixtures 目录
bench --site 你的站点名 export-fixtures --app hb_attendance_app

# 如果只想导出特定类型的 Fixture
bench --site 你的站点名 export-fixtures --app hb_attendance_app --doctype "Custom Field"
```

执行后，会在 `apps/hb_attendance_app/hb_attendance_app/fixtures/` 目录下生成 `custom_field.json` 文件。

### 3.3 fixtures 目录结构

```
apps/hb_attendance_app/hb_attendance_app/
└── fixtures/
    ├── custom_field.json          # 所有自定义字段
    ├── property_setter.json       # 所有属性修改
    ├── workspace.json             # 工作台（Workspace）
    ├── client_script.json         # 客户端脚本（可选）
    └── server_script.json         # 服务端脚本（可选）
```

### 3.4 hooks.py 中的 fixtures 配置

导出 Fixture 文件后，还需要在 `hooks.py` 中注册，`bench migrate` 才会加载它们：

```python
# apps/hb_attendance_app/hb_attendance_app/hooks.py

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            # 这里的 filter 决定了哪些 Custom Field 属于本 App
            # 通常按 module 或 name 过滤
        ]
    },
    # 如果已经在 fixtures 目录放置了 JSON 文件，可以直接引用
    "custom_field.json",
    "property_setter.json",
    "workspace.json",
]
```

**关键点**：`fixtures` 列表中的每一条，migrate 时都会从 JSON 文件同步到数据库。没有配置在这里的内容，不会被自动加载。

### 3.5 多人修改 Custom Field 的协作方式

Custom Field 的 JSON 文件结构相对简单，冲突概率较低，但仍需注意：

```bash
# 修改 Custom Field 前的标准流程

# 1. 拉取最新代码
git pull origin main

# 2. 在 Frappe UI 中进行修改（添加/修改 Custom Field）

# 3. 导出最新的 Fixture
bench --site 你的站点名 export-fixtures --app hb_attendance_app

# 4. 检查 diff，确认只有你的变更
git diff fixtures/custom_field.json

# 5. 提交
git add fixtures/custom_field.json
git commit -m "feat: 给 Employee 增加 emergency_contact 自定义字段"
```

---

## 4. Property Setter 管理

### 4.1 什么是 Property Setter

Property Setter 用于修改已有字段的属性，而不改动 DocType 源码：

```json
{
  "doc_type": "Employee",
  "field_name": "employee_name",
  "property": "label",
  "value": "员工姓名"
}
```

常见使用场景：

| Property | 用途 | 示例 |
|----------|------|------|
| `label` | 修改字段显示名称 | 把 "Employee Name" 改成 "员工姓名" |
| `reqd` | 修改必填属性 | 把某个字段设为必填 |
| `hidden` | 修改隐藏属性 | 把不需要的字段隐藏起来 |
| `read_only` | 修改只读属性 | 把某个字段设为不可编辑 |
| `options` | 修改 Select 的选项 | 增加或修改下拉选项 |
| `default` | 修改默认值 | 设置字段的默认值 |

### 4.2 导出和管理

Property Setter 与 Custom Field 一样，通过 Fixture 导出：

```bash
bench --site 你的站点名 export-fixtures --app hb_attendance_app
```

生成的 `fixtures/property_setter.json` 文件结构类似：

```json
[
  {
    "doc_type": "Employee",
    "field_name": "employee_name",
    "property": "label",
    "value": "员工姓名",
    "property_type": "Data"
  }
]
```

### 4.3 什么时候用 Property Setter vs 直接修改 DocType JSON

| 场景 | 使用方式 | 原因 |
|------|---------|------|
| 修改**自己 App** 的 DocType | 直接改 DocType JSON | 这是你自己的代码，想怎么改都行 |
| 修改**其他 App** 的 DocType（如 HRMS 的 Employee） | Property Setter | 不能改别人的源码，升级会被覆盖 |
| 修改**Frappe 核心** DocType（如 User） | Property Setter | 同上，框架升级会覆盖你的改动 |

**简单记忆**：自己的东西直接改，别人的东西用 Property Setter。

### 4.4 当前项目中可能存在但未导出的 Property Setter

以下定制**极可能**只存在于数据库，不在 Git 中：

- 中文标签翻译（把英文字段名改成中文）
- 字段必填/隐藏/只读属性的调整
- Employee、Attendance 等 HRMS DocType 的界面微调

**自查命令**：

```bash
# 查看数据库中所有 Property Setter（可能很多，建议加上过滤）
bench --site 你的站点名 console
# 在 Frappe Console 中执行：
frappe.get_all("Property Setter", fields=["doc_type", "field_name", "property", "value"])
```

---

## 5. Workspace 管理

### 5.1 当前状态

hb_attendance_app 已经有一个 Workspace **"海滨考勤工作台"**，放在：

```
apps/hb_attendance_app/hb_attendance_app/hbos_attendance/workspace/hbos_workspace/
```

这是正确的做法。Workspace 的 JSON 文件已经在 Git 中。

### 5.2 Workspace 的完整管理流程

```bash
# 1. 在 Frappe UI 中编辑 Workspace（拖拽卡片、调整布局）

# 2. 导出 Workspace JSON
bench --site 你的站点名 export-fixtures --app hb_attendance_app

# 3. 确认 fixtures/workspace.json 中有你的 Workspace

# 4. 提交到 Git
git add fixtures/workspace.json
git commit -m "feat: 更新海滨考勤工作台布局"
```

### 5.3 hooks.py 中的 Workspace 配置

当前 `hooks.py` 中应该有类似配置：

```python
# 在 after_migrate 中初始化 Workspace
def after_migrate():
    create_custom_workspace()

# setup.py 中的 workspace 初始化函数
```

如果只依赖 `fixtures/workspace.json` 的方式，也可以在 `hooks.py` 的 `fixtures` 列表中直接引用。

### 5.4 多人修改 Workspace 的协作方式

Workspace JSON 结构复杂，冲突风险较高。建议：

1. **一个人负责一个 Workspace 的整体布局**，不要多人同时调整
2. 调整完成后立即导出并提交，让其他人基于最新版本工作
3. 如果发生了冲突，建议基于最新版本重新调整，而不是手动合并 JSON

---

## 6. Workflow 管理

### 6.1 什么是 Workflow

Workflow 是文档审批流程的定义，包括：

- **State**：文档当前处于什么状态（草稿、待审批、已批准、已拒绝）
- **Transition**：状态之间如何切换（提交审批、批准、拒绝）
- **Action**：状态切换时可以执行的操作（发邮件、更新字段）

### 6.2 Workflow 的存放位置

自定义 Workflow 应放在 App 的 `workflow` 目录下：

```
apps/hb_attendance_app/hb_attendance_app/
└── hbos_attendance/
    └── workflow/
        └── attendance_approval/
            └── attendance_approval.json
```

### 6.3 Workflow 的导出

```bash
# 导出单个 Workflow
bench --site 你的站点名 export-doc hb_attendance_app "Attendance Approval"

# 或通过 export-fixtures（如果配置了 Workflow 的 fixture）
bench --site 你的站点名 export-fixtures --app hb_attendance_app
```

### 6.4 如果本项目目前没有自定义 Workflow

如果当前不需要审批流程，本节可不关注。但一旦创建了 Workflow（通过 UI 或 `bench new-workflow`），就必须导出并提交到 Git。

---

## 7. Role 和 Permission 管理

### 7.1 自定义 Role

如果有为考勤模块创建专门的 Role，需要导出。Role 通常不在 fixtures 中，而是通过 `hooks.py` 中的配置或 `patches.txt` 中的 Patch 来管理。

```bash
# 查看数据库中自定义的 Role
bench --site 你的站点名 console
# 执行：
frappe.get_all("Role", filters={"custom": 1}, fields=["role_name"])
```

### 7.2 DocType 的 Permission 管理

DocType 的权限是 DocType JSON 的一部分（`permissions` 字段），不需要单独管理。只要 DocType JSON 在 Git 中，权限就在 Git 中。

对于通过 UI 在"Role Permissions Manager"中设置的权限：

```bash
# 导出权限设置
bench --site 你的站点名 export-fixtures --app hb_attendance_app
```

### 7.3 自查

检查当前数据库中是否有只在数据库里的 Role：

```bash
bench --site 你的站点名 console
```

然后在 Console 中执行：

```python
# 查看所有自定义 Role
roles = frappe.get_all("Role", filters={"custom": 1}, fields=["role_name"])
for r in roles:
    print(r.role_name)
```

如果有输出而 Git 中没有对应的定义，说明需要导出。

---

## 8. Report 管理

### 8.1 当前项目已有 Report

hb_attendance_app 已经有 3 个 Report：

| Report | 目录位置 |
|--------|---------|
| 打卡流水 | `report/checkin_record/` |
| 考勤结果 | `report/attendance_result/` |
| HBOS月度汇总暂存（对账） | `report/hbos_monthly_summary_staging/` |

### 8.2 Report 的标准目录结构

```
apps/hb_attendance_app/hb_attendance_app/hbos_attendance/
└── report/
    └── checkin_record/
        ├── checkin_record.json   # Report 定义（核心）
        ├── checkin_record.py     # 数据查询逻辑（核心）
        └── checkin_record.js     # 前端脚本（可选，用于交互式 Report）
```

### 8.3 Report 的版本控制要求

| 文件 | 是否提交 Git | 说明 |
|------|-------------|------|
| `.json` | 必须 | Report 结构定义 |
| `.py` | 必须 | 数据查询逻辑 |
| `.js` | 必须 | 前端交互脚本 |
| `.html` | 必须 | 如果有 HTML 模板 |

### 8.4 修改 Report 后的导出

```bash
# 导出 Report 到 App 目录
bench --site 你的站点名 export-doc hb_attendance_app "打卡流水"

# 如果 Report 名称包含中文，需要确认导出成功
ls apps/hb_attendance_app/hb_attendance_app/hbos_attendance/report/checkin_record/
```

### 8.5 修改标准 Report（基于 Query Report 的简单报表）

如果修改的是 Frappe 内置的 Report（如 Script Report），导出方式相同。如果是基于 Query Report 类型的数据修改，**直接修改 `.json` 文件中的 `query` 字段**即可，不需要在 UI 中操作后再导出。

---

## 9. Fixture 使用规范

### 9.1 什么应该导出为 Fixture

| 内容 | 是否 Fixture | 理由 |
|------|-------------|------|
| Custom Field | 是 | 字段定义必须同步 |
| Property Setter | 是 | 属性修改必须同步 |
| Workspace | 是（或直接在 app 目录中） | 导航布局必须同步 |
| Client Script | 是 | 前端脚本必须同步 |
| Server Script | 是 | 服务端逻辑必须同步 |
| Notification | 是 | 通知模板必须同步 |
| Print Format | 是 | 打印模板必须同步 |
| Letter Head | 是 | 如果需要自定义信纸 |

### 9.2 什么不应该导出为 Fixture

| 内容 | 是否 Fixture | 理由 |
|------|-------------|------|
| 真实员工数据 | **绝对不行** | 包含个人敏感信息 |
| 真实考勤记录 | **绝对不行** | 包含个人敏感信息 |
| API Key / Secret | **绝对不行** | 安全凭证 |
| 系统配置中的密码 | **绝对不行** | 安全凭证 |
| System Settings 中的生产配置 | 不建议 | URL、邮箱配置等因环境而异 |
| 大数据量的历史日志 | 不建议 | 会让 JSON 文件过大 |

### 9.3 导出命令汇总

```bash
# 导出 App 所有 Fixture
bench --site 你的站点名 export-fixtures --app hb_attendance_app

# 导出时指定目录
bench --site 你的站点名 export-fixtures --app hb_attendance_app --fixture-path apps/hb_attendance_app/hb_attendance_app/fixtures

# 导出单个 DocType 到 App 目录
bench --site 你的站点名 export-doc hb_attendance_app "HBOS Attendance Import Log"
```

### 9.4 hooks.py 中的 fixtures 配置示例

```python
# apps/hb_attendance_app/hb_attendance_app/hooks.py

fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "HBOS Attendance"]]},
    {"dt": "Property Setter", "filters": [["module", "=", "HBOS Attendance"]]},
    {"dt": "Workspace", "filters": [["module", "=", "HBOS Attendance"]]},
    {"dt": "Client Script", "filters": [["module", "=", "HBOS Attendance"]]},
]
```

注意：如果已经将 Fixture 导出为独立的 JSON 文件（如 `custom_field.json`），也可以直接引用文件路径。两种方式可以混用，但建议统一使用一种以降低维护复杂度。

---

## 10. Patch 和 Migration 使用规范

### 10.1 什么是 Patch

Patch 是一次性执行的 Python 脚本，在 `bench migrate` 时运行，用于修改数据或结构。执行过后不会再次运行。

**什么时候写 Patch：**

| 场景 | 举例 |
|------|------|
| 给已有记录批量赋值 | 把所有现有 Employee 的考勤组设为默认值 |
| 创建初始数据 | 创建默认的 Shift Type |
| 修改已有数据的结构 | 把某个字段的值从旧格式转为新格式 |
| 创建 Workspace | 初始化标准工作台布局 |

**什么时候不写 Patch：**

| 场景 | 替代方案 |
|------|---------|
| 给 DocType 加字段 | 直接修改 DocType JSON |
| 修改字段标签 | Property Setter |
| 创建 Demo 数据 | 用 SQL dump 或单独的 Demo 脚本 |

### 10.2 Patch 文件的存放位置和命名规范

```
apps/hb_attendance_app/hb_attendance_app/
└── patches/
    ├── v1_0_0/
    │   ├── create_default_shift_types.py
    │   └── migrate_attendance_data.py
    └── v1_1_0/
        └── add_new_fields.py
```

命名规范：

```
patches/[版本号]/[动作描述].py
```

例如：
- `patches/v1_0_0/create_workspace.py`
- `patches/v1_0_0/set_default_holiday_list.py`
- `patches/v1_1_0/rename_field_x_to_y.py`

### 10.3 Patch 文件的内容结构

```python
# patches/v1_0_0/set_default_holiday_list.py

import frappe

def execute():
    """给所有 Employee 设置默认假期列表"""
    employees = frappe.get_all("Employee", fields=["name"])
    for emp in employees:
        frappe.db.set_value("Employee", emp.name, "holiday_list", "Standard")
    frappe.db.commit()
```

关键点：
- Patch 文件必须有一个 `execute()` 函数
- `execute()` 会在 migrate 时被调用一次
- 如果 Patch 中做了大量数据修改，**一定要先备份数据库**

### 10.4 patches.txt 的格式

`patches.txt` 记录了所有要执行的 Patch 路径：

```
# patches.txt
hb_attendance_app.patches.v1_0_0.create_default_shift_types
hb_attendance_app.patches.v1_0_0.migrate_attendance_data
hb_attendance_app.patches.v1_0_0.set_default_holiday_list
hb_attendance_app.patches.v1_1_0.add_new_fields
```

格式说明：
- 每行一个 Patch 路径（从 App 的 Python 包路径开始）
- 按**执行顺序**从上到下排列
- 不要写注释（Frappe 可能不解析）

### 10.5 数据迁移 vs Schema 迁移

| 类型 | 改什么 | 谁负责 | 举例 |
|------|--------|--------|------|
| Schema 迁移 | 表结构（加字段、改字段类型） | Frappe 自动处理（基于 DocType JSON） | 给 DocType 加了一个新字段 |
| 数据迁移 | 现有数据（填充值、转换格式） | 你写的 Patch | 给新字段填充默认值 |

**重要**：
- Schema 迁移（DocType JSON 变更）由 Frappe 自动处理，你只需要修改 JSON 并提交
- 数据迁移需要写 Patch，确保旧数据与新 Schema 兼容

### 10.6 migrate 前必须备份

```bash
# 备份当前数据库
bench --site 你的站点名 backup

# 备份文件存储位置
ls sites/你的站点名/private/backups/

# 查看所有备份
bench --site 你的站点名 list-backups
```

**铁律：`bench migrate` 之前必须备份。**

### 10.7 失败回滚策略

如果 migrate 失败：

```bash
# 1. 记录失败信息，截图保存

# 2. 恢复数据库
bench --site 你的站点名 restore 备份文件名

# 3. 分析原因
# - Patch 逻辑有 bug？
# - DocType JSON 格式有误？
# - 数据库不一致？

# 4. 修复后重新 migrate
bench --site 你的站点名 migrate
```

### 10.8 Patch 只执行一次

一旦 Patch 执行成功，Frappe 会记录它已执行，不会再次运行。如果需要修改 Patch 的逻辑：

- **正确的做法**：写一个新的 Patch（新版本号），在新 Patch 中修正，追加到 `patches.txt` 末尾
- **错误做法**：修改已执行的 Patch 内容（不会重新运行），或者删除记录强行重新执行（可能造成数据重复）

---

## 11. 多人协作规则

### 11.1 DocType 修改的冲突处理流程

```
                    Developer A                    Developer B
                    ───────────                    ───────────
Step 1:             git pull main                  git pull main
Step 2:             在 UI 修改 A 字段              在 UI 修改 B 字段
Step 3:             export-doc                     export-doc
Step 4:             git add + commit               git add + commit
Step 5:             git push                       git push（A 先推送成功）
                                                   
Step 6:                                             git pull（产生冲突）
                                                    
Step 7:                                            手动合并 JSON 文件
Step 8:                                            bench migrate（验证合并结果）
Step 9:                                            git push
```

### 11.2 合并 DocType JSON 冲突的技巧

DocType JSON 文件可能超过 500 行，手动合并建议：

1. 用 VS Code 或其他 IDE 的对比视图查看差异
2. 重点关注 `fields` 数组中的变化
3. 两边的字段都保留（一个人加字段 A，另一个加字段 B，合并后两个字段都在）
4. 布局相关（`links` 等）变化需要更仔细对比
5. 合并后用 `bench migrate` 验证，确认没有 JSON 语法错误

### 11.3 migration 顺序管理

同一个版本内有多个 Patch 时，PATCH 的执行顺序很重要：

```txt
# patches.txt — 按依赖关系从上到下排列

# 1. 先建基础数据
hb_attendance_app.patches.v1_0_0.create_default_shift_types

# 2. 再给 Employee 设置（依赖步骤 1 的 Shift Type）
hb_attendance_app.patches.v1_0_0.set_default_holiday_list

# 3. 最后迁移历史数据（依赖步骤 1、2 都已完成）
hb_attendance_app.patches.v1_0_0.migrate_attendance_data
```

**原则**：被依赖的 Patch 必须写在前面。

### 11.4 合并前检查清单

在提交合并请求前：

- [ ] `bench migrate` 在你的分支上成功执行
- [ ] `git diff main...你的分支` 只包含你修改的文件
- [ ] fixtures JSON 文件没有语法错误（可以用 `python -m json.tool` 验证）
- [ ] patches.txt 的路径拼写正确
- [ ] 没有提交 `sites/` 目录下的数据库文件

---

## 12. 数据库备份与恢复

### 12.1 bench backup 命令

```bash
# 创建备份
bench --site 你的站点名 backup

# 备份包含：数据库 SQL dump + site 配置文件 + public/private 文件

# 查看所有备份
bench --site 你的站点名 list-backups

# 备份文件位置
sites/你的站点名/private/backups/
```

备份文件格式：
```
20260714_143000-你的站点名-database.sql.gz     # 数据库备份
20260714_143000-你的站点名-files.tar           # 文件备份
20260714_143000-你的站点名-private-files.tar   # 私有文件备份
site_config_backup.json                        # 站点配置备份
```

### 12.2 备份频率建议

| 场景 | 备份频率 | 说明 |
|------|---------|------|
| 日常开发 | 每天 1 次 | 防止一天的工作丢失 |
| migrate 前 | 必须备份 | 这是最重要的一次 |
| 写 Patch 并测试 | 每次测试前 | 测试可能损坏数据 |
| 生产环境 | 每天自动备份 | 通过 cron 定时任务 |
| 重大变更前 | 必须备份 | 修改核心 DocType 或运行复杂 Patch |

### 12.3 恢复步骤

```bash
# 1. 先查看有哪些备份可用
bench --site 你的站点名 list-backups

# 2. 恢复数据库（从备份文件名）
bench --site 你的站点名 restore 20260714_143000

# 3. 恢复后验证
bench --site 你的站点名 console
# 快速验证：查询几条关键数据确认恢复成功
```

### 12.4 生产环境备份（参考）

生产环境的备份建议配置自动任务：

```bash
# crontab 示例：每天凌晨 2 点自动备份
0 2 * * * cd /path/to/frappe-bench && bench --site 你的生产站点 backup

# 保留最近 30 天的备份，定期清理旧的
```

---

## 13. Demo 数据规范

### 13.1 核心原则

> **Git 仓库里绝对不能出现真实员工数据。**

真实员工数据包含：
- 姓名、工号
- 手机号、邮箱
- 考勤记录（几点打卡）
- 任何能关联到具体个人的信息

### 13.2 Demo 数据与正式数据隔离

如果测试需要 Demo 数据：

```bash
# 方案一：用 SQL dump 提供 Demo 数据（单独存放，不自动加载）
# 文件放在 apps/hb_attendance_app/demo/ 目录下
apps/hb_attendance_app/demo/demo_data.sql

# 手动加载到开发环境
bench --site 你的站点名 console < apps/hb_attendance_app/demo/demo_data.sql
```

```python
# 方案二：写一个只在开发环境运行的 Demo 脚本
# apps/hb_attendance_app/hb_attendance_app/demo/setup_demo.py

import frappe

def setup_demo_employees():
    """创建 Demo 员工数据（仅用于开发环境）"""
    demo_employees = [
        {"employee_name": "测试用户01", "company": "海滨公司"},
        {"employee_name": "测试用户02", "company": "海滨公司"},
    ]

    # 检查是否为开发环境
    if frappe.conf.developer_mode:
        for emp in demo_employees:
            if not frappe.db.exists("Employee", {"employee_name": emp["employee_name"]}):
                doc = frappe.get_doc({"doctype": "Employee", **emp})
                doc.insert()
        frappe.db.commit()
    else:
        print("Demo 数据只能在开发环境创建")
```

### 13.3 测试数据命名规范

| 内容 | 命名规则 | 示例 |
|------|---------|------|
| Demo 员工 | `测试用户XX`、`DemoUserXX` | 测试用户01 |
| Demo 公司 | `测试公司-XX`、`DemoCompany-XX` | 测试公司-考勤模块 |
| Demo 考勤记录 | 确保日期不涉及真实考勤 | 2024-01-01（遥远的日期） |

### 13.4 .gitignore 中排除敏感文件

```gitignore
# 不要把数据库备份推到 Git
sites/*/private/backups/

# 不要把站点配置推到 Git（包含数据库密码等）
sites/*/site_config.json
```

---

## 14. 检查清单

### 14.1 当前项目中可能"只在数据库里"的内容

以下内容很可能只存在于数据库中，需要逐一核对并导出：

| 内容 | 自查命令 / 方法 | 状态 |
|------|----------------|------|
| Custom Field | `bench console` → `frappe.get_all("Custom Field")` | 需要检查 |
| Property Setter | `bench console` → `frappe.get_all("Property Setter")` | 需要检查 |
| 中文字段标签 (Translation) | `bench console` → `frappe.get_all("Translation")` | 需要检查 |
| Client Script | 检查 `fixtures/` 目录中是否有 | 需要检查 |
| Server Script | 检查 `fixtures/` 目录中是否有 | 需要检查 |
| Role（自定义角色） | `bench console` → `frappe.get_all("Role", filters={"custom": 1})` | 需要检查 |
| Workflow | `bench console` → `frappe.get_all("Workflow")` | 需要检查 |
| Notification | `bench console` → `frappe.get_all("Notification")` | 需要检查 |
| 自定义 DocType | 检查 `doctype/` 目录中是否都有 JSON | 已管理（hbos_attendance_import_log） |
| Workspace | 检查 `workspace/` 目录 | 已管理（海滨考勤工作台） |
| Report | 检查 `report/` 目录 | 已管理（3 个 Report） |

### 14.2 日常开发检查清单

每天收工前：

- [ ] 今天通过 UI 做了哪些修改？
- [ ] 这些修改有没有导出为文件？（`export-doc` 或 `export-fixtures`）
- [ ] 导出后有没有 `git diff` 确认变更内容？
- [ ] 有没有写新的 Patch？有没有加到 `patches.txt`？
- [ ] `bench migrate` 能成功执行吗？

### 14.3 提交前检查清单

在 `git commit` 之前：

- [ ] 所有新增/修改的 DocType 已导出（`export-doc`）
- [ ] 所有新增/修改的 Custom Field 已导出（`export-fixtures`）
- [ ] 所有新增/修改的 Property Setter 已导出（`export-fixtures`）
- [ ] Workspace 修改已同步到 JSON
- [ ] 新增的 Patch 已添加到 `patches.txt`
- [ ] `fixtures` JSON 文件语法正确（无多余逗号、括号匹配）
- [ ] 没有不小心提交 `sites/` 下的数据库文件或备份
- [ ] 没有真实员工数据被包含在提交中
- [ ] commit message 遵循规范格式（`feat:` / `fix:` / `refactor:`）

### 14.4 新人入职环境搭建验证

新人 clone 代码后，应该能通过以下步骤还原完整环境：

```bash
# 1. 获取代码
git clone <仓库地址>
cd frappe-bench

# 2. 获取 App
bench get-app hb_attendance_app

# 3. 创建站点并安装 App
bench new-site 你的站点名
bench --site 你的站点名 install-app hb_attendance_app

# 4. 执行 migrate
bench --site 你的站点名 migrate

# 5. 启动并验证
bench start
# 浏览器访问站点
# 检查：自定义字段是否出现
# 检查：Workspace 是否正常显示
# 检查：Report 能否正常运行
```

**如果以上任何一步失败，说明有配置没有被正确版本控制，需要排查并修复。**

---

## 附录：常用命令速查表

| 操作 | 命令 |
|------|------|
| 导出 DocType | `bench --site SITE export-doc APP "DocType Name"` |
| 导出所有 Fixture | `bench --site SITE export-fixtures --app APP` |
| 执行 migrate | `bench --site SITE migrate` |
| 创建备份 | `bench --site SITE backup` |
| 查看备份列表 | `bench --site SITE list-backups` |
| 恢复备份 | `bench --site SITE restore BACKUP_NAME` |
| 进入 Console | `bench --site SITE console` |
| 查看站点列表 | `bench site list` |
| 重建 DocType（从 JSON） | `bench --site SITE migrate` |
| 验证 JSON 格式 | `python -m json.tool file.json > /dev/null` |

---

> **文档维护者**：HBOS 开发团队  
> **创建日期**：2026-07-14  
> **最后更新**：2026-07-14  
> **相关文档**：
> - [05_Frappe框架应用开发规范.md](./05_Frappe框架应用开发规范.md)
> - [02_后端架构设计规范.md](./02_后端架构设计规范.md)
