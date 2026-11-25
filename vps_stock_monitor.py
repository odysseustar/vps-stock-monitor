#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""US West CN2 GIA Limited-Edition VPS Stock Monitor (BandwagonHost & DMIT)."""

import html
import json
import os
import random
import re
import smtplib
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.environ.get('STATE_FILE', os.path.join(BASE_DIR, 'state.json'))

SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.163.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '465'))
SMTP_USER = os.environ.get('SMTP_USER', '').strip()
SMTP_PASS = os.environ.get('SMTP_PASS', '').strip()
RECIPIENT = (os.environ.get('RECIPIENT', '') or SMTP_USER).strip()

BJT = timezone(timedelta(hours=8))

# Dynamic unknown-plan discovery thresholds (US West CN2 GIA focus)
BWG_KNOWN_MAX_PID = 178
BWG_EXTRA_MAX_ANNUAL_USD = 125.0
VD_EXTRA_MAX_MONTHLY_USD = 10.5  # <= $126/year

# 美西 CN2 GIA 专精监控清单（共 12 款，已移除非 CN2 GIA 的 LAX.EB 系列）
TARGETS = {
    # ==================== T0: 旗舰特惠级（$38 ~ $53 / 年，有货闭眼冲） ====================
    'bwg:157': {
        'tier_group': 'T0',
        'tier': 'T0 · 🥇首选 No.1',
        'tier_color': '#dc2626',
        'merchant': 'BandwagonHost',
        'name': 'MegaBox Pro Limited',
        'price': '$49.00 / 年',
        'specs': '2核 AMD / 2GB / 40GB SSD / 2000GB @ 2.5Gbps',
        'reason': '洛杉矶 DC1 机房，电信双程 CN2 GIA + 移动双程 CMIN2 + 联通回程 GIA，2核2G 高配性价比天花板',
        'url': 'https://bwh81.net/cart.php?a=add&pid=157',
        'bwg_pid': '157',
        'vd_id': 'bandwagon:157',
    },
    'bwg:156': {
        'tier_group': 'T0',
        'tier': 'T0 · 🥈首选 No.2',
        'tier_color': '#dc2626',
        'merchant': 'BandwagonHost',
        'name': 'BiggerBox Pro Limited',
        'price': '$39.00 / 年',
        'specs': '1核 AMD / 1GB / 20GB SSD / 1000GB @ 2.5Gbps',
        'reason': '洛杉矶 DC1 机房，电信双程 CN2 GIA + 移动 CMIN2；抢到后常可在后台补差价一键升级 MegaBox Pro',
        'url': 'https://bwh81.net/cart.php?a=add&pid=156',
        'bwg_pid': '156',
        'vd_id': 'bandwagon:156',
    },
    'dmit:186': {
        'tier_group': 'T0',
        'tier': 'T0 · 🥉首选 No.3',
        'tier_color': '#dc2626',
        'merchant': 'DMIT',
        'name': 'LAX.Pro.MALIBU',
        'price': '$49.90 / 年',
        'specs': '1核 AMD Zen4 / 1GB / 20GB SSD / 1000GB @ 1Gbps',
        'reason': '洛杉矶 Pro 系列三网纯 CN2 GIA，原生 IP 质量显著优于广播 IP，1TB 流量经典限量款',
        'url': 'https://www.dmit.io/cart.php?a=add&pid=186',
        'vd_id': 'dmit:LAX.Pro.MALIBU',
    },
    'dmit:183': {
        'tier_group': 'T0',
        'tier': 'T0 · 🏅首选 No.4',
        'tier_color': '#dc2626',
        'merchant': 'DMIT',
        'name': 'LAX.Pro.Wee',
        'price': '$39.90 / 年',
        'specs': '1核 AMD Zen4 / 1GB / 20GB SSD / 500GB @ 500Mbps',
        'reason': '洛杉矶 Pro 系列三网纯 CN2 GIA + 原生 IP，高性价比入门限量年付款',
        'url': 'https://www.dmit.io/cart.php?a=add&pid=183',
        'vd_id': 'dmit:LAX.Pro.Wee',
    },
    'bwg:145': {
        'tier_group': 'T0',
        'tier': 'T0 · 🏅首选 No.5',
        'tier_color': '#dc2626',
        'merchant': 'BandwagonHost',
        'name': 'DC9 CN2 GIA Limited Edition',
        'price': '$38.00 / 年',
        'specs': '1核 AMD / 768MB / 15GB SSD / 750GB @ 1.5Gbps',
        'reason': '洛杉矶 DC9 (USCA_9) 经典电信直连 CN2 GIA，最低价年付限量门槛款',
        'url': 'https://bwh81.net/cart.php?a=add&pid=145',
        'bwg_pid': '145',
        'vd_id': 'bandwagon:145',
    },
    'bwg:149': {
        'tier_group': 'T0',
        'tier': 'T0 · 🏅首选 No.6',
        'tier_color': '#dc2626',
        'merchant': 'BandwagonHost',
        'name': 'THE DC6 PLAN Limited',
        'price': '$53.00 / 年',
        'specs': '1核 / 1GB / 20GB SSD / 1000GB @ 2.5Gbps',
        'reason': '洛杉矶 DC6 (USCA_6) CN2 GIA-E 商务专线标准配置限量款',
        'url': 'https://bwh81.net/cart.php?a=add&pid=149',
        'bwg_pid': '149',
        'vd_id': 'bandwagon:149',
    },

    # ==================== T1: 经典多机房 / 高配限量（$50 ~ $100 / 年） ====================
    'bwg:94': {
        'tier_group': 'T1',
        'tier': 'T1 · 多机房限量',
        'tier_color': '#d97706',
        'merchant': 'BandwagonHost',
        'name': 'CN2 GIA-E 10G Limited',
        'price': '$49.99 / 年',
        'specs': '1核 / 512MB / 10GB SSD / 500GB @ 1Gbps',
        'reason': '支持后台自由切换 DC6 / DC9 / 日本软银 / 荷兰 9929 等多机房的经典限量款',
        'url': 'https://bwh81.net/cart.php?a=add&pid=94',
        'bwg_pid': '94',
        'vd_id': 'bandwagon:94',
    },
    'bwg:143': {
        'tier_group': 'T1',
        'tier': 'T1 · DC9 高配限量',
        'tier_color': '#d97706',
        'merchant': 'BandwagonHost',
        'name': 'DC9 CN2 GIA 20G Limited',
        'price': '$79.99 / 年',
        'specs': '1核 / 1GB / 20GB SSD / 1000GB @ 1Gbps',
        'reason': '洛杉矶 DC9 CN2 GIA 1TB 流量款，支持切换多个洛杉矶与常规机房',
        'url': 'https://bwh81.net/cart.php?a=add&pid=143',
        'bwg_pid': '143',
        'vd_id': 'bandwagon:143',
    },
    'bwg:132': {
        'tier_group': 'T1',
        'tier': 'T1 · GIA-E 高配',
        'tier_color': '#d97706',
        'merchant': 'BandwagonHost',
        'name': 'CN2 GIA-E 40G Limited',
        'price': '$89.90 / 年',
        'specs': '2核 / 2GB / 40GB SSD / 1000GB @ 2.5Gbps',
        'reason': '2核2G 多机房 CN2 GIA-E（DC6 / DC9 / 圣何塞 / 软银 / 荷兰 9929 自由切换）',
        'url': 'https://bwh81.net/cart.php?a=add&pid=132',
        'bwg_pid': '132',
        'vd_id': 'bandwagon:132',
    },
    'bwg:147': {
        'tier_group': 'T1',
        'tier': 'T1 · 全能传家宝',
        'tier_color': '#d97706',
        'merchant': 'BandwagonHost',
        'name': 'THE PLAN Limited',
        'price': '$99.00 / 年',
        'specs': '2核 / 2GB / 40GB SSD / 1000GB @ 2.5Gbps',
        'reason': '搬瓦工全能机房限量款，后台一键切换 DC6/DC9 CN2 GIA、日本软银及港日优质节点',
        'url': 'https://bwh81.net/cart.php?a=add&pid=147',
        'bwg_pid': '147',
        'vd_id': 'bandwagon:147',
    },
    'dmit:182': {
        'tier_group': 'T1',
        'tier': 'T1 · DMIT 高配',
        'tier_color': '#d97706',
        'merchant': 'DMIT',
        'name': 'LAX.Pro.PalmSpring',
        'price': '$100.00 / 年',
        'specs': '2核 / 2GB / 40GB SSD / 2000GB @ 2Gbps',
        'reason': '洛杉矶 Pro 系列大流量原生 IP 纯 CN2 GIA，2核2G + 2TB 流量 + 2Gbps 端口',
        'url': 'https://www.dmit.io/cart.php?a=add&pid=182',
        'vd_id': 'dmit:LAX.Pro.PalmSpring',
    },

    # ==================== T2: 月付常青备选 ====================
    'dmit:253': {
        'tier_group': 'T2',
        'tier': 'T2 · 月付常青款',
        'tier_color': '#2563eb',
        'merchant': 'DMIT',
        'name': 'LAX.AN3.Pro.TINY',
        'price': '$10.90 / 月',
        'specs': '1核 AMD / 2GB / 20GB SSD / 1000GB @ 1Gbps',
        'reason': '洛杉矶 Pro 系列常规月付纯 CN2 GIA 入门款，适合随时上车过渡',
        'url': 'https://www.dmit.io/cart.php?a=add&pid=253',
        'vd_id': 'dmit:LAX.AN3.Pro.TINY',
    },
}

