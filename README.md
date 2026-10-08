# 超星学习通自动刷课 · Python 版

基于 Python 的超星学习通（Chaoxing）课程任务点自动完成工具，命令行交互。支持登录、拉取课程列表、遍历章节树，并自动完成章节内的 **视频** 与 **PPT/文档** 任务点，提供「同步顺序完成」和「异步并发完成」两种模式。

> ⚠️ 本项目仅供学习交流与自动化技术研讨。刷课可能违反所在平台的服务协议与课程要求，账号风险（风控、成绩无效、封禁）由使用者自行承担，请勿用于正式课业作弊。

## 功能特性

| 能力 | 状态 | 说明 |
|------|------|------|
| 手机号 + 密码登录 | ✅ | 账号密码经 AES-CBC 加密后提交 |
| 课程列表 / 章节树 | ✅ | 解析课程、章节、任务点及其完成状态 |
| 视频任务点 | ✅ | 获取 `dtoken` 后循环上报播放进度，直到 `isPassed: true` |
| PPT / 文档任务点 | ✅ | 读取附件 `jtoken` 后调用文档完成接口 |
| 异步并发刷课 | ✅ | `asyncio` + 信号量（上限 200），一次刷完整门课 |
| 同步顺序刷课 | ✅ | 逐任务点执行，带 `tqdm` 进度条，便于逐个确认 |
| 中途取消 | ✅ | 刷课过程中按 <kbd>R</kbd> 停止（仅 Windows，依赖 `msvcrt`） |
| 作业 / 试题 / 考试 | ❌ | **尚未实现**，见 [开发计划](#开发计划) |

## 环境要求

- Python 3.10+（开发与验证环境：**3.13.12，Windows x64**）
- 依赖清单见 [`requirements.txt`](requirements.txt)，版本已锁定

| 依赖 | 版本 | 用途 |
|------|------|------|
| `requests` | 2.34.2 | 同步 HTTP + Session/Cookie 维持登录态 |
| `aiohttp` | 3.14.4 | 异步并发上报 |
| `beautifulsoup4` | 4.15.0 | 解析课程列表 / 章节 / 知识卡片 HTML |
| `lxml` | 6.1.3 | BeautifulSoup 解析后端 |
| `cryptography` | 50.0.2 | 登录密码 AES-CBC 加密 |
| `colorama` | 0.4.6 | 终端彩色输出 |
| `tqdm` | 4.70.1 | 同步模式进度条 |

## 安装

本目录即仓库根，直接在这里建虚拟环境：

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

装完自检一行，确认解释器与依赖对得上：

```powershell
.venv\Scripts\python -c "import aiohttp, cryptography; print('deps OK')"
```

`.venv/`、`__pycache__/`、`.idea/` 已在 [`.gitignore`](.gitignore) 中排除，不会被提交。

如果用 PyCharm，把解释器指到 `.venv\Scripts\python.exe`。**注意新建的 venv 是隔离环境**（`include-system-site-packages = false`），不会继承系统 Python 里已装的包，漏装时运行会报 `ModuleNotFoundError: No module named 'cryptography'`。

## 快速开始

```bash
.venv\Scripts\python run.py
```

> 入口脚本使用包内相对导入。若在 IDE 里直接运行单个文件报 `ImportError: attempted relative import with no known parent package`，请改为在项目上级目录执行 `python py/run.py`，或把 `run.py` 配置为运行入口。

按提示输入手机号与密码，登录成功后进入课程菜单：

| 输入 | 作用 |
|------|------|
| 课程编号 | 进入该课程的章节界面 |
| `0`（或直接回车） | 打印当前用户 cookie |
| `-1` | 退出程序 |

进入课程后：

| 输入 | 作用 |
|------|------|
| `1` | **一键异步**完成所有任务点（并发同时刷，速度快） |
| `2` | **逐步同步**完成所有任务点（顺序刷，便于确认） |
| `0` | 打印章节信息 |
| `-2` | 重新获取章节信息 |
| `r` | 退出当前课程 |

刷课过程中随时按 <kbd>R</kbd> 取消当前（同步模式取消当前任务，异步模式停止全部任务）。

## 项目结构

```
.
├── run.py             程序入口，处理包导入路径
├── main.py            CLI 交互主循环（两级菜单）
├── api.py             登录、用户信息、课程列表、章节详情、附件提取
├── task.py            同步 / 异步完成任务点（视频 + PPT），取消机制
├── encode.py          AES-CBC 加密、Cookie 解析、视频 enc 签名
├── config.py          API 端点 URL、AES 密钥、通用请求头
├── requirements.txt   pip 依赖清单（版本锁定）
└── AGENTS.md          详细设计文档（数据结构、函数清单、API 速查）
```

模块依赖方向：`run.py → main.py → {api.py, task.py} → {encode.py, config.py}`，`task.py` 另依赖 `api.extract_attachments()`。

## 工作原理

一次完整刷课的调用链（细节见 `AGENTS.md` 第 8 节）：

1. **登录** — `POST /fanyalogin`，`uname`/`password` 为 AES-CBC 密文（key 同时作 IV），成功后 Session 持有登录 cookie。
2. **课程列表** — `POST /mooc-ans/visit/courselistdata`，解析出每门课的 `courseid` / `clazzid` / `cpi`。
3. **章节树** — `GET /mooc2-ans/mycourse/studentcourse` 取章节与页面 `enc`，再对每个 `knowledgeid` 调 `GET studentstudyAjax` 得到该章节的任务点数量 N。
4. **任务附件** — 对每个任务点 `GET /mooc-ans/knowledge/cards?num=0..N-1`，从响应里正则提取 `mArg = {...}` 或 `"attachments":[...]`。
5. **分流完成**
   - 附件含 `jtoken` → `GET /mooc-ans/job/document` → PPT/文档任务点完成；
   - 附件含 `objectId` → `GET /ananas/status/{objectId}` 取 `dtoken` → 循环 `GET /mooc-ans/multimedia/log/a/{cpi}/{dtoken}` 上报进度。
6. **进度上报** — 每次上报都带 `enc = MD5("[clazzId][userid][jobid][objectId][playingTime*1000][SECRET][attDuration*1000][clipTime]")`，步长为 30~60 秒随机，直到响应出现 `"isPassed":true`。

关键约束（改动前务必读）：

- `otherInfo` **不能** 做 URL 编码，其内部自带的 `&courseId=` 会被编码破坏，导致进度上报 403。
- `AES_KEY` 与 `enc` 的 `SECRET` 是协议固定值，不可修改；`enc` 被篡改会导致上报失败。
- 请求参数与 URL 严格对照官方接口，不要随意增删。

## 故障排查

| 现象 | 原因与处理 |
|------|------------|
| `ModuleNotFoundError: cryptography` | venv 未装依赖，执行 `.venv\Scripts\python -m pip install -r requirements.txt` |
| `ImportError: attempted relative import ...` | 未按包方式启动，改用 `python run.py` 或从上级目录 `python py/run.py` |
| 登录返回 `"status":false` | 账号密码错误、需要验证码，或 cookie 已过期（重新登录） |
| `ananas/status` 返回 403 | 请求 cookie / `Referer` 不完整，或登录态失效；先重进课程 |
| 进度上报 403 | 检查 `otherInfo` 是否被 `encodeURIComponent` / `quote` 编码过 |
| 一直不出现 `isPassed:true` | 上报步长过大或平台风控，稍后重试；可改用同步模式逐个确认 |
| 按 R 无反应 | 取消依赖 `msvcrt`，仅 Windows 有效；非 Windows 请重启进程 |
| 章节解析异常 | 学习通改版导致 HTML 结构变化，需更新 `api.py` 的选择器与正则 |

任务点解析内部大量使用 `try/except` 兜底，失败时只输出「没能完成」而不会抛出堆栈。调试时可临时在 `task.py` 的 `except Exception` 分支打印异常类型与信息。

## 开发约定

- 被调用的函数与类需要 Google-style docstring（`Args` / `Returns`）
- 模块间统一使用相对导入；模块级只导入实际使用的符号
- 新增 API 端点常量一律放进 `config.py`
- 新增或升级依赖必须同步写进 `requirements.txt` 并锁定版本（`==`）
- 刷课接口的参数与 URL 不得凭猜测修改，需对照真实抓包
- 仓库内只放占位符：真实抓包（`cpi` / `userid` / `clazzid` / `courseid` / `dtoken` / `jtoken` / `enc` / `JSESSIONID`）以及一级菜单 `0` 打印出的 cookie，一律不得提交或贴到 issue

## 开发计划

- [ ] **作业 / 试题任务点**（当前完全未覆盖：附件既无 `jtoken` 也无 `objectId` 时会被静默跳过）
  - 题目解析：题型识别 + 选项 `id → A/B/C/D` 映射
  - 答案来源可插拔：终端手动作答 → 大模型作答
  - 提交与次数限制处理
- [ ] 附件类型显式分流，合并同步 / 异步之间重复的协议构造代码
- [ ] 异常与失败原因可见化，替换当前的静默 `except`
- [ ] 跨平台取消机制（不依赖 `msvcrt`）
- [ ] 多课程并行处理

## 许可与免责声明

仓库暂未附加许可证。代码为逆向学习通公开接口所得的非官方实现，与超星无关；接口可能随时变更，也可能触发平台风控，请在自己的账号上谨慎试用并遵守平台条款。