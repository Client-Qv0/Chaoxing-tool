# 超星学习通辅助工具python版本 

## 1. 项目概述

本项目是一个基于 Python 的命令行工具，用于自动完成**超星学习通**（Chaoxing）平台上的课程任务点，包括视频播放和 PPT/文档浏览。支持两种刷课模式：**同步逐步完成**和**异步并发完成**。

登录后先进入**模式选择**：`1` 刷课模式（现有完整流程），`2` 刷题模式（当前仅为菜单骨架，作业流程待开发）。

### 技术栈与依赖

依赖版本已在 `requirements.txt` 中锁定，实际验证环境为 **Python 3.13.12 / Windows x64**。

| 组件 | 锁定版本 | 用途 |
|------|----------|------|
| `requests` | 2.34.2 | 同步 HTTP + `Session` 维持登录 Cookie |
| `aiohttp` | 3.14.4 | 异步并发刷课（`task.finish_task_async`） |
| `BeautifulSoup` | 4.15.0 | HTML 解析（课程列表、章节结构、知识卡片） |
| `lxml` | 6.1.3 | BeautifulSoup 的解析后端 |
| `cryptography` | 50.0.2 | AES-CBC 加密（登录时加密手机号/密码） |
| `colorama` | 0.4.6 | 终端彩色输出 |
| `tqdm` | 4.70.1 | 同步模式进度条 |
| `asyncio` | 标准库 | 异步并发控制（信号量上限 200） |

### 环境搭建

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

自检与运行（在本目录执行）：

```powershell
.venv\Scripts\python -c "import aiohttp, cryptography; print('deps OK')"
.venv\Scripts\python run.py
```

> venv 是隔离环境（`include-system-site-packages = false`），不会继承系统 Python 已装的包。若 `.venv\Lib\site-packages` 内只有 pip，运行会报 `ModuleNotFoundError: No module named 'cryptography'`，先执行上面的安装命令。`.venv/`、`__pycache__/`、`.idea/` 已在 `.gitignore` 中排除。

---

## 2. 项目结构

```
./
  run.py             ← 程序入口，执行 `python ./run.py` 启动
  __init__.py
  requirements.txt   ← pip 依赖清单（版本已锁定）
  .gitignore         ← 排除 .venv / __pycache__ / .idea
  main.py            ← CLI 交互主循环
  api.py             ← 登录、课程列表、章节详情、附件提取
  task.py            ← 同步/异步刷视频 + PPT，支持按 R 取消
  encode.py          ← AES 加密、enc 签名、Cookie 解析
  config.py          ← API 端点 URL、AES 密钥常量
  settings.py        ← .env 读写：LLM base_url / model / api_key（含掩码与清除）
  .env               ← 实际配置，明文存储，已被 .gitignore 排除
  .env.example       ← 配置模板，入库
  quiz/
    task.py          ← 刷题模式菜单骨架（0 设置 / 1 章节作业 / 2 流动作业 / r 清除）
```

### 文件关系与依赖

```
./run.py
  └── from .main import main

./main.py
  ├── from .api import login, get_user_info, get_courses_info,
  │                   show_courses_detail, get_course_detail, print_course_info
  ├── from .task import finish_task_sync, finish_all_tasks_async
  └── 调用关系:
        main() → login() → get_user_info() → get_courses_info()
              → show_courses_detail()  (循环)
              → get_course_detail() → print_course_info()
              → finish_all_tasks_async()  或  finish_task_sync()

./api.py
  ├── from .encode import encrypt_by_AES
  ├── from .config import LOGIN_URL, SPACE_URL, COURSE_LIST_URL, ...
  └── 提供: login, get_user_info, get_courses_info, show_courses_detail,
            get_course_detail, print_course_info, extract_attachments

./task.py
  ├── from .api import extract_attachments
  ├── from .encode import generate_enc
  ├── from .config import KNOWLEDGE_CARDS_URL, DOCUMENT_FINISH_URL, ...
  └── 提供: finish_task_sync, finish_task_async, finish_all_tasks_async

./encode.py
  └── 提供: encrypt_by_AES, parse_cookiejar_to_dict, generate_enc

./config.py
  └── 提供: 所有 API URL 常量、AES_KEY、COMMON_HEADERS

./settings.py
  └── 提供: load_settings, save_settings, delete_settings, prompt_settings,
            settings_summary, parse_env_file, write_env_file, mask_secret

./quiz/task.py
  ├── from .. import settings
  └── 提供: run_quiz_mode（刷题菜单循环，返回后回到模式菜单）
```

---

