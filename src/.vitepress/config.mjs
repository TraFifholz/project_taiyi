import { defineConfig } from 'vitepress'
import { readFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const sidebar = JSON.parse(readFileSync(resolve(__dirname, 'sidebar.json'), 'utf8'))

export default defineConfig({
  title: '太一 · 狂野世界规则书',
  description: 'Savage Worlds Adventure Edition 核心规则与私设资源',
  lang: 'zh-CN',
  cleanUrls: true,
  ignoreDeadLinks: true,

  themeConfig: {
    nav: [
      { text: '首页', link: '/' },
      { text: '核心规则', link: '/核心规则/' },
      { text: '私设资源', link: '/私设/' },
    ],

    sidebar,

    search: {
      provider: 'local',
      options: {
        translations: {
          button: { buttonText: '搜索' },
          modal: { noResultsText: '无结果', resetButtonTitle: '清除' }
        }
      }
    },

    docFooter: {
      prev: '上一页',
      next: '下一页',
    },
  },
})
