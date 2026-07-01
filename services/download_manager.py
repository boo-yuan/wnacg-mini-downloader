import os
import time
import json
import re
import asyncio
import threading
from io import BytesIO
from PIL import Image

from core.logger import logger
from core.config_manager import config_manager
from core.event_bus import event_bus
from network.client import network_client
from network.extractor import extractor

def get_unfinished_dir(title, base_path):
    base = re.sub(r'[\\/*?:"<>|]', '_', title).strip()
    if base.startswith("[未完成]_"):
        base = base[len("[未完成]_"):]
    return os.path.join(base_path, f"[未完成]_{base}")

def save_task_state(task_data, base_path):
    save_dir = get_unfinished_dir(task_data['title'], base_path)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)
        
    json_path = os.path.join(save_dir, "download_info.json")
    data = {
        'id': task_data['id'],
        'aid': task_data['aid'],
        'title': task_data['title'],
        'domain': task_data['domain'],
        'status': task_data['status'],
        'progress': task_data['progress']
    }
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save state for {task_data['id']}: {e}")

def delete_task_state(task_data, base_path):
    save_dir = get_unfinished_dir(task_data['title'], base_path)
    json_path = os.path.join(save_dir, "download_info.json")
    if os.path.exists(json_path):
        try:
            os.remove(json_path)
        except:
            pass

