"""超星学习通任务完成模块。

提供同步和异步两种方式完成课程任务点（PPT 文档、视频播放）。
"""

import asyncio
import os
import random
import re
import time

import aiohttp
import requests
from colorama import Fore, Style
from tqdm import tqdm

from .api import extract_attachments
from .encode import generate_enc
from .config import KNOWLEDGE_CARDS_URL, DOCUMENT_FINISH_URL, VIDEO_STATUS_URL, VIDEO_LOG_URL


def _is_r_pressed() -> bool:
    """非阻塞检测 R 键是否被按下（仅 Windows）。"""
    if os.name == 'nt':
        import msvcrt
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            return ch.lower() == b'r'
    return False


def _sleep_sync(seconds: float) -> bool:
    """同步睡眠，每 0.5 秒检测一次 R 键。返回 True 表示被取消。"""
    steps = max(1, int(seconds * 2))
    for _ in range(steps):
        if _is_r_pressed():
            return True
        time.sleep(0.5)
    return False


async def _sleep_async(seconds: float, stop_event: asyncio.Event) -> bool:
    """异步睡眠，每 0.5 秒检测一次停止信号。返回 True 表示被取消。"""
    steps = max(1, int(seconds * 2))
    for _ in range(steps):
        if stop_event.is_set():
            return True
        await asyncio.sleep(0.5)
    return False


async def _keyboard_listener(stop_event: asyncio.Event) -> None:
    """后台协程：监听 R 键按下，触发停止信号。"""
    loop = asyncio.get_running_loop()
    while not stop_event.is_set():
        pressed = await loop.run_in_executor(None, _is_r_pressed)
        if pressed:
            stop_event.set()
            print("\n  [R] 已收到取消信号，正在停止所有任务...")
        await asyncio.sleep(0.5)