## 3. 关键数据结构

以下是在各模块间流转的核心对象定义。

### 3.1 课程对象 `course`

由 `get_courses_info()` 返回的列表中每个元素：

```
course = {
    "course_params": {          # 传入 get_course_detail() 的参数
        "courseid":  str,       #   课程 ID
        "clazzid":   str,       #   班级 ID
        "cpi":       str,       #   用户个人 ID
        "ut":        "s",       #   固定值
        "t":         float,     #   时间戳 (time.time()*1000)
    },
    "course_name":    str,      # 课程名称，如 "示例课程"
    "course_teacher": [         # <p.line2> BeautifulSoup 对象列表
        <p.line2>, ...
    ],
    "course_url":     str,      # 课程链接
}
```

### 3.2 课程详情 `last_course_info`

由 `get_course_detail()` 返回，也是 `task.py` / `main.py` 共享的全局结构：

```
last_course_info = {
    "title":  str,                          # 课程名称
    "enc":    str,                          # 课程 enc 加密标识 (来自页面 <input id="enc">)
    "status": str,                          # 完成状态文字 (来自页面 <h2 class="xs_head_name">)
    "chapter": [                            # 章节列表
        {
            "name":   str,                  #   章节名，如 "第一章 概述"
            "course": [                     #   节内任务列表
                {
                    "params": [             #   该任务的所有子任务参数列表 (长度 = studentstudyAjax 返回的 li 数量)
                        {
                            "clazzid":     str,
                            "courseid":    str,
                            "knowledgeid": str,    # 知识点 ID (来自 id="curXXXX")
                            "num":         int,    # 子任务序号 0/1/2/...
                            "ut":          "s",
                            "cpi":         str,
                            "mooc2":       "1",
                            "isMicroCourse":"false",
                            "editorPreview":"0",
                        },
                        ...
                    ],
                    "knowledgeid": str,     #   (同 params[0].knowledgeid)
                    "name":        str,     #   任务名，如 "视频 概述"
                    "status":      str,     #   任务完成状态，如 "1个待完成任务点"
                },
                ...
            ],
        },
        ...
    ],
}
```

### 3.3 任务参数 `base_params`

传入 `finish_task_sync()` 和 `finish_task_async()` 的单个子任务参数，取自 `last_course_info.chapter[].course[].params[]`：

```
base_params = {
    "clazzid":     str,
    "courseid":    str,
    "knowledgeid": str,
    "num":         int,     # 子任务序号
    "ut":          "s",
    "cpi":         str,
}
```

### 3.4 附件对象 `attachment`

`extract_attachments()` 从 `knowledge/cards` 响应中提取，返回列表。每个元素可能包含：

```
attachment = {

    # ---- 所有任务共有 ----
    "jobid":               str,          # 任务 job ID

    # ---- PPT/文档任务特有 (以此判断) ----
    "jtoken":              str,          # PPT 完成令牌
    "enc":                 str,          # (保留，PPT 完成请求不发送)

    # ---- 视频任务特有 (以此判断) ----
    "objectId":            str,          # 视频对象 ID
    "otherInfo":           str,          # 附加信息
    "attDuration":         int,          # 视频总时长（秒）
    "attDurationEnc":      str,          # 时长加密值
    "videoFaceCaptureEnc": str,          # 人脸抓拍加密值（可为空字符串）
}
```

判断规则（与 Python 源码一致）：
- `try: jtoken = attachment['jtoken']`  成功 → PPT/文档任务
- `except KeyError` → 检查 `objectId` 存在 → 视频任务

### 3.5 视频上报参数 `finish_params`

由 `generate_enc()` 生成 enc 后拼装，每次视频进度上报时构造：

```
finish_params = {
    "clazzId":              str,      # 班级 ID
    "playingTime":          str,      # 当前播放时长（秒）
    "duration":             int,      # 视频总时长（秒）
    "clipTime":             str,      # "0_{duration}"
    "objectId":             str,      # 视频对象 ID
    "courseId":             str,      # 课程 ID
    "jobid":                str,      # 任务 job ID
    "userid":               str,      # 用户 ID (从 knowledge/cards 响应提取)
    "isdrag":               "0",
    "view":                 "pc",
    "rt":                   "0.9",
    "videoFaceCaptureEnc":  str,
    "dtype":                "Video",
    "attDuration":          int,
    "attDurationEnc":       str,
    "enc":                  str,      # MD5 签名 (每次上报重新计算)
    "courseEngineInfo":     "false",
    "_t":                   int,      # 时间戳 (int(time.time()*1000))
}
```

