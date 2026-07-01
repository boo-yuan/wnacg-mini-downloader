import os
import json
import re
from core.logger import get_app_dir, logger
from core.event_bus import event_bus

class ConfigManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self._initialized = True
        
        self.base_dir = get_app_dir()
        self.config_file = os.path.join(self.base_dir, "config.json")
        self.download_path = os.path.join(self.base_dir, "download")
        
        # Defaults
        self.api_domain_mode = "默认"
        self.custom_api_domain = "www.wn07.ru"
        self.proxy_mode = "系统代理"
        self.custom_proxy_ip = "127.0.0.1"
        self.custom_proxy_port = "7890"
        
        self.concurrent_comics = 2
        self.comic_rest_time = 0
        self.concurrent_images = 5
        self.image_rest_time = 1
        
        self.download_format = "jpg"
        self.use_original_filename = True
        
        self.user_cookie = ""
        
        self.load_config()

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.api_domain_mode = config.get('api_domain_mode', self.api_domain_mode)
                    self.custom_api_domain = config.get('custom_api_domain', self.custom_api_domain)
                    self.proxy_mode = config.get('proxy_mode', self.proxy_mode)
                    
                    if 'proxy_mode' not in config:
                        if config.get('use_system_proxy', True):
                            self.proxy_mode = "系统代理"
                        elif config.get('custom_proxy_url'):
                            self.proxy_mode = "自定义"
                            m = re.search(r'//([^:]+):(\d+)', config['custom_proxy_url'])
                            if m:
                                self.custom_proxy_ip = m.group(1)
                                self.custom_proxy_port = m.group(2)
                                
                    self.custom_proxy_ip = config.get('custom_proxy_ip', self.custom_proxy_ip)
                    self.custom_proxy_port = str(config.get('custom_proxy_port', self.custom_proxy_port))
                    
                    self.concurrent_comics = config.get('concurrent_comics', self.concurrent_comics)
                    self.comic_rest_time = config.get('comic_rest_time', self.comic_rest_time)
                    self.concurrent_images = config.get('concurrent_images', self.concurrent_images)
                    self.image_rest_time = config.get('image_rest_time', self.image_rest_time)

                    if 'download_path' in config and os.path.isdir(config['download_path']):
                        self.download_path = config['download_path']
                    self.download_format = config.get('download_format', self.download_format)
                    self.use_original_filename = config.get('use_original_filename', self.use_original_filename)
                    self.user_cookie = config.get('user_cookie', self.user_cookie)
        except Exception as e:
            logger.error(f"Error loading config: {e}")

    def save_config(self):
        try:
            config = {
                'api_domain_mode': self.api_domain_mode,
                'custom_api_domain': self.custom_api_domain,
                'proxy_mode': self.proxy_mode,
                'custom_proxy_ip': self.custom_proxy_ip,
                'custom_proxy_port': self.custom_proxy_port,
                'concurrent_comics': self.concurrent_comics,
                'comic_rest_time': self.comic_rest_time,
                'concurrent_images': self.concurrent_images,
                'image_rest_time': self.image_rest_time,
                'download_path': self.download_path,
                'download_format': self.download_format,
                'use_original_filename': self.use_original_filename,
                'user_cookie': self.user_cookie
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            event_bus.emit("CONFIG_UPDATED", self)
        except Exception as e:
            logger.error(f"Error saving config: {e}")

config_manager = ConfigManager()
