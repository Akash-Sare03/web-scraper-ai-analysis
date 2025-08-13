from playwright.sync_api import sync_playwright, TimeoutError
import os

def get_rendered_html(url):
    try:
        with sync_playwright() as p:
            # Configure the exact browser path we know exists from logs
            browser_path = "/opt/render/.cache/ms-playwright/chromium_headless_shell-1181/chrome-linux/headless_shell"
            
            # Fallback paths if the above doesn't work
            if not os.path.exists(browser_path):
                browser_path = "/opt/render/.cache/ms-playwright/chromium-1084/chrome-linux/chrome"
            
            launch_options = {
                'headless': True,
                'executable_path': browser_path if os.path.exists(browser_path) else None,
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--single-process',
                    '--disable-gpu'
                ]
            }
            
            browser = p.chromium.launch(**launch_options)
            

            # Create a context with custom User-Agent and HTTPS ignore
            context = browser.new_context(
                ignore_https_errors=True,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/115.0.0.0 Safari/537.36"
                )
            )

            page = context.new_page()
            page.set_default_navigation_timeout(40000)

            try:
                # Load page and wait for content
                page.goto(url, timeout=40000, wait_until='domcontentloaded')
                page.wait_for_selector('body', timeout=10000)
                page.wait_for_timeout(5000)  # extra wait for JS-loaded content

                html = page.content()

            except TimeoutError as te:
                print(f"[Timeout] {url} — {te}")
                html = None
            except Exception as e:
                print(f"[Navigation Error] {url} — {e}")
                html = None

            browser.close()
            return html

    except Exception as e:
        print(f"[Playwright Error] {e}")
        return None