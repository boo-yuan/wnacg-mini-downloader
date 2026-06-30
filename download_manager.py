import os
import time
import queue
import threading
import json
import re
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from PIL import Image

from utils import logger, get_proxies, save_task_state, get_unfinished_dir

class DownloadManager:
    def __init__(self, app):
        self.app = app
        self.queue = queue.Queue()
        self.tasks = {} # task_id -> task_data
        self.workers = []
        self.max_workers = getattr(self.app, 'concurrent_comics', 2)
        self.downloaded_bytes = 0
        
        for _ in range(self.max_workers):
            t = threading.Thread(target=self._worker_loop, daemon=True)
            t.start()
            self.workers.append(t)

    def update_workers(self):
        target_workers = getattr(self.app, 'concurrent_comics', 2)
        if target_workers > self.max_workers:
            for _ in range(target_workers - self.max_workers):
                t = threading.Thread(target=self._worker_loop, daemon=True)
                t.start()
                self.workers.append(t)
        elif target_workers < self.max_workers:
            for _ in range(self.max_workers - target_workers):
                self.queue.put(None)
        self.max_workers = target_workers

    def sync_disk_state(self):
        base_dir = self.app.download_path
        if not os.path.exists(base_dir): return
        
        proxies = get_proxies(self.app.proxy_mode, self.app.custom_proxy_ip, self.app.custom_proxy_port)
        disk_task_ids = set()
        
        try:
            for item in os.listdir(base_dir):
                d_path = os.path.join(base_dir, item)
                if os.path.isdir(d_path):
                    json_path = os.path.join(d_path, "download_info.json")
                    if os.path.exists(json_path):
                        try:
                            with open(json_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                
                            status = data.get('status', '')
                            if status != '下载完成' and not item.startswith("[未完成]_"):
                                new_path = os.path.join(base_dir, f"[未完成]_{item}")
                                try:
                                    os.rename(d_path, new_path)
                                    d_path = new_path
                                except: pass
                                
                            tid = data['id']
                            disk_task_ids.add(tid)
                            
                            if tid not in self.tasks:
                                task_data = {
                                    'id': tid,
                                    'aid': data['aid'],
                                    'title': data['title'],
                                    'domain': data['domain'],
                                    'proxies': proxies,
                                    'status': status,
                                    'progress': data.get('progress', 0.0),
                                    'list_btn': None,
                                    'ui_frame': None,
                                    'ui_lbl_status': None,
                                    'ui_progressbar': None,
                                    'cancel_flag': False,
                                    'is_paused': True
                                }
                                self.tasks[tid] = task_data
                                
                                if status != '下载完成':
                                    if status != '已取消':
                                        task_data['status'] = "已暂停 (启动缓存)"
                                    self.app.after(0, lambda t=task_data: self.app.add_task_to_ui(t))
                        except Exception as e:
                            logger.error(f"Error loading {json_path}: {e}")
                            
            for task_id in list(self.tasks.keys()):
                if task_id not in disk_task_ids:
                    task = self.tasks[task_id]
                    task['cancel_flag'] = True
                    if task['ui_frame'] and task['ui_frame'].winfo_exists():
                        self.app.after(0, lambda f=task['ui_frame']: f.destroy())
                        task['ui_frame'] = None
                    if task['list_btn'] and task['list_btn'].winfo_exists():
                        self.update_list_button_state(task['list_btn'], "一键下载")
                    del self.tasks[task_id]
                    if task_id in self.app.selected_task_ids:
                        self.app.selected_task_ids.discard(task_id)
            
            self.app.after(0, self.app.update_task_selection_ui)
        except Exception as e:
            logger.error(f"Error scanning for cached tasks: {e}")
            
    def add_task(self, task_id, aid, title, domain, list_btn, proxies):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task['is_paused']:
                task['cancel_flag'] = False
                task['is_paused'] = False
                self.update_task_ui(task_id, "等待中", task['progress'])
                self.update_list_button_state(list_btn, "等待中")
                self.queue.put(task_id)
            return
            
        task_data = {
            'id': task_id,
            'aid': aid,
            'title': title,
            'domain': domain,
            'proxies': proxies,
            'status': '等待中',
            'progress': 0.0,
            'list_btn': list_btn, 
            'ui_frame': None, 
            'ui_lbl_status': None,
            'ui_progressbar': None,
            'cancel_flag': False,
            'is_paused': False
        }
        self.tasks[task_id] = task_data
        save_task_state(task_data, self.app.download_path)
        
        self.app.add_task_to_ui(task_data) 
        self.queue.put(task_id)
        self.update_list_button_state(list_btn, "等待中")
        
    def update_list_button_state(self, btn, state):
        if not btn: return
        if state == "等待中":
            self.app.after(0, lambda: btn.configure(text="等待中", fg_color=("#E5E5EA", "#3A3A3C"), hover_color=("#D1D1D6", "#2C2C2E"), text_color=("#8E8E93", "#98989D"), state="disabled"))
        elif state == "下载中":
            self.app.after(0, lambda: btn.configure(text="下载中", fg_color=("#007AFF", "#0A84FF"), hover_color=("#0051A8", "#0066CC"), text_color=("#FFFFFF", "#FFFFFF"), state="disabled"))
        elif state == "继续下载":
            self.app.after(0, lambda: btn.configure(text="继续下载", fg_color=("#FF9500", "#FF9F0A"), hover_color=("#CC7700", "#CC7F08"), text_color=("#FFFFFF", "#FFFFFF"), state="normal"))
        elif state == "一键下载":
            self.app.after(0, lambda: btn.configure(text="一键下载", fg_color=("#007AFF", "#0A84FF"), hover_color=("#0051A8", "#0066CC"), text_color=("#FFFFFF", "#FFFFFF"), state="normal"))
        elif state == "下载完成":
            self.app.after(0, lambda: btn.configure(text="下载完成", fg_color=("#E5E5EA", "#3A3A3C"), hover_color=("#D1D1D6", "#2C2C2E"), text_color=("#8E8E93", "#98989D"), state="disabled"))

    def update_task_ui(self, task_id, status_text, progress_val):
        task = self.tasks.get(task_id)
        if not task: return
        task['status'] = status_text
        task['progress'] = progress_val
        
        is_error = "失败" in status_text or "错误" in status_text
        if is_error:
            text_color = ("#FF3B30", "#FF453A")
            pb_color = ("#FF3B30", "#FF453A")
        elif "暂停" in status_text:
            text_color = ("#FF9500", "#FF9F0A")
            pb_color = ("#FF9500", "#FF9F0A")
        elif "解析" in status_text:
            text_color = ("#AF52DE", "#BF5AF2")
            pb_color = ("#AF52DE", "#BF5AF2")
        elif "准备" in status_text:
            text_color = ("#34C759", "#30D158")
            pb_color = ("#34C759", "#30D158")
        elif "等待" in status_text:
            text_color = ("#8E8E93", "#98989D")
            pb_color = ("#D1D1D6", "#3A3A3C")
        else:
            text_color = ("#007AFF", "#0A84FF")
            pb_color = ("#007AFF", "#0A84FF")
        
        if task['ui_lbl_status'] and task['ui_frame'].winfo_exists():
            self.app.after(0, lambda l=task['ui_lbl_status'], text=status_text, c=text_color: l.configure(text=text, text_color=c))
        if task['ui_progressbar'] and task['ui_frame'].winfo_exists():
            self.app.after(0, lambda p=task['ui_progressbar'], val=progress_val, c=pb_color: [p.set(val), p.configure(progress_color=c)])
            
        threading.Thread(target=save_task_state, args=(task, self.app.download_path), daemon=True).start()
            
    def _worker_loop(self):
        while True:
            task_id = self.queue.get()
            if task_id is None:
                try: self.workers.remove(threading.current_thread())
                except: pass
                self.queue.task_done()
                break
                
            task = self.tasks.get(task_id)
            
            if not task or task.get('cancel_flag'):
                self.queue.task_done()
                continue
                
            try:
                self.process_download(task)
            except Exception as e:
                logger.error(f"Task {task_id} failed with error: {e}")
                if not task.get('cancel_flag'):
                    self.update_task_ui(task_id, f"错误: {str(e)[:15]}", task['progress'])
                    self.update_list_button_state(task['list_btn'], "继续下载")
                    task['is_paused'] = True
            finally:
                self.queue.task_done()

    def process_download(self, task):
        if task['cancel_flag']: return
        
        self.update_list_button_state(task['list_btn'], "下载中")
        self.update_task_ui(task['id'], "解析目录...", task['progress'])
        
        aid = task['aid']
        domain = task['domain']
        proxies = task['proxies']
        
        save_dir = get_unfinished_dir(task['title'], self.app.download_path)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
        
        view_urls = []
        page = 1
        
        while True:
            if task['cancel_flag']: return
            
            index_url = f"{domain}/photos-index-page-{page}-aid-{aid}.html"
            try:
                resp = requests.get(index_url, headers=headers, proxies=proxies, timeout=10)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                boxes = soup.find_all('div', class_='pic_box')
                if not boxes: break
                    
                for box in boxes:
                    a = box.find('a')
                    if a and a.has_attr('href'):
                        view_urls.append(a['href'])
                        
                paginator = soup.find('div', class_='f_left paginator')
                has_next = False
                if paginator:
                    next_span = paginator.find('span', class_='next')
                    if next_span and next_span.find('a'):
                        has_next = True
                        
                if has_next:
                    page += 1
                    time.sleep(1)
                else:
                    break
            except Exception as e:
                logger.error(f"Error fetching index page {page}: {e}")
                break
                
        total_imgs = len(view_urls)
        if total_imgs == 0:
            if not task['cancel_flag']:
                self.update_task_ui(task['id'], "解析失败(空图包)", 0.0)
                self.update_list_button_state(task['list_btn'], "继续下载")
                task['is_paused'] = True
            return
            
        if task['cancel_flag']: return
        self.update_task_ui(task['id'], f"准备下载 (0/{total_imgs})", task['progress'])
        
        downloaded = 0
        download_lock = threading.Lock()
        
        def download_single_image(i, view_href):
            nonlocal downloaded
            if task['cancel_flag']: return
            
            view_url = domain + view_href if view_href.startswith('/') else view_href
            success = False
            
            for attempt in range(3):
                if task['cancel_flag']: return
                try:
                    resp = requests.get(view_url, headers=headers, proxies=proxies, timeout=10)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    img = soup.find('img', id='picarea')
                    if not img or not img.has_attr('src'):
                        time.sleep(1)
                        continue
                        
                    img_src = img['src']
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif img_src.startswith('/'):
                        img_src = domain + img_src
                        
                    filename = img_src.split('/')[-1]
                    
                    if not getattr(self.app, 'use_original_filename', True):
                        ext = filename.split('.')[-1] if '.' in filename else 'jpg'
                        filename = f"{i+1:03d}.{ext}"

                    fmt_setting = getattr(self.app, 'download_format', '原始格式')
                    if fmt_setting != "原始格式":
                        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                        filename = f"{base_name}.{fmt_setting}"
                        
                    filepath = os.path.join(save_dir, filename)
                    
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 1024:
                        success = True
                        break

                    dl_headers = headers.copy()
                    dl_headers['Referer'] = view_url
                    with requests.get(img_src, headers=dl_headers, proxies=proxies, stream=True, timeout=15) as r:
                        r.raise_for_status()
                        
                        chunk_iter = r.iter_content(chunk_size=8192)
                        try:
                            first_chunk = next(chunk_iter)
                        except StopIteration:
                            first_chunk = b""
                            
                        if fmt_setting == "原始格式":
                            with open(filepath, 'wb') as f:
                                f.write(first_chunk)
                                self.downloaded_bytes += len(first_chunk)
                                for chunk in chunk_iter:
                                    f.write(chunk)
                                    self.downloaded_bytes += len(chunk)
                        else:
                            buf = BytesIO()
                            buf.write(first_chunk)
                            self.downloaded_bytes += len(first_chunk)
                            for chunk in chunk_iter:
                                buf.write(chunk)
                                self.downloaded_bytes += len(chunk)
                            try:
                                buf.seek(0)
                                image_obj = Image.open(buf)
                                if image_obj.mode in ('RGBA', 'LA', 'P') and fmt_setting == "jpg":
                                    bg = Image.new('RGB', image_obj.size, (255, 255, 255))
                                    try:
                                        bg.paste(image_obj, mask=image_obj.convert('RGBA').split()[3])
                                    except:
                                        bg.paste(image_obj)
                                    image_obj = bg
                                elif image_obj.mode != 'RGB' and fmt_setting == "jpg":
                                    image_obj = image_obj.convert('RGB')
                                    
                                pil_fmt = "JPEG" if fmt_setting == "jpg" else fmt_setting.upper()
                                kwargs = {}
                                if pil_fmt == "JPEG": kwargs['quality'] = 95
                                image_obj.save(filepath, pil_fmt, **kwargs)
                            except Exception as e:
                                logger.error(f"Image convert error: {e}")
                                with open(filepath, 'wb') as f:
                                    f.write(buf.getvalue())
                                    
                    success = True
                    break
                    
                except Exception as e:
                    logger.error(f"Attempt {attempt+1} failed for {view_url}: {e}")
                    time.sleep(2)
                    
            if success:
                with download_lock:
                    downloaded += 1
                    self.update_task_ui(task['id'], f"下载中 ({downloaded}/{total_imgs})", downloaded/total_imgs)
                time.sleep(getattr(self.app, 'image_rest_time', 1))
            else:
                logger.error(f"Completely failed to download {view_url} after 3 attempts.")

        max_img_workers = getattr(self.app, 'concurrent_images', 5)
        if max_img_workers <= 1:
            for i, view_href in enumerate(view_urls):
                if task['cancel_flag']: break
                download_single_image(i, view_href)
        else:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_img_workers) as executor:
                futures = []
                for i, view_href in enumerate(view_urls):
                    futures.append(executor.submit(download_single_image, i, view_href))
                for future in concurrent.futures.as_completed(futures):
                    pass
                
        if task['cancel_flag']: return
        
        if downloaded == total_imgs:
            task['status'] = '下载完成'
            task['progress'] = 1.0
            
            from utils import save_task_state
            save_task_state(task, self.app.download_path) # Save it as '下载完成' before we rename the folder!
            
            try:
                base_title = re.sub(r'[\\/*?:"<>|]', '_', task['title']).strip()
                if base_title.startswith("[未完成]_"):
                    base_title = base_title[len("[未完成]_"):]
                completed_dir = os.path.join(self.app.download_path, base_title)
                
                if os.path.exists(completed_dir):
                    suffix = 1
                    while os.path.exists(f"{completed_dir}_{suffix}"):
                        suffix += 1
                    completed_dir = f"{completed_dir}_{suffix}"
                    
                os.rename(save_dir, completed_dir)
            except Exception as e:
                logger.error(f"Error renaming completed folder: {e}")
                
            self.app.after(0, lambda t_id=task['id']: self.app.remove_task(t_id))
            time.sleep(getattr(self.app, 'comic_rest_time', 0))
        else:
            self.update_task_ui(task['id'], f"部分失败 ({downloaded}/{total_imgs})", downloaded/total_imgs)
            self.update_list_button_state(task['list_btn'], "继续下载")
            task['is_paused'] = True
