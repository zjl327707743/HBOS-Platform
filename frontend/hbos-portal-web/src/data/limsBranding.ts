/**
 * LIMS Shell 的本地品牌兜底资产。
 *
 * 真实环境仍优先使用 Portal branding API 返回的海滨标识；本地资产只
 * 用于 API 尚未返回 logo 时保持双品牌页头完整，不承载业务数据。
 */
export const LIMS_BRANDING = {
  companyLogoUrl: '/assets/branding/haibin-company.png',
  groupLogoUrl: '/assets/branding/healthgen-group.png',
} as const
