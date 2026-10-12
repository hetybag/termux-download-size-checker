#!/usr/bin/env python3
"""
Termux Download Size Checker - Auto Cloudflare Solver
Automatically solves Cloudflare captcha verification and detects file size
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
from urllib.parse import urlparse
import json


class CloudflareAutoBypasser:
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
            
            # Android user agent
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")
            
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                print("[+] Chrome driver initialized")
                return True
            except Exception as e:
                print(f"[!] Chrome failed: {e}")
                return False
                
        except Exception as e:
            print(f"[!] Error setting up driver: {e}")
            return False
    
    def click_cloudflare_checkbox(self, timeout=15):
        """Automatically click the Cloudflare 'I am not a robot' checkbox"""
        try:
            print("[*] Looking for Cloudflare challenge checkbox...")
            wait = WebDriverWait(self.driver, timeout)
            
            # Look for common Cloudflare challenge patterns
            challenge_selectors = [
                (By.XPATH, "//input[@id='challenge-checkbox']"),
                (By.XPATH, "//label[@class='cbx']"),
                (By.XPATH, "//*[contains(text(), 'challenge')]"),
                (By.CLASS_NAME, "challenge"),
                (By.CLASS_NAME, "cf-challenge"),
                (By.ID, "challenge-checkbox"),
                (By.XPATH, "//iframe[@src[contains(., 'challenges')]]"),
            ]
            
            for selector_type, selector_value in challenge_selectors:
                try:
                    element = self.driver.find_element(selector_type, selector_value)
                    if element:
                        print(f"[+] Found challenge element: {selector_value}")
                        
                        # Scroll to element
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        time.sleep(1)
                        
                        # Click it
                        try:
                            element.click()
                            print("[+] Clicked challenge checkbox")
                            return True
                        except:
                            # Try JavaScript click
                            self.driver.execute_script("arguments[0].click();", element)
                            print("[+] Clicked challenge checkbox (via JS)")
                            return True
                except:
                    continue
            
            print("[!] Challenge checkbox not found - waiting for auto-solve...")
            return False
            
        except Exception as e:
            print(f"[!] Error clicking checkbox: {e}")
            return False
    
    def wait_for_challenge_completion(self, timeout=90):
        """Wait for Cloudflare challenge to be completed"""
        try:
            print("[*] Waiting for Cloudflare challenge to complete...")
            print(f"[*] (This may take up to {timeout} seconds)\n")
            
            wait = WebDriverWait(self.driver, timeout)
            
            start_time = time.time()
            
            # Monitor page source for challenge indicators
            while time.time() - start_time < timeout:
                page_source = self.driver.page_source.lower()
                current_url = self.driver.current_url.lower()
                
                # Check if challenge page is gone
                if all(keyword not in page_source for keyword in 
                       ["performing security verification", "cf_challenge", "challenge", "verifying"]):
                    
                    if all(keyword not in current_url for keyword in 
                           ["challenges", "challenge"]):
                        print("[+] Challenge completed!")
                        return True
                
                # Show progress
                elapsed = int(time.time() - start_time)
                print(f"\r[*] Waiting... {elapsed}s", end="", flush=True)
                
                time.sleep(1)
            
            print("\n[!] Challenge timeout - proceeding anyway")
            return True
            
        except Exception as e:
            print(f"\n[!] Error waiting for challenge: {e}")
            return False
    
    def detect_cloudflare_page(self):
        """Check if current page is a Cloudflare challenge"""
        try:
            page_source = self.driver.page_source.lower()
            title = self.driver.title.lower()
            
            cf_keywords = [
                "performing security verification",
                "cf_challenge",
                "cloudflare",
                "verifying",
                "protect",
                "challenge"
            ]
            
            return any(keyword in page_source or keyword in title for keyword in cf_keywords)
            
        except:
            return False
    
    def find_download_link_and_size(self):
        """Find download link and extract file size"""
        try:
            print("\n[*] Searching for download link and file size...")
            page_source = self.driver.page_source
            
            # Look for download buttons and links
            download_selectors = [
                (By.XPATH, "//a[contains(@href, 'download')]"),
                (By.XPATH, "//button[contains(text(), 'Download')]"),
                (By.XPATH, "//a[contains(text(), 'Download')]"),
                (By.CLASS_NAME, "download-btn"),
                (By.CLASS_NAME, "download-link"),
                (By.ID, "download"),
            ]
            
            download_link = None
            for selector_type, selector_value in download_selectors:
                try:
                    elements = self.driver.find_elements(selector_type, selector_value)
                    if elements:
                        for elem in elements:
                            href = elem.get_attribute("href")
                            if href and href.startswith("http"):
                                download_link = href
                                print(f"[+] Found download link: {href[:80]}...")
                                break
                        if download_link:
                            break
                except:
                    continue
            
            # Extract file size from page
            size = self.extract_size_from_page(page_source)
            
            return download_link, size
            
        except Exception as e:
            print(f"[!] Error finding download link: {e}")
            return None, None
    
    def extract_size_from_page(self, page_source):
        """Extract file size from page content"""
        try:
            # Common patterns for file size
            patterns = [
                r'(?:File\s+)?[Ss]ize\s*[:\-]?\s*<?([0-9.]+\s*(?:B|KB|MB|GB|TB))',
                r'[Ss]ize["\']?\s*[:\-]?\s*["\']?([0-9.]+\s*(?:B|KB|MB|GB|TB))["\']?',
                r'(?:Download|Get)\s+([0-9.]+\s*(?:KB|MB|GB))',
                r'([0-9.]+\s*(?:B|KB|MB|GB|TB))\s*(?:file|download)',
                r'data-size=[\'"]*([0-9.]+\s*(?:B|KB|MB|GB|TB))',
                r'\'size\'\s*:\s*[\'"]*([0-9.]+\s*(?:B|KB|MB|GB|TB))',
                r'"size"\s*:\s*"?([0-9.]+\s*(?:B|KB|MB|GB|TB))',
                r'content-length["\']?\s*:\s*[\'"]*([0-9.]+\s*(?:B|KB|MB|GB|TB))',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_source, re.IGNORECASE)
                if match:
                    size_str = match.group(1)
                    print(f"[+] Found size indicator: {size_str}")
                    return self.parse_size(size_str)
            
            print("[!] File size not found in page")
            return None
            
        except Exception as e:
            print(f"[!] Error extracting size: {e}")
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
    
    def get_size(self, url):
        """Main function to get file size with auto Cloudflare solving"""
        print(f"\n{'='*70}")
        print("  AUTO CLOUDFLARE SOLVER - FILE SIZE DETECTOR")
        print(f"{'='*70}")
        print(f"\n[+] Target URL: {url}\n")
        
        if not self.setup_driver():
            print("[!] Failed to setup Chrome driver")
            print("\nInstall in Termux:")
            print("  pkg install chromium chromium-chromedriver")
            print("  pip install selenium")
            return None, None, "driver-setup-failed"
        
        try:
            # Load the page
            print("[*] Loading page...")
            self.driver.get(url)
            print("[+] Page loaded")
            
            # Give page time to render
            time.sleep(3)
            
            # Check if it's a Cloudflare challenge
            if self.detect_cloudflare_page():
                print("[!] Cloudflare challenge detected!")
                print("[*] Attempting to solve challenge...\n")
                
                # Try to click the checkbox
                self.click_cloudflare_checkbox()
                
                # Wait for challenge completion
                self.wait_for_challenge_completion(timeout=90)
                
                print("\n[+] Challenge should be completed")
                time.sleep(3)
            else:
                print("[+] No Cloudflare challenge detected")
            
            # Get final URL after any redirects
            final_url = self.driver.current_url
            print(f"\n[+] Final URL: {final_url}")
            
            # Find download link and size
            download_link, size = self.find_download_link_and_size()
            
            if download_link:
                print(f"[+] Download link: {download_link[:80]}...")
            
            if size:
                print(f"[+] File size detected: {self.human_size(size)}")
                return final_url, size, "success"
            else:
                print("[!] Could not detect file size")
                return final_url, None, "no-size-found"
            
        except Exception as e:
            print(f"[!] Error: {e}")
            import traceback
            traceback.print_exc()
            return url, None, f"error: {str(e)}"
        
        finally:
            if self.driver:
                print("\n[*] Closing browser...")
                try:
                    self.driver.quit()
                except:
                    pass
    
    def check_multiple_links(self, file_path):
        """Check multiple links from a file"""
        try:
            with open(file_path, 'r') as f:
                links = [line.strip() for line in f if line.strip() and line.strip().startswith('http')]
            
            print(f"\n[+] Found {len(links)} links to check\n")
            
            results = []
            for i, link in enumerate(links, 1):
                print(f"\n{'='*70}")
                print(f"Link {i}/{len(links)}")
                print(f"{'='*70}")
                
                final_url, size, status = self.get_size(link)
                
                results.append({
                    'num': i,
                    'original': link,
                    'final': final_url,
                    'size': size,
                    'size_human': self.human_size(size) if size else "Unknown",
                    'status': status
                })
                
                time.sleep(2)
            
            # Print summary
            print(f"\n\n{'='*70}")
            print("SUMMARY")
            print(f"{'='*70}\n")
            
            for r in results:
                status_icon = "✓" if r['size'] else "✗"
                print(f"[{status_icon}] Link {r['num']}: {r['size_human']}")
                print(f"    {r['original'][:60]}...")
                if r['size']:
                    print(f"    {r['size']:,} bytes")
                print()
            
            return results
        
        except FileNotFoundError:
            print(f"[!] File not found: {file_path}")
            return None


def main():
    if len(sys.argv) < 2:
        print("""
