"""LLM 服务配置管理模块。

刷题模式使用的 OpenAI 兼容接口参数（base_url / model / api_key）保存在项目根的
``.env`` 文件里，该文件已在 ``.gitignore`` 中排除，不会进入仓库。

读取优先级：**进程环境变量 > .env 文件**（与 dotenv 惯例一致），因此临时换密钥
可以只设环境变量而不改文件。环境变量名：

- ``CHAOXING_LLM_BASE_URL``
- ``CHAOXING_LLM_MODEL``
- ``CHAOXING_LLM_API_KEY``

密钥在 .env 中为**明文存储**，靠「不进仓库 + 文件只留在本机」控制暴露面；
打印摘要时仍做掩码，避免截图/粘贴 issue 时顺带泄露。格式解析由本模块自带
（不依赖 python-dotenv），支持 ``KEY=value``、``export KEY=value``、
可选引号、``#`` 注释与空行；写回时保留文件里其它无关变量与原注释行。
"""

import os
import re
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent / '.env'

ENV_BASE_URL = 'CHAOXING_LLM_BASE_URL'
ENV_MODEL = 'CHAOXING_LLM_MODEL'
ENV_API_KEY = 'CHAOXING_LLM_API_KEY'

MANAGED_KEYS = (ENV_BASE_URL, ENV_MODEL, ENV_API_KEY)

DEFAULT_BASE_URL = 'https://api.openai.com/v1'
DEFAULT_MODEL = 'gpt-4o-mini'

