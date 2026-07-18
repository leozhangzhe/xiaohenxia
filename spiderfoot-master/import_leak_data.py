# -*- coding: utf-8 -*-
"""从数据集 xlsx 导入数据到 leak-check.db"""
import sqlite3, random, os, sys
from collections import defaultdict

# 路径
BASE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(BASE, '..', '消痕侠-大数据隐私风险数据集.xlsx')
DB = os.path.join(BASE, 'data', 'leak-check.db')

import openpyxl
wb = openpyxl.load_workbook(XLSX, read_only=True)
ws = wb['扫描事件数据']

target_events = defaultdict(list)
for r in ws.iter_rows(min_row=2, values_only=True):
    target = str(r[2]) if r[2] else ''
    evt_type = str(r[4]) if r[4] else ''
    data_val = str(r[5]) if r[5] else ''
    target_events[target].append({'evt': evt_type, 'val': data_val})
wb.close()

# 构建人物画像
persons = []
seen_phones = set()

for target, evts in target_events.items():
    phone = None
    if target.startswith('+86'):
        phone = target.replace('+86', '')

    email = None
    if '@' in target and 'breach' not in target and 'masked' not in target and 'paste' not in target and 'mentioned' not in target:
        email = target

    if not phone and not email:
        continue

    # 去重
    if phone and phone in seen_phones:
        continue
    if phone:
        seen_phones.add(phone)

    # 提取姓名
    name = None
    for e in evts:
        if e['evt'] == 'COA_PERSON_NAME':
            n = e['val'].strip()
            if n and len(n) > 0:
                name = n
                break

    # 提取社交账号
    nicknames = set()
    for e in evts:
        v = e['val']
        if any(x in v for x in ['@github', '@twitter', '@linkedin', '@reddit']):
            nick = v.split('@')[-1].strip()
            nicknames.add(nick)

    # 提取关联邮箱
    linked_emails = set()
    for e in evts:
        v = e['val']
        if '@' in v and 'breach' not in v and 'masked' not in v and 'paste' not in v and 'mentioned' not in v:
            linked_emails.add(v)

    if phone and not email and linked_emails:
        email = linked_emails.pop()
    elif not phone and email:
        for e in evts:
            if e['val'].startswith('+86'):
                phone = e['val'].replace('+86', '')
                break

    persons.append({
        'name': name,
        'phone': phone,
        'email': email,
        'nickname': ', '.join(nicknames) if nicknames else None,
    })

# 写入数据库
conn = sqlite3.connect(DB)
conn.execute('DELETE FROM person')
conn.execute('DELETE FROM source')

sources = [
    'SpiderFoot OSINT',
    'HIBP Breach DB',
    'Shodan IoT',
    'Dark Web Trade',
]
for i, s in enumerate(sources, 1):
    conn.execute('INSERT INTO source (id, source) VALUES (?, ?)', (i, s))
conn.commit()

for p in persons:
    source_id = random.randint(1, len(sources))
    conn.execute('''INSERT INTO person (id, name, receiver, nickname, phone, address, car, email, qq, weibo, contact, company, source_id)
        VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (p['name'], p['name'], p['nickname'], p['phone'], None, None, p['email'],
         None, None, None, None, source_id))

conn.commit()
count = conn.execute('SELECT COUNT(*) FROM person').fetchone()[0]
conn.close()

print(f"Done: {count} records imported")
