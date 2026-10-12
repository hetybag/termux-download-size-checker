#!/usr/bin/env python3
"""
Termux Download Size Checker - Browser-Based Version
Handles Cloudflare captcha and instant download links using Selenium
Compatible with Android Termux environment
"""

import sys
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from urllib.parse import urlparse
import subprocess
import os


class CloudflareBypassChecker:
    def __init__(self, headless=False):
        self.headless = headless
        self.driver = None
        
    def setup_driver(self):
        """Setup Selenium Chrome driver for Android/Termux"""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1280,1024")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")
            
            # Termux-specific: use default Chromium
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")
            
            # Try to use system Chromium
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                print("[+] Chrome driver initialized successfully")
                return True
            except Exception as e:
                print(f"[!] Failed to initialize Chrome: {e}")
                print("[*] Trying with chromium-browser...")
                
                # Alternative for Termux
                chrome_options.binary_location = "/data/data/com.termux/files/usr/bin/chromium-browser"
                self.driver = webdriver.Chrome(options=chrome_options)
                print("[+] Chromium browser driver initialized successfully")
                return True
                
        except Exception as e:
            print(f"[!] Error setting up driver: {e}")
            print("\n[*] To use this script, you need to install chromium in Termux:")
            print("    pkg install chromium chromium-webview")
            return False
    
    def wait_for_cloudflare(self, timeout=30):
        """Wait for Cloudflare challenge to complete"""
        try:
            print("[*] Waiting for Cloudflare verification to complete...")
            
            # Wait for the challenge page to disappear
            wait = WebDriverWait(self.driver, timeout)
            
            # Look for challenge iframe or verification box
            try:
                wait.until_not(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "iframe[src*='challenges']")))
                print("[+] Challenge iframe disappeared")
            except:
                pass
            
            # Wait for page to stabilize after challenge
            time.sleep(3)
            
            print("[+] Cloudflare verification completed (or timed out)")
            return True
            
        except Exception as e:
            print(f"[!] Error waiting for Cloudflare: {e}")
            return False
    
    def detect_cloudflare_challenge(self):
        """Detect if page has Cloudflare challenge"""
        try:
            page_source = self.driver.page_source
            
            if any(keyword in page_source.lower() for keyword in 
                   ["performing security verification", "cf_challenge", "cloudflare", "verifying"]):
                print("[!] Cloudflare security challenge detected")
                return True
            
            # Check for challenge elements
            try:
                self.driver.find_element(By.CLASS_NAME, "cf-challenge")
                print("[!] Cloudflare challenge element found")
                return True
            except:
                pass
            
            return False
            
        except Exception as e:
            print(f"[!] Error detecting challenge: {e}")
            return False
    
    def get_file_size_from_headers(self):
        """Extract file size from response headers via browser DevTools"""
        try:
            # Get all network requests
            logs = self.driver.get_log('performance')
            
            for log in logs:
                message = log['message']
                if 'Network.response' in message or 'Network.request' in message:
                    try:
                        data = eval(message.split('{"message":')[1])
                        if 'message' in data:
                            msg = data['message']
                            if 'params' in msg and 'response' in msg['params']:
                                headers = msg['params']['response'].get('headers', {})
                                size = headers.get('content-length')
                                if size:
                                    return int(size)
                    except:
                        pass
            
            return None
            
        except Exception as e:
            print(f"[!] Error extracting from headers: {e}")
            return None
    
    def find_size_in_page(self):
        """Find file size mentioned in page content"""
        try:
            page_source = self.driver.page_source
            
            # Common patterns for file size display
            patterns = [
                r'(?:File\s+)?[Ss]ize\s*[:\-]?\s*([0-9.]+\s*(?:B|KB|MB|GB|TB))',
                r'([0-9.]+\s*(?:B|KB|MB|GB|TB))\s*(?:file|download)',
                r'(?:Download|Get)\s+([0-9.]+\s*(?:KB|MB|GB))',
                r'([0-9]+(?:[.,][0-9]+)?)\s*(bytes|KB|MB|GB|TB)',
                r'\'size\'\s*:\s*\'?([0-9.]+\s*(?:KB|MB|GB))',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_source, re.IGNORECASE)
                if match:
                    size_str = match.group(1)
                    print(f"[+] Found size in page: {size_str}")
                    return self.parse_size(size_str)
            
            return None
            
        except Exception as e:
            print(f"[!] Error finding size in page: {e}")
            return None
    
    def parse_size(self, size_str):
        """Parse size string to bytes"""
        try:
            size_str = size_str.strip().replace(',', '')
            match = re.match(r'([0-9.]+)\s*([KMGT]?B)?', size_str, re.IGNORECASE)
            
            if match:
                value = float(match.group(1))
                unit = match.group(2) if match.group(2) else 'B'
                
                multipliers = {
                    'B': 1,
                    'KB': 1024,
                    'MB': 1024**2,
                    'GB': 1024**3,
                    'TB': 1024**4,
                }
                
                unit = unit.upper()
                if unit in multipliers:
                    return int(value * multipliers[unit])
            
            return None
            
        except Exception as e:
            print(f"[!] Error parsing size: {e}")
            return None
    
    def human_size(self, num_bytes):
        """Convert bytes to human-readable format"""
        if num_bytes is None:
            return "Unknown"
        
        num_bytes = float(num_bytes)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if num_bytes < 1024.0 or unit == "TB":
                if unit == "B":
                    return f"{num_bytes:.0f} {unit}"
                return f"{num_bytes:.2f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.2f} TB"
    
    def get_size(self, url, wait_time=45):
        """Main function to get file size"""
        print(f"\n[+] Starting browser-based size checker...")
        print(f"[+] Target URL: {url}\n")
        
        if not self.setup_driver():
            return None, None, "driver-setup-failed"
        
        try:
            # Navigate to URL
            print("[*] Loading page...")
            self.driver.get(url)
            print("[+] Page loaded")
            
            # Check for Cloudflare challenge
            if self.detect_cloudflare_challenge():
                print("[*] Waiting for Cloudflare to verify...")
                self.wait_for_cloudflare(timeout=wait_time)
                print("[+] Cloudflare verification passed")
            else:
                print("[+] No Cloudflare challenge detected")
            
            # Wait for page to fully load
            time.sleep(3)
            
            # Get current URL after all redirects
            final_url = self.driver.current_url
            print(f"[+] Final URL: {final_url}")
            
            # Try to find size in page content
            print("[*] Searching for file size in page...")
            size = self.find_size_in_page()
            
            if size:
                return final_url, size, "found-in-page"
            
            print("[!] Could not find file size in page content")
            
            # Try to extract from network logs
            print("[*] Checking network headers...")
            size = self.get_file_size_from_headers()
            
            if size:
                return final_url, size, "found-in-headers"
            
            print("[!] File size not available in headers")
            
            return final_url, None, "size-not-available"
            
        except Exception as e:
            print(f"[!] Error during size checking: {e}")
            return url, None, f"error: {str(e)}"
        
        finally:
            if self.driver:
                print("[*] Closing browser...")
                self.driver.quit()
    
    def check_multiple_links(self, file_path, wait_time=45):
        """Check multiple links from a file"""
        try:
            with open(file_path, 'r') as f:
                links = [line.strip() for line in f if line.strip() and line.strip().startswith('http')]
            
            results = []
            for i, link in enumerate(links, 1):
                print(f"\n{'='*70}")
                print(f"Link {i}/{len(links)}")
                print(f"{'='*70}")
                
                checker = CloudflareBypassChecker(headless=False)
                final_url, size, status = checker.get_size(link, wait_time=wait_time)
                
                results.append({
                    'original': link,
                    'final': final_url,
                    'size': size,
                    'size_human': self.human_size(size) if size else "Unknown",
                    'status': status
                })
                
                time.sleep(2)
            
            return results
        
        except FileNotFoundError:
            print(f"[!] File not found: {file_path}")
            return None