_LINE_RE = re.compile(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$')


def mask_secret(value: str) -> str:
    """把密钥掩码成可安全打印的形式。

    Args:
        value: 原始密钥字符串

    Returns:
        形如 "sk-****abcd" 的掩码串；空值返回 "<未设置>"
    """
    if not value:
        return '<未设置>'
    if len(value) <= 8:
        return '****'
    return f'{value[:3]}****{value[-4:]}'


def _unquote(raw: str) -> str:
    """去掉环境变量值的包裹引号并还原转义。

    Args:
        raw: 等号右侧的原始文本

    Returns:
        解析后的字符串值
    """
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        inner = value[1:-1]
        if value[0] == '"':
            return inner.replace('\\"', '"').replace('\\n', '\n')
        return inner
    return re.split(r'\s+#', value, maxsplit=1)[0].strip()


def _quote_if_needed(value: str) -> str:
    """按需给写入的值加引号。

    Args:
        value: 待写入的字符串

    Returns:
        可直接写进 .env 的右侧文本
    """
    if value == '':
        return '""'
    if re.search(r'[\s"\'#;]', value):
        return '"' + value.replace('"', '\\"').replace('\n', '\\n') + '"'
    return value


def parse_env_file(path: Path | None = None) -> dict[str, str]:
    """解析 .env 文件为键值字典。

    Args:
        path: 文件路径，None 时使用模块级 ENV_FILE

    Returns:
        键值字典；文件不存在或读取失败时返回空字典
    """
    path = path if path is not None else ENV_FILE
    result: dict[str, str] = {}
    if not path.exists():
        return result
    try:
        for line in path.read_text(encoding='utf-8').splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            match = _LINE_RE.match(line)
            if match:
                result[match.group(1)] = _unquote(match.group(2))
    except OSError:
        return {}
    return result


def write_env_file(values: dict[str, str]) -> Path:
    """把若干键写入 .env，保留文件里其它行与注释。

    Args:
        values: 要设置/覆盖的键值

    Returns:
        写入的文件路径
    """
    lines: list[str] = []
    remaining = dict(values)
    if ENV_FILE.exists():
        try:
            for line in ENV_FILE.read_text(encoding='utf-8').splitlines():
                match = _LINE_RE.match(line)
                if match and match.group(1) in remaining:
                    lines.append(f'{match.group(1)}={_quote_if_needed(remaining.pop(match.group(1)))}')
                else:
                    lines.append(line)
        except OSError:
            lines = []
    for key, value in remaining.items():
        lines.append(f'{key}={_quote_if_needed(value)}')

    ENV_FILE.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')
    return ENV_FILE


def load_settings() -> dict:
    """读取 LLM 配置，进程环境变量优先于 .env 文件。

    Returns:
        含 base_url / model / api_key 三项，以及每项的 *_from 来源标记
        （'env' / 'file' / 空串）
    """
    file_values = parse_env_file()
    picked = {}
    for name, env_key in (('base_url', ENV_BASE_URL), ('model', ENV_MODEL), ('api_key', ENV_API_KEY)):
        env_value = os.environ.get(env_key, '')
        picked[name] = env_value or file_values.get(env_key, '')
        picked[name + '_from'] = 'env' if env_value else ('file' if file_values.get(env_key) else '')
    return picked


def save_settings(base_url: str, model: str, api_key: str) -> Path:
    """把三项配置写入 .env。

    Args:
        base_url: OpenAI 兼容接口根地址，形如 https://xx/v1
        model: 模型名
        api_key: 密钥明文

    Returns:
        写入的文件路径
    """
    return write_env_file({ENV_BASE_URL: base_url, ENV_MODEL: model, ENV_API_KEY: api_key})


def env_override_keys() -> list[str]:
    """返回当前由进程环境变量覆盖的受管配置项。

    Returns:
        值非空的受管环境变量名列表；没有覆盖时为空列表
    """
    return [key for key in MANAGED_KEYS if os.environ.get(key)]


def delete_settings() -> bool | None:
    """从 .env 中删除本模块管理的三个键（url / model / api_key）。

    删完后若文件里已无其它内容，则连带删除文件本身。进程环境变量无法在此
    清除，调用方可用 :func:`env_override_keys` 检查它们是否仍然生效。

    Returns:
        True 表示 .env 中确实移除了至少一个键；False 表示没有可删的本地配置；
        None 表示 .env 读取或写入失败
    """
    if not ENV_FILE.exists():
        return False

    try:
        lines = ENV_FILE.read_text(encoding='utf-8').splitlines()
    except OSError:
        return None

    kept: list[str] = []
    removed = 0
    for line in lines:
        match = _LINE_RE.match(line)
        if match and match.group(1) in MANAGED_KEYS:
            removed += 1
            continue
        kept.append(line)

    body = '\n'.join(kept).strip()
    try:
        if body:
            ENV_FILE.write_text(body + '\n', encoding='utf-8')
        else:
            ENV_FILE.unlink()
    except OSError:
        return None
    return removed > 0


def is_configured(settings: dict | None = None) -> bool:
    """判断三项配置是否都已就绪。

    Args:
        settings: 已读取的配置，None 时自动调用 load_settings()

    Returns:
        base_url / model / api_key 均非空时返回 True
    """
    settings = settings if settings is not None else load_settings()
    return all(bool(settings.get(k)) for k in ('base_url', 'model', 'api_key'))


def settings_summary(settings: dict | None = None) -> str:
    """生成可打印的配置摘要，密钥已掩码，并标注每项来源。

    Args:
        settings: 已读取的配置，None 时自动调用 load_settings()

    Returns:
        多行摘要文本
    """
    settings = settings if settings is not None else load_settings()

    def origin(name: str) -> str:
        tag = settings.get(name + '_from', '')
        return {'env': '（环境变量）', 'file': '（.env）'}.get(tag, '')

    return '\n'.join([
        f'  base_url : {settings.get("base_url") or "<未设置>"}{origin("base_url")}',
        f'  model    : {settings.get("model") or "<未设置>"}{origin("model")}',
        f'  api_key  : {mask_secret(settings.get("api_key", ""))}{origin("api_key")}',
        f'  配置文件 : {ENV_FILE.name}（已被 .gitignore 排除，不会进入仓库）',
    ])


def _read_line(prompt_text: str, default: str = '') -> str:
    """读取一行输入，直接回车时沿用默认值。

    Args:
        prompt_text: 提示语
        default: 回车时返回的默认值

    Returns:
        去掉首尾空白的输入内容或默认值
    """
    try:
        value = input(prompt_text).strip()
    except EOFError:
        value = ''
    return value or default


def prompt_settings() -> dict:
    """交互式设置 base_url / model_name / api_key 并写入 .env。

    Returns:
        保存后的配置字典
    """
    current = load_settings()
    print(f'配置 OpenAI 兼容接口，写入 {ENV_FILE.name}（留空则保留原值）')
    base_url = _read_line(f'  base_url [{current["base_url"] or DEFAULT_BASE_URL}]: ',
                          current['base_url'] or DEFAULT_BASE_URL)
    model = _read_line(f'  model_name [{current["model"] or DEFAULT_MODEL}]: ',
                       current['model'] or DEFAULT_MODEL)
    api_key = _read_line('  api_key: ') or current['api_key']

    path = save_settings(base_url, model, api_key)
    print(f'  已写入 {path}')
    print('  提示：该文件已在 .gitignore 中；若曾被 git 跟踪过，请执行 git rm --cached .env')
    return load_settings()
