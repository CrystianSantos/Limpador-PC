"""
Módulo de Abstração Multiplataforma (Windows, macOS, Linux).
Detecta o sistema operacional e fornece caminhos de pastas temporárias,
pastas do usuário e operações na Lixeira/Trash para cada sistema.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def get_os_type():
    """Retorna 'windows', 'macos' ou 'linux'."""
    if sys.platform == "win32":
        return "windows"
    elif sys.platform == "darwin":
        return "macos"
    else:
        return "linux"


def is_windows():
    return sys.platform == "win32"


def is_macos():
    return sys.platform == "darwin"


def is_linux():
    return sys.platform.startswith("linux")


def get_os_display_name():
    """Retorna um nome amigável para exibição na interface."""
    os_type = get_os_type()
    if os_type == "windows":
        return "Microsoft Windows"
    elif os_type == "macos":
        return "Apple macOS"
    else:
        return "GNU/Linux"


# ─────────────────────────────────────────────────────────────────────
# Pastas Temporárias Multiplataforma
# ─────────────────────────────────────────────────────────────────────

def get_platform_temp_directories():
    """
    Retorna lista de tuplas (Label, Caminho) para pastas temporárias
    de acordo com o sistema operacional atual.
    """
    dirs = []
    os_type = get_os_type()

    if os_type == "windows":
        user_temp = os.environ.get("TEMP") or os.environ.get("TMP")
        if user_temp and os.path.isdir(user_temp):
            dirs.append(("Temp do Usuário (%TEMP%)", os.path.realpath(user_temp)))

        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            crash_dumps = os.path.join(local_app_data, "CrashDumps")
            if os.path.isdir(crash_dumps):
                dirs.append(("Relatórios de Falha (CrashDumps)", crash_dumps))

        win_temp = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Temp")
        if os.path.isdir(win_temp):
            dirs.append(("Temp do Sistema Windows", win_temp))

    elif os_type == "macos":
        darwin_user_temp = os.environ.get("TMPDIR")
        if darwin_user_temp and os.path.isdir(darwin_user_temp):
            dirs.append(("Cache Temporário do Usuário ($TMPDIR)", os.path.realpath(darwin_user_temp)))

        home = Path.home()
        user_caches = home / "Library" / "Caches"
        if user_caches.is_dir():
            dirs.append(("Caches de Aplicativos (~/Library/Caches)", str(user_caches)))

        for system_temp in ["/tmp", "/var/tmp"]:
            if os.path.isdir(system_temp):
                dirs.append((f"Temp do Sistema ({system_temp})", system_temp))

    else:  # Linux
        home = Path.home()
        user_cache = home / ".cache"
        if user_cache.is_dir():
            dirs.append(("Cache do Usuário (~/.cache)", str(user_cache)))

        for system_temp in ["/tmp", "/var/tmp"]:
            if os.path.isdir(system_temp):
                dirs.append((f"Temp do Sistema ({system_temp})", system_temp))

    return dirs


# ─────────────────────────────────────────────────────────────────────
# Lixeira / Trash Multiplataforma
# ─────────────────────────────────────────────────────────────────────

def get_platform_trash_items():
    """
    Obtém a lista de itens e o tamanho total na Lixeira do sistema operacional atual.
    Retorna: lista de dicts com name, path, size, type.
    """
    items = []
    os_type = get_os_type()

    if os_type == "windows":
        # Usa Shell COM via PowerShell no Windows
        ps_code = r"""
        $ErrorActionPreference = 'SilentlyContinue'
        $shell = New-Object -ComObject Shell.Application
        $bin = $shell.Namespace(0xa)
        $list = @()
        if ($bin -ne $null) {
            foreach ($item in $bin.Items()) {
                $itemSize = 0
                try { $itemSize = $item.Size } catch {}
                $list += [PSCustomObject]@{
                    Name = $item.Name
                    Path = $item.Path
                    Size = $itemSize
                    Type = $item.Type
                }
            }
        }
        if ($list.Count -eq 0) {
            Write-Output "[]"
        } elseif ($list.Count -eq 1) {
            Write-Output ("[" + ($list | ConvertTo-Json -Compress) + "]")
        } else {
            $list | ConvertTo-Json -Compress
        }
        """
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_code],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=15
            )
            raw = res.stdout.strip()
            if raw and raw != "[]":
                import json
                data = json.loads(raw)
                if isinstance(data, dict):
                    data = [data]
                for entry in data:
                    size = entry.get("Size") or 0
                    try:
                        size = max(0, int(size))
                    except (ValueError, TypeError):
                        size = 0
                    items.append({
                        "name": entry.get("Name") or "Item",
                        "path": entry.get("Path") or "",
                        "size": size,
                        "type": entry.get("Type") or "Arquivo"
                    })
        except Exception:
            pass

    elif os_type == "macos":
        # No macOS: ~/.Trash
        home = Path.home()
        trash_dir = home / ".Trash"
        if trash_dir.is_dir():
            try:
                for entry in trash_dir.iterdir():
                    try:
                        size = entry.stat().st_size if entry.is_file() else sum(
                            f.stat().st_size for f in entry.rglob("*") if f.is_file()
                        )
                        items.append({
                            "name": entry.name,
                            "path": str(entry),
                            "size": size,
                            "type": "Pasta" if entry.is_dir() else "Arquivo"
                        })
                    except (PermissionError, OSError):
                        pass
            except (PermissionError, OSError):
                pass

    else:  # Linux (FreeDesktop.org Trash Specification)
        home = Path.home()
        trash_files_dir = home / ".local" / "share" / "Trash" / "files"
        if trash_files_dir.is_dir():
            try:
                for entry in trash_files_dir.iterdir():
                    try:
                        size = entry.stat().st_size if entry.is_file() else sum(
                            f.stat().st_size for f in entry.rglob("*") if f.is_file()
                        )
                        items.append({
                            "name": entry.name,
                            "path": str(entry),
                            "size": size,
                            "type": "Pasta" if entry.is_dir() else "Arquivo"
                        })
                    except (PermissionError, OSError):
                        pass
            except (PermissionError, OSError):
                pass

    return items


def empty_platform_trash():
    """
    Esvazia a Lixeira no Windows, macOS ou Linux.
    Retorna tupla (sucesso: bool, mensagem_erro: str ou None).
    """
    os_type = get_os_type()

    if os_type == "windows":
        import ctypes
        try:
            res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
            if res <= 0:
                return True, None
        except Exception:
            pass

        try:
            ps_res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                capture_output=True,
                text=True,
                timeout=20
            )
            return ps_res.returncode == 0, None
        except Exception as e:
            return False, str(e)

    elif os_type == "macos":
        # Tenta via AppleScript (método oficial que emite o som e avisa o Finder)
        try:
            res = subprocess.run(
                ["osascript", "-e", 'tell application "Finder" to empty trash'],
                capture_output=True,
                timeout=15
            )
            if res.returncode == 0:
                return True, None
        except Exception:
            pass

        # Fallback: limpar ~/.Trash diretamente
        home = Path.home()
        trash_dir = home / ".Trash"
        if trash_dir.is_dir():
            try:
                for entry in trash_dir.iterdir():
                    if entry.is_dir():
                        shutil.rmtree(entry, ignore_errors=True)
                    else:
                        entry.unlink(missing_ok=True)
                return True, None
            except Exception as e:
                return False, str(e)
        return True, None

    else:  # Linux
        # Limpa ~/.local/share/Trash/{files,info}
        home = Path.home()
        trash_base = home / ".local" / "share" / "Trash"
        for sub in ["files", "info"]:
            target_dir = trash_base / sub
            if target_dir.is_dir():
                try:
                    for entry in target_dir.iterdir():
                        if entry.is_dir():
                            shutil.rmtree(entry, ignore_errors=True)
                        else:
                            entry.unlink(missing_ok=True)
                except Exception as e:
                    return False, str(e)
        return True, None


# ─────────────────────────────────────────────────────────────────────
# Pastas Pessoais e Exclusões Multiplataforma
# ─────────────────────────────────────────────────────────────────────

def get_platform_user_directories():
    """Retorna pastas comuns do usuário para varredura de duplicados."""
    home = Path.home()
    candidates = [
        ("Downloads", home / "Downloads"),
        ("Documentos", home / "Documents"),
        ("Área de Trabalho", home / "Desktop"),
        ("Imagens", home / "Pictures"),
        ("Vídeos", home / "Videos"),
        ("Música", home / "Music")
    ]
    valid = []
    for name, p in candidates:
        try:
            if p.is_dir():
                valid.append((name, str(p)))
        except (PermissionError, OSError):
            continue
    return valid


def get_platform_excluded_directories():
    """Retorna conjunto de nomes de pastas de sistema que devem ser ignoradas."""
    common = {
        ".git", "node_modules", "__pycache__", ".vscode", ".idea",
        "venv", "env", ".env", ".cache", ".npm", ".yarn"
    }
    os_type = get_os_type()

    if os_type == "windows":
        common.update({
            "appdata", "localappdata", "$recycle.bin", "system volume information",
            "windows", "program files", "program files (x86)"
        })
    elif os_type == "macos":
        common.update({
            "library", "system", "applications", ".trash", ".ds_store",
            ".spotlight-v100", ".fseventsd"
        })
    else:  # Linux
        common.update({
            "proc", "sys", "dev", "etc", "var", "usr", "boot", "run"
        })

    return common
