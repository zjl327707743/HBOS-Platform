"""排班表导入: 支持厂外QC矩阵式与四车间纵向式两种 Excel 格式。

厂外QC矩阵式(员工×31天):
  第1行: 员工排班表
  第2行: 开始排班日期 F2=2026.08.18
  第3行: 姓名 工号 部门 班组 考勤规则 1 2 3 ...
  第4行: (空) (空) (空) (空) (空) 星期六 星期日 ...
  第5行起: 员工行, F 列起为每天的班次(班次1-4/年假/产假/护理假/空)
  「班次说明」工作表: 班次1=08:30-17:30 班次2=08:30-16:30 班次3=16:00-24:00 班次4=00:00-08:00

四车间纵向式(日期+班次+成员):
  第1行: 倒班组 (右侧) 行政班组
  之后循环: 日期行 / 班次|人数|班组成员行 / 夜班|7|赵强|张娜|... 等

解析为统一结构: [{employee_number, employee_name, date, shift_type|None, leave_type|None}]
"""
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

# 班次代码 → 系统班次类型
SHIFT_CODE_MAP = {
    "班次1": "行政班",
    "班次2": "8:30班",
    "班次3": "中班",
    "班次4": "夜班",
}

# 请假类型(排班表中的文本)
LEAVE_TYPES = {"年假", "产假", "陪产假", "护理假", "病假", "事假", "调休", "婚假", "丧假"}


def _cell_value(c, strings):
    """读取单元格值，兼容三种 xlsx 存储格式:
    - t="s"         共享字符串(v 为 sharedStrings 索引)
    - t="inlineStr" 内联字符串(文本在 <is><t> 里, 常见于 WPS/部分工具导出)
    - 其他          数值(v 为数值)
    """
    t = c.get('t')
    if t == 'inlineStr':
        is_el = c.find('m:is', NS)
        if is_el is not None:
            t_el = is_el.find('m:t', NS)
            return (t_el.text or '') if t_el is not None else ''
        return ''
    v = c.find('m:v', NS)
    val = v.text if v is not None else ''
    if t == 's' and val and int(val) < len(strings):
        val = strings[int(val)]
    return val


