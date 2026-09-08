# Create this as a Django management command
# File: your_app/management/commands/setup_youtube_cookies.py

import os
import tempfile
import shutil
import sqlite3
import json
from django.core.management.base import BaseCommand
from django.conf import settings
import yt_dlp


class Command(BaseCommand):
    help = 'Setup YouTube cookies for yt-dlp to avoid bot detection'

    def add_arguments(self, parser):
        parser.add_argument(
            '--browser',
            type=str,
            default='chrome',
            help='Browser to extract cookies from (chrome, firefox, safari, edge)'
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Output path for cookies file'
        )
        parser.add_argument(
            '--manual',
            action='store_true',
            help='Use manual cookie extraction method'
        )

    def get_chrome_cookies_path(self):
        """Get Chrome cookies database path for different OS"""
        import platform
        system = platform.system()
        
        if system == "Windows":
            return os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Network\\Cookies")
        elif system == "Darwin":  # macOS
            return os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Cookies")
        else:  # Linux
            return os.path.expanduser("~/.config/google-chrome/Default/Cookies")

    def manual_chrome_cookie_extraction(self, output_path):
        """Manual cookie extraction when browser is closed"""
        try:
            cookies_db_path = self.get_chrome_cookies_path()
            
            if not os.path.exists(cookies_db_path):
                self.stdout.write(self.style.ERROR(f"Chrome cookies database not found at: {cookies_db_path}"))
                return False
            
            # Create a temporary copy of the cookies database
            temp_db = tempfile.mktemp(suffix='.db')
            shutil.copy2(cookies_db_path, temp_db)
            
            # Connect to the database
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # Query YouTube cookies
            cursor.execute("""
                SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly
                FROM cookies 
                WHERE host_key LIKE '%youtube.com%' OR host_key LIKE '%google.com%'
            """)
            
            cookies = cursor.fetchall()
            conn.close()
            
            # Convert to Netscape format for yt-dlp
            with open(output_path, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n")
                for cookie in cookies:
                    name, value, domain, path, expires, secure, httponly = cookie
                    # Convert Chrome timestamp to Unix timestamp
                    expires_unix = (expires - 11644473600000000) // 1000000 if expires else 0
                    f.write(f"{domain}\tTRUE\t{path}\t{'TRUE' if secure else 'FALSE'}\t{expires_unix}\t{name}\t{value}\n")
            
            # Cleanup
            os.remove(temp_db)
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Manual extraction failed: {str(e)}"))
            return False

    def try_browser_extraction(self, browser, output_path):
        """Try browser cookie extraction with yt-dlp using simpler method"""
        browsers_to_try = [browser]
        
        # Add fallback browsers
        if browser == 'chrome':
            browsers_to_try.extend(['chromium', 'firefox', 'safari'])
        elif browser == 'firefox':
            browsers_to_try.extend(['chrome', 'chromium', 'safari'])
        
        for browser_name in browsers_to_try:
            self.stdout.write(f'Trying to extract cookies from {browser_name}...')
            
            try:
                ydl_opts = {
                    'cookiesfrombrowser': (browser_name, None, None, None),
                    'quiet': True,
                    'no_warnings': True,
                    'skip_download': True,
                    'extract_flat': True,  # Avoid format issues
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Get cookies directly from browser
                    cookie_jar = ydl.cookiejar
                    
                    if cookie_jar:
                        # Save cookies to file
                        cookie_jar.save(output_path, ignore_discard=True, ignore_expires=True)
                        
                        # Verify cookies were saved and contain YouTube cookies
                        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                            with open(output_path, 'r') as f:
                                content = f.read()
                                if 'youtube.com' in content or 'google.com' in content:
                                    self.stdout.write(
                                        self.style.SUCCESS(f'Successfully extracted cookies from {browser_name}')
                                    )
                                    return True
                                else:
                                    self.stdout.write(f'No YouTube cookies found in {browser_name}')
                        else:
                            self.stdout.write(f'Cookie file is empty for {browser_name}')
                    else:
                        self.stdout.write(f'No cookies available in {browser_name}')
                    
            except Exception as e:
                self.stdout.write(f'Failed with {browser_name}: {str(e)}')
                continue
                
        return False

    def handle(self, *args, **options):
        browser = options['browser']
        output_path = options['output'] or os.path.join(settings.BASE_DIR, 'youtube_cookies.txt')
        use_manual = options['manual']
        
        success = False
        
        if use_manual and browser == 'chrome':
            self.stdout.write('Using manual Chrome cookie extraction...')
            self.stdout.write(self.style.WARNING('Please close Chrome completely before running this command!'))
            success = self.manual_chrome_cookie_extraction(output_path)
        
        if not success:
            self.stdout.write('Trying automatic browser cookie extraction...')
            success = self.try_browser_extraction(browser, output_path)
        
        if success and os.path.exists(output_path):
            self.stdout.write(
                self.style.SUCCESS(f'Cookies successfully saved to: {output_path}')
            )
            self.stdout.write(
                f'Add this to your settings.py:\n'
                f'YOUTUBE_COOKIES_FILE = "{output_path}"'
            )
        else:
            self.stdout.write(self.style.ERROR('All cookie extraction methods failed!'))
            self.stdout.write('\nAlternative solutions:')
            self.stdout.write('1. Install browser extension "Get cookies.txt LOCALLY"')
            self.stdout.write('2. Export YouTube cookies manually')
            self.stdout.write('3. Use a different browser (try --browser firefox)')
            self.stdout.write('4. Close Chrome completely and run with --manual flag')