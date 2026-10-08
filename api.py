"""超星学习通 API 交互模块。

封装与超星平台的 HTTP 交互，包括登录、获取用户信息、课程列表、
课程章节详情以及附件信息提取。
"""

import json
import os
import time
import random
import re

import requests
from bs4 import BeautifulSoup

from colorama import Fore, Style

from .encode import encrypt_by_AES
from .config import (
    LOGIN_URL, SPACE_URL, COURSE_LIST_URL, COURSE_DETAIL_URL,
    STUDY_AJAX_URL, AES_KEY,
)


def login(session: requests.Session) -> bool:
    """通过手机号+密码登录超星学习通平台。

    密码使用 AES 加密后发送，登录成功后 session 自动保存 cookies。

    Args:
        session: requests.Session 实例，用于维持登录状态

    Returns:
        True 表示登录成功，False 表示失败
    """
    login_cookies = {}

    login_headers = {
        **{k: v for k, v in {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://passport2.chaoxing.com',
            'Pragma': 'no-cache',
            'Referer': 'https://passport2.chaoxing.com/login',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest',
        }.items()},
    }

    login_data = {
        'fid': '-1',
        'uname': '',
        'password': '',
        'refer': f'http%3A%2F%2Fi.mooc.chaoxing.com',
        't': 'true',
        'forbidotherlogin': '0',
        'validate': '',
        'doubleFactorLogin': '0',
        'independentId': '0',
        'independentNameId': '0',
    }

    phone = encrypt_by_AES(input('请输入手机号：'), AES_KEY)
    pwd = encrypt_by_AES(input('请输入密码：'), AES_KEY)
    login_data['uname'] = phone
    login_data['password'] = pwd
    os.system('cls')
    time.sleep(1)

    response = session.post(
        LOGIN_URL,
        cookies=login_cookies,
        headers=login_headers,
        data=login_data,
    )

    if '"status":true' in response.text:
        print('~~超星学习通登录成功！~~')
        return True
    else:
        print('登录失败QAQ！请重新登录')
        return False


def get_user_info(session: requests.Session) -> None:
    """获取并打印当前登录用户的个人信息（用户名等）。

    Args:
        session: 已登录的 requests.Session 实例
    """
    user_headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-site',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    }

    user_params = {
        'ws': '1',
        't': time.time(),
    }

    time.sleep(random.uniform(1, 3))

    response = session.get(
        SPACE_URL,
        params=user_params,
        headers=user_headers,
    )

    print(f'状态码:{response.status_code}')
    soup = BeautifulSoup(response.text, 'lxml')
    print(f"用户名：{soup.find('p', class_='personalName').get('title')}")


def get_courses_info(session: requests.Session) -> list[dict]:
    """获取当前用户的所有课程列表。

    Args:
        session: 已登录的 requests.Session 实例

    Returns:
        课程信息列表，每个元素包含 course_params、course_name、
        course_teacher、course_url 等字段
    """
    course_headers = {
        'Accept': 'text/html, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://mooc1-1.chaoxing.com',
        'Pragma': 'no-cache',
        'Referer': 'https://mooc2-ans.chaoxing.com/mooc2-ans/visit/interaction?moocDomain=https://mooc1-1.chaoxing.com/mooc-ans',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'X-Requested-With': 'XMLHttpRequest',
    }

    course_data = {
        'courseType': '1',
        'courseFolderId': '0',
        'baseEducation': '0',
        'superstarClass': '',
        'courseFolderSize': '0',
    }

    time.sleep(random.uniform(1, 2))
    response = session.post(
        COURSE_LIST_URL,
        headers=course_headers,
        data=course_data,
    )

    soup = BeautifulSoup(response.text, 'lxml')
    courses_name = soup.find_all('li', class_="course")
    course_list = []
    for course in courses_name:
        course_temp = {
            "course_params": {
                'courseid': course.get('courseid'),
                'clazzid': course.get('clazzid'),
                'cpi': course.get('personid'),
                'ut': 's',
                't': time.time() * 1000,
            },
            "course_name": course.find('span', class_='course-name').text,
            "course_teacher": course.find_all('p', class_='line2'),
            "course_url": course.find('a', class_='color1').get('href'),
        }
        course_list.append(course_temp)

    return course_list


def show_courses_detail(course_list: list[dict]) -> None:
    """在终端打印课程列表详情（编号、名称、教师、链接）。

    Args:
        course_list: get_courses_info() 返回的课程列表
    """
    print("================================================================================")
    for tag, course in enumerate(course_list, 1):
        print(Fore.RED + f"{tag}.{course['course_name']}  " + Style.RESET_ALL, end='')
        for teacher in course['course_teacher']:
            print(f"{teacher.text}  ", end='')
        print()
        print(Style.DIM + Fore.BLUE + f"{course['course_url']}" + Style.RESET_ALL)
    print("================================================================================")


