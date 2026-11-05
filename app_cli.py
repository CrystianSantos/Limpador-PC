"""
Interface de Linha de Comando (CLI) Interativa com Menu de Opções.
Ideal para execução direta pelo Prompt de Comando ou PowerShell.
O usuário escolhe exatamente quais funções deseja executar via menu numerado.
"""

import sys
import os
from scanner import TempScanner, RecycleBinScanner, DuplicateScanner, format_size
from cleaner import Cleaner


def print_banner():
    banner = r"""
========================================================================
     OTIMIZADOR E VARREDURA DE ARQUIVOS DO COMPUTADOR
========================================================================
  Varredura inteligente de:
    1. Arquivos Temporarios e Mortos (%TEMP%)
    2. Lixeira do Windows
    3. Arquivos Duplicados (com integridade SHA-256)
------------------------------------------------------------------------
  * NENHUM arquivo e excluido sem a sua autorizacao explicita.
========================================================================
"""
    print(banner)


def ask_yes_no(question, default="n"):
    """Faz uma pergunta Sim/Nao ao usuario no terminal."""
    prompt = " [s/N]: " if default.lower() == "n" else " [S/n]: "
    while True:
        try:
            choice = input(f"{question}{prompt}").strip().lower()
            if not choice:
                choice = default.lower()
            if choice in ["s", "sim", "y", "yes"]:
                return True
            if choice in ["n", "nao", "no"]:
                return False
            print("Opcao invalida. Digite 's' para Sim ou 'n' para Nao.")
        except (KeyboardInterrupt, EOFError):
            print("\nOperacao cancelada pelo usuario.")
            sys.exit(0)


def ask_menu_choice(options, allow_multiple=False):
    """Mostra um menu numerado e retorna a(s) opcao(oes) escolhida(s)."""
    while True:
        try:
            if allow_multiple:
                choice_str = input(
                    "\nDigite os numeros separados por virgula (ex: 1,2,3) ou 0 para voltar: "
                ).strip()
            else:
                choice_str = input("\nDigite o numero da opcao desejada: ").strip()

            if not choice_str:
                continue

            if choice_str == "0":
                return []

            parts = [p.strip() for p in choice_str.replace(" ", ",").split(",") if p.strip()]
            chosen = []
            valid = True
            for p in parts:
                try:
                    num = int(p)
                    if 1 <= num <= len(options):
                        if num not in chosen:
                            chosen.append(num)
                    else:
                        print(f"  Opcao '{p}' fora do intervalo (1 a {len(options)}).")
                        valid = False
                except ValueError:
                    print(f"  '{p}' nao e um numero valido.")
                    valid = False

            if valid and chosen:
                return chosen
        except (KeyboardInterrupt, EOFError):
            print("\nOperacao cancelada pelo usuario.")
            sys.exit(0)


def show_main_menu():
    """Exibe o menu principal e retorna a escolha do usuario."""
    print("\n" + "=" * 72)
    print("                         MENU PRINCIPAL")
    print("=" * 72)
    print("  Escolha o que deseja fazer:\n")
    print("  [1]  Examinar Lixeira do Windows")
    print("  [2]  Examinar Arquivos Temporarios / Mortos (%TEMP%)")
    print("  [3]  Examinar Arquivos Duplicados")
    print("  [4]  Varredura Completa (tudo acima)")
    print("  [5]  Sair")
    print("-" * 72)

    while True:
        try:
            choice = input("  Sua escolha [1-5]: ").strip()
            if choice in ["1", "2", "3", "4", "5"]:
                return int(choice)
            print("  Opcao invalida. Digite um numero de 1 a 5.")
        except (KeyboardInterrupt, EOFError):
            print("\nOperacao cancelada pelo usuario.")
            sys.exit(0)


# ─────────────────────────────────────────────────────────────────────
# Funcoes de varredura e limpeza individuais
# ─────────────────────────────────────────────────────────────────────