╔════════════════════════════════════════════════════════════════════╗
║  AUTO CLOUDFLARE SOLVER - Download Size Detector for Termux        ║
║  Automatically solves Cloudflare captcha and detects file size      ║
╚════════════════════════════════════════════════════════════════════╝

USAGE:
  Single URL:   python sizecheck_browser.py <url>
  Multiple:     python sizecheck_browser.py --file <file>

EXAMPLES:
  python sizecheck_browser.py "https://new1.filesdl.one/l/file123"
  python sizecheck_browser.py --file links.txt

REQUIREMENTS (Install in Termux):
  pkg install chromium chromium-chromedriver python
  pip install selenium

HOW IT WORKS:
  1. Opens the URL in a Chrome browser
  2. Detects if Cloudflare challenge is present
  3. Automatically attempts to solve the challenge
  4. Extracts file size from the final page
  5. Reports size in human-readable format

NOTES:
  • Browser window will open - let it complete
  • Works with links that show "Performing security verification"
  • Requires actual Chromium browser on device
  • Can handle multiple links from a text file
        """)
        sys.exit(1)
    
    bypasser = CloudflareAutoBypasser(headless=False)
    
    if sys.argv[1] == "--file" and len(sys.argv) > 2:
        bypasser.check_multiple_links(sys.argv[2])
    else:
        url = sys.argv[1]
        final_url, size, status = bypasser.get_size(url)
        
        print(f"\n{'='*70}")
        print("FINAL RESULT")
        print(f"{'='*70}")
        print(f"Status: {status.upper()}")
        print(f"Original: {url}")
        print(f"Final URL: {final_url}")
        
        if size is not None:
            human = bypasser.human_size(size)
            print(f"FILE SIZE: {human}")
            print(f"Bytes: {size:,}")
        else:
            print("FILE SIZE: Could not be determined")


if __name__ == "__main__":
    main()
