"""超星学习通常量配置模块。

统一管理所有 API 端点 URL、加密密钥和通用请求头。
"""

# -- API 端点 --
LOGIN_URL = 'https://passport2.chaoxing.com/fanyalogin'
SPACE_URL = 'https://i.mooc.chaoxing.com/space/index'
COURSE_LIST_URL = 'https://mooc1-1.chaoxing.com/mooc-ans/visit/courselistdata'
COURSE_DETAIL_URL = 'https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/studentcourse'
STUDY_AJAX_URL = 'https://mooc1.chaoxing.com/mooc-ans/mycourse/studentstudyAjax'
KNOWLEDGE_CARDS_URL = 'https://mooc1.chaoxing.com/mooc-ans/knowledge/cards'
DOCUMENT_FINISH_URL = 'https://mooc1.chaoxing.com/mooc-ans/job/document'
VIDEO_STATUS_URL = 'https://mooc1.chaoxing.com/ananas/status/{objectid}'
VIDEO_LOG_URL = 'https://mooc1.chaoxing.com/mooc-ans/multimedia/log/a/{cpi}/{dtoken}'

# -- 加密密钥 --
AES_KEY = 'u2oh6Vu^HWe4_AES'

# -- 通用请求头 --
COMMON_HEADERS = {
    'sec-ch-ua': '"Chromium";v="146", "Not-A.Brand";v="24", "Microsoft Edge";v="146"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0',
}