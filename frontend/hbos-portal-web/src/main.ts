import { createApp } from 'vue'
import { createPinia } from 'pinia'
import 'ant-design-vue/dist/reset.css'
import './theme/tokens.css'
import './styles/global.css'
import './theme/typography.css'
import App from './App.vue'
import router from './router'
// **深路径导入**：`from 'ant-design-vue'` 会加载它的整个 barrel（`es/index.js`）。
// 配合逐个注册，实测 vendor-antd 从 1371 kB（gzip 406）降到 990 kB（gzip 290）。
// 从各组件自己的入口导入更稳妥 —— 不依赖 tree-shaking 是否成功。
import Alert from 'ant-design-vue/es/alert'
import Avatar from 'ant-design-vue/es/avatar'
import Badge from 'ant-design-vue/es/badge'
import Button from 'ant-design-vue/es/button'
import Checkbox from 'ant-design-vue/es/checkbox'
import Collapse from 'ant-design-vue/es/collapse'
import ConfigProvider from 'ant-design-vue/es/config-provider'
import DatePicker from 'ant-design-vue/es/date-picker'
import Descriptions from 'ant-design-vue/es/descriptions'
import Divider from 'ant-design-vue/es/divider'
import Drawer from 'ant-design-vue/es/drawer'
import Dropdown from 'ant-design-vue/es/dropdown'
import Empty from 'ant-design-vue/es/empty'
import Form from 'ant-design-vue/es/form'
import Input from 'ant-design-vue/es/input'
import InputNumber from 'ant-design-vue/es/input-number'
import List from 'ant-design-vue/es/list'
import Menu from 'ant-design-vue/es/menu'
import Modal from 'ant-design-vue/es/modal'
import Popover from 'ant-design-vue/es/popover'
import Progress from 'ant-design-vue/es/progress'
import Radio from 'ant-design-vue/es/radio'
import Result from 'ant-design-vue/es/result'
import Segmented from 'ant-design-vue/es/segmented'
import Select from 'ant-design-vue/es/select'
import Skeleton from 'ant-design-vue/es/skeleton'
import Space from 'ant-design-vue/es/space'
import Steps from 'ant-design-vue/es/steps'
import Table from 'ant-design-vue/es/table'
import Tag from 'ant-design-vue/es/tag'
import Timeline from 'ant-design-vue/es/timeline'
import Tooltip from 'ant-design-vue/es/tooltip'

/**
 * **按需注册** Ant Design 组件。
 *
 * 早先是 `app.use(Antd)` —— 全量注册会把整套库（含从未用到的上传、树、
 * 穿梭框等重组件）都打进主包：vendor-antd 单块 1371 kB（gzip 406 kB）。
 * 改成「深路径导入 + 逐个注册」后是 990 kB（gzip 290 kB）。
 *
 * ⚠️ **新增 `a-xxx` 时必须在这里补一行**，否则模板里会静默渲染成空元素
 * （Vue 只打一条 resolve 警告，不报错，页面看起来「少了一块」）。
 * `tests/antdRegistration.test.ts` 扫源码用法与这份清单对账。
 */
const ANTD_COMPONENTS = {
  Alert,
  Avatar,
  Badge,
  Button,
  Checkbox,
  Collapse,
  ConfigProvider,
  DatePicker,
  Descriptions,
  Divider,
  Drawer,
  Dropdown,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  Menu,
  Modal,
  Popover,
  Progress,
  Radio,
  Result,
  Segmented,
  Select,
  Skeleton,
  Space,
  Steps,
  Table,
  Tag,
  Timeline,
  Tooltip,
  // --- 子组件 ---
  // 这些不是由父组件自动挂到全局的：`<a-select-option>` 之类如果不显式注册，
  // 会渲染成未知元素（选项列表空白）。实测只注册 `Select` 时下拉是空的。
  CheckboxGroup: Checkbox.Group,
  CollapsePanel: Collapse.Panel,
  DescriptionsItem: Descriptions.Item,
  FormItem: Form.Item,
  InputPassword: Input.Password,
  InputSearch: Input.Search,
  Textarea: Input.TextArea,
  ListItem: List.Item,
  MenuDivider: Menu.Divider,
  MenuItem: Menu.Item,
  RadioButton: Radio.Button,
  RadioGroup: Radio.Group,
  SelectOption: Select.Option,
  TableColumn: Table.Column,
  TimelineItem: Timeline.Item,
} as const

const canonicalHost = String(import.meta.env.VITE_HBOS_CANONICAL_HOST || '').trim()
const localAliases = new Set(['127.0.0.1', 'localhost'])

if (
  canonicalHost &&
  /^[a-z0-9.-]+$/i.test(canonicalHost) &&
  window.location.hostname !== canonicalHost &&
  localAliases.has(window.location.hostname)
) {
  const port = window.location.port ? `:${window.location.port}` : ''
  window.location.replace(
    `${window.location.protocol}//${canonicalHost}${port}${window.location.pathname}${window.location.search}${window.location.hash}`,
  )
} else {
  const app = createApp(App).use(createPinia()).use(router)
  for (const [name, component] of Object.entries(ANTD_COMPONENTS)) {
    // 注册成 `A<Name>`：模板里的 `a-button` 会被 Vue 解析为 `AButton`。
    // 同时注册不带前缀的名字，供 `<component :is="'Button'">` 这类写法使用。
    app.component(`A${name}`, component as never)
    app.component(name, component as never)
  }
  app.mount('#app')
}
