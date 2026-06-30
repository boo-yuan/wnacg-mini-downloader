import os
import re
import json
import logging
from logging.handlers import RotatingFileHandler
import urllib.request
import urllib.parse
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from PIL import Image

import sys

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# ==========================================
# 1. 设置日志 (Logging Setup)
# ==========================================
LOG_FILE = os.path.join(get_app_dir(), "app.log")
logger = logging.getLogger("wnacg_app")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(LOG_FILE, maxBytes=1*1024*1024, backupCount=1, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

DOMAINS = ['https://www.wnacg.com', 'https://www.wnacg.ru']

def get_proxies(proxy_mode, proxy_ip, proxy_port):
    if proxy_mode == "系统代理" or proxy_mode == "system":
        return urllib.request.getproxies()
    elif proxy_mode == "自定义" or proxy_mode == "custom":
        p_url = f"http://{proxy_ip}:{proxy_port}"
        return {"http": p_url, "https": p_url}
    else:
        return {"http": "", "https": ""}

def get_unfinished_dir(title, base_path=None):
    if not base_path:
        base_path = get_app_dir()
    base = re.sub(r'[\\/*?:"<>|]', '_', title).strip()
    if base.startswith("[未完成]_"):
        base = base[len("[未完成]_"):]
    return os.path.join(base_path, f"[未完成]_{base}")

def save_task_state(task, base_path=None):
    save_dir = get_unfinished_dir(task['title'], base_path)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)
        
    json_path = os.path.join(save_dir, "download_info.json")
    data = {
        'id': task['id'],
        'aid': task['aid'],
        'title': task['title'],
        'domain': task['domain'],
        'status': task['status'],
        'progress': task['progress']
    }
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save state for {task['id']}: {e}")

def delete_task_state(task, base_path=None):
    save_dir = get_unfinished_dir(task['title'], base_path)
    json_path = os.path.join(save_dir, "download_info.json")
    if os.path.exists(json_path):
        try:
            os.remove(json_path)
        except:
            pass

# ==========================================
# 2. 网络请求与数据解析 (Network & Scraping)
# ==========================================
def search_wnacg(query, page, proxies, custom_api_domain=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    domains_to_try = DOMAINS
    if custom_api_domain:
        domains_to_try = [custom_api_domain] + DOMAINS
        
    for domain in domains_to_try:
        url = f"{domain}/search/index.php?q={urllib.parse.quote(query)}&m=&syn=yes&f=_all&s=create_time_DESC&p={page}"
        logger.info(f"Fetching: {url}")
        try:
            resp = requests.get(url, headers=headers, proxies=proxies, timeout=10)
            resp.raise_for_status()
            logger.info(f"Success fetching from {domain}")
            return parse_html(resp.text, domain)
        except Exception as e:
            logger.error(f"Failed fetching {url}: {e}")
            continue
    
    return [], 1, "搜索请求失败，请检查网络或代理设置，并查看日志。"

def parse_html(html_content, domain):
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []
    total_pages = 1
    
    paginator = soup.find('div', class_='f_left paginator')
    if paginator:
        a_tags = paginator.find_all('a')
        for a in a_tags:
            text = a.get_text(strip=True)
            if text.isdigit():
                total_pages = max(total_pages, int(text))
            elif '尾页' in text or '>>' in text:
                href = a.get('href', '')
                m = re.search(r'p=(\d+)', href)
                if m:
                    total_pages = max(total_pages, int(m.group(1)))
                    
        span = paginator.find('span', class_='thisclass')
        if span and span.text.isdigit():
            total_pages = max(total_pages, int(span.text))
    
    items = soup.find_all('li', class_='gallary_item')
    if not items:
        items = soup.select('.pic_box')
        if items:
            items = [item.parent for item in items]
    
    if not items:
        return [], total_pages, None
        
    for item in items:
        try:
            img_tag = item.find('img')
            img_url = img_tag['src'] if img_tag and img_tag.has_attr('src') else ''
            if img_url and img_url.startswith('//'):
                img_url = 'https:' + img_url
            elif img_url and img_url.startswith('/'):
                img_url = domain + img_url
                
            title_tag = item.find('a', title=True)
            a_tag = item.find('a')
            
            if not title_tag and img_tag and img_tag.has_attr('alt'):
                title = img_tag['alt']
            elif title_tag:
                title = title_tag['title']
            else:
                title = item.text.strip()[:20]
            
            title = BeautifulSoup(title, "html.parser").get_text(strip=True)
            
            aid = None
            href = ""
            if title_tag and title_tag.has_attr('href'):
                href = title_tag['href']
            elif a_tag and a_tag.has_attr('href'):
                href = a_tag['href']
                
            if href:
                m = re.search(r'aid-(\d+)', href)
                if m:
                    aid = m.group(1)
                
            count = ""
            info_col = item.find('div', class_='info_col')
            if info_col:
                info_text = info_col.text.strip()
                m_c = re.search(r'(\d+)\s*[张張]', info_text)
                m_d = re.search(r'(\d{4}-\d{2}-\d{2})', info_text)
                c_str = f"{m_c.group(1)}P" if m_c else ""
                d_str = m_d.group(1) if m_d else ""
                count = f"{c_str} | {d_str}".strip(' |')
                
            results.append({
                'title': title,
                'img_url': img_url,
                'count': count,
                'aid': aid,
                'domain': domain
            })
        except Exception as e:
            logger.error(f"Error parsing item: {e}")
            
    return results, total_pages, None

def download_thumbnail(url, proxies, referer="https://www.wnacg.com/"):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Referer': referer
    }
    try:
        resp = requests.get(url, headers=headers, proxies=proxies, timeout=5)
        resp.raise_for_status()
        image = Image.open(BytesIO(resp.content))
        return image
    except Exception as e:
        logger.error(f"Error downloading thumbnail {url}: {e}")
        return None
