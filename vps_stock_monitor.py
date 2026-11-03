#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import random
import re
import smtplib
import sys
import time
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

# 按线路等级与性价比划分监控优先级（无任何个人环境信息）
TARGETS = {
    # ==================== T0: 旗舰特惠级（CN2 GIA 特价年付） ====================
    'bwg:145': {
        'tier': 'T0 · 🥇首选 No.1',
        'tier_color': '#dc2626',
        'merchant': 'BandwagonHost',
        'name': 'DC9 CN2 GIA Limited Edition',
        'price': '$38.00 / 年',
        'specs': '1核 AMD / 768MB / 15GB SSD / 750GB @ 1.5Gbps',
        'reason': '洛杉矶 DC9 (USCA_9) 机房，三网回程 CN2 GIA 精品线路，入门特价年付款',
        'url': 'https://bwh81.net/cart.php?a=add&pid=145',
        'bwg_pid': '145',
        'vd_id': 'bandwagon:145',
    },
    'bwg:156': {
        'tier': 'T0 · 🥈首选 No.2',
        'tier_color': '#dc2626',
        'merchant': 'BandwagonHost',
        'name': 'BiggerBox Pro Limited',
        'price': '$39.00 / 年',
        'specs': '1核 AMD / 1GB / 20GB SSD / 1000GB @ 2.5Gbps',
        'reason': '洛杉矶 DC1 机房，电信双向 CN2 GIA + 联移 CMIN2，均衡标准配置',
        'url': 'https://bwh81.net/cart.php?a=add&pid=156',
        'bwg_pid': '156',
        'vd_id': 'bandwagon:156',
    },
    'dmit:183': {
        'tier': 'T0 · 🥉首选 No.3',
        'tier_color': '#dc2626',
        'merchant': 'DMIT',
        'name': 'LAX.Pro.Wee',
        'price': '$39.90 / 年',
        'specs': '1核 AMD Zen4 / 1GB / 20GB SSD / 500GB @ 500Mbps',
        'reason': '洛杉矶 Premium 系列，三网回程 CN2 GIA 线路，高性价比入门年付款',
        'url': 'https://www.dmit.io/cart.php?a=add&pid=183',
        'vd_id': 'dmit:LAX.Pro.Wee',
    },
    'bwg:157': {
        'tier': 'T0 · 🏅首选 No.4',
        'tier_color': '#dc2626',
        'merchant': 'BandwagonHost',
        'name': 'MegaBox Pro Limited',
        'price': '$49.00 / 年',
        'specs': '2核 AMD / 2GB / 40GB SSD / 2000GB @ 2.5Gbps',
        'reason': '洛杉矶 DC1 机房，CN2 GIA + CMIN2 线路，2核2G高配大流量年付款',
        'url': 'https://bwh81.net/cart.php?a=add&pid=157',
        'bwg_pid': '157',
        'vd_id': 'bandwagon:157',
    },
    'dmit:186': {
        'tier': 'T0 · 🏅首选 No.4',
        'tier_color': '#dc2626',
        'merchant': 'DMIT',
        'name': 'LAX.Pro.MALIBU',
        'price': '$49.90 / 年',
        'specs': '1核 AMD Zen4 / 1GB / 20GB SSD / 1000GB @ 1Gbps',
        'reason': '洛杉矶 Premium 系列，1Gbps 端口 + 1TB 流量 + 三网 CN2 GIA 经典限量款',
        'url': 'https://www.dmit.io/cart.php?a=add&pid=186',
        'vd_id': 'dmit:LAX.Pro.MALIBU',
    },

    # ==================== T1: 强力备选级（CN2 GIA-E 商务线路） ====================
    'bwg:94': {
        'tier': 'T1 · 强力备选',
        'tier_color': '#d97706',
        'merchant': 'BandwagonHost',
        'name': 'CN2 GIA-E 10G Limited',
        'price': '$49.99 / 年',
        'specs': '1核 / 512MB / 10GB SSD / 500GB @ 1Gbps',
        'reason': '支持 DC6 / DC9 / 软银等多机房后台自由切换的限量款',
        'url': 'https://bwh81.net/cart.php?a=add&pid=94',
        'bwg_pid': '94',
        'vd_id': 'bandwagon:94',
    },
    'bwg:149': {
        'tier': 'T1 · 强力备选',
        'tier_color': '#d97706',
        'merchant': 'BandwagonHost',
        'name': 'THE DC6 PLAN Limited',
        'price': '$53.00 / 年',
        'specs': '1核 / 1GB / 20GB SSD / 1000GB @ 2.5Gbps',
        'reason': '洛杉矶 DC6 (USCA_6) CN2 GIA-E 电子商务专线标准配置款',
        'url': 'https://bwh81.net/cart.php?a=add&pid=149',
        'bwg_pid': '149',
        'vd_id': 'bandwagon:149',
    },

    # ==================== T2 / T3: 常规月付 & 其他线路参考 ====================
    'dmit:253': {
        'tier': 'T2 · 月付常青款',
        'tier_color': '#2563eb',
        'merchant': 'DMIT',
        'name': 'LAX.AN3.Pro.TINY',
        'price': '$10.90 / 月',
        'specs': '1核 AMD / 2GB / 20GB SSD / 1000GB @ 1Gbps',
        'reason': '洛杉矶 Premium 系列常规月付入门款（三网 CN2 GIA）',
        'url': 'https://www.dmit.io/cart.php?a=add&pid=253',
        'vd_id': 'dmit:LAX.AN3.Pro.TINY',
    },
    'dmit:188': {
        'tier': 'T3 · 次选参考 (EB)',
        'tier_color': '#6b7280',
        'merchant': 'DMIT',
        'name': 'LAX.EB.WEE',
        'price': '$39.90 / 年',
        'specs': '1核 AMD Zen4 / 1GB / 20GB SSD / 1000GB @ 1Gbps',
        'reason': 'Eyeball 系列（回程 CMIN2 / 9929 线路，非 CN2 GIA）',
        'url': 'https://www.dmit.io/cart.php?a=add&pid=188',
        'vd_id': 'dmit:LAX.EB.WEE',
    },
}


