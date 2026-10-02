import Antd from 'ant-design-vue'

// 注册完整 Ant Design Vue 插件。原先的按需组件清单在 Portal 与 LIMS 视图
// 同时存在后无法保证覆盖所有 `a-*` 标签，改为一次性注册整套组件。
export const antdComponents = [Antd]