def scan_recycle_bin():
    """Examina e opcionalmente esvazia a Lixeira."""
    print("\n" + "=" * 72)
    print("  EXAME DA LIXEIRA DO WINDOWS")
    print("=" * 72)
    print("  Escaneando Lixeira do Windows...")

    recycle_res = RecycleBinScanner.scan(
        lambda msg: print(f"    {msg}", end="\r")
    )

    print(f"\n  Resultado: {recycle_res['total_items']} itens "
          f"({recycle_res['total_size_formatted']}) encontrados na Lixeira.")
    print(f"\n  O que sao: {recycle_res['explanation']}")

    if recycle_res["total_items"] == 0:
        print("\n  A Lixeira ja esta vazia! Nada a fazer.")
        return recycle_res, False

    # Lista os itens
    if ask_yes_no("\n  Deseja listar todos os itens que estao na lixeira?", default="s"):
        print("\n  +---------------------------------------------------------+")
        print("  | Nome                            | Tamanho   | Tipo      |")
        print("  +---------------------------------------------------------+")
        for it in recycle_res["items"]:
            name = it["name"][:30].ljust(30)
            size = it["size_formatted"].rjust(9)
            ftype = (it["type"] or "?")[:10].ljust(10)
            print(f"  | {name}  | {size} | {ftype}|")
        print("  +---------------------------------------------------------+")
        print(f"  | TOTAL: {recycle_res['total_items']} itens".ljust(42)
              + f"| {recycle_res['total_size_formatted'].rjust(9)} |           |")
        print("  +---------------------------------------------------------+")

    auth = ask_yes_no(
        f"\n  >>> Voce AUTORIZA esvaziar a Lixeira ({recycle_res['total_size_formatted']})?",
        default="n"
    )
    return recycle_res, auth


def scan_temp_files():
    """Examina e opcionalmente limpa arquivos temporarios."""
    print("\n" + "=" * 72)
    print("  EXAME DE ARQUIVOS TEMPORARIOS E MORTOS (%TEMP%)")
    print("=" * 72)
    print("  Escaneando pastas temporarias...")

    temp_res = TempScanner.scan(
        lambda msg: print(f"    {msg}", end="\r")
    )

    print(f"\n  Resultado: {temp_res['total_files']} arquivos "
          f"({temp_res['total_size_formatted']}) encontrados.")
    print(f"\n  O que sao: {temp_res['explanation']}")

    if temp_res["total_files"] == 0:
        print("\n  Nenhum arquivo temporario encontrado! Pastas limpas.")
        return temp_res, False

    # Amostra
    if ask_yes_no("\n  Deseja visualizar uma amostra dos arquivos temporarios?", default="n"):
        print("\n  --- Amostra de Arquivos Temporarios ---")
        sample = temp_res["items"][:25]
        for it in sample:
            if not it.get("is_dir"):
                print(f"    [{it['category']}] {it['filename']} ({it['size_formatted']})")
        remaining = len(temp_res["items"]) - len(sample)
        if remaining > 0:
            print(f"    ... e mais {remaining} itens.")
        print("  ----------------------------------------")

    auth = ask_yes_no(
        f"\n  >>> Voce AUTORIZA limpar os arquivos temporarios mortos "
        f"({temp_res['total_size_formatted']})?",
        default="n"
    )
    return temp_res, auth


