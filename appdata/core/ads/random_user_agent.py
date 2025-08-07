# appdata/core/ads/random_user_agent.py
import os, json, time, random, urllib.request

_CACHE = os.path.join(os.path.dirname(__file__), "chrome_versions_cache.json")
_CACHE_TTL = 604800
_ENDPOINT = "https://omahaproxy.appspot.com/all.json"
_OS = [
    ("Windows NT 10.0; Win64; x64", False, "win"),
    ("Macintosh; Intel Mac OS X 10_15_7", False, "mac"),
    ("X11; Linux x86_64", False, "linux"),
    ("Linux; Android 13", True, "android"),
    ("iPhone; CPU iPhone OS 16_4 like Mac OS X", True, "ios"),
]

def _load():
    try:
        if time.time() - os.path.getmtime(_CACHE) < _CACHE_TTL:
            with open(_CACHE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    try:
        data = json.loads(urllib.request.urlopen(_ENDPOINT, timeout=5).read().decode())
        res = {}
        for e in data:
            if e["os"] not in ("win", "mac", "linux", "android", "ios"):
                continue
            s = next((c for c in e["versions"] if c["channel"] == "stable"), None)
            if s:
                res.setdefault(e["os"], []).append(s["current_version"])
        for k, v in res.items():
            v.sort(key=lambda x: [int(a) for a in x.split(".")], reverse=True)
            res[k] = v[:10]
        with open(_CACHE, "w", encoding="utf-8") as f:
            json.dump(res, f)
        return res
    except Exception:
        return {}

_VERS = _load()

def _pick(ver_list):
    w = list(reversed(range(1, len(ver_list) + 1)))
    return random.choices(ver_list, weights=w, k=1)[0]

def generate_random_user_agent():
    os_tok, mob, plat = random.choice(_OS)
    ver = _pick(_VERS.get(plat, ["126.0.0.0"]))
    mob_tag = "Mobile " if mob else ""
    return f"Mozilla/5.0 ({os_tok}) AppleWebKit/537.36 (KHTML, like Gecko) {mob_tag}Chrome/{ver} Safari/537.36"