def parse_xlsx_matrix(file_path):
    """解析厂外QC矩阵式排班表。

    返回: (rows, sheet_date_start)
    rows: [{employee_number, employee_name, department, date, shift_type, leave_type}]
    """
    with zipfile.ZipFile(file_path) as zf:
        # 读 sharedStrings
        strings = []
        if 'xl/sharedStrings.xml' in zf.namelist():
            st = ET.fromstring(zf.read('xl/sharedStrings.xml'))
            for si in st.findall('m:si', NS):
                text = ''.join(t.text or '' for t in si.iter(f'{{{NS["m"]}}}t'))
                strings.append(text)

        # 找排班 sheet(排除"班次说明")
        wb = ET.fromstring(zf.read('xl/workbook.xml'))
        all_sheet_names = [s.get('name') or '' for s in wb.findall('.//m:sheet', NS)]
        # 矩阵式必有「班次说明」工作表(定义班次1-4); 无此表说明不是矩阵式
        # (纵向式文件如「四车间排班表」只有一个 Sheet1, 若当矩阵式解析会产出垃圾行)
        if not any('说明' in n for n in all_sheet_names):
            return [], None
        sheets = []
        for s in wb.findall('.//m:sheet', NS):
            name = s.get('name')
            rid = s.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            if '说明' not in name:
                sheets.append((name, rid))

        # 解析关系映射
        rels = ET.fromstring(zf.read('xl/_rels/workbook.xml.rels'))
        rel_map = {}
        for rel in rels.findall('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
            rel_map[rel.get('Id')] = rel.get('Target')

        all_rows = []
        for sheet_name, rid in sheets:
            target = rel_map[rid]
            if not target.startswith('xl/'):
                target = 'xl/' + target.lstrip('/')
            if target not in zf.namelist():
                continue
            sheet_rows, date_start = _parse_matrix_sheet(zf.read(target), strings)
            all_rows.extend(sheet_rows)
        return all_rows, None


def _parse_matrix_sheet(xml_bytes, strings):
    root = ET.fromstring(xml_bytes)
    cell_map = {}
    for row in root.findall('.//m:row', NS):
        for c in row.findall('m:c', NS):
            ref = c.get('r')
            cell_map[ref] = _cell_value(c, strings)

    # 找开始排班日期(F2)
    date_start = None
    if 'F2' in cell_map:
        try:
            date_start = datetime.strptime(str(cell_map['F2']).strip(), "%Y.%m.%d").date()
        except Exception:
            pass
    # 星期序列校准(Owner 2026-08-21): F2 可能不可信(模板旧值),
    # 用第4行 F 列的星期在 F2 的月份里找真实起点。
    # 例: F2=2026.08.18 但 F 列星期=星期六 → 实际起点为 2026-08-01(星期六)
    WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    first_weekday = str(cell_map.get('F4', '')).strip()
    if date_start and first_weekday in WEEKDAYS:
        month = date_start.replace(day=1)
        target_wd = WEEKDAYS.index(first_weekday)
        # 在当月内找第一个目标星期
        d = month
        while d.month == month.month:
            if d.weekday() == target_wd:
                date_start = d
                break
            d += timedelta(days=1)
    if date_start is None:
        date_start = datetime(2026, 8, 1).date()

    # 第4行 F 列起为星期, 第3行 F 列起为序号(1-31)
    # 数据行从第5行起
    rows = []
    r_idx = 5
    empty_streak = 0
    while empty_streak < 5:
        name = cell_map.get(f'A{r_idx}', '').strip()
        emp_num = cell_map.get(f'B{r_idx}', '').strip()
        if emp_num == '-':
            emp_num = ''
        dept = cell_map.get(f'C{r_idx}', '').strip()
        if not name and not emp_num:
            empty_streak += 1
            r_idx += 1
            continue
        empty_streak = 0
        # 遍历 F..AJ(31天) + AK(第32天, 部分行有)
        for col_idx in range(6, 6 + 32):  # F=6 到 AL=38
            col_letter = _col_letter(col_idx)
            ref = f'{col_letter}{r_idx}'
            day_offset = col_idx - 6
            sched_date = date_start + timedelta(days=day_offset)
            val = cell_map.get(ref, '').strip()
            if val in SHIFT_CODE_MAP:
                rows.append({
                    'employee_number': emp_num,
                    'employee_name': name,
                    'department': dept,
                    'date': sched_date.strftime('%Y-%m-%d'),
                    'shift_type': SHIFT_CODE_MAP[val],
                    'leave_type': '',
                })
            elif val in LEAVE_TYPES:
                rows.append({
                    'employee_number': emp_num,
                    'employee_name': name,
                    'department': dept,
                    'date': sched_date.strftime('%Y-%m-%d'),
                    'shift_type': '',
                    'leave_type': val,
                })
            else:
                # 空白 = 休息(Owner 2026-08-21 确认)
                rows.append({
                    'employee_number': emp_num,
                    'employee_name': name,
                    'department': dept,
                    'date': sched_date.strftime('%Y-%m-%d'),
                    'shift_type': '休息',
                    'leave_type': '',
                })
        r_idx += 1
    return rows, date_start


def parse_xlsx_vertical(file_path):
    """解析四车间纵向式排班表(日期+班次+成员)。

    返回 rows 同矩阵式。
    """
    with zipfile.ZipFile(file_path) as zf:
        strings = []
        if 'xl/sharedStrings.xml' in zf.namelist():
            st = ET.fromstring(zf.read('xl/sharedStrings.xml'))
            for si in st.findall('m:si', NS):
                text = ''.join(t.text or '' for t in si.iter(f'{{{NS["m"]}}}t'))
                strings.append(text)
        sheet_xml = zf.read('xl/worksheets/sheet1.xml')

    root = ET.fromstring(sheet_xml)
    grid = []
    for row in root.findall('.//m:row', NS):
        cells = []
        for c in row.findall('m:c', NS):
            cells.append(str(_cell_value(c, strings)).strip())
        grid.append(cells)

    rows = []
    current_date = None
    shift_map = {"夜班": "夜班", "早班": "早班", "中班": "中班"}
    for line in grid:
        if not line:
            continue
        first = line[0] if line else ''
        if first.startswith('2026.') or (first and first[0].isdigit() and len(first) >= 10 and '.' in first):
            try:
                current_date = datetime.strptime(first, "%Y.%m.%d").date()
            except Exception:
                current_date = None
            continue
        if first in shift_map and current_date:
            # 成员从第3列起
            for name in line[2:]:
                name = name.strip()
                if not name:
                    continue
                rows.append({
                    'employee_number': '',
                    'employee_name': name,
                    'department': '',
                    'date': current_date.strftime('%Y-%m-%d'),
                    'shift_type': shift_map[first],
                    'leave_type': '',
                })
    return rows, None


def _col_letter(idx):
    """列序号(1起) → Excel 列字母。"""
    result = ''
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        result = chr(65 + rem) + result
    return result
