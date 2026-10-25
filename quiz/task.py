"""刷题模式菜单骨架。

本模块当前只提供菜单结构与返回逻辑，作业/试题的实际流程尚未开发。

- ``0`` 设置 OpenAI 兼容接口的 base_url / model_name / api_key（存入 .env）
- ``1`` 进入课程章节作业（studentstudy → doHomeWorkNew）
- ``2`` 进入流动作业（dowork）
- ``r`` 强行删除已保存的配置并返回上级菜单
- ``-1`` 返回上级菜单

考试类题目不在本工具范围内，不预留入口。
"""

from colorama import Fore, Style

from .. import settings


def run_quiz_mode(session, course_list: list[dict]) -> None:
    """刷题模式主循环，退出后返回模式选择菜单。

    Args:
        session: 已登录的 requests.Session 实例
        course_list: 登录后获取的课程列表
    """
    while True:
        print(f'{Fore.MAGENTA}刷题模式{Style.RESET_ALL}  当前接口配置：')
        print(settings.settings_summary())
        key = input(
            '输入0 设置 url / model_name / api key（OpenAI 兼容）\n'
            '输入1 进入课程章节作业（studentstudy）\n'
            '输入2 进入流动作业（dowork）\n'
            '输入r 强行删除已保存的 api key 等配置并返回上级\n'
            '输入-1 返回上级菜单\n->'
        ).strip()

        if key == '0':
            settings.prompt_settings()
        elif key in ('1', '2'):
            name = '课程章节作业（doHomeWorkNew）' if key == '1' else '流动作业（dowork）'
            print(f'{Fore.YELLOW}  [ ] {name}：功能待开发，当前仅为菜单骨架{Style.RESET_ALL}')
        elif key.lower() == 'r':
            removed = settings.delete_settings()
            print('  已清除本工具保存的配置项' if removed else '  本地没有可清除的配置项')
            return
        elif key == '-1':
            return
        elif key == '':
            continue
        else:
            print(f"'{key}' 不是有效选项QAQ")