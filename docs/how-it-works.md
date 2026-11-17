# 关键机制拆解

这一篇讲「为什么这么写」——踩过哪些坑、最后靠哪个信号判定。所有选择器都是实测得到的学习通页面结构。

## 断点续跑：先问服务端「这节做完了没」

章节树里每个小节都挂着自己的未完成任务点数（`input.jobUnfinishCount` / `input.knowledgeJobCount` / `.catalog_points_yi`）。刷之前整棵树扫一遍：说 0 个待完成的小节直接跳过，不点开、不重看视频；读不到数字的才退回「点开看一眼任务点图标」的老办法。扫到的「已完成」还会补记进本地进度，所以换电脑、重装程序都能接着上次的位置跑。

## 1. 登录态判定：三路取证，缺一就重登

只判 URL 会被学习通的「伪登录页」骗，只判 cookie 又会在 profile 过期时误判。

```python
# 伪代码
def is_logged_in(page):
    if probe_api_has_user(page):      # 课程接口返回里带 uid / 用户名
        return True
    if has_uid_cookie(page.context):  # cookie 里有 _uid 且非空
        return True
    return "个人空间" in page.title() or "/base" in page.url
```

课程接口返回不是登录态时是一句「请重新登录」（`{"result":0,"msg":"请重新登录","status":false}`），所以直接看 JSON 里有没有用户信息最省事。

## 2. 章节树：闯关模式与「可学 / 锁定」

学习通的章节列表里，**锁定的小节 onclick 是空的**，标题旁边有一句「需完成之前闯关任务点，该章节才能解锁」。

```
35 个小节（可学 7 / 锁定 28），已完成任务点: 12/66
```

所以「挑哪一节」的规则是：**已解锁 + 本地进度不是 done + 没超过重试上限**。重试上限很关键：`attempts` 到 5 次才放弃，否则一节失败会卡死整个循环。

## 3. 任务点判定：只认学习通自己的图标

小节内容 iframe 里，每个任务点都有 `.ans-job-icon`；**完成的任务点外层 div 多一个 `ans-job-finished` 类**。学习通自己的 JS 也是这么判的（`jQuery(".ans-job-icon").size()` 对比 `.ans-job-finished` 的数量、`!$(model).parent().hasClass("ans-job-finished")`）。

```javascript
// 页面内执行：把任务点条读出来
[...document.querySelectorAll(".ans-job-icon")].map(function (el) {
  var box = el.parentElement;
  return {
    text: (box.innerText || "").slice(0, 80),
    title: box.getAttribute("title") || "",
    icon: el.className,
    finished: /ans-job-finished/.test(box.className),
  };
})
```

日志长这样：

```
本节任务点（2 个）: 视频、章节测验，还有 2 个没完成
视频任务点图标：还没完成（完成条件 观看时长需 ≥ 总时长的 90）
```

**踩过的坑**：一开始想读页面里的 `#_studystate`（`{nextChapterId:…,unfinishCount:1}`），但它只在外层页面存在，在视频卡片 / iframe 里 `fetch` 拿不到，日志只会打印「ok 但无 unfinish」。**结论：判定任务点别看统计数据，看图标。**

## 4. 视频达标：为什么在 91% 就问，而不是等到 100%

任务的完成条件是「观看时长 ≥ 总时长的 90%」。但进度条走到 90% 时服务端往往还没记上（有几秒到几十秒延迟），所以策略是：

1. 到 **91%** 问一次：图标变成 `ans-job-finished` 了吗？
2. 没变 → 等 6 秒再问，最多连续问 3 次；
3. 还没变 → 继续播，到 **96%** 再走一轮同样的问法；
4. 仍没变 → 播到结尾（`ended`）。

命中就立刻 `video.pause()`（穿 shadow DOM 找 video 再 pause），然后切章节测验，不然视频会一直在后台播。

