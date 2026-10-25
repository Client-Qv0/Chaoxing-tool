"""超星学习通自动刷课工具 - 主入口。

登录成功后先进入模式选择，再进入各自菜单：

- 模式 1 刷课：课程列表 → 章节详情 → 异步 / 同步完成任务点
- 模式 2 刷题：接口配置 → 章节作业 / 流动作业（协议待抓包确认）
"""

"""
路径修复代码
- 针对pycharm不支持 “from .文件 import 函数” 的路径修复代码
"""
# ===== 1. 环境自动修复（放在第一行，所有import之前） =====
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    this_file = Path(__file__).resolve()
    root_dir = this_file.parent.parent  # 上级目录，作为包的搜索路径
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    __package__ = this_file.parent.name  # 目录名即包名，仓库被改名/换目录也能跑
# ===== 修复代码结束 =====

import asyncio
import os
import pprint
import warnings

import colorama
import requests

from .api import (
    get_course_detail, get_courses_info, get_user_info, login,
    print_course_info, show_courses_detail,
)
from .quiz.task import run_quiz_mode
from .task import finish_all_tasks_async, finish_task_sync

warnings.filterwarnings("ignore")


def _course_menu(session, course_list: list[dict]) -> None:
    """模式 1：刷课菜单（课程列表 → 章节 → 完成任务点）。

    Args:
        session: 已登录的 requests.Session 实例
        course_list: 课程列表
    """
    option_key = -2
    while True:
        if option_key != 0:
            show_courses_detail(course_list)

        option_key = input(
            '输入课程编号，进入课程主界面\n'
            '输入0 打印用户的cookie\n'
            '输入-1 退出刷课模式\n编号>')
        if option_key == '':
            option_key = 0
            continue
        if option_key == '-1':
            return
        try:
            option_key = int(option_key)
        except ValueError:
            print(f"'{option_key}'不是有效数字QAQ，请重新输入:")
            option_key = 0
            continue
        if option_key == -1:
            return

        if option_key == 0:
            pprint.pprint(session.cookies.get_dict())
            continue
        if option_key < 0:
            option_key = 0
            continue
        if option_key > len(course_list):
            print(f"{option_key}超出范围了QAQ，请重新输入:")
            option_key = 0
            continue


        option_key -= 1
        key = -2
        last_course_info = {}
        while True:
            if key == -2:
                try:
                    os.system('cls')
                    last_course_info = get_course_detail(
                        session,
                        course_list[option_key]['course_name'],
                        course_list[option_key]['course_params'],
                    )
                except Exception as e:
                    print(f"进入课程失败: {e}")
                    break
                key = 0

            if key == 0:
                os.system('cls')
                print_course_info(last_course_info)

            elif key == 1:
                try:
                    task_list = []
                    for chapter in last_course_info['chapter']:
                        chapter_name = chapter['name']
                        for tasks in chapter['course']:
                            _num = 0
                            for task in tasks['params']:
                                _num += 1
                                task_with_name = task.copy()
                                task_with_name['chapter_name'] = f"{tasks['name']} - {_num}"
                                task_with_name['parent_chapter'] = chapter_name
                                task_list.append(task_with_name)
                    if not task_list:
                        print("当前课程没有任务点")
                    else:
                        print(f"·共收集到 {len(task_list)} 个任务点")
                        print("[提示] 刷视频过程中按 R 键可退出当前刷视频")
                        asyncio.run(finish_all_tasks_async(
                            video_list=task_list,
                            base_enc=last_course_info['enc'],
                            cookies=session.cookies.get_dict(),
                            course_name=last_course_info['title'],
                        ))
                except Exception:
                    pass

            elif key == 2:
                print("[提示] 刷视频过程中按 R 键可退出当前刷视频")
                cancelled = False
                for chapter in last_course_info['chapter']:
                    if cancelled:
                        break
                    chapter_name = chapter['name']
                    for task in chapter['course']:
                        if cancelled:
                            break
                        for params in task['params']:
                            if not finish_task_sync(
                                session=session,
                                base_enc=last_course_info['enc'],
                                base_params=params,
                                course_name=last_course_info['title'],
                                chapter_name=chapter_name,
                                task_name=task['name'],
                            ):
                                cancelled = True
                                print("\n[R] 同步刷视频已取消")
                                break

            key = input(
                '输入1 一键完成所有任务点(同时完成)\n'
                '输入2 逐步完成所有任务点(顺序完成)\n'
                '输入-2 重新获取章节信息\n'
                '输入0 打印章节信息\n'
                '输入r 退出当前课程\n->'
            )
            if key == 'r':
                os.system('cls')
                option_key = -2
                break
            elif key == '':
                key = -99999
                continue
            else:
                try:
                    key = int(key)
                except ValueError:
                    print(f"'{key}'不是有效数字QAQ，请重新输入:")
                    key = -99999
                    continue


def main() -> None:
    """运行超星学习通自动刷课 CLI 主程序。

    流程：登录 → 模式选择（1 刷课 / 2 刷题）→ 进入对应菜单。
    """
    colorama.just_fix_windows_console()

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0',
    })

    status_login = False
    while not status_login:
        status_login = login(session)

    get_user_info(session)
    course_list = get_courses_info(session)

    while True:
        mode = input(
            f'{colorama.Fore.GREEN}~~ 请选择工作模式 ~~{colorama.Style.RESET_ALL}\n'
            '输入1 进入刷课模式（视频 / PPT 任务点）\n'
            '输入2 进入刷题模式（章节作业 / 流动作业）\n'
            '输入-1 退出程序\n->'
        ).strip()

        if mode == '1':
            _course_menu(session, course_list)
            os.system('cls')
        elif mode == '2':
            run_quiz_mode(session, course_list)
            os.system('cls')
        elif mode == '-1':
            print('程序已退出0v0~')
            os.system('pause')
            return
        elif mode == '':
            continue
        else:
            print(f"'{mode}' 不是有效选项QAQ")


if __name__ == '__main__':
    main()