KNOWN_VD_IDS = {v['vd_id'] for v in TARGETS.values() if v.get('vd_id')}
KNOWN_BWG_PIDS = {v['bwg_pid'] for v in TARGETS.values() if v.get('bwg_pid')}

# 精准 Telegram 促销/补货关键词（ASCII 词带词边界，避免误匹配 problem/official/offline 等噪声词）
TG_KEYWORD_RE = re.compile(
    r'(补货|上新|促销|黑五|优惠|特惠|限时|闪购|限量|折扣|放货|新品|开售|'
    r'BLACK\s*FRIDAY|CYBER\s*MONDAY|RESTOCK|IN\s+STOCK|PROMO|LIMITED\s+EDITION|'
    r'DISCOUNT|COUPON|CN2\s*GIA|BIGGERBOX|MEGABOX|MINIBOX|THE\s+PLAN|'
    r'MALIBU|PALMSPRING|CORONA|\bWEE\b|\bDC1\b|\bDC6\b|\bDC9\b|\bLAX\.PRO\b)',
    re.IGNORECASE,
)


def log_err(msg):
    print(f'[WARN] {msg}', file=sys.stderr)


def http_get(url, timeout=12):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/json,*/*',
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='ignore')


def esc(val):
    return html.escape(str(val or ''), quote=True)


def parse_float(val, default=9999.0):
    try:
        cleaned = re.sub(r'[^0-9.]', '', str(val or ''))
        return float(cleaned) if cleaned else default
    except Exception:
        return default


def clean_direct_url(slug, raw_url, fallback_pid=None):
    """Strip affiliate tracking parameters and rebuild official cart URLs."""
    pid = fallback_pid
    if raw_url:
        try:
            parsed = urllib.parse.urlparse(raw_url)
            qs = urllib.parse.parse_qs(parsed.query)
            if 'pid' in qs and qs['pid']:
                pid = qs['pid'][0]
        except Exception:
            pass
    if slug == 'bandwagon' and pid:
        return f'https://bwh81.net/cart.php?a=add&pid={pid}'
    if slug == 'dmit' and pid:
        return f'https://www.dmit.io/cart.php?a=add&pid={pid}'
    return raw_url or ''


def is_bwg_us_cn2_gia_candidate(item):
    """Identify US West CN2 GIA / DC1 Box / brand-new limited BWG plans from stock.bwg.net."""
    pid_str = str(item.get('pid', '')).strip()
    try:
        pid_num = int(pid_str)
    except ValueError:
        return False

    price = parse_float(item.get('price'), 9999.0)
    if price > BWG_EXTRA_MAX_ANNUAL_USD:
        return False

    dc = str(item.get('datacenter') or '')
    ctype = str(item.get('circuit_type') or '')
    cats = [str(c).lower() for c in (item.get('category') or [])]
    blob = f'{dc} {ctype}'.upper()

    # 1. Explicit US West CN2 GIA / DC1 Box markers (avoid matching Amsterdam EUNL_1)
    if any(m in blob for m in ('USCA_1', 'USCA_6', 'USCA_9', 'USCA_SJC5', 'DC6 CN2 GIA', 'DC9 CN2 GIA')):
        return True
    if 'cn2-gia-e' in cats:
        return True
    if 'CN2 GIA' in blob and any(us in blob for us in ('美国', 'LOS ANGELES', 'USCA', 'SJC', 'SAN JOSE')):
        return True

    # 2. Brand-new unknown PID (> current max 178) limited-edition catch-all
    if pid_num > BWG_KNOWN_MAX_PID:
        is_limited = ('limited' in cats) or any(k in blob for k in ('限量', 'LIMITED', 'BOX', 'PLAN', 'BF', 'BLACK'))
        is_pure_non_us = bool(dc.strip()) and not any(us in blob for us in ('美国', 'USCA', 'LOS ANGELES', 'SJC'))
        is_non_cn2_fremont = ('USCA_FMT' in blob) and ('CN2' not in blob) and ('USCA_1' not in blob) and ('USCA_6' not in blob) and ('USCA_9' not in blob)
        if is_limited and not is_pure_non_us and not is_non_cn2_fremont:
            return True
    return False


def is_vd_us_cn2_gia_candidate(plan):
    """Identify unlisted US West CN2 GIA plans from vpsding.com/api/plans."""
    slug = plan.get('slug')
    if slug not in ('dmit', 'bandwagon') or plan.get('stock') != 'in':
        return False

    usd_mo = parse_float(plan.get('usdMonth'), 999.0)
    if usd_mo > VD_EXTRA_MAX_MONTHLY_USD:
        return False

    pid_id = str(plan.get('id') or '')
    name = str(plan.get('name') or '')
    line = str(plan.get('line') or '')
    tags = ' '.join(str(t) for t in (plan.get('tags') or []))
    blob = f'{pid_id} {name} {line} {tags}'.upper()

    if slug == 'dmit':
        # Only LAX Pro / sPro / AN3.Pro CN2 GIA (exclude LAX.EB and LAX.T1)
        if any(bad in blob for bad in ('LAX.EB', 'LAX.T1', '.T1.', '.EB.')):
            return False
        is_lax = (plan.get('region') == 'US') or ('LAX' in blob)
        is_gia = ('CN2 GIA' in blob) or ('CN2GIA' in blob) or ('LAX.PRO' in blob) or ('LAX.SPRO' in blob) or ('LAX.AN3.PRO' in blob)
        return is_lax and is_gia

    # BandwagonHost: do not require region == 'US' so multi-DC plans like THE PLAN v2 (region=HK) are caught
    if any(m in blob for m in ('USCA_1', 'USCA_6', 'USCA_9', 'USCA_SJC5', 'DC6 CN2 GIA', 'DC9 CN2 GIA')):
        return True
    if 'CN2 GIA' in blob and any(us in blob for us in ('美国', 'LOS ANGELES', 'USCA', 'SJC')):
        return True
    return False


def verify_bwg_cart(pid_str):
    """First-party cart verification on bwh81.net.
    Returns: False (confirmed out of stock), True (looks available), None (network/parse error).
    """
    try:
        page = http_get(f'https://bwh81.net/cart.php?a=add&pid={pid_str}', timeout=8)
        if 'out of stock' in page.lower():
            return False
        return True
    except Exception as e:
        log_err(f'bwh81.net cart verification failed for pid={pid_str}: {e}')
        return None


def send_email(subject, html_body):
    if not SMTP_USER or not SMTP_PASS or not RECIPIENT:
        raise RuntimeError('请在环境变量或 GitHub Secrets 中配置 SMTP_USER 与 SMTP_PASS')
    msg = MIMEMultipart('alternative')
    msg['From'] = formataddr((str(Header('US West CN2 GIA Monitor', 'utf-8')), SMTP_USER))
    msg['To'] = RECIPIENT
    msg['Subject'] = Header(subject, 'utf-8')
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid()
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [RECIPIENT], msg.as_string())


def check_all_sources():
    """Query vpsding.com and stock.bwg.net with explicit source health tracking.
    Each target result is True (in stock), False (confirmed out of stock), or None (unknown/source failed).
    """
    vd_results = {}
    bwg_results = {}
    extra_map = {}  # canonical_id -> item dict (deduped across sources)

    vd_ok = False
    bwg_ok = False

    # 1. Check vpsding.com/api/plans (Covers both DMIT and BandwagonHost)
    try:
        vd_data = json.loads(http_get('https://vpsding.com/api/plans', timeout=12))
        plans = vd_data.get('plans')
        if not isinstance(plans, list) or not plans:
            raise ValueError('vpsding plans list empty or malformed')
        vd_ok = True
        vd_map = {p.get('id'): p for p in plans}

        for key, info in TARGETS.items():
            vd_id = info.get('vd_id')
            if vd_id and vd_id in vd_map:
                vd_results[key] = (vd_map[vd_id].get('stock') == 'in')

        for p in plans:
            if not is_vd_us_cn2_gia_candidate(p):
                continue
            raw_id = str(p.get('id') or '')
            if raw_id in KNOWN_VD_IDS:
                continue

            slug = p.get('slug')
            bwg_pid = None
            canon_id = raw_id
            if slug == 'bandwagon':
                m = re.match(r'^bandwagon:(\d+)', raw_id)
                if m:
                    bwg_pid = m.group(1)
                    if bwg_pid in KNOWN_BWG_PIDS:
                        continue
                    canon_id = f'bwg:{bwg_pid}'

            buy_url = clean_direct_url(slug, p.get('buy', ''), fallback_pid=bwg_pid)
            extra_map[canon_id] = {
                'id': canon_id,
                'source': 'vd',
                'bwg_pid': bwg_pid,
                'tier': '🔥 新增美西 CN2 GIA 特惠',
                'tier_color': '#dc2626',
                'merchant': p.get('merchant') or ('BandwagonHost' if slug == 'bandwagon' else 'DMIT'),
                'name': p.get('name') or canon_id,
                'price': p.get('priceText') or f"${p.get('usdMonth')}/月",
                'specs': f"{p.get('cpu')} / {p.get('ram')} / {p.get('disk')} / {p.get('traffic')} @ {p.get('bw')}",
                'reason': f"检测到在售美西 CN2 GIA 限量/特惠 ({p.get('line')})",
                'url': buy_url,
            }
    except Exception as e:
        log_err(f'vpsding.com query failed: {e}')

    # 2. Check stock.bwg.net/api/products (Fastest BWG 1st-party-adjacent tracker + catches brand-new PIDs!)
    try:
        bwg_data = json.loads(http_get('https://stock.bwg.net/api/products', timeout=12))
        if not isinstance(bwg_data, list) or not bwg_data:
            raise ValueError('stock.bwg.net product list empty or malformed')
        bwg_ok = True
        bwg_map = {str(p.get('pid')): p for p in bwg_data if p.get('pid') is not None}

        for key, info in TARGETS.items():
            bpid = info.get('bwg_pid')
            if bpid and bpid in bwg_map:
                bwg_results[key] = (int(bwg_map[bpid].get('status', 0)) == 1)

        # Dynamically capture unlisted & brand-new unknown PIDs
        for p in bwg_data:
            if int(p.get('status', 0)) != 1:
                continue
            bpid = str(p.get('pid', '')).strip()
            if not bpid or bpid in KNOWN_BWG_PIDS:
                continue
            if not is_bwg_us_cn2_gia_candidate(p):
                continue

            canon_id = f'bwg:{bpid}'
            dc_clean = str(p.get('datacenter') or '').replace('\n', ' / ').strip()
            is_brand_new = bpid.isdigit() and int(bpid) > BWG_KNOWN_MAX_PID
            tier_label = '🚨 全新黑五/限量 PID 上新' if is_brand_new else '🔥 搬瓦工美西 CN2 GIA 限量'
            extra_map[canon_id] = {
                'id': canon_id,
                'source': 'bwg',
                'bwg_pid': bpid,
                'tier': tier_label,
                'tier_color': '#dc2626',
                'merchant': 'BandwagonHost',
                'name': p.get('circuit_type') or f'BWG Plan #{bpid}',
                'price': f"${p.get('price')} / 年",
                'specs': f"{p.get('cpu')}核 / {p.get('memory')} / {p.get('ssd')} / {p.get('band')} @ {p.get('bandwidth')}",
                'reason': f"stock.bwg.net 捕获在售限量 (PID={bpid} | {dc_clean or '待确认机房'})",
                'url': f'https://bwh81.net/cart.php?a=add&pid={bpid}',
            }
    except Exception as e:
        log_err(f'stock.bwg.net query failed: {e}')

    # Merge target results: preserve None when all relevant sources failed
    results = {}
    for key, info in TARGETS.items():
        if info.get('bwg_pid'):
            vals = [v for v in (vd_results.get(key), bwg_results.get(key)) if v is not None]
            if not vals:
                results[key] = None
            else:
                results[key] = any(vals)
        else:
            results[key] = vd_results.get(key)  # None if vpsding failed or missing

    # 3. Direct 1st-party double-verification on bwh81.net/cart.php for positive BWG targets
    for key, info in TARGETS.items():
        bpid = info.get('bwg_pid')
        if bpid and results.get(key) is True:
            verified = verify_bwg_cart(bpid)
            if verified is False:
                results[key] = False

    # Also double-verify BWG extra deals to avoid stale aggregator false alarms
    verified_extras = []
    for canon_id, item in extra_map.items():
        bpid = item.get('bwg_pid')
        if bpid:
            verified = verify_bwg_cart(bpid)
            if verified is False:
                continue
        verified_extras.append(item)

    return results, verified_extras, {'vd_ok': vd_ok, 'bwg_ok': bwg_ok}


def parse_tg_post_num(post_id):
    if not post_id or '/' not in str(post_id):
        return 0
    try:
        return int(str(post_id).rsplit('/', 1)[1])
    except ValueError:
        return 0


def check_tg_channel(channel_name, prev_post_id):
    """Fetch public Telegram web preview and return ALL new posts with msg_num > prev_num.
    Returns (latest_post_id, matched_posts, ok) where matched_posts is list of (post_id, clean_text).
    """
    try:
        page = http_get(f'https://t.me/s/{channel_name}', timeout=12)
    except Exception as e:
        log_err(f'Telegram @{channel_name} fetch failed: {e}')
        return prev_post_id, [], False

    blocks = page.split('class="tgme_widget_message_wrap')
    if len(blocks) <= 1:
        log_err(f'Telegram @{channel_name} returned no message blocks')
        return prev_post_id, [], False

    prev_num = parse_tg_post_num(prev_post_id)
    max_num = prev_num
    max_post_id = prev_post_id
    new_posts = []

    for block in blocks[1:]:
        m_id = re.search(r'data-post="([^"]+)"', block)
        if not m_id:
            continue
        post_id = m_id.group(1)
        num = parse_tg_post_num(post_id)
        if num <= 0:
            continue

        if num > max_num:
            max_num = num
            max_post_id = post_id

        if prev_num > 0 and num > prev_num:
            m_tx = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', block, re.S)
            if m_tx:
                raw_text = re.sub(r'<br\s*/?>', ' ', m_tx.group(1), flags=re.I)
                raw_text = re.sub(r'<[^>]+>', ' ', raw_text)
                clean_text = re.sub(r'\s+', ' ', html.unescape(raw_text)).strip()
                if clean_text and TG_KEYWORD_RE.search(clean_text):
                    new_posts.append((post_id, clean_text))

    return max_post_id, new_posts, True


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault('stock', {})
                    data.setdefault('tg', {})
                    data.setdefault('extra', {})
                    return data
        except Exception as e:
            log_err(f'Failed to read {STATE_FILE}: {e}')
    return {'stock': {}, 'tg': {}, 'extra': {}}


