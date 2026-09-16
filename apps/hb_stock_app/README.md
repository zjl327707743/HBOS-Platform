# hb_stock_app

海滨库存工作台 App。

只承载 `海滨库存` Workspace 定义与 `after_migrate` 幂等同步，不新建 DocType、不重写库存逻辑。
库存单据、报表、估价与会计联动全部复用 ERPNext 原生能力。

安装站点：`stock`（独立站点）。**不要**安装到 `frontend` 考勤站点。
