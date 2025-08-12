import urllib.robotparser
from urllib.parse import urlparse

def is_allowed(url, user_agent='*'):
    try:
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(base_url)
        rp.read()

        return rp.can_fetch(user_agent, url)
    except Exception as e:
        print(f"Robots.txt check failed: {e}")
        return True  # fallback to allowed