def scan_duplicates():
    """Examina e opcionalmente exclui copias duplicadas."""
    print("\n" + "=" * 72)
    print("  EXAME DE ARQUIVOS DUPLICADOS")
    print("=" * 72)

    available_dirs = DuplicateScanner.get_default_scan_directories()

    if not available_dirs:
        print("  Nenhuma pasta pessoal acessivel foi encontrada para varredura.")
        return None, False, []

    print("  Pastas disponiveis para busca de duplicados:\n")
    for i, (label, path) in enumerate(available_dirs, 1):
        print(f"    [{i}] {label} -> {path}")

    print(f"\n    [0] Voltar ao menu principal")
    print(f"\n  Selecione as pastas que deseja escanear.")
    chosen = ask_menu_choice(available_dirs, allow_multiple=True)

    if not chosen:
        return None, False, []

    scan_dirs = [available_dirs[i - 1][1] for i in chosen]
    chosen_labels = [available_dirs[i - 1][0] for i in chosen]
    print(f"\n  Escaneando: {', '.join(chosen_labels)}...")

    dup_res = DuplicateScanner.scan(
        scan_dirs,
        progress_callback=lambda msg: print(f"    {msg}", end="\r")
    )

    scanned_count = dup_res.get("total_scanned", 0)
    print(f"\n  Resultado: {scanned_count} arquivos analisados.")
    print(f"    -> {dup_res['total_groups']} grupos de duplicados encontrados "
          f"({dup_res['total_duplicate_copies']} copias, "
          f"{dup_res['total_wasted_formatted']} desperdicados).")
    print(f"\n  O que sao: {dup_res['explanation']}")

    if dup_res["total_duplicate_copies"] == 0:
        print("\n  Nenhum arquivo duplicado encontrado! Suas pastas estao limpas.")
        return dup_res, False, []

    # Mostra os grupos
    if ask_yes_no("\n  Deseja visualizar os grupos de arquivos duplicados?", default="s"):
        print("\n  --- Arquivos Duplicados Encontrados ---")
        for idx, grp in enumerate(dup_res["groups"], 1):
            orig = grp["original"]
            print(f"\n  [Grupo {idx}] Tamanho: {grp['file_size_formatted']}")
            print(f"    ORIGINAL (MANTER):  {orig['path']}")
            print(f"                        Modificado: {orig['mtime']}")
            for c in grp["copies"]:
                print(f"    COPIA (EXCLUIR):    {c['path']}")
                print(f"                        Modificado: {c['mtime']}")
        print("\n  -----------------------------------------")

    auth = ask_yes_no(
        f"\n  >>> Voce AUTORIZA excluir as {dup_res['total_duplicate_copies']} copias "
        f"duplicadas ({dup_res['total_wasted_formatted']}), mantendo o original?",
        default="n"
    )

    selected_copies = []
    if auth:
        for grp in dup_res["groups"]:
            for c in grp["copies"]:
                selected_copies.append(c["path"])

    return dup_res, auth, selected_copies


# ─────────────────────────────────────────────────────────────────────
# Funcao de execucao da limpeza
# ─────────────────────────────────────────────────────────────────────

