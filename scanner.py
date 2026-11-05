"""
Módulo de Varredura Multiplataforma (Scanner)
Compatível com Windows, macOS e Linux.

Responsável por identificar:
1. Arquivos temporários e mortos (%TEMP%, caches, logs).
2. Itens armazenados na Lixeira / Trash do sistema operacional.
3. Arquivos duplicados com algoritmo de 3 fases (Tamanho -> Hash Parcial -> SHA-256).
"""

import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime

from platform_utils import (
    get_platform_temp_directories,
    get_platform_trash_items,
    get_platform_user_directories,
    get_platform_excluded_directories,
    get_os_display_name
)


def format_size(bytes_val):
    """Formata bytes em B, KB, MB, GB de forma legível e segura."""
    if bytes_val is None:
        return "0 B"
    try:
        bytes_val = int(bytes_val)
    except (ValueError, TypeError):
        return "0 B"
    if bytes_val < 0:
        bytes_val = 0
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    elif bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"


class TempScanner:
    """Varredura de arquivos temporários e mortos (Multiplataforma)."""

    @staticmethod
    def get_temp_directories():
        return get_platform_temp_directories()

    @staticmethod
    def scan(progress_callback=None):
        items = []
        total_size = 0
        file_count = 0
        dir_count = 0

        temp_dirs = TempScanner.get_temp_directories()

        for label, temp_dir_path in temp_dirs:
            if not os.path.isdir(temp_dir_path):
                continue

            try:
                for root, dirs, files in os.walk(temp_dir_path):
                    for name in files:
                        file_path = os.path.join(root, name)
                        file_count += 1
                        try:
                            stat = os.stat(file_path)
                            size = stat.st_size
                            mtime = datetime.fromtimestamp(stat.st_mtime)
                            total_size += size

                            items.append({
                                "category": label,
                                "path": file_path,
                                "filename": name,
                                "size": size,
                                "size_formatted": format_size(size),
                                "mtime": mtime.strftime("%d/%m/%Y %H:%M:%S"),
                                "is_dir": False
                            })
                        except (PermissionError, OSError, ValueError):
                            pass

                        if progress_callback and file_count % 50 == 0:
                            progress_callback(
                                f"Analisando temporários: {file_count} arquivos "
                                f"({format_size(total_size)})"
                            )

                    for name in dirs:
                        sub_dir_path = os.path.join(root, name)
                        dir_count += 1
                        items.append({
                            "category": label,
                            "path": sub_dir_path,
                            "filename": name,
                            "size": 0,
                            "size_formatted": "-",
                            "mtime": "-",
                            "is_dir": True
                        })
            except (PermissionError, OSError):
                continue

        explanation = (
            "Arquivos temporários e mortos são resíduos gerados pelo sistema e aplicativos "
            "para uso transitório. A grande maioria torna-se obsoleta após o encerramento "
            "dos programas e pode ser removida com segurança. Arquivos em uso ativo no momento "
            "são preservados automaticamente."
        )

        return {
            "title": f"Arquivos Temporários ({get_os_display_name()})",
            "items": items,
            "total_files": file_count,
            "total_dirs": dir_count,
            "total_size": total_size,
            "total_size_formatted": format_size(total_size),
            "explanation": explanation,
            "safe_to_delete": True,
            "recommendation": "Recomendado excluir para liberar espaço no disco."
        }


class RecycleBinScanner:
    """Varredura dos arquivos na Lixeira / Trash (Multiplataforma)."""

    @staticmethod
    def scan(progress_callback=None):
        if progress_callback:
            progress_callback(f"Consultando Lixeira ({get_os_display_name()})...")

        raw_items = get_platform_trash_items()
        items = []
        total_size = 0

        for it in raw_items:
            size = it.get("size", 0)
            total_size += size
            items.append({
                "name": it.get("name") or "Item",
                "path": it.get("path") or "",
                "size": size,
                "size_formatted": format_size(size),
                "type": it.get("type") or "Arquivo"
            })

        explanation = (
            "A Lixeira armazena arquivos e pastas excluídos anteriormente. "
            "Enquanto permanecerem na Lixeira, eles continuam ocupando espaço físico no disco. "
            "Esvaziar a lixeira libera esse espaço imediatamente."
        )

        return {
            "title": f"Lixeira do Sistema ({get_os_display_name()})",
            "items": items,
            "total_items": len(items),
            "total_size": total_size,
            "total_size_formatted": format_size(total_size),
            "explanation": explanation,
            "safe_to_delete": True,
            "recommendation": "Seguro esvaziar, caso você não queira recuperar nenhum arquivo listado."
        }