def finish_task_sync(
    session: requests.Session,
    base_enc: str,
    base_params: dict,
    course_name: str,
    chapter_name: str,
    task_name: str,
) -> bool:
    """同步方式完成单个任务点（PPT 或视频）。

    使用 requests 库顺序执行，适合逐步完成所有任务点。

    Args:
        session: 已登录的 requests.Session 实例
        base_enc: 课程章节加密标识
        base_params: 任务参数，包含 knowledgeid, courseid, clazzid, cpi 等
        course_name: 课程名称（用于进度显示）
        chapter_name: 章节名称（用于进度显示）
        task_name: 任务名称（用于进度显示）

    Returns:
        True 表示任务完成，False 表示用户按 R 取消
    """
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'priority': 'u=0, i',
        'referer': f"https://mooc1.chaoxing.com/mycourse/studentstudy?chapterId={base_params['knowledgeid']}&courseId={base_params['courseid']}&clazzid={base_params['clazzid']}&cpi={base_params['cpi']}&enc={base_enc}&mooc2=1&hidetype=0",
        'sec-fetch-dest': 'iframe',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
    }

    base_response = session.get(
        KNOWLEDGE_CARDS_URL,
        params=base_params,
        headers=headers,
    )
    if _sleep_sync(random.uniform(0.5, 1.5)):
        print("  已取消")
        return False
    finish_flag = 0
    final_attachments = extract_attachments(base_response.text)
    for response in final_attachments:
        try:
            try:
                jobid = response['jobid']
            except KeyError:
                jobid = response['property']['_jobid']

            jtoken = response['jtoken']
            enc = response['enc']

            finish_params = {
                'jobid': jobid,
                'knowledgeid': base_params['knowledgeid'],
                'courseid': base_params['courseid'],
                'clazzid': base_params['clazzid'],
                'jtoken': jtoken,
                'checkMicroTopic': 'true',
                'microTopicId': 'undefined',
                'courseEngineInfo': 'false',
                '_dc': f"{time.time() * 1000}",
            }
            finish_headers = {
                'accept': '*/*',
                'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                'cache-control': 'no-cache',
                'pragma': 'no-cache',
                'priority': 'u=0, i',
                'referer': 'https://mooc1.chaoxing.com/ananas/modules/pdf/index.html',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'x-requested-with': 'XMLHttpRequest',
            }

            session.get(
                DOCUMENT_FINISH_URL,
                params=finish_params,
                headers=finish_headers,
            )
            print("  √ PPT 完成")
            finish_flag = 1

        except KeyError:
            try:
                jobid = response['jobid']
            except KeyError:
                jobid = response['property']['_jobid']

            if 'objectid' not in response and 'objectId' not in response:
                continue
            objectid = response['objectId']

            otherInfo = response['otherInfo']

            try:
                videoFaceCaptureEnc = response['videoFaceCaptureEnc']
            except KeyError:
                videoFaceCaptureEnc = ''

            attDurationEnc = response['attDurationEnc']

            v_time = response['attDuration']

            userid = re.search(r'"userid":"([^"]+)"', base_response.text).group(1)

            if _sleep_sync(random.uniform(0.5, 1.5)):
                print("  已取消")
                return False

            display_name = f"{course_name} - {chapter_name} - {task_name}"

            with tqdm(
                total=v_time, desc=f"  mv {display_name[:100]}",
                unit="秒", leave=False,
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}秒",
            ) as pbar:

                playtime = 0
                flag = True
                finish_params = {
                    'clazzId': base_params['clazzid'],
                    'playingTime': f'{playtime}',
                    'duration': v_time,
                    'clipTime': f'0_{v_time}',
                    'objectId': objectid,
                    'courseId': base_params['courseid'],
                    'jobid': jobid,
                    'userid': userid,
                    'isdrag': '0',
                    'view': 'pc',
                    'rt': '0.9',
                    'videoFaceCaptureEnc': videoFaceCaptureEnc,
                    'dtype': 'Video',
                    'attDuration': v_time,
                    'attDurationEnc': attDurationEnc,
                    'courseEngineInfo': 'false',
                }

                finish_headers = {
                    'Accept': '*/*',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Pragma': 'no-cache',
                    'Referer': 'https://mooc1.chaoxing.com/ananas/modules/video/index.html?',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin',
                    'X-Requested-With': 'XMLHttpRequest',
                }

                js_cookies = {
                    'writenote': 'yes',
                    'doubleSpeedValue': '1',
                    'thirdRegist': '0',
                    'tl': '1',
                    '_industry': '5',
                    f'{base_params["courseid"]}cpi': base_params['cpi'],
                    f'{base_params["courseid"]}ut': base_params['ut'],
                    f'{base_params["courseid"]}t': str(time.time() * 1000),
                }

                video_doc = session.get(
                    f"{VIDEO_STATUS_URL.format(objectid=objectid)}?k=1001&flag=normal&ro=0&_dc={time.time() * 1000}",
                    headers=finish_headers,
                    cookies=js_cookies,
                )

                match = re.search(r'"dtoken":"([^"]+)"', video_doc.text)
                dtoken = match.group(1)
                base_url = VIDEO_LOG_URL.format(
                    cpi=base_params['cpi'],
                    dtoken=dtoken,
                ) + f"?otherInfo={otherInfo}"

                while True:
                    finish_params['playingTime'] = f'{playtime}'
                    finish_params['enc'] = generate_enc(
                        clazzId=base_params['clazzid'],
                        userid=userid,
                        jobid=jobid,
                        objectId=objectid,
                        playTime=playtime,
                        attDuration=v_time,
                        clipTime=f'0_{v_time}',
                    )
                    finish_params['_t'] = int(time.time() * 1000)

                    rps = session.get(base_url, params=finish_params, headers=finish_headers)
                    if '"isPassed":true' in rps.text:
                        finish_flag = 1
                        print("  √  视频完成")
                        break
                    if not flag:
                        break

                    temp = random.randint(30, 60)

                    if playtime + temp >= v_time:
                        flag = False
                        temp = int(v_time) - playtime
                        playtime = v_time
                    else:
                        playtime += temp
                    if _sleep_sync(temp):
                        print("  已取消")
                        return False
                    pbar.update(temp)
                if playtime == v_time:
                    finish_flag = 1

        except Exception:
            pass
        if finish_flag != 1:
            print("==============QAQ没能完成作业==============")

    return True