def main():
    if len(sys.argv) < 2:
        print("""
╔════════════════════════════════════════════════════════════════╗
║   Download Size Checker - Browser-Based (Cloudflare Support)   ║
╚════════════════════════════════════════════════════════════════╝

USAGE:
  Single URL:   python sizecheck_browser.py <url>
  Multiple:     python sizecheck_browser.py --file <file>
  Wait time:    python sizecheck_browser.py <url> --wait 60

EXAMPLES:
  python sizecheck_browser.py "https://new1.filesdl.one/l/file.zip"
  python sizecheck_browser.py --file links.txt --wait 60

REQUIREMENTS (Termux):
  pkg install python python-pip chromium chromium-webview
  pip install selenium

NOTES:
  • This version uses a real browser to handle Cloudflare challenges
  • Will open a browser window - let it complete verification
  • Wait time is how long to wait for Cloudflare (default 45 seconds)
  • For multiple links, provide a text file with one URL per line
        """)
        sys.exit(1)
    
    wait_time = 45
    
    # Parse --wait argument
    if "--wait" in sys.argv:
        wait_idx = sys.argv.index("--wait")
        if wait_idx + 1 < len(sys.argv):
            try:
                wait_time = int(sys.argv[wait_idx + 1])
                sys.argv.pop(wait_idx)
                sys.argv.pop(wait_idx)
            except:
                pass
    
    checker = CloudflareBypassChecker(headless=False)
    
    if sys.argv[1] == "--file" and len(sys.argv) > 2:
        results = checker.check_multiple_links(sys.argv[2], wait_time=wait_time)
        
        if results:
            print(f"\n\n{'='*70}")
            print("SUMMARY")
            print(f"{'='*70}")
            
            for i, r in enumerate(results, 1):
                print(f"\n[{i}] {r['status'].upper()}")
                print(f"    URL: {r['original']}")
                print(f"    Final: {r['final']}")
                print(f"    Size: {r['size_human']}")
                if r['size']:
                    print(f"    Bytes: {r['size']:,}")
    else:
        url = sys.argv[1]
        final_url, size, status = checker.get_size(url, wait_time=wait_time)
        
        print(f"\n{'='*70}")
        print("RESULT")
        print(f"{'='*70}")
        print(f"Original URL: {url}")
        print(f"Final URL: {final_url}")
        print(f"Status: {status}")
        
        if size is not None:
            human = checker.human_size(size)
            print(f"Size: {human} ({size:,} bytes)")
        else:
            print("Size: Could not be determined")
            print("\nPossible reasons:")
            print("  • Size not displayed on page")
            print("  • Page requires additional interaction")
            print("  • Dynamic content loaded via JavaScript")


if __name__ == "__main__":
    main()