def execute_cleaning(
    auth_recycle, recycle_res,
    auth_temp, temp_res,
    auth_dup, dup_res, selected_dup_copies
):
    """Executa as limpezas autorizadas pelo usuario com confirmacao final."""

    if not any([auth_recycle, auth_temp, auth_dup]):
        print("\n  Nenhuma funcao foi autorizada. Nenhum arquivo foi modificado.")
        return

    # Confirmacao final
    print("\n" + "=" * 72)
    print("              CONFIRMACAO FINAL DE EXECUCAO")
    print("=" * 72)
    print("  Funcoes que voce AUTORIZOU:\n")

    total_estimated = 0

    if auth_recycle:
        r_size = recycle_res["total_size"]
        total_estimated += r_size
        print(f"    [X] Esvaziar Lixeira: {recycle_res['total_items']} itens "
              f"({recycle_res['total_size_formatted']})")

    if auth_temp:
        t_size = temp_res["total_size"]
        total_estimated += t_size
        print(f"    [X] Limpar Temporarios: {temp_res['total_files']} arquivos "
              f"({temp_res['total_size_formatted']})")

    if auth_dup:
        w_size = dup_res["total_wasted_bytes"]
        total_estimated += w_size
        print(f"    [X] Excluir Copias Duplicadas: {len(selected_dup_copies)} copias "
              f"({dup_res['total_wasted_formatted']})")

    print(f"\n  Total estimado para liberar: {format_size(total_estimated)}")
    print("\n  ATENCAO: Esta operacao excluira definitivamente os itens autorizados.")

    if not ask_yes_no("  Tem certeza absoluta que deseja prosseguir agora?", default="n"):
        print("\n  Operacao cancelada. Nenhum arquivo foi modificado.")
        return

    # Execucao
    print("\n  [*] Executando limpeza autorizada...\n")
    freed_total = 0

    if auth_temp:
        print("    -> Limpando temporarios...")
        res_t = Cleaner.clean_temp_files(
            temp_res["items"],
            lambda msg: print(f"       {msg}", end="\r")
        )
        freed_total += res_t["freed_bytes"]
        print(f"\n       Concluido: {res_t['deleted_count']} apagados "
              f"({res_t['freed_formatted']} liberados), "
              f"{res_t['skipped_count']} em uso preservados.")

    if auth_recycle:
        print("    -> Esvaziando a Lixeira...")
        res_r = Cleaner.empty_recycle_bin()
        if res_r["success"]:
            freed_total += recycle_res["total_size"]
            print(f"       Concluido: Lixeira esvaziada "
                  f"({recycle_res['total_size_formatted']} liberados).")
        else:
            print(f"       Aviso: {res_r['error'] or 'Nao foi possivel esvaziar a lixeira.'}")

    if auth_dup:
        print(f"    -> Excluindo {len(selected_dup_copies)} copias duplicadas...")
        res_d = Cleaner.delete_duplicate_copies(
            selected_dup_copies,
            lambda msg: print(f"       {msg}", end="\r")
        )
        freed_total += res_d["freed_bytes"]
        print(f"\n       Concluido: {res_d['deleted_count']} copias removidas "
              f"({res_d['freed_formatted']} liberados).")
        if res_d["errors"]:
            print(f"       {res_d['skipped_count']} arquivos nao puderam ser removidos.")

    print("\n" + "=" * 72)
    print("              LIMPEZA FINALIZADA COM SUCESSO!")
    print("=" * 72)
    print(f"  Total de espaco liberado no disco: {format_size(freed_total)}")
    print("=" * 72)


# ─────────────────────────────────────────────────────────────────────
# Loop principal do menu
# ─────────────────────────────────────────────────────────────────────