def http_get(url, timeout=10):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/json,*/*',
        }
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='ignore')


def send_email(subject, html_body):
    if not SMTP_USER or not SMTP_PASS or not RECIPIENT:
        raise RuntimeError('请在 GitHub Secrets 中配置 SMTP_USER 与 SMTP_PASS')
    msg = MIMEMultipart('alternative')
    msg['From'] = formataddr((str(Header('Cloud Stock Monitor', 'utf-8')), SMTP_USER))
    msg['To'] = RECIPIENT
    msg['Subject'] = Header(subject, 'utf-8')
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid()
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [RECIPIENT], msg.as_string())


def check_all_sources():
    results = {k: False for k in TARGETS}
    extra_deals = []

    # 1. Check vpsding.com/api/plans (Covers both DMIT and BWG)
    try:
        vd_data = json.loads(http_get('https://vpsding.com/api/plans', timeout=10))
        vd_map = {p.get('id'): p for p in vd_data.get('plans', [])}
        for key, info in TARGETS.items():
            p = vd_map.get(info['vd_id'])
            if p and p.get('stock') == 'in':
                results[key] = True

        known_vd_ids = {v['vd_id'] for v in TARGETS.values()}
        for p in vd_data.get('plans', []):
            if p.get('slug') in ('dmit', 'bandwagon') and p.get('region') == 'US' and p.get('stock') == 'in':
                pid_id = p.get('id', '')
                if pid_id in known_vd_ids:
                    continue
                tags_and_line = (p.get('line', '') + ' ' + ' '.join(p.get('tags', []))).upper()
                is_cn2_gia = ('CN2 GIA' in tags_and_line) or ('LAX.PRO' in p.get('name', '').upper())
                usd_mo = float(p.get('usdMonth', 999))
                if is_cn2_gia and usd_mo <= 9.0:
                    clean_buy = re.sub(r'aff\.php\?aff=\d+&', 'cart.php?a=add&', p.get('buy', ''))
                    extra_deals.append({
                        'id': pid_id,
                        'tier': '🔥 新增特惠套餐',
                        'tier_color': '#dc2626',
                        'merchant': p.get('merchant'),
                        'name': p.get('name'),
                        'price': p.get('priceText'),
                        'specs': f"{p.get('cpu')} / {p.get('ram')} / {p.get('disk')} / {p.get('traffic')} @ {p.get('bw')}",
                        'reason': f"检测到在售低价 CN2 GIA 套餐 ({p.get('line')})",
                        'url': clean_buy,
                    })
    except Exception:
        pass

    # 2. Check stock.bwg.net/api/products
    try:
        bwg_data = json.loads(http_get('https://stock.bwg.net/api/products', timeout=10))
        bwg_map = {str(p.get('pid')): p for p in bwg_data}
        for key, info in TARGETS.items():
            bpid = info.get('bwg_pid')
            if bpid and bpid in bwg_map and int(bwg_map[bpid].get('status', 0)) == 1:
                results[key] = True
    except Exception:
        pass

    # 3. Direct 1st-party double-verification on bwh81.net/cart.php ONLY when a BWG plan is reported in stock
    for key, info in TARGETS.items():
        bpid = info.get('bwg_pid')
        if bpid and results.get(key):
            try:
                html = http_get(f'https://bwh81.net/cart.php?a=add&pid={bpid}', timeout=8)
                if 'Out of Stock' in html:
                    results[key] = False
            except Exception:
                pass

    return results, extra_deals


def check_tg_channel(channel_name):
    try:
        html = http_get(f'https://t.me/s/{channel_name}', timeout=10)
        posts = re.findall(r'data-post="([^"]+)".*?class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', html, re.S)
        if not posts:
            return None, None
        post_id, raw_html = posts[-1]
        clean_text = re.sub(r'<[^>]+>', ' ', raw_html).strip()
        return post_id, clean_text
    except Exception:
        return None, None


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'stock': {}, 'tg': {}, 'extra': {}}


def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write('\n')


def main():
    is_test = ('--test' in sys.argv) or (os.environ.get('SEND_TEST_EMAIL', '').lower() == 'true')
    if not is_test and not os.environ.get('GITHUB_ACTIONS'):
        time.sleep(random.uniform(2.0, 25.0))

    state = load_state()
    results, extra_deals = check_all_sources()

    now_str = datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')

    if is_test:
        rows_html = ''
        for key, info in TARGETS.items():
            in_stock = results.get(key, False)
            badge = '<span style="color:#16a34a;font-weight:bold;">🟢 有货</span>' if in_stock else '<span style="color:#dc2626;">🔴 缺货</span>'
            rows_html += f'''
            <tr>
              <td style="padding:10px;border-bottom:1px solid #e5e7eb;white-space:nowrap;">
                <span style="background:{info['tier_color']};color:#fff;padding:3px 7px;border-radius:4px;font-size:12px;font-weight:bold;">{info['tier']}</span>
              </td>
              <td style="padding:10px;border-bottom:1px solid #e5e7eb;white-space:nowrap;"><b>{info['merchant']}</b></td>
              <td style="padding:10px;border-bottom:1px solid #e5e7eb;">
                <b>{info['name']}</b><br>
                <span style="font-size:12px;color:#4b5563;">{info['specs']}</span><br>
                <span style="font-size:12px;color:#059669;">💡 {info['reason']}</span>
              </td>
              <td style="padding:10px;border-bottom:1px solid #e5e7eb;color:#d97706;font-weight:bold;white-space:nowrap;">{info['price']}</td>
              <td style="padding:10px;border-bottom:1px solid #e5e7eb;white-space:nowrap;">{badge}</td>
              <td style="padding:10px;border-bottom:1px solid #e5e7eb;white-space:nowrap;"><a href="{info['url']}" style="color:#2563eb;font-weight:bold;text-decoration:none;">官网直达 &rarr;</a></td>
            </tr>'''

        html = f'''
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:860px;margin:0 auto;padding:20px;border:1px solid #e5e7eb;border-radius:10px;background:#ffffff;">
          <h2 style="color:#111827;margin-top:0;">☁️ GitHub Actions 云端库存监控报表</h2>
          <p style="color:#374151;line-height:1.6;">
            • <b style="color:#dc2626;">T0 旗舰特惠级（5款）</b>：三网 CN2 GIA 限量特价年付（<b>$38 ~ $49.90 / 年</b>）<br>
            • <b style="color:#d97706;">T1 强力备选级（2款）</b>：CN2 GIA-E 商务专线年付（<b>$49.99 ~ $53.00 / 年</b>）<br>
            • <b style="color:#2563eb;">T2 月付常青款（1款）</b>：DMIT CN2 GIA 月付（<b>$10.90 / 月</b>）
          </p>
          <h3 style="color:#1f2937;margin-top:20px;">📋 实时库存清单（UTC+8 {now_str}）</h3>
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
        </div>'''
        send_email('【云端库存监控】CN2 GIA 套餐实时状态一览', html)
        for ch in ('dmitnews', 'BandwagonHostNews'):
            pid, _ = check_tg_channel(ch)
            if pid:
                state['tg'][ch] = pid
        for k, v in results.items():
            state['stock'][k] = v
        state['extra'] = {item['id']: True for item in extra_deals}
        save_state(state)
        print('Test email sent and state updated!')
        return

    # Normal scheduled run
    newly_in_stock = []
    for key, in_stock in results.items():
        was_in_stock = state['stock'].get(key, False)
        if in_stock and not was_in_stock:
            newly_in_stock.append(TARGETS[key])
        state['stock'][key] = in_stock

    for item in extra_deals:
        eid = item['id']
        if not state['extra'].get(eid, False):
            newly_in_stock.append(item)
            state['extra'][eid] = True

    new_tg_alerts = []
    for ch in ('dmitnews', 'BandwagonHostNews'):
        post_id, text = check_tg_channel(ch)
        if post_id and state['tg'].get(ch) != post_id:
            prev_id = state['tg'].get(ch)
            state['tg'][ch] = post_id
            if prev_id and text and any(kw in text.upper() for kw in ('补货', 'WEE', 'MALIBU', 'PRO', 'BOX', 'DC9', 'DC6', 'BLACK FRIDAY', '黑五', '优惠', 'PROMO', 'OFF', 'STOCK', 'TINY', 'GIA')):
                new_tg_alerts.append((ch, text))

    save_state(state)

    if newly_in_stock or new_tg_alerts:
        subj_parts = []
        if newly_in_stock:
            names = ', '.join([f"[{x['tier']}] {x['merchant']} {x['name']} ({x['price']})" for x in newly_in_stock])
            subj_parts.append(f'🔥补货提醒: {names}')
        if new_tg_alerts:
            subj_parts.append('📢官方频道新促销动态')
        subject = ' | '.join(subj_parts)

        body = '<div style="font-family:-apple-system,sans-serif;max-width:760px;margin:0 auto;padding:20px;border:2px solid #dc2626;border-radius:10px;">'
        body += f'<h2 style="color:#dc2626;margin-top:0;">🚨 监控到套餐补货 / 促销动态！（UTC+8 {now_str}）</h2>'

        if newly_in_stock:
            body += '<h3>🟢 刚刚补货的套餐：</h3><ul>'
            for x in newly_in_stock:
                body += '<li style="margin-bottom:14px;font-size:15px;">'
                body += f'<span style="background:{x["tier_color"]};color:#fff;padding:2px 6px;border-radius:4px;font-size:12px;font-weight:bold;">{x["tier"]}</span> '
                body += f'<b>【{x["merchant"]}】{x["name"]} — <span style="color:#dc2626;">{x["price"]}</span></b><br>'
                body += f'配置：{x["specs"]}<br>'
                body += f'说明：<span style="color:#059669;">{x["reason"]}</span><br>'
                body += f'👉 官网直达链接：<a href="{x["url"]}" style="font-weight:bold;color:#2563eb;">{x["url"]}</a></li>'
            body += '</ul>'

        if new_tg_alerts:
            body += '<h3>📢 官方频道最新消息：</h3><ul>'
            for ch, txt in new_tg_alerts:
                body += f'<li style="margin-bottom:10px;"><b>@{ch}</b>：{txt}</li>'
            body += '</ul>'

        body += '</div>'
        send_email(subject, body)
        print(f'[{now_str}] ALERT SENT: {subject}')
    else:
        print(f'[{now_str}] No new CN2 GIA stock changes.')


if __name__ == '__main__':
    main()
