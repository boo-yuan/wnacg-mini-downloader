import json
import re
import os
from bs4 import BeautifulSoup
from core.logger import logger

class Extractor:
    def __init__(self):
        self.rules = {}
        self.load_rules()

    def load_rules(self):
        rules_path = os.path.join(os.path.dirname(__file__), "parser_rules.json")
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                self.rules = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load parser_rules.json: {e}")

    def parse_search_results(self, html_content, domain):
        soup = BeautifulSoup(html_content, 'html.parser')
        rules = self.rules.get("search_page", {})
        results = []
        total_pages = 1
        
        paginator = soup.select_one(rules.get("paginator_container", "div.f_left.paginator"))
        if paginator:
            a_tags = paginator.select(rules.get("paginator_links", "a"))
            for a in a_tags:
                text = a.get_text(strip=True)
                if text.isdigit():
                    total_pages = max(total_pages, int(text))
                elif '尾页' in text or '>>' in text:
                    href = a.get('href', '')
                    m = re.search(r'p=(\d+)', href)
                    if m:
                        total_pages = max(total_pages, int(m.group(1)))
                        
            span = paginator.select_one(rules.get("paginator_current", "span.thisclass"))
            if span and span.text.isdigit():
                total_pages = max(total_pages, int(span.text))
        
        items = []
        for selector in rules.get("item_container", ["li.gallary_item", ".pic_box"]):
            items = soup.select(selector)
            if items: 
                if selector == ".pic_box":
                    items = [item.parent for item in items]
                break
        
        if not items:
            return [], total_pages
            
        for item in items:
            try:
                img_tag = item.select_one(rules.get("item_img", "img"))
                img_url = img_tag['src'] if img_tag and img_tag.has_attr('src') else ''
                if img_url and img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url and img_url.startswith('/'):
                    img_url = domain + img_url
                    
                title_tag = item.select_one(rules.get("item_title_a", "a[title]"))
                a_tag = item.select_one(rules.get("item_any_a", "a"))
                
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
                info_col = item.select_one(rules.get("item_info_col", "div.info_col"))
                if info_col:
                    info_text = info_col.text.strip()
                    m_c = re.search(r'(\d+)\s*[张張]', info_text)
                    m_d = re.search(r'(\d{4}-\d{2}-\d{2})', info_text)
                    c_str = f"{m_c.group(1)} 图" if m_c else ""
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
                
        return results, total_pages

    def parse_index_page(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        rules = self.rules.get("index_page", {})
        
        view_urls = []
        boxes = soup.select(rules.get("pic_box", "div.pic_box"))
        for box in boxes:
            a = box.find('a')
            if a and a.has_attr('href'):
                view_urls.append(a['href'])
                
        has_next = False
        paginator = soup.select_one(rules.get("paginator", "div.f_left.paginator"))
        if paginator:
            next_span = paginator.select_one(rules.get("next_span", "span.next"))
            if next_span and next_span.find('a'):
                has_next = True
                
        return view_urls, has_next

    def parse_view_page(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        rules = self.rules.get("view_page", {})
        
        img = soup.find('img', id=rules.get("img_id", "picarea"))
        if not img or not img.has_attr('src'):
            return None
        return img['src']

extractor = Extractor()