def run_cli():
    print_banner()

    while True:
        choice = show_main_menu()

        if choice == 5:
            print("\n  Saindo do programa. Ate logo!")
            break

        elif choice == 1:
            recycle_res, auth_recycle = scan_recycle_bin()
            if auth_recycle:
                execute_cleaning(
                    auth_recycle=True, recycle_res=recycle_res,
                    auth_temp=False, temp_res=None,
                    auth_dup=False, dup_res=None, selected_dup_copies=[]
                )
            input("\n  Pressione ENTER para voltar ao menu...")

        elif choice == 2:
            temp_res, auth_temp = scan_temp_files()
            if auth_temp:
                execute_cleaning(
                    auth_recycle=False, recycle_res=None,
                    auth_temp=True, temp_res=temp_res,
                    auth_dup=False, dup_res=None, selected_dup_copies=[]
                )
            input("\n  Pressione ENTER para voltar ao menu...")

        elif choice == 3:
            dup_res, auth_dup, selected_copies = scan_duplicates()
            if auth_dup:
                execute_cleaning(
                    auth_recycle=False, recycle_res=None,
                    auth_temp=False, temp_res=None,
                    auth_dup=True, dup_res=dup_res,
                    selected_dup_copies=selected_copies
                )
            input("\n  Pressione ENTER para voltar ao menu...")

        elif choice == 4:
            # Varredura completa
            print("\n" + "=" * 72)
            print("              VARREDURA COMPLETA DO COMPUTADOR")
            print("=" * 72)

            # 1. Lixeira
            print("\n  [1/3] Verificando Lixeira do Windows...")
            recycle_res = RecycleBinScanner.scan(
                lambda msg: print(f"    {msg}", end="\r")
            )
            print(f"\n    -> {recycle_res['total_items']} itens "
                  f"({recycle_res['total_size_formatted']})")

            # 2. Temporarios
            print("\n  [2/3] Verificando arquivos temporarios (%TEMP%)...")
            temp_res = TempScanner.scan(
                lambda msg: print(f"    {msg}", end="\r")
            )
            print(f"\n    -> {temp_res['total_files']} arquivos "
                  f"({temp_res['total_size_formatted']})")

            # 3. Duplicados
            print("\n  [3/3] Buscando arquivos duplicados em pastas pessoais...")
            scan_dirs = [p for _, p in DuplicateScanner.get_default_scan_directories()]
            dup_res = DuplicateScanner.scan(
                scan_dirs,
                progress_callback=lambda msg: print(f"    {msg}", end="\r")
            )
            print(f"\n    -> {dup_res['total_groups']} grupos, "
                  f"{dup_res['total_duplicate_copies']} copias "
                  f"({dup_res['total_wasted_formatted']})")

            total_space = (
                recycle_res["total_size"]
                + temp_res["total_size"]
                + dup_res["total_wasted_bytes"]
            )

            print("\n" + "=" * 72)
            print("                      RESUMO DA VARREDURA")
            print("=" * 72)
            print(f"  1. Lixeira:       {recycle_res['total_items']:>6} itens"
                  f"       | {recycle_res['total_size_formatted']:>10}")
            print(f"  2. Temporarios:   {temp_res['total_files']:>6} arquivos"
                  f"    | {temp_res['total_size_formatted']:>10}")
            print(f"  3. Duplicados:    {dup_res['total_duplicate_copies']:>6} copias"
                  f"      | {dup_res['total_wasted_formatted']:>10}")
            print("-" * 72)
            print(f"  TOTAL ESTIMADO PARA RECUPERAR: {format_size(total_space)}")
            print("=" * 72)

            if total_space == 0:
                print("\n  Seu computador ja esta totalmente limpo!")
                input("\n  Pressione ENTER para voltar ao menu...")
                continue

            # Autorizacoes
            print("\n  AUTORIZACAO DE FUNCOES - O QUE VOCE DESEJA REALIZAR?")
            print("-" * 72)

            auth_recycle = False
            auth_temp = False
            auth_dup = False
            selected_dup_copies = []

            if recycle_res["total_items"] > 0:
                print(f"\n  Lixeira: {recycle_res['total_items']} itens "
                      f"({recycle_res['total_size_formatted']})")
                print(f"  {recycle_res['explanation']}")
                auth_recycle = ask_yes_no(
                    "  >>> Autoriza esvaziar a Lixeira?", default="n"
                )

            if temp_res["total_files"] > 0:
                print(f"\n  Temporarios: {temp_res['total_files']} arquivos "
                      f"({temp_res['total_size_formatted']})")
                print(f"  {temp_res['explanation']}")
                auth_temp = ask_yes_no(
                    "  >>> Autoriza limpar temporarios?", default="n"
                )

            if dup_res["total_duplicate_copies"] > 0:
                print(f"\n  Duplicados: {dup_res['total_duplicate_copies']} copias "
                      f"({dup_res['total_wasted_formatted']})")
                print(f"  {dup_res['explanation']}")
                auth_dup = ask_yes_no(
                    "  >>> Autoriza excluir copias duplicadas (mantendo o original)?",
                    default="n"
                )
                if auth_dup:
                    for grp in dup_res["groups"]:
                        for c in grp["copies"]:
                            selected_dup_copies.append(c["path"])

            execute_cleaning(
                auth_recycle, recycle_res,
                auth_temp, temp_res,
                auth_dup, dup_res, selected_dup_copies
            )
            input("\n  Pressione ENTER para voltar ao menu...")


if __name__ == "__main__":
    run_cli()
