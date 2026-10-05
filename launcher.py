# launcher.py
# يشغّل Streamlit في الخلفية ويعرضه داخل نافذة مستقلة (بدون متصفح)
# التثبيت:  pip install pywebview
# التشغيل:  pythonw launcher.py   (أو دبل كليك على Techtoon.bat)
import atexit
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import webview

ROOT = Path(__file__).resolve().parent
PORT = 8501
URL = f"http://localhost:{PORT}"
TITLE = "Techtoon Accounting"
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

LOADING_HTML = """
<html dir="rtl"><body style="background:#0e1117;color:#fff;font-family:Segoe UI,Tahoma;
display:flex;align-items:center;justify-content:center;height:100vh;margin:0;flex-direction:column">
<h1>💼 Techtoon Accounting</h1><p>جاري تشغيل النظام...</p></body></html>
"""

server = None


def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_server():
    log = open(ROOT / "streamlit.log", "ab")
    # عند تحويل المخرجات إلى ملف يستخدم ويندوز ترميز cp1252 الذي لا يدعم العربية
    # والإيموجي، فتنهار أي print() تحتويها. نفرض UTF-8 على العملية الفرعية.
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    return subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
            "--server.port", str(PORT),
            "--server.address", "127.0.0.1",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=log,
        creationflags=NO_WINDOW,
    )


def wait_ready(timeout=90):
    end = time.time() + timeout
    while time.time() < end:
        if port_open(PORT):
            return True
        if server and server.poll() is not None:  # العملية انتهت بخطأ
            return False
        time.sleep(0.5)
    return False


def stop_server():
    if server and server.poll() is None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(server.pid)],
                creationflags=NO_WINDOW,
                capture_output=True,
            )
        else:
            server.terminate()


def boot(window):
    global server
    if not port_open(PORT):  # لا نشغّل نسخة ثانية إن كان الخادم يعمل
        server = start_server()
    if wait_ready():
        window.load_url(URL)
    else:
        window.load_html(
            "<h2 style='font-family:Tahoma;text-align:center;margin-top:20vh' dir='rtl'>"
            "❌ تعذّر تشغيل النظام. راجع الملف streamlit.log</h2>"
        )


def main():
    atexit.register(stop_server)

    try:
        webview.settings["ALLOW_DOWNLOADS"] = True  # لتنزيل ملفات Excel/PDF
    except Exception:
        pass

    window = webview.create_window(
        TITLE, html=LOADING_HTML, width=1400, height=850, min_size=(1000, 650)
    )
    # private_mode=False + storage_path: يحفظ الـ Cookie فيبقى تسجيل الدخول بعد الإغلاق
    webview.start(
        boot, window, private_mode=False, storage_path=str(ROOT / ".webview_data")
    )
    stop_server()


if __name__ == "__main__":
    main()