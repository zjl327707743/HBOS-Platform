import type { ThemeConfig } from 'ant-design-vue/es/config-provider/context'

export const hbosAntdTheme: ThemeConfig = {
  token: {
    colorPrimary: '#5b63ff',
    colorInfo: '#4b9cff',
    colorSuccess: '#1bbc86',
    colorWarning: '#f4a523',
    colorError: '#ed5a72',
    colorText: '#17253c',
    colorTextSecondary: '#425675',
    colorBorder: 'rgba(65,91,138,.10)',
    borderRadius: 12,
    controlHeight: 40,
    fontSize: 14,
    fontSizeSM: 12,
    fontSizeLG: 16,
    fontSizeXL: 20,
    fontSizeHeading5: 16,
    fontSizeHeading4: 20,
    fontSizeHeading3: 24,
    fontSizeHeading2: 30,
    fontSizeHeading1: 38,
    lineHeight: 1.5714285714285714,
    lineHeightHeading5: 1.5,
    lineHeightHeading4: 1.4,
    lineHeightHeading3: 1.3333333333333333,
    lineHeightHeading2: 1.2666666666666666,
    lineHeightHeading1: 1.2105263157894737,
    fontWeightStrong: 600,
    fontFamily: 'Inter, "SF Pro Display", "PingFang SC", "Noto Sans SC", "Microsoft YaHei", system-ui, sans-serif',
  },
  components: {
    Button: {
      borderRadius: 12,
      controlHeight: 40,
    },
    Input: {
      borderRadius: 12,
      controlHeight: 40,
    },
    Select: {
      borderRadius: 12,
      controlHeight: 40,
    },
    Drawer: {
      paddingLG: 20,
    },
    Modal: {
      borderRadiusLG: 24,
    },
  },
}
