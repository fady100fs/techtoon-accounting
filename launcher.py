# launcher.py - Launch Streamlit in a desktop window (no browser)
# Install: pip install pywebview
# Run: pythonw launcher.py  OR  Techtoon.bat
import atexit
import ctypes
import os
import socket
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

import webview

ROOT = Path(__file__).resolve().parent
TITLE = "Techtoon Accounting"
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

# ═══════════════════════════════════════════════════
#  Single Instance Lock (منع فتح أكثر من نسخة)
# ═══════════════════════════════════════════════════
_mutex_handle = None


def _ensure_single_instance():
    """Return True if first instance; False if another is running."""
    global _mutex_handle
    if os.name != "nt":
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    mutex_name = "Local\\TechtoonAccounting_Mutex_v1"
    _mutex_handle = kernel32.CreateMutexW(None, False, mutex_name)
    last_err = ctypes.get_last_error()
    if last_err == 183:  # ERROR_ALREADY_EXISTS
        return False
    return True


def _focus_existing_window():
    """Find and bring existing Techtoon window to front."""
    if os.name != "nt":
        return
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)

        # محاولة إيجاد النافذة بالعنوان الحرفي
        hwnd = user32.FindWindowW(None, TITLE)

        # إن فشل، ابحث عن أي نافذة تحتوي "Techtoon"
        if not hwnd:
            results = []
            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

            def enum_proc(h, _):
                length = user32.GetWindowTextLengthW(h)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(h, buf, length + 1)
                    if "Techtoon" in buf.value:
                        results.append(h)
                return True

            user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
            if results:
                hwnd = results[0]

        if hwnd:
            user32.ShowWindow(hwnd, 9)       # SW_RESTORE
            user32.SetForegroundWindow(hwnd)  # اجعلها في المقدمة
    except Exception:
        pass


# ═══════════════════════════════════════════════════
#  Port + Streamlit
# ═══════════════════════════════════════════════════
def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _port_open(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


PORT = 8501
URL = f"http://localhost:{PORT}"

LOADING_HTML = (
    '<html dir="rtl"><body style="background:#0e1117;color:#fff;'
    'font-family:Segoe UI,Tahoma;display:flex;align-items:center;'
    'justify-content:center;height:100vh;margin:0;flex-direction:column">'
    '<h1>&#x1F4BC; Techtoon Accounting</h1>'
    '<p style="font-size:18px">&#x062C;&#x0627;&#x0631;&#x064A; &#x0627;&#x0644;&#x062A;&#x0634;&#x063A;&#x064A;&#x0644;...</p>'
    '</body></html>'
)

ERROR_HTML = (
    '<html dir="rtl"><body style="background:#0e1117;color:#fff;'
    'font-family:Segoe UI,Tahoma;padding:40px;text-align:center">'
    '<h1 style="color:#ef4444">&#x26A0;&#xFE0F; &#x062A;&#x0639;&#x0630;&#x0651;&#x0631; &#x062A;&#x0634;&#x063A;&#x064A;&#x0644; &#x0627;&#x0644;&#x062E;&#x0627;&#x062F;&#x0645;</h1>'
    '<p style="font-size:16px">&#x064A;&#x0631;&#x062C;&#x0649; &#x0627;&#x0644;&#x062A;&#x062D;&#x0642;&#x0642; &#x0645;&#x0646;:</p>'
    '<div style="display:inline-block;text-align:right;background:#1e293b;'
    'padding:20px 30px;border-radius:12px;margin:20px auto;line-height:2">'
    '&#x2022; .env / DATABASE_URL<br>'
    '&#x2022; &#x0627;&#x0644;&#x0627;&#x062A;&#x0635;&#x0627;&#x0644; &#x0628;&#x0627;&#x0644;&#x0625;&#x0646;&#x062A;&#x0631;&#x0646;&#x062A;<br>'
    '&#x2022; Python + packages<br>'
    '&#x2022; streamlit.log'
    '</div>'
    '<p style="color:#94a3b8;margin-top:30px">&#x0623;&#x063A;&#x0644;&#x0642; &#x0627;&#x0644;&#x0646;&#x0627;&#x0641;&#x0630;&#x0629; &#x0648;&#x062D;&#x0627;&#x0648;&#x0644; &#x0645;&#x0631;&#x0629; &#x0623;&#x062E;&#x0631;&#x0649;.</p>'
    '</body></html>'
)

server = None


def start_server():
    log = open(ROOT / "streamlit.log", "ab")
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    return subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
            "--server.port", str(PORT),
            "--server.address", "127.0.0.1",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ],
        cwd=ROOT, env=env,
        stdin=subprocess.DEVNULL, stdout=log, stderr=log,
        creationflags=NO_WINDOW,
    )


def wait_ready(timeout=90):
    end = time.time() + timeout
    while time.time() < end:
        if _port_open(PORT):
            return True
        if server and server.poll() is not None:
            return False
        time.sleep(0.5)
    return False


def stop_server():
    if server and server.poll() is None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(server.pid)],
                creationflags=NO_WINDOW, capture_output=True,
            )
        else:
            server.terminate()


def boot(window):
    global server, PORT, URL
    if _port_open(PORT):
        PORT = _find_free_port()
        URL = f"http://localhost:{PORT}"
    server = start_server()
    if wait_ready():
        window.load_url(URL)
    else:
        window.load_html(ERROR_HTML)


def main():
    # ⭐ منع تعدد النسخ — قبل أي شيء
    if not _ensure_single_instance():
        _focus_existing_window()
        sys.exit(0)

    atexit.register(stop_server)
    try:
        webview.settings["ALLOW_DOWNLOADS"] = True
    except Exception:
        pass

    window = webview.create_window(
        TITLE, html=LOADING_HTML,
        width=1400, height=850, min_size=(1000, 650),
    )
    webview.start(
        boot, window,
        private_mode=False,
        storage_path=str(ROOT / ".webview_data"),
        debug=False,
    )
    stop_server()


if __name__ == "__main__":
    main()