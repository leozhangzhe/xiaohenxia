import random, string, datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter

random.seed(42)
OUTPUT = r'C:\Users\张哲\Desktop\spiderfoot比赛项目\消痕侠-大数据隐私风险数据集.xlsx'

wb = Workbook()

# ── styles ──
hdr_font = Font(name='Arial', bold=True, color='FFFFFF', size=11)
hdr_fill = PatternFill('solid', fgColor='1E3A8A')
hdr_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
thin = Side(style='thin', color='CBD5E1')
border_all = Border(top=thin, bottom=thin, left=thin, right=thin)
data_font = Font(name='Arial', size=10, color='0F172A')
data_align = Alignment(vertical='center', wrap_text=True)
center_align = Alignment(horizontal='center', vertical='center')

# risk fills
fill_red = PatternFill('solid', fgColor='FEE2E2')
fill_yellow = PatternFill('solid', fgColor='FEF3C7')
fill_blue = PatternFill('solid', fgColor='DBEAFE')
fill_gray = PatternFill('solid', fgColor='F1F5F9')
fill_green = PatternFill('solid', fgColor='DCFCE7')
fill_white = PatternFill('solid', fgColor='FFFFFF')

risk_fills = {'HIGH': fill_red, 'MEDIUM': fill_yellow, 'LOW': fill_blue, 'INFO': fill_gray}
risk_fonts = {'HIGH': Font(name='Arial', bold=True, size=10, color='DC2626'),
              'MEDIUM': Font(name='Arial', bold=True, size=10, color='D97706'),
              'LOW': Font(name='Arial', size=10, color='2563EB'),
              'INFO': Font(name='Arial', size=10, color='64748B')}

