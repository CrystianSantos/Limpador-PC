"""
Script de Compilação do Executável Standalone com PyInstaller.
Empacota a aplicação inteira (código Python, módulos e interface Web)
em um único arquivo executável (.exe no Windows, binário no Mac/Linux).
"""

import os
import sys
import subprocess
import shutil

_dir = os.path.dirname(os.path.abspath(__file__))


def build():
    print("=======================================================")
    print("       Compilando Executável do Limpador-PC...")
    print("=======================================================")

    sep = ";" if sys.platform == "win32" else ":"
    web_data = f"{os.path.join(_dir, 'web')}{sep}web"
    version_data = f"{os.path.join(_dir, 'version.json')}{sep}."

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=Limpador-PC",
        "--onefile",
        "--clean",
        f"--add-data={web_data}",
        f"--add-data={version_data}",
        os.path.join(_dir, "main.py")
    ]

    print("Executando:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=_dir)

    if res.returncode == 0:
        exe_ext = ".exe" if sys.platform == "win32" else ""
        dist_exe = os.path.join(_dir, "dist", f"Limpador-PC{exe_ext}")
        print("\n" + "=" * 60)
        print(" [OK] EXECUTÁVEL CRIADO COM SUCESSO!")
        print(f" Caminho: {dist_exe}")
        print("=" * 60)
        return dist_exe
    else:
        print("\n[ERRO] Falha na compilação do executável.")
        return None


if __name__ == "__main__":
    build()