---

## 4. 模块与函数详解

### 4.1 `./config.py` — 常量配置 (26行)

| 常量 | 值 |
|------|-----|
| `LOGIN_URL` | `'https://passport2.chaoxing.com/fanyalogin'` |
| `SPACE_URL` | `'https://i.mooc.chaoxing.com/space/index'` |
| `COURSE_LIST_URL` | `'https://mooc1-1.chaoxing.com/mooc-ans/visit/courselistdata'` |
| `COURSE_DETAIL_URL` | `'https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/studentcourse'` |
| `STUDY_AJAX_URL` | `'https://mooc1.chaoxing.com/mooc-ans/mycourse/studentstudyAjax'` |
| `KNOWLEDGE_CARDS_URL` | `'https://mooc1.chaoxing.com/mooc-ans/knowledge/cards'` |
| `DOCUMENT_FINISH_URL` | `'https://mooc1.chaoxing.com/mooc-ans/job/document'` |
| `VIDEO_STATUS_URL` | `'https://mooc1.chaoxing.com/ananas/status/{objectid}'` |
| `VIDEO_LOG_URL` | `'https://mooc1.chaoxing.com/mooc-ans/multimedia/log/a/{cpi}/{dtoken}'` |
| `AES_KEY` | `'u2oh6Vu^HWe4_AES'` — 登录 AES 加密密钥 |

---

### 4.2 `./encode.py` — 加密签名模块 (82行)

**`encrypt_by_AES(message: str, key: str) -> str`**

> 使用 AES-CBC 对明文加密（key 同时作为 IV），PKCS7 填充，结果经 Base64 编码返回。**仅用于登录时加密手机号和密码**。

**`parse_cookiejar_to_dict(cookiejar_str: str) -> dict[str, str]`**

> 解析 `requests.Session.cookies` 的字符串表示，提取为 `{name: value}` 字典（当前版本未直接使用，保留备用）。

**`generate_enc(clazzId, userid, jobid, objectId, playTime, attDuration, clipTime) -> str`**

> 生成视频播放进度上报所需的 **enc 签名**（32 位小写 MD5）。
> 
> 拼接公式：
> ```
> data = f"[{clazzId}][{userid}][{jobid}][{objectId}][{playTime * 1000}][{SECRET}][{attDuration * 1000}][{clipTime}]"
> enc  = hashlib.md5(data).hexdigest()
> ```
> `SECRET = "d_yHJ!$pdA~5"`

---

### 4.3 `./api.py` — API 交互模块 (401行)

#### 4.3.1 `login(session: requests.Session) -> bool`

> `input()` 获取手机号+密码 → `encrypt_by_AES()` 加密 → POST 登录接口 → 成功后 session 自动保存 Cookie。

**请求：**

```
POST LOGIN_URL   (= https://passport2.chaoxing.com/fanyalogin)

Cookies:  (代码实际发送空字典 login_cookies = {}，见 api.py:36；下列仅为登录页可能出现的会话类 cookie，值已全部脱敏为占位符)
  route=<32位hex>
  retainlogin=2
  JSESSIONID=<容器会话ID>
  fanyamoocs=<16位hex>

Headers:
  Content-Type: application/x-www-form-urlencoded; charset=UTF-8
  Origin: https://passport2.chaoxing.com
  Referer: https://passport2.chaoxing.com/login?fid=<单位fid>&refer=...&space=2

Data:                                   # Python 代码中的 login_data
  fid                = '-1'
  uname              = encrypt_by_AES(手机号, AES_KEY)
  password           = encrypt_by_AES(密码, AES_KEY)
  refer              = 'http%3A%2F%2Fi.mooc.chaoxing.com'        # 与 api.py:59 实际发送值一致
  t                  = 'true'
  forbidotherlogin   = '0'
  validate           = ''
  doubleFactorLogin  = '0'
  independentId      = '0'
  independentNameId  = '0'
```

**返回值：** `True`（响应含 `"status":true`）/ `False`（登录失败，循环重输）

---

#### 4.3.2 `get_user_info(session: requests.Session) -> None`

> 获取并打印当前登录用户的姓名。

**请求：**

```
GET SPACE_URL?ws=1&t={time.time()*1000}     (= https://i.mooc.chaoxing.com/space/index?ws=1&t={...})

Headers:  (session 自动携带登录 Cookie)
  Accept: text/html,application/xhtml+xml,...
  Upgrade-Insecure-Requests: 1
```

**输出：** 打印 `状态码:{resp.status_code}` + `用户名：{p.personalName[title]}`

---

