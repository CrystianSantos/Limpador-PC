"""
Módulo de Atualização Automática via GitHub (Updater).
Permite verificar se há commits mais recentes no branch 'main' do repositório
do usuário no GitHub e atualizar os arquivos da aplicação automaticamente.
"""

import os
import sys
import json
import urllib.request
import urllib.error
import zipfile
import shutil
import tempfile
from pathlib import Path


DEFAULT_REPO = "crystian/Limpador-PC"

if getattr(sys, "frozen", False):
    _base_dir = os.path.dirname(sys.executable)
else:
    _base_dir = os.path.dirname(os.path.abspath(__file__))

VERSION_FILE = os.path.join(_base_dir, "version.json")


def get_version_info():
    """Lê as informações de versão e configuração do repositório GitHub."""
    default_info = {
        "app_name": "Limpador-PC Multiplataforma",
        "version": "1.0.0",
        "github_repo": DEFAULT_REPO,
        "current_commit": "initial",
        "last_checked": None
    }
    if os.path.isfile(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_info.update(data)
        except Exception:
            pass
    return default_info


def save_version_info(info):
    """Salva as informações de versão e repositório configurado."""
    try:
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def check_for_updates(repo_override=None):
    """
    Consulta a API pública do GitHub para verificar o commit mais recente
    no branch 'main'.
    Retorna dicionário com status da verificação.
    """
    info = get_version_info()
    repo = repo_override or info.get("github_repo", DEFAULT_REPO)
    repo = repo.strip().strip("/")

    # Se o usuário digitou uma URL completa do GitHub, extrai owner/repo
    if "github.com/" in repo:
        repo = repo.split("github.com/")[-1].replace(".git", "").strip("/")

    api_url = f"https://api.github.com/repos/{repo}/commits/main"
    headers = {
        "User-Agent": "Limpador-PC-Updater",
        "Accept": "application/vnd.github.v3+json"
    }

    req = urllib.request.Request(api_url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status != 200:
                return {
                    "success": False,
                    "error": f"GitHub retornou status {response.status}",
                    "repo": repo
                }
            data = json.loads(response.read().decode("utf-8"))

        latest_sha = data.get("sha", "")
        commit_data = data.get("commit", {})
        message = commit_data.get("message", "Sem mensagem de commit").split("\n")[0]
        author = commit_data.get("author", {}).get("name", "Autor")
        date = commit_data.get("author", {}).get("date", "")

        current_sha = info.get("current_commit", "")
        # Há atualização se o SHA do commit mais recente for diferente do atual
        has_update = (latest_sha != current_sha) and bool(latest_sha)

        return {
            "success": True,
            "repo": repo,
            "has_update": has_update,
            "latest_sha": latest_sha[:7],
            "latest_sha_full": latest_sha,
            "current_sha": current_sha[:7] if len(current_sha) >= 7 else current_sha,
            "commit_message": message,
            "author": author,
            "date": date,
            "version": info.get("version", "1.0.0")
        }

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {
                "success": False,
                "error": f"Repositório '{repo}' ou branch 'main' não encontrado no GitHub (404).",
                "repo": repo
            }
        return {
            "success": False,
            "error": f"Erro de comunicação com o GitHub (HTTP {e.code}): {e.reason}",
            "repo": repo
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Falha na conexão: {str(e)}",
            "repo": repo
        }


def apply_github_update(repo_override=None, progress_callback=None):
    """
    Baixa o arquivo zip do branch 'main' do GitHub e atualiza os arquivos
    do aplicativo preservando configurações do usuário.
    """
    info = get_version_info()
    repo = repo_override or info.get("github_repo", DEFAULT_REPO)
    repo = repo.strip().strip("/")
    if "github.com/" in repo:
        repo = repo.split("github.com/")[-1].replace(".git", "").strip("/")

    if progress_callback:
        progress_callback("Verificando informações do repositório...")

    check_res = check_for_updates(repo)
    if not check_res.get("success"):
        return {
            "success": False,
            "error": check_res.get("error", "Não foi possível verificar o repositório.")
        }

    zip_url = f"https://github.com/{repo}/archive/refs/heads/main.zip"
    headers = {"User-Agent": "Limpador-PC-Updater"}

    app_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = tempfile.mkdtemp(prefix="limpador_update_")
    zip_path = os.path.join(temp_dir, "main.zip")

    try:
        if progress_callback:
            progress_callback(f"Baixando versão mais recente do branch 'main' ({check_res['latest_sha']})...")

        req = urllib.request.Request(zip_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp, open(zip_path, "wb") as out_file:
            shutil.copyfileobj(resp, out_file)

        if progress_callback:
            progress_callback("Extraindo arquivos da nova versão...")

        extract_dir = os.path.join(temp_dir, "extracted")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        # O GitHub empacota como {repo-name}-main/
        subfolders = [os.path.join(extract_dir, f) for f in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, f))]
        source_dir = subfolders[0] if subfolders else extract_dir

        if progress_callback:
            progress_callback("Instalando atualizações...")

        # Copia os arquivos novos substituindo os existentes
        # mas preserva arquivos locais como configurações ou logs
        ignore_files = {"version.json", ".git", ".idea", ".vscode"}

        updated_files = 0
        for root, dirs, files in os.walk(source_dir):
            rel_path = os.path.relpath(root, source_dir)
            dest_root = os.path.join(app_dir, rel_path) if rel_path != "." else app_dir

            os.makedirs(dest_root, exist_ok=True)

            for file_name in files:
                if file_name in ignore_files and os.path.exists(os.path.join(dest_root, file_name)):
                    continue

                src_file = os.path.join(root, file_name)
                dest_file = os.path.join(dest_root, file_name)

                shutil.copy2(src_file, dest_file)
                updated_files += 1

        # Atualiza o arquivo version.json com o novo SHA
        info["github_repo"] = repo
        info["current_commit"] = check_res.get("latest_sha_full", check_res.get("latest_sha", "main-updated"))
        info["last_updated_date"] = check_res.get("date")
        save_version_info(info)

        if progress_callback:
            progress_callback("Atualização concluída com sucesso!")

        return {
            "success": True,
            "updated_files": updated_files,
            "new_sha": check_res.get("latest_sha"),
            "message": f"Atualizado para o commit {check_res.get('latest_sha')} com sucesso! ({updated_files} arquivos atualizados)"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Erro durante a atualização: {str(e)}"
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
