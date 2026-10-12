#!/usr/bin/env python3
"""
Termux Download Size Checker
Handles instant download links including Cloudflare captcha verification
"""

import sys
import re
import json
import time
from urllib.parse import urlparse, urljoin

try:
    import cloudscraper
except ImportError:
    cloudscraper = None

try:
    import requests
except ImportError:
    requests = None

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    webdriver = None


def human_size(num_bytes):
    """Convert bytes to human-readable format"""
    if num_bytes is None:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{num_bytes:.0f} {unit}"
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"


def get_size_cloudscraper(url):
    """Try using cloudscraper to bypass Cloudflare"""
    if cloudscraper is None:
        return None, None, "cloudscraper-not-installed"
    
    try:
        print("[*] Attempting with cloudscraper (Cloudflare bypass)...")
        scraper = cloudscraper.create_scraper()
        
        # Try HEAD request first
        try:
            resp = scraper.head(url, timeout=20, allow_redirects=True)
            if resp.status_code == 200:
                size = resp.headers.get("Content-Length")
                if size:
                    return resp.url, int(size), "cloudscraper-HEAD"
        except Exception:
            pass
        
        # Try GET request
        resp = scraper.get(url, timeout=25, allow_redirects=True, stream=True)
        
        if resp.status_code == 200:
            size = resp.headers.get("Content-Length")
            if size:
                return resp.url, int(size), "cloudscraper-GET"
            
            # Check Content-Range header
            rang = resp.headers.get("Content-Range")
            if rang:
                m = re.search(r'/(\d+)$', rang)
                if m:
                    return resp.url, int(m.group(1)), "cloudscraper-Content-Range"
            
            # For streaming, check actual downloaded size
            total_size = 0
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    total_size += len(chunk)
                if total_size > 1000000:  # Limit to 1MB sample
                    break
            
            if total_size > 0:
                return resp.url, total_size, "cloudscraper-stream-sample"
        
        return resp.url, None, f"cloudscraper-HTTP-{resp.status_code}"
    
    except Exception as e:
        return url, None, f"cloudscraper-error: {str(e)}"


def get_size_requests(url):
    """Try using requests library with custom headers"""
    if requests is None:
        return None, None, "requests-not-installed"
    
    try:
        print("[*] Attempting with requests library...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # Try HEAD
        try:
            resp = requests.head(url, headers=headers, timeout=20, allow_redirects=True)
            if resp.status_code == 200:
                size = resp.headers.get("Content-Length")
                if size:
                    return resp.url, int(size), "requests-HEAD"
        except Exception:
            pass
        
        # Try GET
        resp = requests.get(url, headers=headers, timeout=25, allow_redirects=True, stream=True)
        
        if resp.status_code == 200:
            size = resp.headers.get("Content-Length")
            if size:
                return resp.url, int(size), "requests-GET"
            
            rang = resp.headers.get("Content-Range")
            if rang:
                m = re.search(r'/(\d+)$', rang)
                if m:
                    return resp.url, int(m.group(1)), "requests-Content-Range"
        
        return resp.url, None, f"requests-HTTP-{resp.status_code}"
    
    except Exception as e:
        return url, None, f"requests-error: {str(e)}"


def get_size_selenium(url):
    """Use Selenium with headless browser as last resort"""
    if webdriver is None:
        return None, None, "selenium-not-installed"
    
    try:
        print("[*] Attempting with Selenium (headless browser)...")
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        
        # Wait for page to load
        time.sleep(5)
        
        # Try to find file size in page content
        page_source = driver.page_source
        
        # Look for common size indicators
        patterns = [
            r'size["\']?\s*:\s*["\']?(\d+(?:\.\d+)?)\s*(KB|MB|GB)?',
            r'(\d+(?:\.\d+)?)\s*(KB|MB|GB|TB)',
            r'download["\']?\s*.*?(\d+(?:\.\d+)?)\s*(KB|MB|GB)',
        ]
        
        for pattern in patterns:
            m = re.search(pattern, page_source, re.I)
            if m:
                multipliers = {"KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
                size = float(m.group(1))
                unit = m.group(2) if m.group(2) else "B"
                size = int(size * multipliers.get(unit.upper(), 1))
                driver.quit()
                return driver.current_url, size, "selenium-found-in-page"
        
        driver.quit()
        return url, None, "selenium-no-size-found"
    
    except Exception as e:
        return url, None, f"selenium-error: {str(e)}"


def get_size(url):
    """Main function to get file size using available methods"""
    print(f"\n[+] Checking size for: {url}\n")
    
    methods = [
        ("Cloudscraper", get_size_cloudscraper),
        ("Requests", get_size_requests),
        ("Selenium", get_size_selenium),
    ]
    
    for method_name, method_func in methods:
        final_url, size, status = method_func(url)
        
        if size is not None:
            return final_url, size, status
        
        print(f"[✗] {method_name} failed: {status}")
    
    return url, None, "All-methods-failed"


def check_multiple_links(file_path):
    """Check multiple links from a file"""
    try:
        with open(file_path, 'r') as f:
            links = [line.strip() for line in f if line.strip() and line.strip().startswith('http')]
        
        results = []
        for i, link in enumerate(links, 1):
            print(f"\n{'='*60}")
            print(f"Link {i}/{len(links)}")
            print(f"{'='*60}")
            
            final_url, size, status = get_size(link)
            results.append({
                'original': link,
                'final': final_url,
                'size': size,
                'size_human': human_size(size) if size else "Unknown",
                'status': status
            })
            
            time.sleep(2)  # Be polite to servers
        
        return results
    
    except FileNotFoundError:
        print(f"[!] File not found: {file_path}")
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Single URL:  python sizecheck.py <download-url>")
        print("  Multiple:    python sizecheck.py --file <file-with-links>")
        print("\nExample:")
        print("  python sizecheck.py 'https://new1.filesdl.one/l/file.zip'")
        print("  python sizecheck.py --file links.txt")
        sys.exit(1)
    
    if sys.argv[1] == "--file" and len(sys.argv) > 2:
        results = check_multiple_links(sys.argv[2])
        if results:
            print(f"\n\n{'='*60}")
            print("SUMMARY")
            print(f"{'='*60}")
            for r in results:
                print(f"\n[{r['status']}]")
                print(f"  URL: {r['original']}")
                print(f"  Size: {r['size_human']}")
    else:
        url = sys.argv[1]
        final_url, size, status = get_size(url)
        
        print(f"\n{'='*60}")
        print("RESULT")
        print(f"{'='*60}")
        print(f"Original URL: {url}")
        print(f"Final URL: {final_url}")
        print(f"Status: {status}")
        
        if size is not None:
            print(f"Size: {human_size(size)} ({size:,} bytes)")
        else:
            print("Size: Could not be determined")
            print("\nPossible reasons:")
            print("  • Server requires JavaScript/browser (try installing selenium + chromium)")
            print("  • Site blocks automated access")
            print("  • Link requires login/authentication")


if __name__ == "__main__":
    main()
