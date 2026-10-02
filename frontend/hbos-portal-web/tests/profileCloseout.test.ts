import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import Antd from 'ant-design-vue'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import Profile from '@/views/ProfileSettingsView.vue'
import Sidebar from '@/components/layout/PortalSidebar.vue'
import MobileNav from '@/components/layout/MobilePortalNav.vue'
import Header from '@/components/layout/GlobalHeader.vue'

const state = vi.hoisted(() => ({ user: {id:'closeout@example.test',displayName:'合成收尾验证',avatarText:'合',avatarUrl:'https://s1-imfile.feishucdn.com/owned-synthetic-avatar.png'}, apps:[] }))
const getSecurity = vi.hoisted(() => vi.fn())
vi.mock('@/stores/portal', () => ({usePortalStore: () => state}))
vi.mock('@/services/accountApi', () => ({getSecurity}))
const SecurityStub = defineComponent({emits:['statusChange'], setup(_, {emit}) {getSecurity().then((status:unknown) => emit('statusChange',status)).catch(() => emit('statusChange',null)); return {}}, template:'<section>账号与安全</section>'})
let wrappers: VueWrapper[] = []
async function render(component: object, props = {}) {
 const router=createRouter({history:createMemoryHistory(),routes:[{path:'/:pathMatch(.*)*',component:defineComponent({template:'<div />'})}]})
 await router.push('/hbos/profile'); await router.isReady()
 const wrapper=mount(component,{props,global:{plugins:[Antd,router],stubs:{AccountSecurity:SecurityStub,AppDiagnostics:true}}});wrappers.push(wrapper);await flushPromises();return wrapper
}
beforeEach(() => getSecurity.mockResolvedValue({user:state.user.id,has_password:true,password_login_available:true,feishu_bound:false,feishu_configured:true,desk_access:false,can_admin_recover:false}))
afterEach(() => {wrappers.forEach(w => w.unmount());wrappers=[]})
describe('小范围账号收尾', () => {
 it.each([
  [{has_password:false,feishu_bound:true,feishu_configured:true},'本人飞书','尚未设置密码'],
  [{has_password:true,feishu_bound:false,feishu_configured:true},'密码','飞书未绑定'],
  [{has_password:true,feishu_bound:true,feishu_configured:false},'密码','飞书已绑定 · 渠道暂不可用'],
  [{has_password:true,password_login_available:false,feishu_bound:false},'暂无可用登录方式','密码登录暂不可用'],
 ])('资料页反映真实渠道 %j',async (status,enabled,detail) => {
  getSecurity.mockResolvedValue({user:state.user.id,...status});const w=await render(Profile)
  const card=w.find('.profile-card');expect(card.text()).toContain('已启用的登录方式');expect(card.text()).toContain(enabled);expect(card.text()).toContain(detail);expect(card.text()).not.toMatch(/本次.*飞书|密码 \/ 本人飞书/)
 })
 it('读取失败不保留或猜测登录渠道',async () => {getSecurity.mockResolvedValue(null);const w=await render(Profile);expect(w.find('.profile-card').text()).toContain('暂未取得账号状态')})
 it('安全写操作后的状态同步资料摘要',async () => {const w=await render(Profile);w.findComponent(SecurityStub).vm.$emit('statusChange',{user:state.user.id,has_password:true,feishu_bound:true,feishu_configured:true});await flushPromises();expect(w.find('.profile-card').text()).toContain('密码、本人飞书')})
 it('拒绝另一主体的安全状态',async () => {getSecurity.mockResolvedValue({user:'another@example.test',has_password:true,feishu_bound:true,feishu_configured:true});const w=await render(Profile);expect(w.find('.profile-card').text()).toContain('暂未取得账号状态')})
 it('桌面和移动端各仅有一个个人路由选中项',async () => {for(const component of [Sidebar,MobileNav]){const w=await render(component,{workCount:0});const links=w.findAll('a[href="/hbos/profile"]');expect(links).toHaveLength(1);expect(links[0]!.text()).toBe('我的与设置');expect(w.findAll('a[href="/hbos/profile"].router-link-exact-active')).toHaveLength(1)}})
 it('未实现偏好收为默认折叠说明',async () => {const w=await render(Profile);expect(w.findAll('.setting-row button,.setting-row input')).toHaveLength(0);const details=w.find('details');expect(details.exists()).toBe(true);expect(details.attributes('open')).toBeUndefined()})
 it('资料页与菜单头像都加载当前用户图片，失败时回退文字',async () => {
  const profile=await render(Profile);const header=await render(Header,{apps:[],avatarText:'合',avatarUrl:state.user.avatarUrl})
  for(const w of [profile,header]){const image=w.find('img');expect(image.attributes('src')).toBe(state.user.avatarUrl);await image.trigger('error');await flushPromises();expect(w.text()).toContain('合');expect(w.find('img').exists()).toBe(false)}
 })
})
