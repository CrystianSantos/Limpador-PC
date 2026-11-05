"""
Servidor Web e API REST Local para o Limpador-PC.
Fornece os endpoints de backend consumidos pela interface moderna Web/Desktop.
100% nativo em Python (sem necessidade de pacotes externos como Flask ou Django).
"""

import os
import sys
import json
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs

# Garante importação dos módulos locais e suporte a executável PyInstaller
if getattr(sys, 'frozen', False):
    _dir = sys._MEIPASS
    _app_dir = os.path.dirname(sys.executable)
else:
    _dir = os.path.dirname(os.path.abspath(__file__))
    _app_dir = _dir

if _dir not in sys.path:
    sys.path.insert(0, _dir)

from scanner import TempScanner, RecycleBinScanner, DuplicateScanner, format_size
from cleaner import Cleaner
from platform_utils import get_os_type, get_os_display_name
import updater

# Estado compartilhado da aplicação
APP_STATE = {
    "is_scanning": False,
    "is_cleaning": False,
    "status_message": "Pronto para iniciar.",
    "temp_data": None,
    "recycle_data": None,
    "duplicate_data": None,
    "logs": []
}

def add_log(msg):
    import datetime
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    APP_STATE["logs"].append(f"[{ts}] {msg}")
    if len(APP_STATE["logs"]) > 300:
        APP_STATE["logs"] = APP_STATE["logs"][-300:]


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class AppRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve arquivos estáticos da pasta web/
        web_dir = os.path.join(_dir, "web")
        super().__init__(*args, directory=web_dir, **kwargs)

    def end_headers(self):
        # Desativa cache para garantir atualizações dinâmicas
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        url_parts = urlparse(self.path)
        path = url_parts.path

        if path.startswith("/api/"):
            self.handle_api_get(path, parse_qs(url_parts.query))
            return

        # Rota raiz serve index.html
        if path == "/":
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self):
        url_parts = urlparse(self.path)
        path = url_parts.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if path.startswith("/api/"):
            self.handle_api_post(path, data)
            return

        self.send_error(404, "Not Found")

    def send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def handle_api_get(self, path, query):
        if path == "/api/status":
            info = updater.get_version_info()
            total_recoverable = 0
            if APP_STATE["temp_data"]:
                total_recoverable += APP_STATE["temp_data"].get("total_size", 0)
            if APP_STATE["recycle_data"]:
                total_recoverable += APP_STATE["recycle_data"].get("total_size", 0)
            if APP_STATE["duplicate_data"]:
                total_recoverable += APP_STATE["duplicate_data"].get("total_wasted_bytes", 0)

            self.send_json({
                "os_type": get_os_type(),
                "os_name": get_os_display_name(),
                "version_info": info,
                "is_scanning": APP_STATE["is_scanning"],
                "is_cleaning": APP_STATE["is_cleaning"],
                "status_message": APP_STATE["status_message"],
                "has_temp": APP_STATE["temp_data"] is not None,
                "has_recycle": APP_STATE["recycle_data"] is not None,
                "has_duplicates": APP_STATE["duplicate_data"] is not None,
                "total_recoverable": total_recoverable,
                "total_recoverable_formatted": format_size(total_recoverable),
                "temp_summary": {
                    "count": APP_STATE["temp_data"]["total_files"] if APP_STATE["temp_data"] else 0,
                    "size": APP_STATE["temp_data"]["total_size_formatted"] if APP_STATE["temp_data"] else "0 B",
                    "bytes": APP_STATE["temp_data"]["total_size"] if APP_STATE["temp_data"] else 0
                },
                "recycle_summary": {
                    "count": APP_STATE["recycle_data"]["total_items"] if APP_STATE["recycle_data"] else 0,
                    "size": APP_STATE["recycle_data"]["total_size_formatted"] if APP_STATE["recycle_data"] else "0 B",
                    "bytes": APP_STATE["recycle_data"]["total_size"] if APP_STATE["recycle_data"] else 0
                },
                "duplicate_summary": {
                    "groups": APP_STATE["duplicate_data"]["total_groups"] if APP_STATE["duplicate_data"] else 0,
                    "copies": APP_STATE["duplicate_data"]["total_duplicate_copies"] if APP_STATE["duplicate_data"] else 0,
                    "wasted": APP_STATE["duplicate_data"]["total_wasted_formatted"] if APP_STATE["duplicate_data"] else "0 B",
                    "bytes": APP_STATE["duplicate_data"]["total_wasted_bytes"] if APP_STATE["duplicate_data"] else 0
                },
                "logs": APP_STATE["logs"][-50:]
            })
            return

        elif path == "/api/details/temp":
            if APP_STATE["temp_data"]:
                # Retorna os itens (limitando a 1500 arquivos para carregamento veloz)
                items = [it for it in APP_STATE["temp_data"]["items"] if not it.get("is_dir")][:1500]
                self.send_json({
                    "success": True,
                    "total_files": APP_STATE["temp_data"]["total_files"],
                    "total_size_formatted": APP_STATE["temp_data"]["total_size_formatted"],
                    "items": items
                })
            else:
                self.send_json({"success": False, "items": []})
            return

        elif path == "/api/details/recycle":
            if APP_STATE["recycle_data"]:
                self.send_json({
                    "success": True,
                    "total_items": APP_STATE["recycle_data"]["total_items"],
                    "total_size_formatted": APP_STATE["recycle_data"]["total_size_formatted"],
                    "items": APP_STATE["recycle_data"]["items"]
                })
            else:
                self.send_json({"success": False, "items": []})
            return

        elif path == "/api/details/duplicates":
            if APP_STATE["duplicate_data"]:
                self.send_json({
                    "success": True,
                    "total_groups": APP_STATE["duplicate_data"]["total_groups"],
                    "total_copies": APP_STATE["duplicate_data"]["total_duplicate_copies"],
                    "total_wasted_formatted": APP_STATE["duplicate_data"]["total_wasted_formatted"],
                    "groups": APP_STATE["duplicate_data"]["groups"]
                })
            else:
                self.send_json({"success": False, "groups": []})
            return

        elif path == "/api/scan/all":
            self.trigger_background_scan("all")
            self.send_json({"success": True, "message": "Varredura completa iniciada."})
            return

        elif path == "/api/scan/recycle":
            self.trigger_background_scan("recycle")
            self.send_json({"success": True, "message": "Varredura da lixeira iniciada."})
            return

        elif path == "/api/scan/temp":
            self.trigger_background_scan("temp")
            self.send_json({"success": True, "message": "Varredura de temporários iniciada."})
            return

        elif path == "/api/scan/duplicates":
            self.trigger_background_scan("duplicates")
            self.send_json({"success": True, "message": "Varredura de duplicados iniciada."})
            return

        elif path == "/api/update/check":
            repo = query.get("repo", [None])[0]
            res = updater.check_for_updates(repo)
            self.send_json(res)
            return

        self.send_error(404, "Endpoint não encontrado")

    def handle_api_post(self, path, data):
        if path == "/api/clean":
            auth_temp = data.get("auth_temp", False)
            auth_recycle = data.get("auth_recycle", False)
            auth_dup = data.get("auth_duplicates", False)
            selected_copies = data.get("selected_copies", [])

            self.trigger_background_cleaning(auth_temp, auth_recycle, auth_dup, selected_copies)
            self.send_json({"success": True, "message": "Processo de limpeza iniciado."})
            return

        elif path == "/api/update/apply":
            repo = data.get("repo")
            self.trigger_background_update(repo)
            self.send_json({"success": True, "message": "Atualização iniciada em segundo plano."})
            return

        elif path == "/api/settings":
            repo = data.get("github_repo")
            if repo:
                info = updater.get_version_info()
                info["github_repo"] = repo.strip()
                updater.save_version_info(info)
                self.send_json({"success": True, "message": "Configurações salvas."})
            else:
                self.send_json({"success": False, "error": "Repositório inválido."})
            return

        self.send_error(404, "Endpoint não encontrado")

    def trigger_background_scan(self, scan_type):
        if APP_STATE["is_scanning"] or APP_STATE["is_cleaning"]:
            return

        def worker():
            APP_STATE["is_scanning"] = True
            add_log(f"Iniciando varredura ({scan_type})...")

            def progress_cb(msg):
                APP_STATE["status_message"] = msg

            try:
                if scan_type in ("recycle", "all"):
                    APP_STATE["status_message"] = "Analisando Lixeira..."
                    r_res = RecycleBinScanner.scan(progress_cb)
                    APP_STATE["recycle_data"] = r_res
                    add_log(f"Lixeira: {r_res['total_items']} itens ({r_res['total_size_formatted']})")

                if scan_type in ("temp", "all"):
                    APP_STATE["status_message"] = "Analisando Arquivos Temporários..."
                    t_res = TempScanner.scan(progress_cb)
                    APP_STATE["temp_data"] = t_res
                    add_log(f"Temporários: {t_res['total_files']} arquivos ({t_res['total_size_formatted']})")

                if scan_type in ("duplicates", "all"):
                    APP_STATE["status_message"] = "Analisando Arquivos Duplicados..."
                    dirs = [p for _, p in DuplicateScanner.get_default_scan_directories()]
                    d_res = DuplicateScanner.scan(dirs, progress_callback=progress_cb)
                    APP_STATE["duplicate_data"] = d_res
                    add_log(f"Duplicados: {d_res['total_groups']} grupos, {d_res['total_duplicate_copies']} cópias ({d_res['total_wasted_formatted']})")

                APP_STATE["status_message"] = "Varredura concluída! Escolha o que deseja autorizar."
                add_log("Varredura finalizada com sucesso.")

            except Exception as e:
                APP_STATE["status_message"] = f"Erro na varredura: {str(e)}"
                add_log(f"Erro: {str(e)}")
            finally:
                APP_STATE["is_scanning"] = False

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def trigger_background_cleaning(self, auth_temp, auth_recycle, auth_dup, selected_copies):
        if APP_STATE["is_cleaning"] or APP_STATE["is_scanning"]:
            return

        def worker():
            APP_STATE["is_cleaning"] = True
            add_log("Iniciando execução da limpeza autorizada...")
            total_freed = 0

            def progress_cb(msg):
                APP_STATE["status_message"] = msg

            try:
                # 1. Temporários
                if auth_temp and APP_STATE["temp_data"]:
                    APP_STATE["status_message"] = "Limpando arquivos temporários..."
                    res_t = Cleaner.clean_temp_files(APP_STATE["temp_data"]["items"], progress_cb)
                    total_freed += res_t["freed_bytes"]
                    add_log(f"Temporários removidos: {res_t['deleted_count']} ({res_t['freed_formatted']} liberados)")

                # 2. Lixeira
                if auth_recycle and APP_STATE["recycle_data"]:
                    APP_STATE["status_message"] = "Esvaziando lixeira do sistema..."
                    res_r = Cleaner.empty_recycle_bin(progress_cb)
                    if res_r["success"]:
                        total_freed += APP_STATE["recycle_data"]["total_size"]
                        add_log(f"Lixeira esvaziada: {APP_STATE['recycle_data']['total_size_formatted']} liberados")
                    else:
                        add_log(f"Aviso ao esvaziar lixeira: {res_r['error']}")

                # 3. Duplicados
                if auth_dup and selected_copies:
                    APP_STATE["status_message"] = f"Excluindo {len(selected_copies)} cópias duplicadas..."
                    res_d = Cleaner.delete_duplicate_copies(selected_copies, progress_cb)
                    total_freed += res_d["freed_bytes"]
                    add_log(f"Cópias duplicadas removidas: {res_d['deleted_count']} ({res_d['freed_formatted']} liberados)")

                APP_STATE["status_message"] = f"Limpeza concluída! Total de {format_size(total_freed)} liberados no seu disco."
                add_log(f"Limpeza concluída: {format_size(total_freed)} liberados.")

                # Re-executa varredura rápida para atualizar
                dirs = [p for _, p in DuplicateScanner.get_default_scan_directories()]
                APP_STATE["recycle_data"] = RecycleBinScanner.scan()
                APP_STATE["temp_data"] = TempScanner.scan()
                APP_STATE["duplicate_data"] = DuplicateScanner.scan(dirs)

            except Exception as e:
                APP_STATE["status_message"] = f"Erro na limpeza: {str(e)}"
                add_log(f"Erro na limpeza: {str(e)}")
            finally:
                APP_STATE["is_cleaning"] = False

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def trigger_background_update(self, repo):
        def worker():
            add_log("Iniciando processo de auto-atualização do GitHub...")
            def progress_cb(msg):
                APP_STATE["status_message"] = msg
                add_log(msg)

            res = updater.apply_github_update(repo, progress_cb)
            if res.get("success"):
                APP_STATE["status_message"] = f"Atualização aplicada com sucesso! ({res.get('new_sha')})"
                add_log(res.get("message"))
            else:
                APP_STATE["status_message"] = f"Erro na atualização: {res.get('error')}"
                add_log(f"Falha na atualização: {res.get('error')}")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()


def start_server(port=5000):
    """Inicia o servidor HTTP local na porta especificada."""
    server_address = ("127.0.0.1", port)
    for p in range(port, port + 20):
        try:
            httpd = ThreadedHTTPServer(("127.0.0.1", p), AppRequestHandler)
            print(f"[OK] Servidor Web ativo em: http://127.0.0.1:{p}")
            return httpd, p
        except OSError:
            continue
    raise RuntimeError("Não foi possível encontrar uma porta livre para iniciar o servidor.")


if __name__ == "__main__":
    httpd, port = start_server(5000)
    print(f"Acesse: http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando servidor...")
        httpd.shutdown()
