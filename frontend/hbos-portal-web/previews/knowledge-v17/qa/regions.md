# v1.7 展示层归属

| 冻结原型区域 | 正式组件 | 样式归属 |
|---|---|---|
| topbar、sidebar、context | KnowledgeTwinLayout、KnowledgeHeader、KnowledgeSidebar | knowledge.css 和侧栏组件局部样式 |
| query、catalog、favorites、history、个人反馈 | KnowledgeView、KnowledgeTools | knowledge.css |
| 来源与文档 | EvidenceDrawer、DocumentReader、PdfPreview | 知识域抽屉根类和组件样式 |
| manage、upload、versions、D01 | KnowledgeMaintenanceView、KnowledgeBatchMaintenance | 知识域外壳统一加载 knowledgeUploadV17.css |
| staffFeedback | KnowledgeMaintenanceView、KnowledgeStaffFeedback | 员工反馈组件局部轨道 |
| D02 | KnowledgeConnections | 知识域抽屉根类和组件样式 |
