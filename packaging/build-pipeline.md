# 加密 · 打包 · 安装 的管线

目标：发出去的 exe 里**没有明文 .py**，同学生双击安装包就能用。

## 为什么不能直接「PyInstaller 一把梭」

PyInstaller 在分析（analysis）阶段靠读 .py 的 import 语句决定收哪些依赖。加密后的字节码它读不懂，于是 sqlite3 / numpy / fontTools / playwright 全收不到 —— 运行到一半就 `ModuleNotFoundError`。

所以拆成两件事：

| 谁 | 干什么 |
| --- | --- |
| PyArmor | 把 app.py + 业务包加密成 `app_src/`（字节码 + pyarmor_runtime） |
| 依赖登记表 `deps.py` | 一次性 import 所有第三方/标准库模块，让 PyInstaller 把它们收进来 |
| `launcher.py` | 启动时把 `app_src` 挂到 `sys.path`，再 `import app; app.main()` |
| PyInstaller | 把 `app_src` 与 `assets` 当**数据**塞进 exe |

## 管线（简化版）

```
1) 复制：app.py + 业务包 -> build_enc/src
2) 加密：pyarmor gen -O build_enc/obf -r build_enc/src/app.py build_enc/src/<pkg>
3) 封装：pyinstaller --windowed --name 玄眼奇工 \
            --add-data "build_enc/obf;app_src" \
            --add-data "assets;assets" \
            --collect-all playwright \
            --paths pack pack/launcher.py
4) 清理：删掉 build_enc/src 与 build_enc/obf（明文不留盘）
5) 打安装器：pyinstaller --onefile --windowed --add-data "dist/玄眼奇工;payload" pack/installer.py
```

## 两个必须知道的限制

1. **单文件体积上限**：PyArmor 试用版对**单个 .py** 有大小限制（实测 ~33.5KB 通过、41KB 报 `out of license`）。所以界面被拆成 `app.py` / `app_ui.py` / `app_hist.py` / `wizard.py` 四块。
2. **新加第三方库要登记**：只要加密代码里 import 了新库，就必须往 `deps.py` 加一行，否则打包后运行时找不到。

## 安装器做了什么

- 复制 payload 到 `%LOCALAPPDATA%\玄眼奇工`（不需要管理员）；
- 桌面 + 开始菜单建 `.lnk`（PowerShell `WScript.Shell`）；
- 生成 `卸载 玄眼奇工.bat`，并写 HKCU 的 Uninstall 注册表项（控制面板可见）；
- **升级时保留已存在的 config.json**（用户设置不丢）；
- 登录态不随安装走：它在 `%LOCALAPPDATA%\LearnAuto` 里，重装不丢、换机器要重登。

## 半开源的处理

这个仓库**不含**上述任何构建产物：没有 `app_src/`、没有 exe、没有安装包，也没有原始业务模块。只有这份说明。