def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write('\n')


def build_test_email_html(results, extra_deals, now_str, health):
    tier_counts = {'T0': 0, 'T1': 0, 'T2': 0}
    rows_html = ''

    for key, info in TARGETS.items():
        grp = info.get('tier_group', 'T2')
        if grp in tier_counts:
            tier_counts[grp] += 1
        status = results.get(key)
        if status is True:
            badge = '<span style="color:#16a34a;font-weight:bold;">🟢 有货</span>'
        elif status is False:
            badge = '<span style="color:#dc2626;">🔴 缺货</span>'
        else:
            badge = '<span style="color:#d97706;">🟡 查询失败</span>'

        rows_html += f'''
        <tr>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;white-space:nowrap;">
            <span style="background:{esc(info['tier_color'])};color:#fff;padding:3px 7px;border-radius:4px;font-size:12px;font-weight:bold;">{esc(info['tier'])}</span>
          </td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;white-space:nowrap;"><b>{esc(info['merchant'])}</b></td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;">
            <b>{esc(info['name'])}</b><br>
            <span style="font-size:12px;color:#4b5563;">{esc(info['specs'])}</span><br>
            <span style="font-size:12px;color:#059669;">💡 {esc(info['reason'])}</span>
          </td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;color:#d97706;font-weight:bold;white-space:nowrap;">{esc(info['price'])}</td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;white-space:nowrap;">{badge}</td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;white-space:nowrap;"><a href="{esc(info['url'])}" style="color:#2563eb;font-weight:bold;text-decoration:none;">官网直达 &rarr;</a></td>
        </tr>'''

    extra_html = ''
    if extra_deals:
        extra_html += '<h3 style="color:#dc2626;margin-top:20px;">🚨 动态捕获的未收录美西 CN2 GIA 限量/新品</h3><ul>'
        for item in extra_deals:
            extra_html += (
                f'<li style="margin-bottom:10px;"><b>【{esc(item["merchant"])}】{esc(item["name"])} — {esc(item["price"])}</b><br>'
                f'配置：{esc(item["specs"])}<br>'
                f'说明：{esc(item["reason"])}<br>'
                f'<a href="{esc(item["url"])}">{esc(item["url"])}</a></li>'
            )
        extra_html += '</ul>'

    src_badge = f"vpsding={'✅' if health['vd_ok'] else '❌'} | stock.bwg={'✅' if health['bwg_ok'] else '❌'}"
    return f'''
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:880px;margin:0 auto;padding:20px;border:1px solid #e5e7eb;border-radius:10px;background:#ffffff;">
      <h2 style="color:#111827;margin-top:0;">☁️ 美西 CN2 GIA 专精监控报表（共 {len(TARGETS)} 款 + 动态未知新品捕获）</h2>
      <p style="color:#374151;line-height:1.6;">
        • <b style="color:#dc2626;">T0 旗舰特惠级（{tier_counts['T0']} 款）</b>：美西 CN2 GIA 限量年付（<b>$38 ~ $53 / 年</b>）<br>
        • <b style="color:#d97706;">T1 多机房/高配限量（{tier_counts['T1']} 款）</b>：GIA-E 多机房、THE PLAN 与 DMIT PalmSpring（<b>$49.99 ~ $100 / 年</b>）<br>
        • <b style="color:#2563eb;">T2 月付常青备选（{tier_counts['T2']} 款）</b>：DMIT LAX.Pro 月付入门（<b>$10.90 / 月</b>）<br>
        • <b>数据源健康状态</b>：{esc(src_badge)}
      </p>
      <h3 style="color:#1f2937;margin-top:20px;">📋 实时库存清单（UTC+8 {esc(now_str)}）</h3>
      <table style="width:100%;border-collapse:collapse;font-size:13px;text-align:left;">
        <thead>
          <tr style="background:#f3f4f6;">
            <th style="padding:10px;">优先级</th>
            <th style="padding:10px;">商家</th>
            <th style="padding:10px;">套餐型号 / 规格 / 线路说明</th>
            <th style="padding:10px;">价格</th>
            <th style="padding:10px;">库存</th>
            <th style="padding:10px;">链接</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
      {extra_html}
    </div>'''


