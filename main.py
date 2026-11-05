"""
Ponto de entrada principal do Limpador-PC Pro Multiplataforma.

Opções de Execução:
    python main.py             -> Abre a nova interface visual moderna (Desktop Window)
    python main.py --tkinter   -> Abre a interface clássica em Tkinter
    python main.py --cli       -> Abre o modo interativo via Prompt / Terminal
"""

import sys
import os

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)


def main():
    # 1. Modo Terminal / CLI
    if "--cli" in sys.argv or "--terminal" in sys.argv:
        from app_cli import run_cli
        run_cli()
        return

    # 2. Modo Clássico Tkinter
    if "--tkinter" in sys.argv or "--tk" in sys.argv:
        try:
            from app_gui import start_gui
            start_gui()
            return
        except Exception as e:
            print(f"[!] Tkinter indisponível ({e}). Tentando interface desktop moderna...")

    # 3. Modo Padrão: Nova Interface Visual Moderna Multiplataforma
    try:
        from app_launcher import launch
        launch()
    except Exception as e:
        print(f"[!] Erro ao iniciar interface desktop: {e}")
        print("[*] Iniciando modo de terminal interativo (CLI)...\n")
        from app_cli import run_cli
        run_cli()


if __name__ == "__main__":
    main()
