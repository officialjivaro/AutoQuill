# appdata/core/ads/adsense.py
import json, random, secrets, hashlib
from PySide6.QtCore import QUrl, QTimer, QObject
from PySide6.QtGui import QDesktopServices
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineScript, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView
from appdata.core.ads.random_user_agent import generate_random_user_agent

_LOCALES = ["en-US", "en-GB", "de-DE", "fr-FR", "es-ES", "ru-RU", "ja-JP", "ko-KR", "pt-BR"]
_PLATFORMS = ["Win32", "MacIntel", "Linux x86_64"]


def _persona():
    ua = generate_random_user_agent()
    return dict(
        ua=ua,
        accept=random.choice(_LOCALES),
        platform=random.choice(_PLATFORMS),
        vp=(728, 90),
        dpr=1,
        plugins=["Chrome PDF Plugin", "Chrome PDF Viewer", "Native Client"],
        canvasSalt=secrets.token_hex(4),
    )


_P = _persona()


def _profile():
    tag = hashlib.sha256(_P["ua"].encode()).hexdigest()[:8]
    p = QWebEngineProfile(f"ads_profile_{tag}")
    p.setHttpUserAgent(_P["ua"])
    if hasattr(p, "setHttpAcceptLanguage"):
        p.setHttpAcceptLanguage(_P["accept"])
    p.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
    p.setPersistentStoragePath("")
    return p


_STEALTH_JS = (
    f"(()=>{{const d=z=>({{get:()=>z,configurable:true}});"
    f"Object.defineProperty(navigator,'webdriver',d(undefined));"
    f"Object.defineProperty(navigator,'platform',d('{_P['platform']}'));"
    f"Object.defineProperty(navigator,'language',d('{_P['accept']}'));"
    f"Object.defineProperty(navigator,'languages',d(['{_P['accept']}']));"
    f"Object.defineProperty(navigator,'plugins',d({json.dumps(_P['plugins'])}));"
    f"Object.defineProperty(screen,'width',d({_P['vp'][0]}));"
    f"Object.defineProperty(screen,'height',d({_P['vp'][1]}));"
    f"Object.defineProperty(window,'devicePixelRatio',d({_P['dpr']}));"
    f"const o={int(_P['canvasSalt'][:2],16)};"
    f"const t=HTMLCanvasElement.prototype.toDataURL;"
    f"HTMLCanvasElement.prototype.toDataURL=function(){{const c=this.getContext('2d');"
    f"if(c){{c.fillStyle='rgba(0,0,0,0.01)';c.fillRect(o,o,1,1);}}"
    f"return t.apply(this,arguments);}};"
    f"}})();"
)

_AD_HTML = (
    "<html><head><meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\">"
    "<script async src=\"https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4223077320283786\" crossorigin=\"anonymous\"></script>"
    "</head><body style=\"background:#323232;margin:0;text-align:center;\">"
    "<ins class=\"adsbygoogle\" style=\"display:inline-block;width:728px;height:90px\" data-ad-client=\"ca-pub-4223077320283786\" data-ad-slot=\"5482552078\"></ins>"
    "<script>(adsbygoogle=window.adsbygoogle||[]).push({});</script></body></html>"
)


class _AdPage(QWebEnginePage):
    def acceptNavigationRequest(self, u, t, m):
        if t == QWebEnginePage.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(u)
            return False
        return super().acceptNavigationRequest(u, t, m)

    def javaScriptConsoleMessage(self, lvl, msg, line, src):
        if "googleads" in src or "googlesyndication" in src:
            return
        super().javaScriptConsoleMessage(lvl, msg, line, src)


def _install_stealth(pg):
    s = QWebEngineScript()
    s.setName("stealth")
    s.setInjectionPoint(getattr(QWebEngineScript, "DocumentStart", QWebEngineScript.DocumentReady))
    s.setRunsOnSubFrames(True)
    s.setWorldId(QWebEngineScript.MainWorld)
    s.setSourceCode(_STEALTH_JS)
    pg.profile().scripts().insert(s)


def _simulate(view):
    pg = view.page()

    def step(i=0):
        if i > 2:
            return
        pg.runJavaScript("window.dispatchEvent(new MouseEvent('mousemove',{clientX:10,clientY:10}));")
        QTimer.singleShot(300 + i * 200, lambda: step(i + 1))

    step()


class _Once(QObject):
    def __init__(self, v):
        super().__init__(v)
        v.loadFinished.connect(self.cb)

    def cb(self, ok):
        if ok:
            _simulate(self.parent())
            self.parent().loadFinished.disconnect(self.cb)


def create_adsense_view():
    v = QWebEngineView()
    v.setFixedSize(728, 90)
    prof = _profile()
    prof.setParent(v)
    pg = _AdPage(prof, v)
    v.setPage(pg)
    _install_stealth(pg)
    _Once(v)
    return v


def load_adsense_content(v):
    v.setHtml(_AD_HTML, QUrl("https://jivaro.net/downloads/programs/info/jtype"))
