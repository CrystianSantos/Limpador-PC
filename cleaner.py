"""
Módulo de Limpeza e Exclusão Segura Multiplataforma (Cleaner)
Compatível com Windows, macOS e Linux.

Responsável por:
1. Limpeza de arquivos temporários com preservação de arquivos em uso.
2. Esvaziamento seguro da Lixeira do sistema (Windows, macOS Finder, Linux FreeDesktop Trash).
3. Exclusão das cópias duplicadas autorizadas pelo usuário.
"""

import os
import stat
from scanner import format_size
from platform_utils import empty_platform_trash


class Cleaner:
    """Execução segura de exclusões com tratamento de permissões e multiplataforma."""

    @staticmethod
    def _safe_remove(path):
        """Remove um arquivo com tratamento robusto de permissões (Windows, Mac, Linux)."""
        if not os.path.isfile(path):
            return False
        try:
            os.remove(path)
            return True
        except PermissionError:
            try:
                os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
                os.remove(path)
                return True
            except (PermissionError, OSError):
                return False
        except OSError:
            return False

    @staticmethod
    def clean_temp_files(temp_items, progress_callback=None):
        deleted_count = 0
        skipped_count = 0
        freed_bytes = 0
        errors = []

        files_to_clean = [item for item in temp_items if not item.get("is_dir")]
        dirs_to_clean = [item for item in temp_items if item.get("is_dir")]

        total_files = len(files_to_clean)
        for idx, item in enumerate(files_to_clean, 1):
            path = item.get("path", "")
            size = item.get("size", 0)

            if progress_callback and idx % 20 == 0:
                progress_callback(
                    f"Limpando temporários: {idx}/{total_files} "
                    f"({format_size(freed_bytes)} liberados)..."
                )

            if Cleaner._safe_remove(path):
                deleted_count += 1
                freed_bytes += size
            else:
                skipped_count += 1

        dirs_sorted = sorted(
            dirs_to_clean,
            key=lambda x: len(x.get("path", "")),
            reverse=True
        )
        for item in dirs_sorted:
            dir_path = item.get("path", "")
            if dir_path and os.path.isdir(dir_path):
                try:
                    os.rmdir(dir_path)
                except (PermissionError, OSError):
                    pass

        return {
            "deleted_count": deleted_count,
            "skipped_count": skipped_count,
            "freed_bytes": freed_bytes,
            "freed_formatted": format_size(freed_bytes),
            "errors": errors
        }

    @staticmethod
    def empty_recycle_bin(progress_callback=None):
        """Esvazia a Lixeira usando o método apropriado para o SO atual."""
        if progress_callback:
            progress_callback("Esvaziando a Lixeira do sistema...")

        success, error_msg = empty_platform_trash()
        return {
            "success": success,
            "error": error_msg
        }

    @staticmethod
    def delete_duplicate_copies(copy_paths, progress_callback=None):
        deleted_count = 0
        skipped_count = 0
        freed_bytes = 0
        errors = []

        total = len(copy_paths)
        for idx, path in enumerate(copy_paths, 1):
            if progress_callback and idx % 10 == 0:
                progress_callback(f"Excluindo cópias duplicadas: {idx}/{total}...")

            if not os.path.isfile(path):
                continue

            try:
                file_size = os.path.getsize(path)
            except (PermissionError, OSError):
                file_size = 0

            if Cleaner._safe_remove(path):
                deleted_count += 1
                freed_bytes += file_size
            else:
                skipped_count += 1
                errors.append(f"{path}: Arquivo em uso ou protegido.")

        return {
            "deleted_count": deleted_count,
            "skipped_count": skipped_count,
            "freed_bytes": freed_bytes,
            "freed_formatted": format_size(freed_bytes),
            "errors": errors
        }