#### 4.3.3 `get_courses_info(session: requests.Session) -> list[dict]`

> 获取当前用户的所有课程列表。

**请求：**

```
POST COURSE_LIST_URL     (= https://mooc1-1.chaoxing.com/mooc-ans/visit/courselistdata)

Headers:
  Content-Type: application/x-www-form-urlencoded; charset=UTF-8
  Origin: https://mooc1-1.chaoxing.com
  Referer: https://mooc2-ans.chaoxing.com/mooc2-ans/visit/interaction?moocDomain=...

Data:                                   # Python 代码中的 course_data
  courseType      = '1'
  courseFolderId  = '0'
  baseEducation   = '0'
  superstarClass  = ''
  courseFolderSize= '0'
```

**返回值：** `list[course]`，结构见 [§3.1](#31-课程对象-course)

---

#### 4.3.4 `show_courses_detail(course_list: list[dict]) -> None`

> 纯本地函数，无 HTTP 请求。用 `colorama` 彩色打印课程列表（编号 + 课程名 + 教师 + URL）。

---

#### 4.3.5 `get_course_detail(session, course_title, params) -> dict`

> 获取指定课程的章节结构。**发出 1 + N 个请求**（N = 章节内 `li` 数量）。

**请求 ① — 获取课程主页面（章节列表）：**

```
GET COURSE_DETAIL_URL?courseid={params['courseid']}&clazzid={params['clazzid']}&cpi={params['cpi']}&ut={params['ut']}&t={params['t']}

Headers:
  referer: https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu
  sec-fetch-dest: iframe
  (session 自动携带登录 Cookie)
```

> 从响应 HTML 中解析：`<input id="enc" value="...">`、`div.chapter_unit` 列表、`h2.xs_head_name`（完成状态文字）。

**请求 ② — 对每个章节的每个 `li > div.chapter_item[id="curXXXX"]` 调用，获取子任务数量（N 次）：**

```
GET STUDY_AJAX_URL?courseId={params['courseid']}&clazzid={params['clazzid']}&chapterId={knowledgeid}&cpi={params['cpi']}&verificationcode=&mooc2=1&toComputer=false&microTopicId=0&editorPreview=0&isPreviewVideo=false&videoWidth=0&videoHeight=0&targetVideoJobId=&cardIndex=0
```

> 从响应 HTML 中解析 `div.prev_list > li` 数量，作为该任务下的子任务数。

**返回值：** `last_course_info` (dict)，结构见 [§3.2](#32-课程详情-last_course_info)

---

#### 4.3.6 `print_course_info(last_course_info: dict) -> None`

> 纯本地函数，无 HTTP 请求。彩色树形打印章节名 + 任务名 + 完成状态。

---

#### 4.3.7 `extract_attachments(response_text: str) -> list[dict]`

> 纯本地函数，无 HTTP 请求。从 `knowledge/cards` API 返回的 HTML 文本中提取附件信息。三种策略按优先级：
>
> 1. 正则匹配 `mArg = ({...});` → `json.loads()` → 取 `.attachments` 列表
> 2. 正则匹配 `"attachments": [{...}]` → 包装为 `{"attachments": [...]}` → `json.loads()`
> 3. 逐字段正则匹配 `jobid` / `objectid` / `otherInfo` / `attDuration` 等（单任务兜底）
>
> **返回值：** `list[attachment]`，结构见 [§3.4](#34-附件对象-attachment)

---

### 4.4 `./task.py` — 任务完成模块 (590行)

#### 4.4.1 辅助函数

| 函数 | 说明 | 是否有 HTTP |
|------|------|:----------:|
| `_is_r_pressed() -> bool` | Windows `msvcrt.kbhit` 非阻塞检测 R 键 | ✗ |
| `_sleep_sync(seconds: float) -> bool` | 每 0.5s 检测 R 键，返回 True=被取消 | ✗ |
| `_sleep_async(seconds, stop_event: asyncio.Event) -> bool` | 异步版，每 0.5s 检测 `stop_event` | ✗ |
| `_keyboard_listener(stop_event)` | 后台协程，`run_in_executor` 监听 R 键 | ✗ |

---

#### 4.4.2 `finish_task_sync(session, base_enc, base_params, course_name, chapter_name, task_name) -> bool`

> 同步完成单个任务点。返回 `True`=成功 / `False`=用户按 R 取消。

**请求 ① — 获取任务附件信息：**

```
GET KNOWLEDGE_CARDS_URL?courseid={base_params['courseid']}&clazzid={base_params['clazzid']}&knowledgeid={base_params['knowledgeid']}&num={base_params['num']}&ut={base_params['ut']}&cpi={base_params['cpi']}&mooc2=1&isMicroCourse=false&editorPreview=0

Headers:
  referer: https://mooc1.chaoxing.com/mycourse/studentstudy?chapterId={base_params['knowledgeid']}&courseId={base_params['courseid']}&clazzid={base_params['clazzid']}&cpi={base_params['cpi']}&enc={base_enc}&mooc2=1&hidetype=0
  sec-fetch-dest: iframe
  (session 自动携带登录 Cookie)
```

> 响应经 `extract_attachments()` 解析 → `list[attachment]`。对每个 attachment 判断类型：

---

**请求 ② — PPT/文档任务（`try: jtoken = attachment['jtoken']` 成功）：**

```
GET DOCUMENT_FINISH_URL?jobid={jobid}&knowledgeid={base_params['knowledgeid']}&courseid={base_params['courseid']}&clazzid={base_params['clazzid']}&jtoken={jtoken}&checkMicroTopic=true&microTopicId=undefined&courseEngineInfo=false&_dc={time.time()*1000}

Headers:
  referer: https://mooc1.chaoxing.com/ananas/modules/pdf/index.html
  x-requested-with: XMLHttpRequest
  sec-fetch-dest: empty
  sec-fetch-mode: cors
```

> 成功 → 打印 `√ PPT 完成`，该 attachment 处理结束。

---

**请求 ③ — 视频任务（`except KeyError` 后检查 `objectId` 存在）：获取 dtoken**

```
GET VIDEO_STATUS_URL?k=1001&flag=normal&ro=0&_dc={time.time()*1000}
     (其中 VIDEO_STATUS_URL = 'https://mooc1.chaoxing.com/ananas/status/{objectid}')

Cookies:  (额外设置，与 session cookie 叠加)
  writenote            = 'yes'
  doubleSpeedValue     = '1'
  thirdRegist          = '0'
  tl                   = '1'
  _industry            = '5'
  {courseid}cpi        = {base_params['cpi']}
  {courseid}ut         = {base_params['ut']}
  {courseid}t          = str(time.time() * 1000)

Headers:
  referer: https://mooc1.chaoxing.com/ananas/modules/video/index.html?
  X-Requested-With: XMLHttpRequest
```

> 从响应提取 `"dtoken":"{dtoken}"` → 构造上报 base_url。

---

**请求 ④ — 视频任务：循环上报播放进度（每 30~60 秒一次）**

```
GET VIDEO_LOG_URL?otherInfo={otherInfo}&clazzId={clazzid}&playingTime={playtime}&duration={v_time}&clipTime=0_{v_time}&objectId={objectid}&courseId={courseid}&jobid={jobid}&userid={userid}&isdrag=0&view=pc&rt=0.9&videoFaceCaptureEnc={videoFaceCaptureEnc}&dtype=Video&attDuration={v_time}&attDurationEnc={attDurationEnc}&enc={enc}&courseEngineInfo=false&_t={int(time.time()*1000)}
     (其中 VIDEO_LOG_URL = 'https://mooc1.chaoxing.com/mooc-ans/multimedia/log/a/{cpi}/{dtoken}')

     参数 enc 每次循环重新计算:
       enc = generate_enc(
           clazzId     = base_params['clazzid'],
           userid      = userid,
           jobid       = jobid,
           objectId    = objectid,
           playTime    = playtime,
           attDuration = v_time,
           clipTime    = f'0_{v_time}',
       )

Headers:
  referer: https://mooc1.chaoxing.com/ananas/modules/video/index.html?
  X-Requested-With: XMLHttpRequest
```

> 循环逻辑（`while True`）：
> 1. 构造 `finish_params`（见 [§3.5](#35-视频上报参数-finish_params)），生成 enc
> 2. `session.get(base_url, params=finish_params, ...)` 上报
> 3. 若响应含 `"isPassed":true` → 打印 `√ 视频完成` → break
> 4. 若 `flag == False`（已到末尾） → break
> 5. `temp = random.randint(30, 60)` 秒递增 `playtime`
> 6. `_sleep_sync(temp)`（同步版用 `tqdm` 进度条 + R 键检测）
> 7. 继续循环

---

#### 4.4.3 `finish_task_async(base_enc, base_params, session_cookies, semaphore, stop_event, course_name, chapter_name, task_name) -> None`

> 异步版，与 `finish_task_sync` 逻辑完全一致，差异仅在于：
> - `aiohttp.ClientSession(cookies=session_cookies)` 替代 `requests.Session`
> - `await asyncio.sleep()` 替代 `time.sleep()`
> - 所有 sleep 调用处改为 `await _sleep_async(seconds, stop_event)`，检测到停止信号立即 return
> - semaphore 入口 + attachment 循环 + while 循环三处增加 `if stop_event.is_set(): return`
>
> **HTTP 请求①②③④ 完全相同，不重复列出。**

---

#### 4.4.4 `finish_all_tasks_async(video_list, base_enc, cookies, course_name) -> None`

> 批量异步入口，本身**不直接发 HTTP 请求**。内部流程：
> 1. 创建 `asyncio.Semaphore(200)` 控制并发上限
> 2. 创建 `asyncio.Event()` 停止信号
> 3. 启动后台协程 `_keyboard_listener(stop_event)`（每 0.5s 通过 `run_in_executor` 检测 R 键），单独保存句柄，**不放进待 gather 的任务列表**
> 4. 遍历 `video_list`（每个元素须含 `parent_chapter` 和 `chapter_name` 字段）：
>    - 取出 `parent_chapter` → `base_chapter_name`
>    - 取出 `chapter_name` → `task_name`
>    - 创建 `delayed_task` 协程：`await asyncio.sleep(delay)` + 检查 `stop_event` + `await finish_task_async(...)`
>    - `delay = random.uniform(0.5, 1.5) * (i + 1)`（递增延迟分散压力）
> 5. `await asyncio.gather(*work_tasks, return_exceptions=True)` **只等待刷课任务**；`finally` 中 `listener.cancel()` 回收监听协程
>    - 监听协程仅在 `stop_event` 置位时自行退出，若与任务一起 gather，全部任务完成后本函数永不返回（表现为刷完课后卡死、回不到主菜单）
>    - `return_exceptions=True` 保证个别任务协程异常时不中断整体等待，其余正在上报的视频不会被事件循环收尾强制取消
>    - 监听协程被取消或自身抛异常（如非交互终端下 `msvcrt` 报 `OSError`）一律吞掉，不影响刷课结果；`KeyboardInterrupt` 不在捕获范围
> 6. 打印结果：`stop_event.is_set()` → `[R] 所有视频任务已取消`；否则 → `0v0 所有视频任务完成！`
> 7. 统计 `results` 中的异常项，非 0 时追加一行 `[!] N 个任务协程异常退出，可重新进入课程重试`

---

### 4.5 `./main.py` — 主入口 (219行)

> 运行 CLI 交互循环，包含三级菜单：模式选择 → 课程列表 → 课程内操作。

#### 零级菜单（模式选择）

```
输入 1 → 刷课模式 (_course_menu)：课程列表 → 章节 → 完成任务点
输入 2 → 刷题模式 (quiz.task.run_quiz_mode)：菜单骨架，1/2 目前只提示「功能待开发」
输入 -1 → 退出程序
```

两个模式退出后都回到这里。

#### 一级菜单（课程列表，刷课模式内）

```
输入课程编号 (1 ~ len(course_list)) → 进入课程主界面
输入 0      → 打印 Cookie (pprint session.cookies.get_dict())
输入 -1     → 退出刷课模式，返回模式选择
```

输入课程编号后，自动调用 `get_course_detail()` 获取章节，然后进入二级菜单。

#### 二级菜单（课程内操作）

```
输入 1  → 一键完成所有任务点（异步并发）
           流程: 从 last_course_info 收集所有子任务 params →
                每个 params 附加 chapter_name / parent_chapter →
                asyncio.run(finish_all_tasks_async(...))

输入 2  → 逐步完成所有任务点（同步顺序）
           流程: 三重循环遍历 chapter → course → params →
                逐个调用 finish_task_sync() →
                返回 False 时 break 全部循环，打印 "[R] 同步刷视频已取消"

输入 -2 → 重新获取章节信息 (key 重置为 -2 → get_course_detail 重新执行)
输入 0  → 打印章节信息 (print_course_info)
输入 r  → 退出当前课程，返回课程列表 (option_key = -2)
```

#### 刷题模式菜单（`./quiz/task.py`，51 行）

```
输入 0  → 设置 base_url / model_name / api_key，写入 .env（回车保留原值）
输入 1  → 课程章节作业 studentstudy → doHomeWorkNew（待开发）
输入 2  → 流动作业 dowork（待开发）
输入 r  → 从 .env 删除本工具保存的三个键并返回模式菜单（进程环境变量仍在时无法清除）
输入 -1 → 返回模式菜单
```

考试类题目不在本工具范围内，不预留入口。

---

## 5. 完整运行流程

### 5.1 启动

```bash
python ./run.py
```

### 5.2 登录阶段

```
┌─────────────────────────────────┐
│  请输入手机号：                  │  ← 终端输入，AES 加密 → POST LOGIN_URL
│  请输入密码：                    │  ← 同上
│  ~~超星学习通登录成功！~~         │
│  状态码: 200                     │
│  用户名：XXX                     │
└─────────────────────────────────┘
```

### 5.3 课程列表界面

```
================================================================================
1.课程1  示例大学  教师A
  https://mooc1-1.chaoxing.com/...
2.课程2  老师2
  https://mooc1-1.chaoxing.com/...
...
================================================================================
输入课程编号，进入课程主界面
输入0 打印用户的cookie
输入-1 退出刷课模式（返回模式选择）
编号>
```

### 5.4 进入课程后的章节界面

```
================================================================================
示例课程
已完成任务点: 0 / 56
第一章 概述
    视频 概述  [1个待完成任务点]
    文档 习题  [0个待完成任务点]
第二章 数据表示
    ...
================================================================================
输入1 一键完成所有任务点(同时完成)
输入2 逐步完成所有任务点(顺序完成)
输入-2 重新获取章节信息
输入0 打印章节信息
输入r 退出当前课程
->
```

### 5.5 刷课过程

#### 异步模式（输入 `1`）
```
·共收集到 56 个任务点
[提示] 刷视频过程中按 R 键可退出当前刷视频
  √ PPT 完成
  Xxx课程 - Yyy章节 - Zzz视频 - 1: |████████████________| 60% 180/300秒
  ...
0v0 所有视频任务完成！
```

#### 同步模式（输入 `2`）
```
[提示] 刷视频过程中按 R 键可退出当前刷视频
mv 课程 - 章节 - 任务名: 100%|████████████████████| 300/300秒
  √  视频完成
mv 课程 - 章节 - 任务名:  33%|██████______________| 60/180秒
  [R] 同步刷视频已取消          ← 按 R 后跳出
```

---

## 6. 核心数据流

```
登录 (login)
  │  手机号 + 密码 → encrypt_by_AES() → POST LOGIN_URL → Session 保存 Cookie
  ▼
获取用户信息 (get_user_info)
  │  GET SPACE_URL → 解析 p.personalName[title] → 打印用户名
  ▼
获取课程列表 (get_courses_info)
  │  POST COURSE_LIST_URL → 解析 li.course → 返回 list[course]
  ▼
用户选择课程编号 → 进入课程 (get_course_detail)
  │  → 请求① GET COURSE_DETAIL_URL → 解析 #enc + div.chapter_unit → 提取 knowledgeid
  │  → 请求② GET STUDY_AJAX_URL (对每个 knowledgeid) → 解析 prev_list li 数量
  │  → 返回 last_course_info
  ▼
用户选择刷课模式 (1→异步 / 2→同步)
  │
  ├─ 异步: finish_all_tasks_async()  → 并发执行 finish_task_async()
  │    └─ 每个 finish_task_async():
  │          → 请求③ GET KNOWLEDGE_CARDS_URL → extract_attachments()
  │          → PPT: 请求④ GET DOCUMENT_FINISH_URL → 完成
  │          → 视频:
  │               请求⑤ GET VIDEO_STATUS_URL → dtoken
  │               循环: generate_enc() → 请求⑥ GET VIDEO_LOG_URL → sleep 30-60s
  │               等待 "isPassed":true → break
  │
  └─ 同步: finish_task_sync() (逐个任务, 同上述③④⑤⑥)
         ├─ tqdm 进度条显示
         └─ _sleep_sync 每 0.5s 检测 R 键 → return False → 外部 break
```

---

## 7. 按键操作速查

| 按键 | 上下文 | 效果 |
|------|--------|------|
| 数字 `1` / `2` | 模式选择界面 | 进入刷课 / 刷题模式 |
| `-1` | 模式选择界面 | 退出程序 |
| 数字 `1`~`N` | 课程列表界面 | 进入对应课程 |
| `0` | 课程列表界面 | 打印 Cookie |
| `-1` | 课程列表界面 | 退出刷课模式，返回模式选择 |
| `1` | 课程内界面 | 一键异步完成所有任务点 |
| `2` | 课程内界面 | 逐步同步完成所有任务点 |
| `-2` | 课程内界面 | 重新获取章节信息 |
| `0` | 课程内界面 | 打印章节信息 |
| `r` | 课程内界面 | 返回课程列表 |
| `0` / `r` | 刷题界面 | 写入 .env / 清除配置并返回 |
| `R` | 刷视频过程中 | **取消当前刷课**，回到课程内界面 |

---

## 8. API 端点速查

| # | URL 模式 | 方法 | 所在函数 | 用途 |
|---|----------|------|----------|------|
| — | `LOGIN_URL` | **POST** | `api.login()` | 登录，data 含 AES 加密后的账号密码 |
| — | `SPACE_URL?ws=1&t=...` | **GET** | `api.get_user_info()` | 获取用户姓名 |
| — | `COURSE_LIST_URL` | **POST** | `api.get_courses_info()` | 获取课程列表 (data: courseType=1 ...) |
| ① | `COURSE_DETAIL_URL?courseid={}&clazzid={}&cpi={}&ut=s&t={}` | **GET** | `api.get_course_detail()` | 获取课程章节结构 + `#enc` 值 |
| ② | `STUDY_AJAX_URL?courseId={}&clazzid={}&chapterId={}&cpi={}...` | **GET** | `api.get_course_detail()` | 获取每个 knowledgeid 下的子任务数量 (N 次) |
| ③ | `KNOWLEDGE_CARDS_URL?courseid={}&clazzid={}&knowledgeid={}&num={}&ut=s&cpi={}&mooc2=1...` | **GET** | `task.finish_task_*` | 获取任务附件信息 (每个任务 1 次) |
| ④ | `DOCUMENT_FINISH_URL?jobid={}&knowledgeid={}&courseid={}&clazzid={}&jtoken={}...` | **GET** | `task.finish_task_*` | 完成 PPT/文档 (仅当附件含 jtoken) |
| ⑤ | `VIDEO_STATUS_URL?k=1001&flag=normal&ro=0&_dc={}` | **GET** | `task.finish_task_*` | 获取视频 dtoken (仅当附件含 objectId) |
| ⑥ | `VIDEO_LOG_URL?otherInfo={}&clazzId={}&playingTime={}&enc={}...` | **GET** | `task.finish_task_*` | 循环上报播放进度 (每个视频 1~N 次，至 isPassed:true) |

---

## 9. 注意事项

1. **密码加密**：登录时手机号和密码经 AES-CBC 加密后传输，密钥 `u2oh6Vu^HWe4_AES`，key 同时也是 IV。
2. **enc 签名**：视频进度上报依赖 `generate_enc()` 生成 MD5 哈希，含固定 `SECRET`，篡改公式会导致上报失败。
3. **异步信号量**：并发上限 200（`asyncio.Semaphore(200)`），避免瞬时请求过多被服务器限流。
4. **随机延时**：请求间有 0.5-1.5s 随机延时 + 视频上报间隔 30-60s，模拟真实播放行为。
5. **R 键取消**：基于 Windows `msvcrt.kbhit()` 非阻塞检测，每 0.5s 轮询一次。异步版通过 `asyncio.Event` 跨协程传递停止信号。
6. **Session 管理**：`requests.Session` 统一管理所有请求的 Cookie 和 Header，登录后自动保存，无需手动传递。
7. **文档脱敏**：本文档中的 cookie、fid、课程名、章节名一律为占位符或示例值，真实抓包（`cpi` / `userid` / `clazzid` / `courseid` / `dtoken` / `jtoken` / `enc`）禁止写入仓库，也不要把 `main.py` 一级菜单 `0` 打印出的 cookie 粘贴到 issue 或聊天记录。
8. **PPT/视频判断**：依据 `try: jtoken = attachment['jtoken']` → PPT；`except KeyError` 且 `'objectId' in attachment` → 视频。`enc` 字段虽被提取但不参与判断也不发送。

9. **LLM 配置存储**：base_url / model_name / api_key 明文存于 `.env`（`settings.py` 读写），`.env` 与 `.env.*` 已在 `.gitignore` 排除，仓库内只保留无密钥的 `.env.example`。进程环境变量（`CHAOXING_LLM_*`）优先于文件；摘要打印时 api_key 一律掩码，避免截图顺手泄露。
10. **刷题模式状态**：目前仅是 `main.py` 之下的菜单骨架，不发起任何作业请求；`config.py` 中不保留未经抓包验证的作业端点常量。

11. **课程列表首屏**：`_course_menu()` 靠 `option_key` 哨兵控制是否重画列表，初值必须是**非 0**（现为 `-2`）。写成 `0` 会导致进入刷课模式后不出课程列表；非法输入分支也要保持 `continue`，否则会掉进 `== 0` 打印 cookie。