实测数据：18:56 的长视频在 91%（17:15）就拿到「已完成」，提前省掉 1 分半；也遇到过 91% 时没记上、96% 才认的。

## 5. 禁倍速：试一次，读回原速就认

有些课程在播放器里禁了倍速。做法是设完 `video.playbackRate = 1.25` 后**读回**，读回 1.00 就说明被限制：

```
这门课禁止倍速播放（想设 1.25x，播放器读回 1.00x）。
已按原速继续 —— 这是学校的课程设置，脚本不会去绕它。
```

## 6. 弹窗题（弹题）

视频播到中途会弹一道题，不答不算进度。真实 DOM 是这样：

```html
<div class="tkTopic">
  <div class="tkTopic_oper" id="ext-gen1067">
    <a class="ans-videoquiz-submit" id="videoquiz-submit">提交</a>
    <a id="videoquiz-continue">继续</a>
    <span id="spanHas">回答正确</span>
    <span id="spanNot">回答错误</span>
    <span id="spanNotBack">回答错误，回看 N 分钟</span>
  </div>
</div>
```

**踩过的坑（死循环）**：容器 `.tkTopic_oper` 的 innerText 恰好也是「提交」（其它按钮被 CSS 藏着），按文档序取第一个「提交」就会点到容器，等于没点，于是每 1.3 秒重复交一次、视频永远不动。

修法是「提交按钮选择器打分选优」：

- 只认 `a / button / input`（+10 分）；
- id / class 里含 submit / 提交 / continue 再加分；
- 后代里还有别的按钮文字的元素直接排除（那是容器）；
- `div / span` 必须带 onclick 或 btn 类名才算。

点完提交还要**等判分**再点「继续」，否则弹窗不消失。做得成 `finish()`：轮询 `.boxOpen` 是否消失，超时兜底按 Esc。

## 7. 章节测验页：三种形态，必须先认清

| 形态 | URL 特征 | 现象 | 处理 |
| --- | --- | --- | --- |
| 待完成 | `work/doHomeWorkNew` | 正文有「待完成」「题量: 4」 | 正常作答 |
| 已批阅 | `work/selectWorkQuestionYiPiYue` | 「已完成」「本次成绩 0 分」「我的答案：」，**没有 radio、选项不可点** | 记 reviewed，查重做入口，没有就跳过 |
| 已交过但没批阅 | 同待完成 | 能填、能交 | 正常作答 |

不区分的话，脚本会把批阅页当新题去点，自检 0/2 选中 → 拒交 → 下一轮又挑同一节 → 死循环。

## 8. 选项怎么点：没有 radio，是 li + 隐藏域

新版学习通的选项不是 input[type=radio]：

```html
<li class="font-cxsecret before-after" onclick="addChoice(this);" qid="211740917" qtype="0" role="radio">
  <label class="fl before" data-la-qo="0_1">
    <span class="num_option choice211740917" name="answer211740917" data="B">B</span>
  </label>
  <a class="fl after">光线</a>
</li>
<input type="hidden" name="answer211740917" id="answer211740917" value="">
```

点 label / li 有效：**隐藏域的 value 被写成 "B"**，选项 span 上多一个 `check_answer` 类。

所以「自检」不能查 `:checked`，要查隐藏域：

```javascript
// 每题：把 hidden[name^=answer] 建成 qid -> 字母 表
var filled = {};
for (el of document.querySelectorAll("input[type=hidden][name^=answer]")) {
  var qid = el.name.replace("answer", "");
  filled[qid] = el.value;   // "B" 或判断题的 "true"
}
```

实测输出：`{"boxes":14,"sel":{"0":1,"1":1,"2":1,"3":1},"filled":{"211740917":"A",…}}` —— 4 题全选上才允许提交。

## 9. 字体加密：font-cxsecret 的 cmap 反查