async def finish_task_async(
    base_enc: str,
    base_params: dict,
    session_cookies: dict,
    semaphore: asyncio.Semaphore,
    stop_event: asyncio.Event,
    course_name: str,
    chapter_name: str,
    task_name: str,
) -> None:
    """异步方式完成单个任务点（PPT 或视频）。

    使用 aiohttp 库异步执行，通过信号量控制并发数，支持批量同时完成。

    Args:
        base_enc: 课程章节加密标识
        base_params: 任务参数，包含 knowledgeid, courseid, clazzid, cpi 等
        session_cookies: 登录后的 cookies 字典
        semaphore: 异步信号量，控制并发数上限
        stop_event: 停止信号，R 键触发后设为 set
        course_name: 课程名称（用于进度显示）
        chapter_name: 章节名称（用于进度显示）
        task_name: 任务名称（用于进度显示）
    """
    async with semaphore:
        if stop_event.is_set():
            return
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'referer': f"https://mooc1.chaoxing.com/mycourse/studentstudy?chapterId={base_params['knowledgeid']}&courseId={base_params['courseid']}&clazzid={base_params['clazzid']}&cpi={base_params['cpi']}&enc={base_enc}&mooc2=1&hidetype=0",
            'sec-fetch-dest': 'iframe',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
        }

        async with aiohttp.ClientSession(cookies=session_cookies) as aio_session:
            try:
                async with aio_session.get(
                    KNOWLEDGE_CARDS_URL,
                    params=base_params,
                    headers=headers,
                ) as resp:
                    text = await resp.text()

                if await _sleep_async(random.uniform(0.5, 1.5), stop_event):
                    return
                final_attachments = extract_attachments(text)

                if not final_attachments:
                    return

                for att in final_attachments:
                    if stop_event.is_set():
                        return
                    if 'jtoken' in att and 'enc' in att:
                        try:
                            jobid = att['jobid']
                            jtoken = att['jtoken']

                            finish_params = {
                                'jobid': jobid,
                                'knowledgeid': base_params['knowledgeid'],
                                'courseid': base_params['courseid'],
                                'clazzid': base_params['clazzid'],
                                'jtoken': jtoken,
                                'checkMicroTopic': 'true',
                                'microTopicId': 'undefined',
                                'courseEngineInfo': 'false',
                                '_dc': f"{time.time() * 1000}",
                            }
                            finish_headers = {
                                'accept': '*/*',
                                'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                                'cache-control': 'no-cache',
                                'pragma': 'no-cache',
                                'priority': 'u=0, i',
                                'referer': 'https://mooc1.chaoxing.com/ananas/modules/pdf/index.html',
                                'sec-fetch-dest': 'empty',
                                'sec-fetch-mode': 'cors',
                                'sec-fetch-site': 'same-origin',
                                'x-requested-with': 'XMLHttpRequest',
                            }

                            async with aio_session.get(
                                DOCUMENT_FINISH_URL,
                                params=finish_params,
                                headers=finish_headers,
                            ) as resp:
                                await resp.text()

                            print("  √ PPT 完成")
                            continue

                        except Exception:
                            continue

                    if 'objectId' not in att and 'objectid' not in att:
                        continue

                    jobid = att.get('jobid')
                    objectid = att.get('objectId') or att.get('objectid')
                    otherInfo = att.get('otherInfo', '')
                    videoFaceCaptureEnc = att.get('videoFaceCaptureEnc', '')
                    attDurationEnc = att.get('attDurationEnc', '')
                    v_time = att.get('attDuration', 0)

                    userid_match = re.search(r'"userid":"([^"]+)"', text)
                    userid = userid_match.group(1) if userid_match else ''

                    if not jobid or not objectid:
                        continue

                    if await _sleep_async(random.uniform(0.5, 1.5), stop_event):
                        return

                    display_name = f"{course_name} - {chapter_name} - {task_name}"

                    finish_headers = {
                        'Accept': '*/*',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive',
                        'Pragma': 'no-cache',
                        'Referer': 'https://mooc1.chaoxing.com/ananas/modules/video/index.html?',
                        'Sec-Fetch-Dest': 'empty',
                        'Sec-Fetch-Mode': 'cors',
                        'Sec-Fetch-Site': 'same-origin',
                        'X-Requested-With': 'XMLHttpRequest',
                    }

                    js_cookies = {
                        'writenote': 'yes',
                        'doubleSpeedValue': '1',
                        'thirdRegist': '0',
                        'tl': '1',
                        '_industry': '5',
                        f'{base_params["courseid"]}cpi': base_params['cpi'],
                        f'{base_params["courseid"]}ut': base_params['ut'],
                        f'{base_params["courseid"]}t': str(time.time() * 1000),
                    }

                    async with aio_session.get(
                        f"{VIDEO_STATUS_URL.format(objectid=objectid)}?k=1001&flag=normal&ro=0&_dc={time.time() * 1000}",
                        headers=finish_headers,
                        cookies=js_cookies,
                    ) as resp:
                        video_text = await resp.text()

                    match = re.search(r'"dtoken":"([^"]+)"', video_text)
                    if not match:
                        print("  ✗ 无法获取 dtoken")
                        continue
                    dtoken = match.group(1)

                    base_url = VIDEO_LOG_URL.format(
                        cpi=base_params['cpi'],
                        dtoken=dtoken,
                    ) + f"?otherInfo={otherInfo}"

                    bar_length = 20
                    playtime = 0
                    last_progress = -1
                    flag = True
                    finish_params = {
                        'clazzId': base_params['clazzid'],
                        'playingTime': f'{playtime}',
                        'duration': v_time,
                        'clipTime': f'0_{v_time}',
                        'objectId': objectid,
                        'courseId': base_params['courseid'],
                        'jobid': jobid,
                        'userid': userid,
                        'isdrag': '0',
                        'view': 'pc',
                        'rt': '0.9',
                        'videoFaceCaptureEnc': videoFaceCaptureEnc,
                        'dtype': 'Video',
                        'attDuration': v_time,
                        'attDurationEnc': attDurationEnc,
                        'courseEngineInfo': 'false',
                    }

                    while True:
                        if stop_event.is_set():
                            return
                        progress = int(playtime * bar_length / v_time) if v_time > 0 else 0

                        if progress != last_progress:
                            bar = '_' * progress + ' ' * (bar_length - progress)
                            print(
                                f"  {Fore.CYAN}{display_name[:75]}{Style.RESET_ALL}: |{Fore.GREEN}{bar}{Style.RESET_ALL}| {(playtime / v_time) * 100:.0f}% {playtime}/{v_time}秒",
                                flush=True,
                            )
                            last_progress = progress

                        finish_params['playingTime'] = f'{playtime}'
                        finish_params['enc'] = generate_enc(
                            clazzId=base_params['clazzid'],
                            userid=userid,
                            jobid=jobid,
                            objectId=objectid,
                            playTime=playtime,
                            attDuration=v_time,
                            clipTime=f'0_{v_time}',
                        )
                        finish_params['_t'] = int(time.time() * 1000)

                        async with aio_session.get(base_url, params=finish_params, headers=finish_headers) as resp:
                            result_text = await resp.text()
                            if '"isPassed":true' in result_text:
                                print(
                                    f" √{Fore.LIGHTBLUE_EX}{display_name[:75]}{Style.RESET_ALL}: |{Fore.LIGHTBLUE_EX}{'____________________'}{Style.RESET_ALL}| 100% {v_time}/{v_time}秒    视频完成√",
                                    flush=True,
                                )
                                break

                        if not flag:
                            break

                        temp = random.randint(30, 60)

                        if playtime + temp >= v_time:
                            flag = False
                            temp = v_time - playtime
                            playtime = v_time
                        else:
                            playtime += temp

                        if await _sleep_async(temp, stop_event):
                            return

            except Exception:
                pass


