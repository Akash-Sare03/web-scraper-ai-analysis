from playwright.sync_api import sync_playwright, TimeoutError

def get_rendered_html(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Increase global timeout
            page.set_default_navigation_timeout(40000)

            try:
                # Go to the URL and wait for some element (like body or a container)
                page.goto(url, timeout=40000, wait_until='domcontentloaded')

                # Explicitly wait for a stable DOM element (CNN uses body/main/container)
                page.wait_for_selector('body', timeout=10000)

                # Optional: wait extra time for JS widgets/lazy loads
                page.wait_for_timeout(5000)

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