def build_alert_email(newly_in_stock, new_tg_alerts, now_str):
    subj_parts = []
    if newly_in_stock:
        names = ', '.join(f"[{x['tier']}] {x['merchant']} {x['name']} ({x['price']})" for x in newly_in_stock)
        subj_parts.append(f'🔥CN2 GIA补货: {names}')
    if new_tg_alerts:
        subj_parts.append(f'📢官方频道促销动态({len(new_tg_alerts)}条)')
    subject = ' | '.join(subj_parts)

    body = '<div style="font-family:-apple-system,sans-serif;max-width:780px;margin:0 auto;padding:20px;border:2px solid #dc2626;border-radius:10px;">'
    body += f'<h2 style="color:#dc2626;margin-top:0;">🚨 监控到美西 CN2 GIA 补货 / 促销动态！（UTC+8 {esc(now_str)}）</h2>'

    if newly_in_stock:
        body += '<h3>🟢 刚刚补货 / 上新的套餐：</h3><ul>'
        for x in newly_in_stock:
            body += '<li style="margin-bottom:14px;font-size:15px;">'
            body += f'<span style="background:{esc(x["tier_color"])};color:#fff;padding:2px 6px;border-radius:4px;font-size:12px;font-weight:bold;">{esc(x["tier"])}</span> '
            body += f'<b>【{esc(x["merchant"])}】{esc(x["name"])} — <span style="color:#dc2626;">{esc(x["price"])}</span></b><br>'
            body += f'配置：{esc(x["specs"])}<br>'
            body += f'说明：<span style="color:#059669;">{esc(x["reason"])}</span><br>'
            body += f'👉 官网直达链接：<a href="{esc(x["url"])}" style="font-weight:bold;color:#2563eb;">{esc(x["url"])}</a></li>'
        body += '</ul>'

    if new_tg_alerts:
        body += '<h3>📢 官方频道最新促销/补货消息：</h3><ul>'
        for ch, post_id, txt in new_tg_alerts:
            post_url = f'https://t.me/{post_id}'
            body += f'<li style="margin-bottom:10px;"><b><a href="{esc(post_url)}">@{esc(ch)} ({esc(post_id)})</a></b>：{esc(txt)}</li>'
        body += '</ul>'

    body += '</div>'
    return subject, body


