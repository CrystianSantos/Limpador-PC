"""
Testes unitários e de integração para o Limpador e Otimizador de PC.
Cobre: format_size, TempScanner, DuplicateScanner, Cleaner.
"""

import os
import sys
import tempfile
import unittest
import shutil

# Adiciona o diretório do projeto ao sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scanner import TempScanner, DuplicateScanner, RecycleBinScanner, format_size
from cleaner import Cleaner


class TestFormatSize(unittest.TestCase):
    """Testes para a função format_size com valores normais e edge cases."""

    def test_bytes(self):
        self.assertEqual(format_size(0), "0 B")
        self.assertEqual(format_size(500), "500 B")
        self.assertEqual(format_size(1023), "1023 B")

    def test_kilobytes(self):
        self.assertEqual(format_size(1024), "1.0 KB")
        self.assertEqual(format_size(2048), "2.0 KB")

    def test_megabytes(self):
        self.assertEqual(format_size(5 * 1024 * 1024), "5.00 MB")

    def test_gigabytes(self):
        self.assertEqual(format_size(2 * 1024 * 1024 * 1024), "2.00 GB")

    def test_none_input(self):
        self.assertEqual(format_size(None), "0 B")

    def test_negative_input(self):
        self.assertEqual(format_size(-100), "0 B")

    def test_string_input(self):
        self.assertEqual(format_size("abc"), "0 B")

    def test_float_input(self):
        result = format_size(1500.7)
        self.assertIn("KB", result)


