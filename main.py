"""超星学习通自动刷课工具 - 主入口。

提供交互式命令行界面，支持：
- 手机号+密码登录
- 查看课程列表和章节详情
- 一键异步完成所有任务点
- 逐步同步完成所有任务点
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
    root_dir = this_file.parent.parent  # 定位到 "超星学习通" 文件夹
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    __package__ = "py"  # 声明当前包名
# ===== 修复代码结束 =====

import os
import asyncio
import warnings

import requests
import pprint
import colorama

from .api import (
    login, get_user_info, get_courses_info,
    show_courses_detail, get_course_detail,
    print_course_info,
)
from .task import finish_task_sync, finish_all_tasks_async

warnings.filterwarnings("ignore")


def main() -> None:
    """运行超星学习通自动刷课 CLI 主程序。

    流程：登录 -> 获取用户信息 -> 选择课程 -> 查看章节 -> 完成任务点。
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

    option_key = -2
    while True:
        if option_key != 0:
            show_courses_detail(course_list)

        option_key = input('输入课程编号，进入课程主界面\n输入0 打印用户的cookie\n输入-1 退出程序\n编号>')
        if option_key == '':
            option_key = 0
            continue
        else:
            try:
                option_key = int(option_key)
            except ValueError:
                print(f"'{option_key}'不是有效数字QAQ，请重新输入:")
                option_key = 0
                continue

        if option_key == -1:
            print('程序已退出0v0~')
            os.system('pause')
            return

        if option_key <= -2:
            continue

        if option_key == 0:
            pprint.pprint(session.cookies.get_dict())
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


if __name__ == '__main__':
    main()