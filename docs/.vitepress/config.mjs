import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

export default withMermaid(
    defineConfig({
        base: '/llm_GoogleFootball/',
        cleanUrls: true,

        head: [
            ['link', { rel: 'icon', type: 'image/svg+xml', href: '/logo.svg' }],
            ['meta', { name: 'theme-color', content: '#3eaf7c' }],
        ],

        locales: {
            root: {
                label: '简体中文',
                lang: 'zh-CN',
                title: "LLM Google Football",
                description: "基于大语言模型的自动化足球战术决策框架",
                themeConfig: {
                    logo: '/logo.svg',
                    nav: [
                        { text: '首页', link: '/' },
                        { text: '指南', link: '/guide/introduction' },
                        { text: 'Leaderboard', link: '/leaderboard' },
                        { text: '战术演化', link: '/evolution' },
                        { text: '更新日志', link: 'https://github.com/HuangShengZeBlueSky/llm_GoogleFootball' }
                    ],
                    sidebar: {
                        '/guide/': [
                            {
                                text: '入门',
                                items: [
                                    { text: '项目概述', link: '/guide/introduction' },
                                    { text: '快速开始', link: '/guide/quickstart' }
                                ]
                            },
                            {
                                text: '详细说明',
                                items: [
                                    { text: '代码架构与 IPO', link: '/guide/architecture' },
                                    { text: '实验配置', link: '/guide/configuration' },
                                    { text: '多模型批量测试', link: '/guide/batch-testing' }
                                ]
                            }
                        ]
                    },
                    footer: {
                        message: 'Released under the MIT License.',
                        copyright: 'Copyright © 2026-present Bluesky Lab'
                    }
                }
            },
            en: {
                label: 'English',
                lang: 'en-US',
                link: '/en/',
                title: "LLM Google Football",
                description: "Autonomous Football Tactics Decision Framework powered by Large Language Models",
                themeConfig: {
                    logo: '/logo.svg',
                    nav: [
                        { text: 'Home', link: '/en/' },
                        { text: 'Guide', link: '/en/guide/introduction' },
                        { text: 'Leaderboard', link: '/en/leaderboard' },
                        { text: 'Evolution', link: '/en/evolution' },
                        { text: 'Changelog', link: 'https://github.com/HuangShengZeBlueSky/llm_GoogleFootball' }
                    ],
                    sidebar: {
                        '/en/guide/': [
                            {
                                text: 'Getting Started',
                                items: [
                                    { text: 'Overview', link: '/en/guide/introduction' },
                                    { text: 'Quickstart', link: '/en/guide/quickstart' }
                                ]
                            },
                            {
                                text: 'Deep Dive',
                                items: [
                                    { text: 'Architecture & IPO', link: '/en/guide/architecture' },
                                    { text: 'Configuration', link: '/en/guide/configuration' },
                                    { text: 'Batch Testing', link: '/en/guide/batch-testing' }
                                ]
                            }
                        ]
                    },
                    footer: {
                        message: 'Released under the MIT License.',
                        copyright: 'Copyright © 2026-present Bluesky Lab'
                    }
                }
            }
        },

        themeConfig: {
            socialLinks: [
                { icon: 'github', link: 'https://github.com/HuangShengZeBlueSky/llm_GoogleFootball' }
            ],
            search: {
                provider: 'local'
            }
        }
    })
)