题干和选项里的字会被换成生僻字（「空间」→「空问」这种是解码后的错字，「空」本身被换成 `宄`）。页面上挂着 5 个 @font-face，**只有 `font-cxsecret`（data:base64 的 ttf）是真的加密字体**，其它（icomoon / marking / din / 兰亭黑）解出来全是错的。

还原逻辑：

1. 收全页面上所有 @font-face 候选，逐个下载 ttf；
2. 用 fontTools 读 cmap，得到「这份字体认领了哪些码位」；
3. 用题面里的汉字算命中数 `hits`；
4. 按（family 名含 cxsecret / secret，hits，cmap 大小）排序取最优；
5. **只还原字体认领过的码位** —— 没被劫持的字（「从诺阿」）在这份字体里没有字形，硬凑会被解成 `冈`。

```python
# 核心判据（片段）
def decode_chars(text, ttf_bytes):
    names = glyph_names(ttf_bytes)        # cmap: code -> glyph name
    out = []
    for ch in text:
        if ord(ch) not in names:          # 没被这份字体认领 -> 原样保留
            out.append(ch)
            continue
        out.append(reverse_lookup(ord(ch)))
    return "".join(out)
```

实测还原率 20/61 ～ 25/67，剩下的错字交给 AI 容错（提示词里明确写「可能有一两个字是乱码，按最接近的意思理解」）。

## 10. 答案从哪来：数据库 → 豆包 → 兜底（但兜底会被拦）

- **本地题库**（SQLite）：题干指纹 → 答案，跨课程复用；
- **豆包网页版**：把题干和选项按固定格式发过去，要求「只回一行 `答案=B`」，多选回 `答案=ABD`，判断题回 `答案=对` / `答案=错`；
- **兜底**：题库和 AI 都没答案时按 `quiz.fallback` 选（first / random），但每道题会标记「（没有把握，是蒙的）」，**蒙题比例超过 `max_guess_percent`（默认 50%）就不提交**。

为什么不用搜索引擎：实测连续搜 5 题全部撞上滑块验证码（HIT 0/5），这条路不可用。

豆包这条链的关键实现细节：

- **同一条线程**跑 Playwright（sync API 不能在两个线程各开一套）；
- 发问时逐行 `type` + 行间 `Shift+Enter`，否则换行会被当成「发送」，题目只发了第一行；
- 取答案时先拍「发送前正文快照」，只解析**新增的那一段**，再用提问结尾 20 字当锚点切，避免把「展开全部」「推荐问题」当答案；
- 解析按 `答案[:：=＝]\s*([A-Ja-j]{1,6})` 取最后一处（前面那处是回显），判断题单独判「对/错」。

## 11. 提交与 80 分线

提交前做三道闸：

1. `answered == 0` → 不交（否则 0 分永久记录）；
2. 自检有题没选上 → 不交；
3. 蒙的题超过 50% → 不交。

交完读分（`本次成绩 50.0 分`），`pass_percent` 默认 80。没过线时**不自动点重做**（重做会覆盖记录），只把分数和「有没有重做入口」报出来。

## 12. 断点续跑

三份状态各管一件事：`progress.json` 管「这节做完没」、`run_state.json` 管「上次跑到哪、总进度多少」、`run_history.json` 管「每节的结果和评级」。关窗口不会丢；重开从上次那节接着来。

## 13. 界面为什么在 2026 年被重做了一遍

原来是最朴素的 ttk 表单，用户的要求是「有二次元感、背景图要看得清、字看不清楚就放大」。最后：

- 背景是一张插画，按窗口比例 `cover` 裁切，再从偏上 1/3 处取景；
- 所有卡片是 Pillow 画的半透明磨砂片（圆角 + 白描边 + 粉色外发光 + 顶部高光），不是纯色底；
- 按钮是 AI 生成的素材图（花瓣 / 蝴蝶结），按三段式横向拉伸保持两端不变形，文字由 Pillow 烘焙到图上；
- 每个库/标准库都登记在 deps 清单里，因为加密后的代码对 PyInstaller 不透明；