def main():
    is_dry_run = '--dry-run' in sys.argv
    is_test = ('--test' in sys.argv) or (os.environ.get('SEND_TEST_EMAIL', '').lower() == 'true')

    if not is_test and not is_dry_run and not os.environ.get('GITHUB_ACTIONS'):
        time.sleep(random.uniform(2.0, 15.0))

    old_state = load_state()
    results, extra_deals, health = check_all_sources()

    # Fail loudly if ALL stock sources failed (prevent silent blind monitoring)
    if not health['vd_ok'] and not health['bwg_ok']:
        print('FATAL: All stock data sources (vpsding.com & stock.bwg.net) failed!', file=sys.stderr)
        sys.exit(1)

    now_str = datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')

    # Prepare updated state in memory first (never persist before alert email succeeds!)
    new_stock = {}
    newly_in_stock = []
    for key in TARGETS:
        was_in_stock = bool(old_state['stock'].get(key, False))
        current = results.get(key)
        if current is None:
            # Source failed for this target -> preserve previous state to prevent false oscillation
            new_stock[key] = was_in_stock
        else:
            if current and not was_in_stock:
                newly_in_stock.append(TARGETS[key])
            new_stock[key] = current

    # Reconcile extra_deals: alert newly seen items, AND clear out-of-stock extras when their source succeeded
    old_extra = dict(old_state.get('extra', {}))
    new_extra = {}
    active_extra_ids = set()
    for item in extra_deals:
        eid = item['id']
        active_extra_ids.add(eid)
        if not old_extra.get(eid, False):
            newly_in_stock.append(item)
        new_extra[eid] = True

    # Preserve previously tracked extra IDs ONLY if their source failed this run
    for old_eid, was_active in old_extra.items():
        if not was_active or old_eid in active_extra_ids:
            continue
        is_bwg_extra = old_eid.startswith('bwg:')
        source_ok = (health['bwg_ok'] or health['vd_ok']) if is_bwg_extra else health['vd_ok']
        if not source_ok:
            new_extra[old_eid] = True

    # Check Telegram channels monotonically (catches ALL burst posts without skipping)
    new_tg = dict(old_state.get('tg', {}))
    new_tg_alerts = []
    for ch in ('dmitnews', 'BandwagonHostNews'):
        prev_id = old_state.get('tg', {}).get(ch)
        latest_id, matched_posts, tg_ok = check_tg_channel(ch, prev_id)
        if tg_ok and latest_id:
            new_tg[ch] = latest_id
            for post_id, text in matched_posts:
                new_tg_alerts.append((ch, post_id, text))

    new_state = {
        'stock': new_stock,
        'tg': new_tg,
        'extra': new_extra,
    }

    if is_dry_run:
        in_cnt = sum(1 for v in results.values() if v is True)
        unk_cnt = sum(1 for v in results.values() if v is None)
        print(
            f'[DRY-RUN {now_str}] sources=(vd:{health["vd_ok"]}, bwg:{health["bwg_ok"]}) '
            f'targets={len(TARGETS)} in_stock={in_cnt} unknown={unk_cnt} '
            f'extras={len(extra_deals)} new_alerts={len(newly_in_stock)} tg_alerts={len(new_tg_alerts)}'
        )
        print('Next state preview:', json.dumps(new_state, ensure_ascii=False, sort_keys=True))
        if newly_in_stock:
            print('Would alert plans:', [f"{x['merchant']} {x['name']} ({x['price']})" for x in newly_in_stock])
        if new_tg_alerts:
            print('Would alert TG:', new_tg_alerts)
        return

    if is_test:
        html_body = build_test_email_html(results, extra_deals, now_str, health)
        send_email('【美西 CN2 GIA 专精监控】实时状态一览', html_body)
        save_state(new_state)
        print(f'[{now_str}] Test email sent and state updated!')
        return

    if newly_in_stock or new_tg_alerts:
        subject, body = build_alert_email(newly_in_stock, new_tg_alerts, now_str)
        send_email(subject, body)
        save_state(new_state)
        print(f'[{now_str}] ALERT SENT: {subject}')
    else:
        save_state(new_state)
        print(
            f'[{now_str}] No new US West CN2 GIA stock changes '
            f'(vd_ok={health["vd_ok"]}, bwg_ok={health["bwg_ok"]}, targets={len(TARGETS)}).'
        )


if __name__ == '__main__':
    main()
