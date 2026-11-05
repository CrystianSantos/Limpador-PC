"""
Inicializador Desktop Multiplataforma (App Launcher).
Inicia o servidor local de backend e abre a interface moderna como uma janela
nativa de aplicativo desktop no Windows, macOS ou Linux.
"""

import os
import sys
import time
import subprocess
import webbrowser
import threading

# Garante path de importação
_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

import web_server
from platform_utils import is_windows, is_macos, is_linux


def find_app_browser():
    """
    Localiza executáveis de navegadores baseados em Chromium para abrir em modo
    janela de aplicativo nativa (--app=http://...), sem abas ou barra de endereços.
    """
    if is_windows():
        candidates = [
            # Microsoft Edge (nativo em todo Windows 10/11)
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            # Google Chrome
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            # Brave
            os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path

    elif is_macos():
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path

    elif is_linux():
        for cmd in ["google-chrome", "chromium-browser", "chromium", "brave-browser"]:
            path = shutil_which(cmd)
            if path:
                return path

    return None


def shutil_which(cmd):
    import shutil
    return shutil.which(cmd)


def open_desktop_window(url):
    """Abre a URL em modo de janela de aplicativo nativa ou no navegador padrão."""
    browser_bin = find_app_browser()
    if browser_bin:
        try:
            # Modo janela nativa (--app) com dimensões ideais
            cmd = [browser_bin, f"--app={url}", "--window-size=1150,780"]
            subprocess.Popen(cmd)
            return
        except Exception:
            pass

    # Fallback automático
    webbrowser.open(url)


def launch():
    print("=======================================================")
    print("      Limpador-PC Pro | Otimizador Multiplataforma")
    print("=======================================================")
    
    httpd, port = web_server.start_server(5000)
    app_url = f"http://127.0.0.1:{port}"

    # Inicia o servidor em uma thread de suporte
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    time.sleep(0.4)
    print(f"[*] Abrindo interface desktop em: {app_url}")
    open_desktop_window(app_url)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando Limpador-PC...")
        httpd.shutdown()


if __name__ == "__main__":
    launch()
