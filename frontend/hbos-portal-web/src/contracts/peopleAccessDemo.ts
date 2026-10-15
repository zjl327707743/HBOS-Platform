// 前端复刻的展示模型；不作为后端授权契约或真实人员主数据。
export interface DemoDepartment { id: string; name: string; parentId: string | null; level: number }
export interface DemoPermission { id: string; label: string }
export interface DemoMenu { id: string; label: string; actions: DemoPermission[] }
export interface DemoPermissionApp { id: string; label: string; menus: DemoMenu[] }
export interface DemoRole { id: string; name: string; description: string; createdAt: string; permissionIds: string[] }
export interface DemoPosition { id: string; departmentId: string; name: string; scopeLabel: string; roleIds: string[] }
export interface DemoPerson { id: string; name: string; phone: string; active: boolean; positionIds: string[] }
export interface DemoPersonFilter {
  departmentId: string; includeChildren: boolean; name: string; phone: string; position: string; roleId: string
}
