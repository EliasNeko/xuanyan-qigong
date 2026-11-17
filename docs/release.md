# 发版流程

每个版本都走同一套动作，保证「所有版本都留在仓库里、都能追溯」。

## 1. 改版本号

- `app.py` 顶部 `APP_VER`（界面右下角显示）
- `pack/installer.py` 的 `APP_VER`（安装器窗口）
- `README.md` 版本表

## 2. 写更新说明

在 `CHANGELOG.md` 顶部追加一节（新版本在最上面）：

```markdown
## [v1.1.0] - 2026-12-01
### 新增
- …
### 修复
- …
### 变化
- …
```

同时在 `docs/versions/v1.1.0.md` 写一份展开版（背景、改动点、验证方式、已知问题）。

## 3. 提交与打标签

```powershell
git add -A
git commit -m "v1.1.0: 一句话主题"
git tag -a v1.1.0 -m "v1.1.0 一句话主题"
git push origin main --tags
```

## 4. Release 自动生成

推送 tag 后，`.github/workflows/release.yml` 会：

1. 读出该 tag；
2. 从 `CHANGELOG.md` 里抽出「## [vX.Y.Z]」这一节当 Release 正文；
3. 建一个 GitHub Release（标题带版本号，正文就是更新说明）。

也可以手动：仓库 → Releases → Draft a new release → 选 tag → 粘贴 `docs/versions/vX.Y.Z.md` 的内容。

## 5. 版本号怎么定

| 变化 | 涨哪一位 | 例子 |
| --- | --- | --- |
| 学习通改版、适配新页面 | 次 | v1.0.0 → v1.1.0 |
| 新能力（比如多课程排队） | 次 | v1.1.0 → v1.2.0 |
| 修 bug、调文案、改样式 | 修 | v1.0.0 → v1.0.1 |
| 架构重写、配置不兼容 | 主 | v1.x → v2.0.0 |

## 6. 历史版本怎么保留

- `CHANGELOG.md` 只追加不删；
- 每个版本一个 git tag（`git tag -l` 能列全）；
- `docs/versions/` 里一版一个文件；
- Release 页面天然按版本存档。

三条腿互相印证：想看「哪版改了什么」看 CHANGELOG，想看「为什么改」看 versions，想看「代码那一版长什么样」checkout 那个 tag。