class TestDuplicateScanner(unittest.TestCase):
    """Testes para detecção e limpeza de arquivos duplicados."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_limpador_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_finds_exact_duplicates(self):
        content_a = b"Conteudo identico para duplicatas." * 100
        content_b = b"Conteudo totalmente diferente." * 100

        dir_sub1 = os.path.join(self.test_dir, "pasta1")
        dir_sub2 = os.path.join(self.test_dir, "pasta2")
        os.makedirs(dir_sub1)
        os.makedirs(dir_sub2)

        file_orig = os.path.join(dir_sub1, "original.txt")
        file_copy1 = os.path.join(dir_sub2, "copia1.txt")
        file_copy2 = os.path.join(dir_sub2, "copia2.txt")
        file_unique = os.path.join(dir_sub1, "unico.txt")

        with open(file_orig, "wb") as f:
            f.write(content_a)
        with open(file_copy1, "wb") as f:
            f.write(content_a)
        with open(file_copy2, "wb") as f:
            f.write(content_a)
        with open(file_unique, "wb") as f:
            f.write(content_b)

        res = DuplicateScanner.scan([self.test_dir], min_size=10)

        self.assertEqual(res["total_groups"], 1)
        self.assertEqual(res["total_duplicate_copies"], 2)
        self.assertGreater(res["total_scanned"], 0)

        group = res["groups"][0]
        self.assertEqual(len(group["copies"]), 2)
        self.assertTrue(
            group["original"]["path"] in [file_orig, file_copy1, file_copy2]
        )

    def test_no_false_positives_same_size_different_content(self):
        """Arquivos com mesmo tamanho mas conteúdo diferente NÃO são duplicados."""
        dir1 = os.path.join(self.test_dir, "d1")
        dir2 = os.path.join(self.test_dir, "d2")
        os.makedirs(dir1)
        os.makedirs(dir2)

        # Cria dois arquivos com MESMO tamanho mas conteúdo diferente
        content_a = b"A" * 5000
        content_b = b"B" * 5000

        with open(os.path.join(dir1, "file_a.bin"), "wb") as f:
            f.write(content_a)
        with open(os.path.join(dir2, "file_b.bin"), "wb") as f:
            f.write(content_b)

        res = DuplicateScanner.scan([self.test_dir], min_size=10)
        self.assertEqual(res["total_groups"], 0)
        self.assertEqual(res["total_duplicate_copies"], 0)

    def test_empty_directory_list(self):
        res = DuplicateScanner.scan([], min_size=10)
        self.assertEqual(res["total_groups"], 0)
        self.assertEqual(res["total_duplicate_copies"], 0)

    def test_nonexistent_directory(self):
        res = DuplicateScanner.scan(["/caminho/que/nao/existe"], min_size=10)
        self.assertEqual(res["total_groups"], 0)

    def test_cleaner_deletes_only_copies(self):
        content_a = b"Conteudo duplicado." * 100

        dir_sub1 = os.path.join(self.test_dir, "pasta1")
        dir_sub2 = os.path.join(self.test_dir, "pasta2")
        os.makedirs(dir_sub1)
        os.makedirs(dir_sub2)

        file_orig = os.path.join(dir_sub1, "original.txt")
        file_copy1 = os.path.join(dir_sub2, "copia1.txt")
        file_copy2 = os.path.join(dir_sub2, "copia2.txt")

        with open(file_orig, "wb") as f:
            f.write(content_a)
        with open(file_copy1, "wb") as f:
            f.write(content_a)
        with open(file_copy2, "wb") as f:
            f.write(content_a)

        res = DuplicateScanner.scan([self.test_dir], min_size=10)
        group = res["groups"][0]

        copy_paths = [c["path"] for c in group["copies"]]
        clean_res = Cleaner.delete_duplicate_copies(copy_paths)

        self.assertEqual(clean_res["deleted_count"], 2)
        # O original NÃO pode ter sido excluído
        self.assertTrue(os.path.exists(group["original"]["path"]))
        # As cópias foram excluídas
        for cp in copy_paths:
            self.assertFalse(os.path.exists(cp))


class TestTempCleaner(unittest.TestCase):
    """Testes para limpeza de temporários."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_temp_clean_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_deletes_temp_files(self):
        temp_file1 = os.path.join(self.test_dir, "temp1.tmp")
        temp_file2 = os.path.join(self.test_dir, "temp2.tmp")

        with open(temp_file1, "wb") as f:
            f.write(b"Dados temporarios 1")
        with open(temp_file2, "wb") as f:
            f.write(b"Dados temporarios 2")

        items = [
            {"path": temp_file1, "size": 19, "is_dir": False},
            {"path": temp_file2, "size": 19, "is_dir": False},
        ]

        res = Cleaner.clean_temp_files(items)
        self.assertEqual(res["deleted_count"], 2)
        self.assertEqual(res["freed_bytes"], 38)
        self.assertFalse(os.path.exists(temp_file1))
        self.assertFalse(os.path.exists(temp_file2))

    def test_skips_nonexistent_files(self):
        items = [
            {"path": os.path.join(self.test_dir, "fantasma.tmp"), "size": 100, "is_dir": False},
        ]
        res = Cleaner.clean_temp_files(items)
        self.assertEqual(res["deleted_count"], 0)
        self.assertEqual(res["skipped_count"], 1)

    def test_removes_empty_dirs_after_files(self):
        sub_dir = os.path.join(self.test_dir, "subpasta")
        os.makedirs(sub_dir)
        temp_file = os.path.join(sub_dir, "arquivo.tmp")
        with open(temp_file, "wb") as f:
            f.write(b"dados")

        items = [
            {"path": temp_file, "size": 5, "is_dir": False},
            {"path": sub_dir, "size": 0, "is_dir": True},
        ]
        res = Cleaner.clean_temp_files(items)
        self.assertEqual(res["deleted_count"], 1)
        # A pasta deve ter sido removida (estava vazia após apagar o arquivo)
        self.assertFalse(os.path.exists(sub_dir))


class TestRecycleBinScanner(unittest.TestCase):
    """Testes básicos para o scanner da lixeira."""

    def test_scan_returns_valid_structure(self):
        res = RecycleBinScanner.scan()
        self.assertIn("items", res)
        self.assertIn("total_items", res)
        self.assertIn("total_size", res)
        self.assertIn("total_size_formatted", res)
        self.assertIsInstance(res["items"], list)
        self.assertIsInstance(res["total_items"], int)
        self.assertGreaterEqual(res["total_items"], 0)
        self.assertGreaterEqual(res["total_size"], 0)


class TestCleanerSafeRemove(unittest.TestCase):
    """Testes para o método _safe_remove."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_safe_rm_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_removes_normal_file(self):
        f = os.path.join(self.test_dir, "normal.txt")
        with open(f, "w") as fh:
            fh.write("test")
        self.assertTrue(Cleaner._safe_remove(f))
        self.assertFalse(os.path.exists(f))

    def test_returns_false_for_nonexistent(self):
        self.assertFalse(Cleaner._safe_remove("/arquivo/que/nao/existe.txt"))

    def test_returns_false_for_directory(self):
        d = os.path.join(self.test_dir, "pasta")
        os.makedirs(d)
        self.assertFalse(Cleaner._safe_remove(d))


if __name__ == "__main__":
    unittest.main()