async def finish_all_tasks_async(
    video_list: list[dict],
    base_enc: str,
    cookies: dict,
    course_name: str,
) -> None:
    """批量异步完成当前课程的所有任务点。

    为每个任务创建异步协程，按索引递增延迟后并发执行。

    Args:
        video_list: 任务参数列表，每项需包含 parent_chapter 和 chapter_name 字段
        base_enc: 课程章节加密标识
        cookies: 登录后的 cookies 字典
        course_name: 课程名称

    Returns:
        None。所有任务结束或被 R 取消后返回，返回前取消键盘监听协程。
    """
    semaphore = asyncio.Semaphore(200)
    stop_event = asyncio.Event()
    # 键盘监听是后台协程，只在 stop_event 置位时才退出，因此不能和刷课任务放进
    # 同一个 gather：否则所有任务跑完后 gather 仍在等监听协程，本函数永不返回。
    listener = asyncio.ensure_future(_keyboard_listener(stop_event))
    work_tasks = []
    for i, params in enumerate(video_list):
        delay = random.uniform(0.5, 1.5) * (i + 1)
        base_chapter_name = params.pop('parent_chapter', '未知章节')
        task_name = params.pop('chapter_name', '未知任务')

        async def delayed_task(
            p=params, d=delay, cn=base_chapter_name, tn=task_name, se=stop_event,
        ):
            await asyncio.sleep(d)
            if se.is_set():
                return
            return await finish_task_async(base_enc, p, cookies, semaphore, se, course_name, cn, tn)

        work_tasks.append(asyncio.ensure_future(delayed_task()))

    try:
        # return_exceptions=True: 个别任务协程抛异常时不中断整体等待，
        # 避免其余正在上报的视频被事件循环收尾时强制取消。
        results = await asyncio.gather(*work_tasks, return_exceptions=True)
    finally:
        listener.cancel()
        try:
            await listener
        except (asyncio.CancelledError, Exception):
            # 键盘监听只是辅助协程：被取消、或因 msvcrt 在非交互终端抛 OSError，
            # 都不应影响刷课结果与收尾输出。KeyboardInterrupt 不在捕获范围内。
            pass

    if stop_event.is_set():
        print("\n[R] 所有视频任务已取消")
    else:
        print("0v0 所有视频任务完成！")

    failures = [r for r in results if isinstance(r, BaseException)]
    if failures:
        print(f"[!] {len(failures)} 个任务协程异常退出，可重新进入课程重试")
