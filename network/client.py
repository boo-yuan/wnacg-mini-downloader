import urllib.request
import requests
from io import BytesIO
from PIL import Image
from core.logger import logger
from core.config_manager import config_manager
from core.exceptions import NetworkError

class NetworkClient:
    def __init__(self):
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }

    def get_proxies(self):
        proxy_mode = config_manager.proxy_mode
        if proxy_mode == "系统代理" or proxy_mode == "system":
            return urllib.request.getproxies()
        elif proxy_mode == "自定义" or proxy_mode == "custom":
            p_url = f"http://{config_manager.custom_proxy_ip}:{config_manager.custom_proxy_port}"
            return {"http": p_url, "https": p_url}
        else:
            return {"http": "", "https": ""}

    def fetch_text(self, url, headers=None, timeout=10, retries=1):
        req_headers = self.default_headers.copy()
        if headers:
            req_headers.update(headers)
            
        proxies = self.get_proxies()
        
        for attempt in range(retries):
            try:
                resp = requests.get(url, headers=req_headers, proxies=proxies, timeout=timeout)
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                logger.error(f"Failed fetching {url} on attempt {attempt+1}: {e}")
                if attempt == retries - 1:
                    raise NetworkError(f"Request failed: {e}")
        return ""
        
    def fetch_image_stream(self, url, headers=None, timeout=15):
        req_headers = self.default_headers.copy()
        if headers:
            req_headers.update(headers)
        proxies = self.get_proxies()
        
        resp = requests.get(url, headers=req_headers, proxies=proxies, stream=True, timeout=timeout)
        resp.raise_for_status()
        return resp

    def download_thumbnail(self, url, referer="https://www.wnacg.com/"):
        headers = {'Referer': referer}
        try:
            resp = requests.get(url, headers=self.default_headers, proxies=self.get_proxies(), timeout=5)
            resp.raise_for_status()
            image = Image.open(BytesIO(resp.content))
            return image
        except Exception as e:
            logger.error(f"Error downloading thumbnail {url}: {e}")
            return None

network_client = NetworkClient()
