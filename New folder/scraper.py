import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

async def fetch_html(session, url):
    """Helper function to fetch HTML safely."""
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                return await response.text()
    except Exception:
        pass
    return ""

async def sweep_domain(domain: str, allow_deep_crawl: bool = False) -> dict:
    """Core scraping engine with gated Deep Path Recrawl logic."""
    clean_domain = domain.lower().replace("www.", "").replace("http://", "").replace("https://", "").split('/')[0]
    base_url = f"https://{clean_domain}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"
    }
    
    results = {
        "emails": [],
        "linkedin": "",
        "twitter": "",
        "facebook": "",
        "instagram": "",
        "github": "",
        "youtube": ""
    }
    
    email_regex = r'[a-zA-Z0-9.\-_+#:]+@[a-zA-Z0-9.\-_]+\.[a-zA-Z]{2,5}'
    
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            # 1. THE ROOT SWEEP
            html = await fetch_html(session, base_url)
            if not html:
                return results
                
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract Emails
            found_emails = re.findall(email_regex, html)
            results["emails"] = list(set([
                e.lower() for e in found_emails 
                if not e.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'))
            ]))
            
            # Extract Socials
            for anchor in soup.find_all('a', href=True):
                href = anchor['href'].lower()
                if "linkedin.com/company" in href or "linkedin.com/in" in href:
                    results["linkedin"] = anchor['href']
                elif "twitter.com/" in href or "x.com/" in href:
                    results["twitter"] = anchor['href']
                elif "facebook.com/" in href:
                    results["facebook"] = anchor['href']
                elif "instagram.com/" in href:
                    results["instagram"] = anchor['href']
                elif "github.com/" in href:
                    results["github"] = anchor['href']
                elif "youtube.com/" in href:
                    results["youtube"] = anchor['href']

            # 2. THE DEEP PATH RECRAWL (Only runs if authorized by Ultra plan or UI)
            if allow_deep_crawl and len(results["emails"]) == 0:
                deep_paths = []
                
                for anchor in soup.find_all('a', href=True):
                    href = anchor['href'].lower()
                    if 'contact' in href or 'about' in href:
                        full_url = urljoin(base_url, anchor['href'])
                        if clean_domain in full_url and full_url not in deep_paths:
                            deep_paths.append(full_url)
                            if len(deep_paths) >= 2: 
                                break
                
                if deep_paths:
                    tasks = [fetch_html(session, url) for url in deep_paths]
                    pages_html = await asyncio.gather(*tasks)
                    
                    for page_html in pages_html:
                        if page_html:
                            deep_emails = re.findall(email_regex, page_html)
                            results["emails"].extend([
                                e.lower() for e in deep_emails 
                                if not e.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'))
                            ])
                    
                    results["emails"] = list(set(results["emails"]))

        return results
    except Exception:
        return results
