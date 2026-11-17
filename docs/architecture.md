# 整体架构与模块职责

## 一句话

一个进程里跑「界面线程 + 后台工作线程」，后台线程握着**一套** Playwright（Edge），按「挑小节 → 看视频 → 答测验 → 记状态」循环；AI 答题另有一条专属线程，避免两套 sync Playwright 撞在同一个线程里。

## 分层

```
┌──────────────────────────── 界面层（Tkinter）────────────────────────────┐
│ app.py          入口：DPI、协议/引导弹窗、主窗口                        │
│ app_ui.py       主窗口骨架（Canvas + 磨砂卡片 + 图片按钮）              │
│ app_hist.py     进度条、当前小节、上次跑到哪、刷课记录页签              │
│ wizard.py       首次运行的登录向导（两枚二维码 + 账密小窗）             │
│ dialogs.py      用户协议 / 上手引导 / 运行停顿检测                      │
│ ui_theme.py     皮肤：背景图、磨砂片、按钮素材烘焙                      │
│ ui_kit.py       Canvas 文字、galgame 图片按钮                          │
├──────────────────────────── 调度层 ─────────────────────────────────────┤
│ runner.py       主循环：重扫章节 → 挑一节 → 看视频 → 答测验 → 记账      │
│ progress.py     每节做到哪一步（done / partial / failed）              │
│ runstate.py     「上次跑到哪」+ 刷课记录（JSON）                        │
│ heartbeat.py    心跳：界面判断「它是不是卡住了」                        │
├──────────────────────────── 业务层 ─────────────────────────────────────┤
│ browser.py      Playwright 会话、登录态判定、窗口最大化/小窗            │
│ onboard.py      登录向导的后台：抓学习通二维码、豆包(抖音)二维码        │
│ courses.py      课程列表解析                                          │
│ chapters.py     章节树扫描、点击、导航、**任务点判定**                  │
│ player.py       视频播放主循环：保活、弹题、91%/96% 提前判定            │
│ quiz.py         弹窗题：检测 → 选 → 提交 → 等判分 → 继续               │
│ exam.py         章节测验整页答题：解析、勾选、自检、提交、读分、找重做  │
│ answers.py      答题链（题库 → AI → 兜底）与 SQLite 题库                │
│ aichat.py       豆包网页版：常驻线程 + 提问 + 解析「答案=X」            │
│ fontdecode.py   字体加密还原（cmap 反查）                              │
├──────────────────────────── 入口 ───────────────────────────────────────┤
│ cli.py          命令行子命令：login / ai / courses / run / probe / bank │
│ run.py          命令行入口                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

## 一次完整运行的数据流

1. **启动** → 读 config.json → 建 Session（Edge 持久化上下文，profile 在本地）
2. **判登录**：三路取证——课程接口返回里有没有用户信息、cookie 里有没有 _uid、当前页面是不是个人空间
3. **课程列表** → 用户选一门（或命令行 --index）
4. **章节树**：进入 stucoursemiddle 页，解析每个小节的标题、chapterId、是否解锁（tip 文案）、已完成任务点数
5. **主循环**：
   - pick_next()：看本地 progress 记录 → 跳过 done → 挑第一个「未完成且已解锁」
   - do_section()：
     a. 打开小节，读任务点条（视频 / 章节测验 / 还有几个没完成）
     b. 任务点全完成 → 直接跳过
     c. 有视频 → player.watch()：播放、保活、盯弹题、91% 问一次任务点、96% 再问
     d. 视频达标（或被判 timeout/stuck）→ 切「章节测验」标签 → exam.answer_all()
     e. 交完 → 读分 → 判定 ≥80% → 找重做入口
6. **记账**：progress.mark()、runstate.save()（上次跑到哪）、runstate.add_section()（刷课记录）
7. **收尾**：总结完成后小节数 / 失败数，界面弹小结

## 本地状态文件（都在 state/ 下，不进版本库）

| 文件 | 内容 |
| --- | --- |
| progress.json | 每节做到哪一步：done / partial / failed + attempts + 备注 + 时间 |
| run_state.json | 上次跑到哪个任务点、总任务点进度、时间（界面那行「上次跑到：…」） |
| run_history.json | 刷课记录：每节的视频结果、答题分数、评级（优秀/及格/不及格），留最近 300 条 |
| bank.sqlite | 本地题库（题干指纹 → 答案），跨课程复用 |
| shots/ | 答题截图、没过线时的批阅页 HTML dump（查错用） |
| browser_profile/ | Edge 的持久化 profile（登录态就在里面，绝不外传） |
| chat_profile/ | 豆包的持久化 profile |

## 为什么这么分

- **界面与业务分开**：业务在后台线程跑，界面只从队列取消息刷新，避免 Tk 卡死。
- **AI 单独一条线程**：Playwright 的 sync API 在一个线程里只能有一套；主线程已经有一套学习通的浏览器，再开第二套会抛「using Playwright Sync API inside the asyncio loop」。所以 AI 浏览器那条线程自己 `with sync_playwright() as pw:` 包住整个生命周期，其它线程通过队列 + Event 让它代跑。
- **状态落盘而非只在内存**：随时关窗口都不丢进度；重开就从「上次跑到哪」接着来。