def get_course_detail(
    session: requests.Session,
    course_title: str,
    params: dict,
) -> dict:
    """获取指定课程的章节结构和任务点详情。

    Args:
        session: 已登录的 requests.Session 实例
        course_title: 课程名称
        params: 课程参数，包含 courseid, clazzid, cpi, ut 等

    Returns:
        课程详情字典，包含 title、enc、status 和 chapter 列表。
        chapter 中每个元素包含 name 和 course 子任务列表。
    """
    into_course_headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'priority': 'u=0, i',
        'referer': 'https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu',
        'sec-fetch-dest': 'iframe',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'upgrade-insecure-requests': '1',
    }

    response = session.get(
        COURSE_DETAIL_URL,
        params=params,
        headers=into_course_headers,
    )

    print(f"进入课程状态码: {response.status_code}")
    course_soup = BeautifulSoup(response.text, 'lxml')
    chapter_enc = course_soup.find('input', id='enc').get('value')
    chapter_list = course_soup.find_all('div', class_='chapter_unit')
    course_finish_status = course_soup.find('h2', class_='xs_head_name')

    last_course_info = {
        "title": course_title,
        'enc': chapter_enc,
        "status": course_finish_status.text.replace(' ', '').replace('\n', ''),
    }

    chapter_temp = []
    for chapter in chapter_list:
        name_pattern = r'title="([^"]+)"'
        chapter_course_soup = chapter.find_all('li')
        chapter_course_list = []
        for li in chapter_course_soup:
            temp = str(li.find('div', class_='chapter_item'))
            id_pattern = r'id="cur(\d+)"'
            knowledgeid = re.search(id_pattern, temp)
            name = re.search(name_pattern, temp)
            try:
                status = li.find('span', class_='bntHoverTips').text
            except Exception:
                status = '0个待完成任务点'
            _ajax = session.get(
                STUDY_AJAX_URL,
                params={
                    'courseId': params['courseid'],
                    'clazzid': params['clazzid'],
                    'chapterId': knowledgeid.group(1),
                    'cpi': params['cpi'],
                    'verificationcode': '',
                    'mooc2': '1',
                    'toComputer': 'false',
                    'microTopicId': '0',
                    'editorPreview': '0',
                    'isPreviewVideo': 'false',
                    'videoWidth': '0',
                    'videoHeight': '0',
                    'targetVideoJobId': '',
                    'cardIndex': '0',
                },
            )

            _ajax = BeautifulSoup(_ajax.text)
            nums = len(_ajax.find('div', class_='prev_list').find_all('li'))
            final_params = []
            for j in range(nums):
                final_params.append({
                    'clazzid': params['clazzid'],
                    'courseid': params['courseid'],
                    'knowledgeid': knowledgeid.group(1),
                    'num': j,
                    'ut': 's',
                    'cpi': params['cpi'],
                    'mooc2': '1',
                    'isMicroCourse': 'false',
                    'editorPreview': '0',
                })
            chapter_course_list.append({
                "params": final_params,
                "knowledgeid": knowledgeid.group(1),
                "name": f"{li.find('span', class_='catalog_sbar').text} {name.group(1)}",
                "status": status,
            })

        chapter_temp.append({
            "name": f"{chapter.find('em', style='font-style:normal;').text} {re.search(name_pattern, str(chapter.find('div', class_='chapter_item'))).group(1)}",
            "course": chapter_course_list,
        })
    last_course_info["chapter"] = chapter_temp
    return last_course_info


def print_course_info(last_course_info: dict) -> None:
    """在终端打印课程详情信息（章节结构、任务点状态）。

    Args:
        last_course_info: get_course_detail() 返回的课程详情字典
    """
    print("================================================================================")
    print(f'{Fore.GREEN}{last_course_info["title"]}{Style.RESET_ALL}')
    print(last_course_info["status"])
    for chapter in last_course_info["chapter"]:
        print(f"{Fore.YELLOW}{chapter['name']}{Style.RESET_ALL}")
        for course in chapter["course"]:
            print(
                f"    {Fore.BLUE}{course['name']}{Style.RESET_ALL}  "
                f"{Fore.MAGENTA}{course['status']}{Style.RESET_ALL}"
            )
    print("================================================================================")


def extract_attachments(response_text: str) -> list[dict]:
    """从知识卡片 API 响应中提取附件信息。

    支持三种提取方式：
    1. 匹配 mArg = {...} JavaScript 对象
    2. 匹配 "attachments":[...] JSON 数组
    3. 直接从响应文本中提取单个视频/文档的参数

    Args:
        response_text: knowledge/cards API 返回的 HTML 文本

    Returns:
        附件信息列表，每个元素包含 jobid、objectId、attDuration 等字段
    """
    match = re.search(r'mArg = ({.*?});', response_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            attachments = data.get('attachments', [])
            if attachments:
                return attachments
        except Exception:
            pass

    match = re.search(r'"attachments":\[(.*?)\]', response_text, re.DOTALL)
    if match:
        try:
            wrapped = f'{{"attachments":[{match.group(1)}]}}'
            data = json.loads(wrapped)
            return data.get('attachments', [])
        except Exception:
            pass

    single_att = {}

    match = re.search(r'"jobid":"([^"]+)"', response_text)
    if match:
        single_att['jobid'] = match.group(1)

    match = re.search(r'"objectid":"([^"]+)"', response_text)
    if match:
        single_att['objectId'] = match.group(1)

    match = re.search(r'"otherInfo":"([^"]+)"', response_text)
    if match:
        single_att['otherInfo'] = match.group(1)

    match = re.search(r'"attDuration":(\d+)', response_text)
    if match:
        single_att['attDuration'] = int(match.group(1))

    match = re.search(r'"attDurationEnc":"([^"]+)"', response_text)
    if match:
        single_att['attDurationEnc'] = match.group(1)

    match = re.search(r'"videoFaceCaptureEnc":"([^"]+)"', response_text)
    if match:
        single_att['videoFaceCaptureEnc'] = match.group(1)

    if single_att:
        return [single_att]

    return []