import urllib.request
import httpx
import asyncio
from io import BytesIO
from PIL import Image
from core.logger import logger
from core.config_manager import config_manager
from core.exceptions import NetworkError

class AsyncNetworkClient:
    def __init__(self):
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }
        self.client = None
        
        from core.event_bus import event_bus
        event_bus.subscribe("CONFIG_UPDATED", self.on_config_updated)

    def on_config_updated(self, config):
        if self.client and not self.client.is_closed:
            import asyncio
            # We must close the old client cleanly
            asyncio.run_coroutine_threadsafe(self.client.aclose(), asyncio.get_event_loop())
        self.client = None

    def get_proxy(self):
        proxy_mode = config_manager.proxy_mode
        if proxy_mode == "系统代理" or proxy_mode == "system":
            p = urllib.request.getproxies()
            if not p: return None
            return p.get('http') or p.get('https')
        elif proxy_mode == "自定义" or proxy_mode == "custom":
            p_url = f"http://{config_manager.custom_proxy_ip}:{config_manager.custom_proxy_port}"
            return p_url
        else:
            return None

    def _get_client(self):
        if self.client is None or self.client.is_closed:
            proxy_url = self.get_proxy()
            
            cookies = {}
            if config_manager.user_cookie:
                for chunk in config_manager.user_cookie.split(';'):
                    if '=' in chunk:
                        k, v = chunk.strip().split('=', 1)
                        cookies[k] = v
                        
            self.client = httpx.AsyncClient(
                proxy=proxy_url, 
                headers=self.default_headers, 
                cookies=cookies,
                follow_redirects=True, 
                timeout=15.0
            )
        return self.client

    async def fetch_text(self, url, headers=None, timeout=10.0, retries=1):
        req_headers = headers if headers else {}
        client = self._get_client()
        for attempt in range(retries):
            try:
                resp = await client.get(url, headers=req_headers, timeout=timeout)
                resp.raise_for_status()
                return resp.text
            except Exception as e:
                logger.error(f"Failed fetching {url} on attempt {attempt+1}: {e}")
                if attempt == retries - 1:
                    raise NetworkError(f"Request failed: {e}")
        return ""

    async def get_client(self):
        return self._get_client()

    async def download_thumbnail(self, url, referer="https://www.wnacg.com/"):
        headers = {'Referer': referer}
        client = self._get_client()
        try:
            resp = await client.get(url, headers=headers, timeout=5.0)
            resp.raise_for_status()
            image = Image.open(BytesIO(resp.content))
            return image
        except Exception as e:
            logger.error(f"Error downloading thumbnail {url}: {e}")
            return None

network_client = AsyncNetworkClient()