class DuplicateScanner:
    """Varredura de arquivos duplicados (Multiplataforma)."""

    @staticmethod
    def get_default_scan_directories():
        return get_platform_user_directories()

    @staticmethod
    def get_file_partial_hash(filepath, chunk_size=8192):
        try:
            with open(filepath, "rb") as f:
                data = f.read(chunk_size)
                if not data:
                    return None
                return hashlib.md5(data).hexdigest()
        except (PermissionError, OSError):
            return None

    @staticmethod
    def get_file_full_hash(filepath, chunk_size=65536):
        h = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()
        except (PermissionError, OSError):
            return None

    @staticmethod
    def scan(directories, min_size=1024, progress_callback=None):
        if not directories:
            return {
                "title": "Arquivos Duplicados",
                "groups": [],
                "total_groups": 0,
                "total_duplicate_copies": 0,
                "total_wasted_bytes": 0,
                "total_wasted_formatted": "0 B",
                "total_scanned": 0,
                "explanation": "",
                "safe_to_delete": True,
                "recommendation": ""
            }

        excluded_names = get_platform_excluded_directories()
        norm_dirs = sorted(set(os.path.realpath(d) for d in directories if os.path.isdir(d)))
        filtered_dirs = []
        for d in norm_dirs:
            if not any(d.startswith(existing + os.sep) for existing in filtered_dirs):
                filtered_dirs.append(d)

        size_map = {}
        total_scanned = 0
        seen_paths = set()

        # FASE 1: Agrupamento por tamanho
        for directory in filtered_dirs:
            try:
                for root, dirs, files in os.walk(directory):
                    dirs[:] = [d for d in dirs if d.lower() not in excluded_names]

                    for f in files:
                        file_path = os.path.join(root, f)
                        total_scanned += 1
                        try:
                            real_path = os.path.realpath(file_path)
                            if real_path in seen_paths:
                                continue
                            seen_paths.add(real_path)

                            stat = os.stat(file_path)
                            size = stat.st_size
                            if size >= min_size:
                                size_map.setdefault(size, []).append({
                                    "path": file_path,
                                    "name": f,
                                    "size": size,
                                    "mtime": stat.st_mtime
                                })
                        except (PermissionError, OSError):
                            pass

                        if progress_callback and total_scanned % 100 == 0:
                            progress_callback(
                                f"Indexando arquivos por tamanho: {total_scanned} analisados..."
                            )
            except (PermissionError, OSError):
                continue

        same_size_candidates = {sz: fl for sz, fl in size_map.items() if len(fl) > 1}

        # FASE 2: Hash parcial
        partial_map = {}
        partial_total = sum(len(fl) for fl in same_size_candidates.values())
        partial_count = 0

        for sz, file_list in same_size_candidates.items():
            for item in file_list:
                partial_count += 1
                if progress_callback and partial_count % 20 == 0:
                    progress_callback(
                        f"Comparando amostras de conteúdo: {partial_count}/{partial_total}..."
                    )

                p_hash = DuplicateScanner.get_file_partial_hash(item["path"])
                if p_hash:
                    key = (sz, p_hash)
                    partial_map.setdefault(key, []).append(item)

        same_partial_candidates = {k: fl for k, fl in partial_map.items() if len(fl) > 1}

        # FASE 3: SHA-256 completo
        final_groups = []
        wasted_bytes = 0
        total_duplicates_count = 0

        full_total = sum(len(fl) for fl in same_partial_candidates.values())
        full_count = 0

        for (sz, _), file_list in same_partial_candidates.items():
            full_map = {}
            for item in file_list:
                full_count += 1
                if progress_callback and full_count % 10 == 0:
                    progress_callback(
                        f"Confirmando integridade SHA-256: {full_count}/{full_total}..."
                    )

                f_hash = DuplicateScanner.get_file_full_hash(item["path"])
                if f_hash:
                    full_map.setdefault(f_hash, []).append(item)

            for f_hash, dup_files in full_map.items():
                if len(dup_files) > 1:
                    dup_files.sort(key=lambda x: x["mtime"])

                    original = dup_files[0]
                    copies = dup_files[1:]

                    group_info = {
                        "hash": f_hash,
                        "file_size": original["size"],
                        "file_size_formatted": format_size(original["size"]),
                        "original": {
                            "path": original["path"],
                            "name": original["name"],
                            "mtime": datetime.fromtimestamp(
                                original["mtime"]
                            ).strftime("%d/%m/%Y %H:%M:%S"),
                            "is_primary": True,
                            "suggested_action": "Manter (Original)"
                        },
                        "copies": [
                            {
                                "path": c["path"],
                                "name": c["name"],
                                "mtime": datetime.fromtimestamp(
                                    c["mtime"]
                                ).strftime("%d/%m/%Y %H:%M:%S"),
                                "is_primary": False,
                                "suggested_action": "Excluir cópia"
                            }
                            for c in copies
                        ]
                    }

                    wasted_bytes += original["size"] * len(copies)
                    total_duplicates_count += len(copies)
                    final_groups.append(group_info)

        explanation = (
            "Arquivos duplicados são arquivos idênticos bit a bit (confirmados por hash SHA-256) "
            "em pastas diferentes. O arquivo original mais antigo é automaticamente protegido "
            "para ser mantido, e apenas as cópias idênticas são sugeridas para remoção."
        )

        return {
            "title": "Arquivos Duplicados",
            "groups": final_groups,
            "total_groups": len(final_groups),
            "total_duplicate_copies": total_duplicates_count,
            "total_wasted_bytes": wasted_bytes,
            "total_wasted_formatted": format_size(wasted_bytes),
            "total_scanned": total_scanned,
            "explanation": explanation,
            "safe_to_delete": True,
            "recommendation": "Recomendado excluir as cópias duplicadas para recuperar espaço."
        }
