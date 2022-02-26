import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup


with open(os.path.join(os.path.dirname(__file__), '.env.json'), 'r') as f:
    env = json.load(f)
USER_ID    = env['user_id']
PASSWORD   = env['password']
LINE_TOKEN = env['line_token']

USER_AGENT    = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/85.0.4183.109 Mobile/15E148 Safari/604.1'
E_BASE_URL    = 'https://www.e-license.jp/el2'
E_MOBILE_HREF = '?abc=tZ%2FXW2Ic%2BpA%2BbrGQYS%2B1OA%3D%3D&senisakiCd=5'
LINE_URL      = 'https://notify-api.line.me/api/notify'
TARGET_STATE  = 'O'

SESSION   = requests.session()
TIME_LIST = [f'{str(i+8).zfill(2)}:00 ~' for i in range(12)]


def notify_line(message_list):
    r = requests.post(
        LINE_URL,
        headers={'Authorization': f'Bearer {LINE_TOKEN}'},
        params={'message': '\n' + '\n'.join(message_list)})
    print(r)
    print(r.text)


def session_acccess(href, param=None):
    if href[0] == '/':
        href = href[1:]
    url = os.path.join(E_BASE_URL, href)
    if param:
        response = SESSION.post(
            url,
            cookies=param['cookies'],
            data=param['data'],
            headers=param['headers'],
        )
    else:
        response = SESSION.get(url)
    response.encoding = 'shift_jis'
    time.sleep(1)
    if 'システムメンテナンス' in response.text:
        notify_texts = ['システムメンテナンス中です']
        notify_texts.append(f'\n{os.path.join(E_BASE_URL, E_MOBILE_HREF)}')
        notify_line(notify_texts)
        print('This page in maintenance.')
    else:
        return response, BeautifulSoup(response.text, 'html.parser')


def get_href(bs, link_text):
    return [l for l in bs.find_all('a') if l.text == link_text][0].get('href')


# セッション開始
response, bs = session_acccess(E_MOBILE_HREF)
cookies = response.cookies
login_info = {}
for element in bs.findAll('input'):
    login_info[element['name']] = element['value']
login_info['b.studentId'] = USER_ID
login_info['b.password'] = PASSWORD
login_href = f'mobile/m01a.action;jsessionid={cookies.get_dict()["JSESSIONID"]}'

# ログイン
response, bs = session_acccess(
    login_href,
    param={
        'cookies': cookies,
        'data': login_info,
        'headers': {'User-Agent': USER_AGENT}
    }
)
print('Login successfull.')


def seek_free_time(bs):
    free_times = []
    day_links = [l for l in bs.findAll('a') if re.match(r'..月..日\(.\)', l.text)]
    for day in day_links:
        status = day.next_sibling.next_element.strip().replace(' ', '')
        for i, state in enumerate(status):
            if state == TARGET_STATE:
                free_times.append(f"{day.text} {TIME_LIST[i]}")
    return free_times


# 技能予約ページ
response, bs = session_acccess(get_href(bs, '技能予約'))
free_times = seek_free_time(bs)
print('Ginou Yoyaku (this week)')

# 次週ページ
response, bs = session_acccess(get_href(bs, '次週'))
free_times += seek_free_time(bs)
print('Ginou Yoyaku (next week)')

# ログアウト
response, _ = session_acccess(get_href(bs, 'ﾛｸﾞｱｳﾄ'))
print('Logout successfull.')

# LINE通知
if len(free_times) > 0:
    free_times.append('上記の枠が空いています!!')
    free_times.append(f'\n{os.path.join(E_BASE_URL, E_MOBILE_HREF)}')
    notify_line(free_times)
