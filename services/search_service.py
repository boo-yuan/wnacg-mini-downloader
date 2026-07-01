import urllib.parse
from core.logger import logger
from core.config_manager import config_manager
from network.client import network_client
from network.extractor import extractor

DOMAINS = ['https://www.wnacg.com', 'https://www.wnacg.ru']

class SearchService:
    def search(self, query, page=1):
        domains_to_try = DOMAINS
        if config_manager.api_domain_mode == "自定义" and config_manager.custom_api_domain:
            custom_domain = config_manager.custom_api_domain
            if not custom_domain.startswith("http"):
                custom_domain = "https://" + custom_domain
            domains_to_try = [custom_domain] + DOMAINS
            
        for domain in domains_to_try:
            url = f"{domain}/search/index.php?q={urllib.parse.quote(query)}&m=&syn=yes&f=_all&s=create_time_DESC&p={page}"
            logger.info(f"Fetching: {url}")
            try:
                html_content = network_client.fetch_text(url, timeout=10)
                logger.info(f"Success fetching from {domain}")
                results, total_pages = extractor.parse_search_results(html_content, domain)
                return results, total_pages, None
            except Exception as e:
                logger.error(f"Failed fetching {url}: {e}")
                continue
        
        return [], 1, "搜索请求失败，请检查网络或代理设置，并查看日志。"

search_service = SearchService()