class DownloadManager:
    def __init__(self):
        self.tasks = {} # task_id -> task_data dict
        self.downloaded_bytes = 0
        
        # Asyncio Event Loop in Background
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._start_loop, daemon=True)
        self.thread.start()
        
        while not self.loop.is_running():
            time.sleep(0.01)
            
        self.max_workers = config_manager.concurrent_comics
        self.worker_tasks = []
        asyncio.run_coroutine_threadsafe(self._init_workers(), self.loop)
            
        event_bus.subscribe("CONFIG_UPDATED", self.on_config_updated)

    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _init_workers(self):
        self.queue = asyncio.Queue()
        for _ in range(self.max_workers):
            self.worker_tasks.append(asyncio.create_task(self._worker_loop()))

    def on_config_updated(self, config):
        target_workers = config.concurrent_comics
        if target_workers > self.max_workers:
            async def add_workers():
                for _ in range(target_workers - self.max_workers):
                    self.worker_tasks.append(asyncio.create_task(self._worker_loop()))
            asyncio.run_coroutine_threadsafe(add_workers(), self.loop)
        elif target_workers < self.max_workers:
            for _ in range(self.max_workers - target_workers):
                asyncio.run_coroutine_threadsafe(self.queue.put(None), self.loop)
        self.max_workers = target_workers

    def sync_disk_state(self):
        base_dir = config_manager.download_path
        if not os.path.exists(base_dir): return
        
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
                                except: pass
                                
                            tid = data['id']
                            disk_task_ids.add(tid)
                            
                            if tid not in self.tasks:
                                task_data = {
                                    'id': tid,
                                    'aid': data['aid'],
                                    'title': data['title'],
                                    'domain': data['domain'],
                                    'status': status,
                                    'progress': data.get('progress', 0.0),
                                    'cancel_flag': False,
                                    'is_paused': True
                                }
                                self.tasks[tid] = task_data
                                
                                if status != '下载完成':
                                    if status != '已取消':
                                        task_data['status'] = "已暂停 (启动缓存)"
                                    event_bus.emit("TASK_ADDED_FROM_CACHE", task_data)
                        except Exception as e:
                            logger.error(f"Error loading {json_path}: {e}")
                            
            for task_id in list(self.tasks.keys()):
                if task_id not in disk_task_ids:
                    task = self.tasks[task_id]
                    task['cancel_flag'] = True
                    event_bus.emit("TASK_REMOVED", task_id)
                    del self.tasks[task_id]
                    
            event_bus.emit("DISK_SYNC_COMPLETED")
        except Exception as e:
            logger.error(f"Error scanning for cached tasks: {e}")

    def add_task(self, task_id, aid, title, domain):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task['is_paused']:
                task['cancel_flag'] = False
                task['is_paused'] = False
                self.update_task_state(task_id, "等待中", task['progress'])
                asyncio.run_coroutine_threadsafe(self.queue.put(task_id), self.loop)
            return
            
        task_data = {
            'id': task_id,
            'aid': aid,
            'title': title,
            'domain': domain,
            'status': '等待中',
            'progress': 0.0,
            'cancel_flag': False,
            'is_paused': False
        }
        self.tasks[task_id] = task_data
        
        def _save():
            save_task_state(task_data, config_manager.download_path)
        threading.Thread(target=_save, daemon=True).start()
        
        event_bus.emit("TASK_ADDED", task_data)
        asyncio.run_coroutine_threadsafe(self.queue.put(task_id), self.loop)

    def update_task_state(self, task_id, status_text, progress_val):
        task = self.tasks.get(task_id)
        if not task: return
        task['status'] = status_text
        task['progress'] = progress_val
        
        event_bus.emit("TASK_PROGRESS", task_id, status_text, progress_val)
        threading.Thread(target=save_task_state, args=(task, config_manager.download_path), daemon=True).start()

    def pause_task(self, task_id):
        task = self.tasks.get(task_id)
        if task and task['status'] not in ['下载完成', '已暂停', '已暂停 (启动缓存)']:
            task['cancel_flag'] = True
            task['is_paused'] = True
            self.update_task_state(task_id, "已暂停", task['progress'])

    def resume_task(self, task_id):
        task = self.tasks.get(task_id)
        if task and task['is_paused']:
            task['cancel_flag'] = False
            task['is_paused'] = False
            self.update_task_state(task_id, "等待中", task['progress'])
            asyncio.run_coroutine_threadsafe(self.queue.put(task_id), self.loop)

    def cancel_task(self, task_id):
        task = self.tasks.get(task_id)
        if task and task['status'] not in ['下载完成']:
            task['cancel_flag'] = True
            task['is_paused'] = True
            self.update_task_state(task_id, "已取消", task['progress'])

    def remove_task(self, task_id):
        task = self.tasks.get(task_id)
        if task:
            task['cancel_flag'] = True
            threading.Thread(target=delete_task_state, args=(task, config_manager.download_path), daemon=True).start()
            event_bus.emit("TASK_REMOVED", task_id)
            del self.tasks[task_id]

    async def _worker_loop(self):
        while True:
            task_id = await self.queue.get()
            if task_id is None:
                self.queue.task_done()
                break
                
            task = self.tasks.get(task_id)
            if not task or task.get('cancel_flag'):
                self.queue.task_done()
                continue
                
            try:
                await self.process_download(task)
            except Exception as e:
                logger.error(f"Task {task_id} failed with error: {e}")
                if not task.get('cancel_flag'):
                    self.update_task_state(task_id, f"错误: {str(e)[:15]}", task['progress'])
                    task['is_paused'] = True
            finally:
                self.queue.task_done()

    async def process_download(self, task):
        if task['cancel_flag']: return
        
        self.update_task_state(task['id'], "解析目录...", task['progress'])
        
        aid = task['aid']
        domain = task['domain']
        
        save_dir = get_unfinished_dir(task['title'], config_manager.download_path)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        view_urls = []
        page = 1
        
        while True:
            if task['cancel_flag']: return
            
            index_url = f"{domain}/photos-index-page-{page}-aid-{aid}.html"
            try:
                html_content = await network_client.fetch_text(index_url)
                urls, has_next = extractor.parse_index_page(html_content)
                view_urls.extend(urls)
                
                if has_next:
                    page += 1
                    await asyncio.sleep(1)
                else:
                    break
            except Exception as e:
                logger.error(f"Error fetching index page {page}: {e}")
                break
                
        total_imgs = len(view_urls)
        if total_imgs == 0:
            if not task['cancel_flag']:
                self.update_task_state(task['id'], "解析失败(空图包)", 0.0)
                task['is_paused'] = True
            return
            
        if task['cancel_flag']: return
        self.update_task_state(task['id'], f"准备下载 (0/{total_imgs})", task['progress'])
        
        downloaded = 0
        
        async def download_single_image(i, view_href):
            nonlocal downloaded
            if task['cancel_flag']: return
            
            view_url = domain + view_href if view_href.startswith('/') else view_href
            success = False
            client = await network_client.get_client()
            
            for attempt in range(3):
                if task['cancel_flag']: return
                try:
                    view_html = await network_client.fetch_text(view_url)
                    img_src = extractor.parse_view_page(view_html)
                    
                    if not img_src:
                        await asyncio.sleep(1)
                        continue
                        
                    if img_src.startswith('//'):
                        img_src = 'https:' + img_src
                    elif img_src.startswith('/'):
                        img_src = domain + img_src
                        
                    filename = img_src.split('/')[-1]
                    
                    if not config_manager.use_original_filename:
                        ext = filename.split('.')[-1] if '.' in filename else 'jpg'
                        filename = f"{i+1:03d}.{ext}"

                    fmt_setting = config_manager.download_format
                    if fmt_setting != "原始格式":
                        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                        filename = f"{base_name}.{fmt_setting}"
                        
                    filepath = os.path.join(save_dir, filename)
                    
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 1024:
                        success = True
                        break

                    async with client.stream("GET", img_src, headers={'Referer': view_url}) as resp:
                        resp.raise_for_status()
                        
                        if fmt_setting == "原始格式":
                            def write_original():
                                with open(filepath, 'wb') as f:
                                    for chunk in resp.iter_bytes(chunk_size=8192):
                                        f.write(chunk)
                                        self.downloaded_bytes += len(chunk)
                            # Actually, stream response iteration needs to be async.
                            pass
                            # To be safe from blocking UI thread, we can just do blocking write, it's fast enough.
                            with open(filepath, 'wb') as f:
                                async for chunk in resp.aiter_bytes(chunk_size=8192):
                                    f.write(chunk)
                                    self.downloaded_bytes += len(chunk)
                        else:
                            buf = BytesIO()
                            async for chunk in resp.aiter_bytes(chunk_size=8192):
                                buf.write(chunk)
                                self.downloaded_bytes += len(chunk)
                                
                            def convert_and_save():
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
                                
                            await asyncio.get_event_loop().run_in_executor(None, convert_and_save)
                            
                    success = True
                    break
                    
                except Exception as e:
                    logger.error(f"Attempt {attempt+1} failed for {view_url}: {e}")
                    await asyncio.sleep(2)
                    
            if success:
                downloaded += 1
                self.update_task_state(task['id'], f"下载中 ({downloaded}/{total_imgs})", downloaded/total_imgs)
                await asyncio.sleep(config_manager.image_rest_time)
            else:
                logger.error(f"Completely failed to download {view_url} after 3 attempts.")

        max_img_workers = max(1, config_manager.concurrent_images)
        sem = asyncio.Semaphore(max_img_workers)
        
        async def bounded_download(i, href):
            async with sem:
                await download_single_image(i, href)
                
        tasks = [asyncio.create_task(bounded_download(i, href)) for i, href in enumerate(view_urls)]
        await asyncio.gather(*tasks)
                
        if task['cancel_flag']: return
        
        if downloaded == total_imgs:
            task['status'] = '下载完成'
            task['progress'] = 1.0
            
            try:
                delete_task_state(task, config_manager.download_path)
            except: pass
            
            try:
                base_title = re.sub(r'[\\/*?:"<>|]', '_', task['title']).strip()
                if base_title.startswith("[未完成]_"):
                    base_title = base_title[len("[未完成]_"):]
                completed_dir = os.path.join(config_manager.download_path, base_title)
                
                if os.path.exists(completed_dir):
                    suffix = 1
                    while os.path.exists(f"{completed_dir}_{suffix}"):
                        suffix += 1
                    completed_dir = f"{completed_dir}_{suffix}"
                    
                os.rename(save_dir, completed_dir)
            except Exception as e:
                logger.error(f"Error renaming completed folder: {e}")
                
            event_bus.emit("TASK_COMPLETED", task['id'])
            
            event_bus.emit("TASK_REMOVED", task['id'])
            if task['id'] in self.tasks:
                del self.tasks[task['id']]
                
            await asyncio.sleep(config_manager.comic_rest_time)
        else:
            self.update_task_state(task['id'], f"部分失败 ({downloaded}/{total_imgs})", downloaded/total_imgs)
            task['is_paused'] = True

download_manager = DownloadManager()