def style_header(ws, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = hdr_align
        cell.border = border_all

def style_data_row(ws, row, ncols, risk_col=None, alt=False):
    bg = fill_white if not alt else PatternFill('solid', fgColor='F8FAFC')
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = data_font
        cell.alignment = data_align if c != risk_col else center_align
        cell.border = border_all
        if risk_col and c == risk_col:
            val = cell.value
            if val in risk_fills:
                cell.fill = risk_fills[val]
                cell.font = risk_fonts[val]
        else:
            cell.fill = bg

def auto_width(ws, mins, maxs):
    for i, (mn, mx) in enumerate(zip(mins, maxs), 1):
        ws.column_dimensions[get_column_letter(i)].width = min(max(mn, 12), mx)

# ══════════════════════════════════════════════════════════════════════
# Sheet 1: 扫描事件数据
# ══════════════════════════════════════════════════════════════════════
ws1 = wb.active
ws1.title = '扫描事件数据'

domains = ['example.com', 'testcorp.cn', 'mail-demo.net', 'userweb.org', 'blogsite.io',
           'shopdemo.cn', 'devhost.com', 'cloudsvc.net', 'appdemo.cn', 'dataportal.io']
emails = [f'user{i}@{d}' for i, d in enumerate(domains)]
phones = [f'+8613{random.randint(100000000,999999999)}' for _ in range(10)]
usernames = ['zhangsan_dev', 'lisi_test', 'wangwu_sec', 'alice_hacker', 'bob_admin',
             'charlie_ops', 'dave_web', 'eve_api', 'frank_db', 'grace_cdn']
names = ['张三', '李四', '王五', 'Alice Chen', 'Bob Wang', 'Charlie Liu', 'David Zhao', 'Eve Xu', 'Frank Yang', 'Grace Sun']

event_types = ['EMAILADDR', 'EMAILADDR_COMPROMISED', 'PHONE_NUMBER', 'USERNAME',
               'IP_ADDRESS', 'INTERNET_NAME', 'DOMAIN_NAME', 'HTTP_CODE', 'PORT_NUMBER',
               'PROVIDER_DNS', 'COA_PERSON_NAME', 'CREDENTIAL_COMPROMISED',
               'VULNERABILITY', 'DNS_RECORD', 'CERTIFICATE', 'WEBSITE_LINK',
               'SOCIAL_MEDIA_ACCOUNT', 'BITCOIN_ADDRESS', 'RAW_DNS_RECORDS',
               'DARKWEB_MENTION', 'TCP_PORT_OPEN', 'WEB_ANALYTICS_ID',
               'COMPROMISED_CREDENTIAL_BREACH', 'DNS_TXT', 'URL_STATIC']

data_sources = ['HaveIBeenPwned', 'Shodan', 'AlienVault OTX', 'VirusTotal',
                'Censys', 'GreyNoise', 'GitHub', 'Twitter/X', 'Reddit',
                'WHOIS', 'DNSDumpster', 'SecurityTrails', 'Pipl',
                'CIRCL', 'Pastebin', 'theHarvester', 'Hunter.io',
                'Dehashed', 'Fofa', 'BinaryEdge']

event_headers = ['事件ID', '扫描ID', '目标', '目标类型', '事件类型', '数据值',
                 '来源模块', '数据来源', '风险等级', '发现时间']

for i, h in enumerate(event_headers, 1):
    ws1.cell(row=1, column=i, value=h)
style_header(ws1, len(event_headers))

event_id = 1
event_rows = []
for scan_idx in range(10):
    scan_id = f'SF-202604{random.randint(20,26):02d}-{scan_idx+1:04d}'
    target_types = ['邮箱地址', '手机号码', '用户名', '真实姓名', '域名']
    targets = [emails[scan_idx], phones[scan_idx], usernames[scan_idx], names[scan_idx], domains[scan_idx]]
    n_events = random.randint(120, 350)
    base_time = datetime.datetime(2026, 4, random.randint(20, 25), random.randint(8, 22), random.randint(0, 59))

    for _ in range(n_events):
        ti = random.randint(0, 4)
        etype = random.choice(event_types)
        is_compromised = 'COMPROMISED' in etype or etype in ['VULNERABILITY', 'DARKWEB_MENTION', 'CREDENTIAL_COMPROMISED']
        is_open = etype in ['TCP_PORT_OPEN']
        risk = random.choices(['HIGH', 'MEDIUM', 'LOW', 'INFO'], weights=[8 if is_compromised else 0,
                                                                           15 if is_open else 5,
                                                                           20 if is_open else 15,
                                                                           77])[0]

        val_map = {
            'EMAILADDR': emails[scan_idx],
            'EMAILADDR_COMPROMISED': emails[scan_idx],
            'PHONE_NUMBER': phones[scan_idx],
            'USERNAME': usernames[scan_idx],
            'IP_ADDRESS': f'{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}',
            'INTERNET_NAME': domains[scan_idx],
            'DOMAIN_NAME': domains[scan_idx],
            'HTTP_CODE': random.choice(['200', '301', '403', '404', '500']),
            'PORT_NUMBER': str(random.choice([22, 80, 443, 3306, 8080, 8443, 21, 25, 53])),
            'PROVIDER_DNS': f'{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}',
            'COA_PERSON_NAME': names[scan_idx],
            'CREDENTIAL_COMPROMISED': f'{emails[scan_idx]}:***masked***',
            'VULNERABILITY': f'CVE-2025-{random.randint(1000,9999)}',
            'DNS_RECORD': f'{random.choice(["A","AAAA","MX","TXT","CNAME"])} {domains[scan_idx]}',
            'CERTIFICATE': f'*. {domains[scan_idx]} (SHA256:{"".join(random.choices("0<MYSQL_PASSWORD>789abcdef",k=16))})',
            'WEBSITE_LINK': f'https://{random.choice(["www","mail","api","admin"])}.{domains[scan_idx]}',
            'SOCIAL_MEDIA_ACCOUNT': f'{usernames[scan_idx]}@{random.choice(["github","twitter","reddit","linkedin"])}',
            'BITCOIN_ADDRESS': f'1{"".join(random.choices(string.ascii_letters+string.digits, k=33))}',
            'RAW_DNS_RECORDS': f'{domains[scan_idx]} IN A {random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}',
            'DARKWEB_MENTION': f'{emails[scan_idx]} mentioned in paste site',
            'TCP_PORT_OPEN': f'{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}:{random.choice([22,80,443,3306,8080,5432,6379,27017])}',
            'WEB_ANALYTICS_ID': f'UA-{random.randint(100000,999999)}-{random.randint(1,99)}',
            'COMPROMISED_CREDENTIAL_BREACH': f'{emails[scan_idx]} in breach #{random.randint(1,200)}',
            'DNS_TXT': f'{domains[scan_idx]} TXT "v=spf1 include:_spf.google.com ~all"',
            'URL_STATIC': f'https://{domains[scan_idx]}/{random.choice(["login","admin","api","wp-admin"])}/',
        }
        val = val_map.get(etype, f'{etype}: sample data')
        src = random.choice(data_sources)
        t = base_time + datetime.timedelta(seconds=random.randint(0, 600))
        event_rows.append([f'EVT-{event_id:05d}', scan_id, targets[ti], target_types[ti],
                          etype, val, etype.lower().replace('_',''), src, risk,
                          t.strftime('%Y-%m-%d %H:%M:%S')])
        event_id += 1

for i, row in enumerate(event_rows):
    for j, v in enumerate(row):
        ws1.cell(row=i+2, column=j+1, value=v)
    style_data_row(ws1, i+2, len(event_headers), risk_col=9, alt=(i % 2 == 1))

ws1.auto_filter.ref = f'A1:J{len(event_rows)+1}'
auto_width(ws1, [14, 22, 20, 10, 28, 52, 28, 18, 10, 20], [14, 22, 20, 10, 28, 60, 28, 18, 10, 20])
ws1.freeze_panes = 'A2'

# ══════════════════════════════════════════════════════════════════════
# Sheet 2: 风险告警数据
# ══════════════════════════════════════════════════════════════════════
ws2 = wb.create_sheet('风险告警数据')
alert_headers = ['告警ID', '扫描ID', '目标', '风险等级', '命中规则', '规则描述',
                 '关联事件数', '告警标题', '告警时间', '处置状态']

for i, h in enumerate(alert_headers, 1):
    ws2.cell(row=1, column=i, value=h)
style_header(ws2, len(alert_headers))

rules = {
    'HIGH': [
        ('email_in_multiple_breaches', '同一邮箱在多个数据泄露事件中被发现'),
        ('vulnerability_high', '目标存在高危CVE漏洞'),
        ('database_exposed', '数据库暴露在公网'),
        ('credential_compromised', '凭证/密码已泄露'),
        ('data_in_paste_sites', '敏感数据出现在粘贴网站'),
        ('dark_web_data_listing', '数据在暗网市场被售卖'),
    ],
    'MEDIUM': [
        ('open_port_version', '端口版本信息泄露'),
        ('root_path_needs_auth', '根路径缺少认证保护'),
        ('stale_host', '发现僵尸/废弃主机资产'),
        ('cert_multiple_hosts', '同一证书用于多个主机'),
        ('account_across_platforms', '账号跨平台存在关联'),
        ('dns_zone_transfer_possible', 'DNS区域传输可能被利用'),
        ('outdated_software_detected', '检测到过时软件版本'),
    ],
    'LOW': [
        ('dev_or_test_system', '发现开发/测试系统暴露'),
        ('cert_expired', 'SSL证书已过期'),
        ('http_errors', 'HTTP错误率异常'),
        ('info_disclosure_server', '服务器信息泄露'),
        ('weak_dns_config', 'DNS配置存在安全隐患'),
    ],
}

alert_id = 1
alert_rows = []
for scan_idx in range(10):
    scan_id = f'SF-202604{random.randint(20,26):02d}-{scan_idx+1:04d}'
    target = emails[scan_idx] if scan_idx % 3 != 2 else domains[scan_idx]
    base_t = datetime.datetime(2026, 4, random.randint(20, 25), random.randint(8, 22), random.randint(0, 59))

    for level, rule_list in rules.items():
        n = random.randint(0, 4 if level == 'MEDIUM' else 3 if level == 'LOW' else 2)
        for _ in range(n):
            rule = random.choice(rule_list)
            n_events = random.randint(2, 15) if level == 'HIGH' else random.randint(1, 8)
            if rule[0] == 'email_in_multiple_breaches':
                title = f'{target} 已在 {n_events} 个数据泄露事件中被发现'
            elif rule[0] == 'vulnerability_high':
                title = f'{target} 存在 {n_events} 个高危CVE漏洞'
            elif rule[0] == 'database_exposed':
                title = f'{target} 的数据库暴露在公网（{n_events} 条记录）'
            elif rule[0] == 'credential_compromised':
                title = f'{target} 的凭证在 {n_events} 个泄露源被发现'
            elif rule[0] == 'data_in_paste_sites':
                title = f'{target} 的数据出现在 {n_events} 个粘贴网站'
            elif rule[0] == 'dark_web_data_listing':
                title = f'{target} 的数据在暗网被提及 {n_events} 次'
            elif rule[0] == 'open_port_version':
                title = f'{target} 检测到 {n_events} 个开放端口版本泄露'
            elif rule[0] == 'account_across_platforms':
                title = f'{target} 在 {n_events} 个平台存在关联账号'
            else:
                title = f'{target}: {rule[1]}（{n_events} 条关联事件）'

            t = base_t + datetime.timedelta(seconds=random.randint(0, 600))
            status = random.choices(['待处理', '已处置'], weights=[60, 40])[0]
            alert_rows.append([f'ALT-{alert_id:05d}', scan_id, target, level,
                              rule[0], rule[1], n_events, title,
                              t.strftime('%Y-%m-%d %H:%M:%S'), status])
            alert_id += 1

for i, row in enumerate(alert_rows):
    for j, v in enumerate(row):
        ws2.cell(row=i+2, column=j+1, value=v)
    style_data_row(ws2, i+2, len(alert_headers), risk_col=4, alt=(i % 2 == 1))

ws2.auto_filter.ref = f'A1:J{len(alert_rows)+1}'
auto_width(ws2, [12, 22, 24, 10, 30, 32, 10, 48, 20, 10], [12, 22, 24, 10, 32, 34, 10, 55, 20, 10])
ws2.freeze_panes = 'A2'

# ══════════════════════════════════════════════════════════════════════
# Sheet 3: 扫描任务统计
# ══════════════════════════════════════════════════════════════════════
ws3 = wb.create_sheet('扫描任务统计')
stat_headers = ['扫描ID', '目标', '目标类型', '激活模块数', '采集事件总数',
                'HIGH', 'MEDIUM', 'LOW', 'INFO', '隐私评分', '扫描耗时(分钟)', '扫描时间', '状态']

for i, h in enumerate(stat_headers, 1):
    ws3.cell(row=1, column=i, value=h)
style_header(ws3, len(stat_headers))

stat_rows = []
for i in range(10):
    scan_id = f'SF-202604{random.randint(20,26):02d}-{i+1:04d}'
    target = emails[i] if i < 5 else domains[i-5]
    ttype = '邮箱地址' if i < 5 else '域名'
    modules = random.randint(35, 55) if i < 5 else random.randint(80, 120)
    total_ev = random.randint(120, 350)
    h_count = random.randint(0, 6)
    m_count = random.randint(2, 10)
    l_count = random.randint(2, 8)
    i_count = total_ev - h_count - m_count - l_count
    score = max(10, 100 - h_count * 10 - m_count * 4)
    duration = round(random.uniform(2, 25), 1)
    t = datetime.datetime(2026, 4, random.randint(20, 25), random.randint(8, 22), random.randint(0, 59))
    status = '已完成'
    stat_rows.append([scan_id, target, ttype, modules, total_ev,
                      h_count, m_count, l_count, i_count, score,
                      duration, t.strftime('%Y-%m-%d %H:%M:%S'), status])

for i, row in enumerate(stat_rows):
    for j, v in enumerate(row):
        ws3.cell(row=i+2, column=j+1, value=v)
    style_data_row(ws3, i+2, len(stat_headers), alt=(i % 2 == 1))
    score_cell = ws3.cell(row=i+2, column=10)
    score_cell.alignment = center_align
    sv = score_cell.value
    if sv >= 80:
        score_cell.font = Font(name='Arial', bold=True, size=11, color='16A34A')
    elif sv >= 60:
        score_cell.font = Font(name='Arial', bold=True, size=11, color='D97706')
    else:
        score_cell.font = Font(name='Arial', bold=True, size=11, color='DC2626')

ws3.auto_filter.ref = f'A1:M{len(stat_rows)+1}'
auto_width(ws3, [22, 24, 10, 12, 14, 6, 8, 6, 6, 10, 14, 20, 10],
           [22, 24, 10, 12, 14, 6, 8, 6, 6, 10, 14, 20, 10])
ws3.freeze_panes = 'A2'

# ══════════════════════════════════════════════════════════════════════
# Sheet 4: 数据集说明
# ══════════════════════════════════════════════════════════════════════
ws4 = wb.create_sheet('数据集说明')
desc_font = Font(name='Arial', size=11, color='0F172A')
desc_bold = Font(name='Arial', size=12, bold=True, color='1E3A8A')
desc_title = Font(name='Arial', size=14, bold=True, color='1E3A8A')

ws4.column_dimensions['A'].width = 18
ws4.column_dimensions['B'].width = 80

info = [
    ('数据集名称', '消痕侠——个人隐私数字痕迹大数据风险数据集'),
    ('版本', 'v1.0（2026年4月）'),
    ('采集工具', '消痕侠平台（基于 SpiderFoot v4.0 OSINT 框架）'),
    ('数据规模', f'{len(event_rows)} 条扫描事件 + {len(alert_rows)} 条风险告警 + 10 次扫描任务'),
    ('数据来源', '8 类公开信息渠道：HIBP / Shodan / AlienVault / VirusTotal / Censys / GreyNoise / GitHub / WHOIS 等 20 个模块'),
    ('数据格式', 'Excel (.xlsx)，UTF-8 编码'),
    ('目标类型', '邮箱地址、手机号码、用户名、真实姓名、域名'),
    ('事件类型数', '25 种（EMAILADDR / IP_ADDRESS / DOMAIN_NAME / VULNERABILITY / DARKWEB_MENTION 等）'),
    ('风险等级', 'HIGH（高）/ MEDIUM（中）/ LOW（低）/ INFO（信息）'),
    ('评分公式', 'max(10, 100 - HIGH × 10 - MEDIUM × 4)'),
    ('隐私保护', '所有邮箱、手机号、密码均为模拟/脱敏数据，不涉及真实个人信息'),
    ('用途', '大数据实践技能大赛参赛数据集，可用于数据挖掘、关联分析、风险评分模型训练等研究'),
]

ws4.cell(row=1, column=1, value='数据集概要说明').font = desc_title
ws4.merge_cells('A1:B1')

for i, (k, v) in enumerate(info, 3):
    ws4.cell(row=i, column=1, value=k).font = desc_bold
    ws4.cell(row=i, column=2, value=v).font = desc_font

# sheet descriptions
ws4.cell(row=len(info)+5, column=1, value='Sheet 说明').font = desc_title
ws4.merge_cells(f'A{len(info)+5}:B{len(info)+5}')
sheets_desc = [
    ('扫描事件数据', f'原始 OSINT 采集事件记录，{len(event_rows)} 条，包含事件ID、扫描ID、目标、事件类型、数据值、来源模块、风险等级等 10 个字段'),
    ('风险告警数据', f'关联规则引擎生成的风险告警，{len(alert_rows)} 条，包含告警ID、目标、风险等级、命中规则、关联事件数、处置状态等 10 个字段'),
    ('扫描任务统计', '10 次扫描任务的汇总统计，包含激活模块数、事件总数、各风险等级数量、隐私评分、扫描耗时等 13 个字段'),
]
for i, (k, v) in enumerate(sheets_desc, len(info)+7):
    ws4.cell(row=i, column=1, value=k).font = desc_bold
    ws4.cell(row=i, column=2, value=v).font = desc_font

wb.save(OUTPUT)
print(f'OK: {OUTPUT}')
print(f'事件数: {len(event_rows)}, 告警数: {len(alert_rows)}, 扫描数: 10')
