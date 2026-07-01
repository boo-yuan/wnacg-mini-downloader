import threading
import json
import asyncio
from network.client import network_client
from services.download_manager import download_manager
from core.logger import logger
from core.event_bus import event_bus
from network.extractor import extractor
import os

class UpdateService:
    def __init__(self):
        self.rules_url = "https://raw.githubusercontent.com/boo-yuan/WNACG-Mini-Downloader/main/network/parser_rules.json"
        
    def check_for_updates(self):
        asyncio.run_coroutine_threadsafe(self._check_rules_update(), download_manager.loop)
        
    async def _check_rules_update(self):
        try:
            logger.info("Checking for parser rules update...")
            text = await network_client.fetch_text(self.rules_url, timeout=10)
            if not text:
                return
            new_rules = json.loads(text)
            if new_rules.get("version", 0) > extractor.rules.get("version", 0):
                import network
                rules_path = os.path.join(os.path.dirname(network.__file__), "parser_rules.json")
                with open(rules_path, "w", encoding="utf-8") as f:
                    json.dump(new_rules, f, ensure_ascii=False, indent=2)
                extractor.load_rules()
                logger.info(f"Rules updated to version {new_rules.get('version')}")
                event_bus.emit("TOAST", "解析规则已热更新")
                
        except Exception as e:
            logger.error(f"Failed to check rules update: {e}")

update_service = UpdateService()
