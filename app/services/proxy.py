# Proxy fetcher using real API (free list from geonode.com)
import requests
import random

def get_next_proxy():
    try:
        url = "https://proxylist.geonode.com/api/proxy-list?limit=10&page=1&sort_by=lastChecked&sort_type=desc"
        response = requests.get(url, timeout=10)
        data = response.json()
        proxy_list = [
            f"http://{proxy['ip']}:{proxy['port']}"
            for proxy in data.get("data", [])
            if proxy.get("protocols") and "http" in proxy["protocols"]
        ]
        return random.choice(proxy_list) if proxy_list else None
    except Exception as e:
        print("Proxy fetch failed:", e)
        return None
