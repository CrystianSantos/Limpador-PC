"""
Interface Gráfica Moderna (GUI) para Limpeza e Otimização do Computador.
Desenvolvida com Tkinter / TTK nativo do Python (não requer dependências externas).
Inclui menu de ações individuais para escolher exatamente o que examinar.
"""

import os
import sys
import threading
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

from scanner import TempScanner, RecycleBinScanner, DuplicateScanner, format_size
from cleaner import Cleaner


class CleanerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Limpeza e Otimizacao do Computador")
        self.geometry("1020x760")
        self.minsize(860, 600)

        # Configuração de estilo
        self.configure(bg="#f1f5f9")
        self._setup_styles()

        # Dados da varredura
        self.temp_data = None
        self.recycle_data = None
        self.duplicate_data = None

        # Flag para evitar varreduras simultâneas
        self._scan_in_progress = False

        # Variáveis de autorização do usuário
        self.auth_temp_var = tk.BooleanVar(value=False)
        self.auth_recycle_var = tk.BooleanVar(value=False)
        self.auth_duplicates_var = tk.BooleanVar(value=False)

        # Variáveis de pastas para busca de duplicados
        self.duplicate_dirs_vars = {}
        for label, path in DuplicateScanner.get_default_scan_directories():
            self.duplicate_dirs_vars[path] = (label, tk.BooleanVar(value=True))

        # Lista de cópias duplicadas selecionadas para exclusão
        self.selected_duplicate_paths = set()

        # Construção da interface
        self._create_widgets()

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Configurações de abas
        style.configure("TNotebook", background="#f1f5f9", borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            padding=[14, 8],
            font=("Segoe UI", 10, "bold"),
            background="#e2e8f0",
            foreground="#334155",
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#ffffff")],
            foreground=[("selected", "#0f172a")],
        )

        # Botões
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            background="#2563eb",
            foreground="#ffffff",
            borderwidth=0,
            padding=8,
        )
        style.map("Primary.TButton", background=[("active", "#1d4ed8")])

        style.configure(
            "Success.TButton",
            font=("Segoe UI", 11, "bold"),
            background="#16a34a",
            foreground="#ffffff",
            borderwidth=0,
            padding=10,
        )
        style.map("Success.TButton", background=[("active", "#15803d")])

        style.configure(
            "Secondary.TButton",
            font=("Segoe UI", 9),
            background="#e2e8f0",
            foreground="#0f172a",
            borderwidth=0,
            padding=6,
        )
        style.map("Secondary.TButton", background=[("active", "#cbd5e1")])

        style.configure(
            "Menu.TButton",
            font=("Segoe UI", 9, "bold"),
            background="#1e40af",
            foreground="#ffffff",
            borderwidth=0,
            padding=7,
        )
        style.map("Menu.TButton", background=[("active", "#1e3a8a")])

        # Treeview (Tabelas)
        style.configure(
            "Treeview",
            font=("Segoe UI", 9),
            rowheight=24,
            background="#ffffff",
            fieldbackground="#ffffff",
        )
        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 9, "bold"),
            background="#e2e8f0",
            foreground="#1e293b",
        )

    # ─── Thread-safe GUI updates ────────────────────────────────────

    def _update_status(self, text):
        """Atualiza o label de status de forma thread-safe."""
        self.after(0, lambda: self.status_label.config(text=text))

    def _log_safe(self, text):
        """Escreve nos logs de forma thread-safe."""
        self.after(0, lambda: self.log_message(text))

    def _progress_cb(self, msg):
        """Callback unificado para progresso — thread-safe."""
        self._update_status(msg)
        self._log_safe(msg)

    # ─── Widget creation ────────────────────────────────────────────

    def _create_widgets(self):
        # Top Header Bar
        header_frame = tk.Frame(self, bg="#0f172a", height=80)
        header_frame.pack(fill=tk.X)

        tk.Label(
            header_frame,
            text="Otimizador e Varredura de Arquivos",
            font=("Segoe UI", 17, "bold"),
            bg="#0f172a",
            fg="#f8fafc",
        ).pack(anchor="w", padx=20, pady=(12, 2))

        tk.Label(
            header_frame,
            text="Identifique arquivos temporarios, lixeira e copias duplicadas "
                 "com controle total e confirmacao de seguranca.",
            font=("Segoe UI", 9),
            bg="#0f172a",
            fg="#94a3b8",
        ).pack(anchor="w", padx=20, pady=(0, 12))

        # ── Menu de Ações ──
        menu_bar = tk.Frame(self, bg="#ffffff", bd=1, relief=tk.SOLID)
        menu_bar.pack(fill=tk.X, padx=16, pady=(10, 2))

        tk.Label(
            menu_bar,
            text="Escolha o que examinar:",
            font=("Segoe UI", 10, "bold"),
            bg="#ffffff",
            fg="#0f172a",
        ).pack(side=tk.LEFT, padx=(12, 16), pady=8)

        self.btn_scan_recycle = ttk.Button(
            menu_bar,
            text="Lixeira",
            style="Menu.TButton",
            command=lambda: self._start_scan("recycle"),
        )
        self.btn_scan_recycle.pack(side=tk.LEFT, padx=4, pady=6)

        self.btn_scan_temp = ttk.Button(
            menu_bar,
            text="Temporarios (%TEMP%)",
            style="Menu.TButton",
            command=lambda: self._start_scan("temp"),
        )
        self.btn_scan_temp.pack(side=tk.LEFT, padx=4, pady=6)

        self.btn_scan_dup = ttk.Button(
            menu_bar,
            text="Duplicados",
            style="Menu.TButton",
            command=lambda: self._start_scan("duplicates"),
        )
        self.btn_scan_dup.pack(side=tk.LEFT, padx=4, pady=6)

        self.btn_scan_all = ttk.Button(
            menu_bar,
            text="Varredura Completa",
            style="Primary.TButton",
            command=lambda: self._start_scan("all"),
        )
        self.btn_scan_all.pack(side=tk.LEFT, padx=(12, 4), pady=6)

        # ── Status / Progress Bar ──
        status_bar = tk.Frame(self, bg="#ffffff", bd=1, relief=tk.SOLID)
        status_bar.pack(fill=tk.X, padx=16, pady=(2, 6))

        self.status_label = tk.Label(
            status_bar,
            text="Clique em um dos botoes acima para iniciar a analise.",
            font=("Segoe UI", 9, "italic"),
            bg="#ffffff",
            fg="#475569",
        )
        self.status_label.pack(side=tk.LEFT, padx=12, pady=6, fill=tk.X, expand=True)

        self.progress_bar = ttk.Progressbar(status_bar, mode="indeterminate", length=220)

        # Notebook (Abas)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        self.tab_overview = tk.Frame(self.notebook, bg="#f8fafc")
        self.tab_recycle = tk.Frame(self.notebook, bg="#f8fafc")
        self.tab_temp = tk.Frame(self.notebook, bg="#f8fafc")
        self.tab_duplicates = tk.Frame(self.notebook, bg="#f8fafc")
        self.tab_logs = tk.Frame(self.notebook, bg="#f8fafc")

        self.notebook.add(self.tab_overview, text=" Visao Geral e Autorizacoes")
        self.notebook.add(self.tab_recycle, text=" Lixeira")
        self.notebook.add(self.tab_temp, text=" Arquivos Temporarios (%TEMP%)")
        self.notebook.add(self.tab_duplicates, text=" Arquivos Duplicados")
        self.notebook.add(self.tab_logs, text=" Historico / Logs")

        self._build_overview_tab()
        self._build_recycle_tab()
        self._build_temp_tab()
        self._build_duplicates_tab()
        self._build_logs_tab()

    def _build_overview_tab(self):
        container = tk.Frame(self.tab_overview, bg="#f8fafc")
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        tk.Label(
            container,
            text="Abaixo esta o resumo dos arquivos encontrados. "
                 "Marque as caixas de selecao apenas das funcoes que voce "
                 "AUTORIZA realizar e clique no botao de limpeza.",
            font=("Segoe UI", 10),
            bg="#f8fafc",
            fg="#334155",
            justify=tk.LEFT,
            wraplength=860,
        ).pack(anchor="w", pady=(0, 15))

        # Cards
        cards_frame = tk.Frame(container, bg="#f8fafc")
        cards_frame.pack(fill=tk.X, pady=5)
        cards_frame.columnconfigure(0, weight=1)
        cards_frame.columnconfigure(1, weight=1)
        cards_frame.columnconfigure(2, weight=1)

        # Card 1: Lixeira
        self.card_recycle = tk.Frame(
            cards_frame, bg="#ffffff", bd=1, relief=tk.SOLID, padx=15, pady=15
        )
        self.card_recycle.grid(row=0, column=0, padx=8, sticky="nsew")

        tk.Label(
            self.card_recycle,
            text="Lixeira do Windows",
            font=("Segoe UI", 12, "bold"),
            bg="#ffffff",
            fg="#b45309",
        ).pack(anchor="w")
        self.lbl_recycle_stat = tk.Label(
            self.card_recycle,
            text="Aguardando varredura...",
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#64748b",
        )
        self.lbl_recycle_stat.pack(anchor="w", pady=(6, 8))
        tk.Label(
            self.card_recycle,
            text="Arquivos e pastas descartados que ainda ocupam espaco fisico no disco.",
            font=("Segoe UI", 8),
            bg="#ffffff",
            fg="#64748b",
            wraplength=240,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(0, 12))

        self.chk_recycle = tk.Checkbutton(
            self.card_recycle,
            text="Autorizo esvaziar a Lixeira",
            variable=self.auth_recycle_var,
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#0f172a",
            activebackground="#ffffff",
            state=tk.DISABLED,
        )
        self.chk_recycle.pack(anchor="w")

        # Card 2: Temporários
        self.card_temp = tk.Frame(
            cards_frame, bg="#ffffff", bd=1, relief=tk.SOLID, padx=15, pady=15
        )
        self.card_temp.grid(row=0, column=1, padx=8, sticky="nsew")

        tk.Label(
            self.card_temp,
            text="Arquivos Mortos (%TEMP%)",
            font=("Segoe UI", 12, "bold"),
            bg="#ffffff",
            fg="#0284c7",
        ).pack(anchor="w")
        self.lbl_temp_stat = tk.Label(
            self.card_temp,
            text="Aguardando varredura...",
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#64748b",
        )
        self.lbl_temp_stat.pack(anchor="w", pady=(6, 8))
        tk.Label(
            self.card_temp,
            text="Residuos de instalacoes, caches e arquivos mortos. "
                 "100% seguro para excluir.",
            font=("Segoe UI", 8),
            bg="#ffffff",
            fg="#64748b",
            wraplength=240,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(0, 12))

        self.chk_temp = tk.Checkbutton(
            self.card_temp,
            text="Autorizo limpar temporarios",
            variable=self.auth_temp_var,
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#0f172a",
            activebackground="#ffffff",
            state=tk.DISABLED,
        )
        self.chk_temp.pack(anchor="w")

        # Card 3: Duplicados
        self.card_dup = tk.Frame(
            cards_frame, bg="#ffffff", bd=1, relief=tk.SOLID, padx=15, pady=15
        )
        self.card_dup.grid(row=0, column=2, padx=8, sticky="nsew")

        tk.Label(
            self.card_dup,
            text="Arquivos Duplicados",
            font=("Segoe UI", 12, "bold"),
            bg="#ffffff",
            fg="#7c3aed",
        ).pack(anchor="w")
        self.lbl_dup_stat = tk.Label(
            self.card_dup,
            text="Aguardando varredura...",
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#64748b",
        )
        self.lbl_dup_stat.pack(anchor="w", pady=(6, 8))
        tk.Label(
            self.card_dup,
            text="Arquivos com o mesmo conteudo em locais diferentes. "
                 "Mantem o original.",
            font=("Segoe UI", 8),
            bg="#ffffff",
            fg="#64748b",
            wraplength=240,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(0, 12))

        self.chk_dup = tk.Checkbutton(
            self.card_dup,
            text="Autorizo excluir copias duplicadas",
            variable=self.auth_duplicates_var,
            font=("Segoe UI", 9, "bold"),
            bg="#ffffff",
            fg="#0f172a",
            activebackground="#ffffff",
            state=tk.DISABLED,
        )
        self.chk_dup.pack(anchor="w")

        # Totais e botão de ação
        action_box = tk.Frame(container, bg="#f8fafc")
        action_box.pack(fill=tk.X, pady=(25, 10))

        self.lbl_total_space = tk.Label(
            action_box,
            text="Espaco Total Recuperavel: 0 B",
            font=("Segoe UI", 13, "bold"),
            bg="#f8fafc",
            fg="#0f172a",
        )
        self.lbl_total_space.pack(anchor="w", pady=(0, 12))

        self.btn_execute = ttk.Button(
            action_box,
            text="Executar Limpeza dos Itens Autorizados",
            style="Success.TButton",
            command=self.confirm_and_execute,
            state=tk.DISABLED,
        )
        self.btn_execute.pack(anchor="w")

    def _build_recycle_tab(self):
        container = tk.Frame(self.tab_recycle, bg="#f8fafc")
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        banner = tk.Frame(container, bg="#fef3c7", bd=1, relief=tk.SOLID, padx=12, pady=10)
        banner.pack(fill=tk.X, pady=(0, 10))
        tk.Label(
            banner,
            text="O que sao estes arquivos? Sao arquivos e pastas que voce excluiu "
                 "anteriormente. Eles continuam ocupando espaco no disco ate que a "
                 "Lixeira seja esvaziada. Caso nao precise de nada listado abaixo, "
                 "e seguro esvaziar.",
            font=("Segoe UI", 9),
            bg="#fef3c7",
            fg="#92400e",
            justify=tk.LEFT,
            wraplength=850,
        ).pack(anchor="w")

        tree_frame = tk.Frame(container)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("Nome", "Tamanho", "Tipo")
        self.tree_recycle = ttk.Treeview(
            tree_frame, columns=cols, show="headings", selectmode="extended"
        )
        self.tree_recycle.heading("Nome", text="Nome do Arquivo / Pasta")
        self.tree_recycle.heading("Tamanho", text="Tamanho")
        self.tree_recycle.heading("Tipo", text="Tipo")
        self.tree_recycle.column("Nome", width=450)
        self.tree_recycle.column("Tamanho", width=120, anchor="e")
        self.tree_recycle.column("Tipo", width=180)

        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_recycle.yview)
        self.tree_recycle.configure(yscrollcommand=sb.set)
        self.tree_recycle.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_temp_tab(self):
        container = tk.Frame(self.tab_temp, bg="#f8fafc")
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        banner = tk.Frame(container, bg="#e0f2fe", bd=1, relief=tk.SOLID, padx=12, pady=10)
        banner.pack(fill=tk.X, pady=(0, 10))
        tk.Label(
            banner,
            text="O que sao estes arquivos? Sao arquivos temporarios criados por "
                 "programas do Windows durante o uso ou instalacao (%TEMP%). Quando "
                 "os programas fecham, esses arquivos viram 'arquivos mortos'. "
                 "Sao 100% seguros para remocao (arquivos que estiverem em uso no "
                 "momento serao ignorados automaticamente).",
            font=("Segoe UI", 9),
            bg="#e0f2fe",
            fg="#0369a1",
            justify=tk.LEFT,
            wraplength=850,
        ).pack(anchor="w")

        tree_frame = tk.Frame(container)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("Nome", "Categoria", "Tamanho", "Modificado em", "Caminho")
        self.tree_temp = ttk.Treeview(
            tree_frame, columns=cols, show="headings", selectmode="extended"
        )
        self.tree_temp.heading("Nome", text="Nome do Arquivo")
        self.tree_temp.heading("Categoria", text="Origem")
        self.tree_temp.heading("Tamanho", text="Tamanho")
        self.tree_temp.heading("Modificado em", text="Data")
        self.tree_temp.heading("Caminho", text="Caminho Completo")
        self.tree_temp.column("Nome", width=220)
        self.tree_temp.column("Categoria", width=150)
        self.tree_temp.column("Tamanho", width=90, anchor="e")
        self.tree_temp.column("Modificado em", width=140)
        self.tree_temp.column("Caminho", width=300)

        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_temp.yview)
        self.tree_temp.configure(yscrollcommand=sb.set)
        self.tree_temp.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_duplicates_tab(self):
        container = tk.Frame(self.tab_duplicates, bg="#f8fafc")
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        banner = tk.Frame(container, bg="#ede9fe", bd=1, relief=tk.SOLID, padx=12, pady=10)
        banner.pack(fill=tk.X, pady=(0, 10))
        tk.Label(
            banner,
            text="O que sao estes arquivos? Sao arquivos exatamente identicos "
                 "ocupando espaco duplicado no seu computador. O arquivo original "
                 "e marcado em verde (Manter) e as copias duplicadas sao listadas "
                 "para exclusao autorizada.",
            font=("Segoe UI", 9),
            bg="#ede9fe",
            fg="#5b21b6",
            justify=tk.LEFT,
            wraplength=850,
        ).pack(anchor="w")

        # Seletor de pastas
        self.folder_frame = tk.LabelFrame(
            container,
            text="Pastas incluidas na busca de duplicados",
            font=("Segoe UI", 9, "bold"),
            bg="#f8fafc",
            padx=10,
            pady=6,
        )
        self.folder_frame.pack(fill=tk.X, pady=(0, 10))

        self.cb_row = tk.Frame(self.folder_frame, bg="#f8fafc")
        self.cb_row.pack(fill=tk.X)

        for p, (label, var) in self.duplicate_dirs_vars.items():
            chk = tk.Checkbutton(
                self.cb_row, text=label, variable=var, bg="#f8fafc",
                font=("Segoe UI", 9)
            )
            chk.pack(side=tk.LEFT, padx=8)

        btn_add_folder = ttk.Button(
            self.cb_row,
            text="+ Escolher Outra Pasta...",
            style="Secondary.TButton",
            command=self.add_custom_folder,
        )
        btn_add_folder.pack(side=tk.LEFT, padx=12)

        # Barra de ferramentas para duplicados
        tools_row = tk.Frame(container, bg="#f8fafc")
        tools_row.pack(fill=tk.X, pady=(0, 6))

        ttk.Button(
            tools_row,
            text="Marcar Todas as Copias",
            style="Secondary.TButton",
            command=self.select_all_duplicate_copies,
        ).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            tools_row,
            text="Desmarcar Todas",
            style="Secondary.TButton",
            command=self.deselect_all_duplicate_copies,
        ).pack(side=tk.LEFT)

        # Treeview com grupos
        tree_frame = tk.Frame(container)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("Acao", "Nome", "Tamanho", "Data", "Caminho")
        self.tree_dup = ttk.Treeview(
            tree_frame, columns=cols, show="tree headings", selectmode="extended"
        )
        self.tree_dup.heading("#0", text="Status")
        self.tree_dup.heading("Acao", text="Acao Sugerida")
        self.tree_dup.heading("Nome", text="Arquivo")
        self.tree_dup.heading("Tamanho", text="Tamanho")
        self.tree_dup.heading("Data", text="Modificado em")
        self.tree_dup.heading("Caminho", text="Caminho Completo")

        self.tree_dup.column("#0", width=120)
        self.tree_dup.column("Acao", width=130)
        self.tree_dup.column("Nome", width=220)
        self.tree_dup.column("Tamanho", width=90, anchor="e")
        self.tree_dup.column("Data", width=140)
        self.tree_dup.column("Caminho", width=320)

        self.tree_dup.tag_configure(
            "original", foreground="#166534", font=("Segoe UI", 9, "bold")
        )
        self.tree_dup.tag_configure(
            "copy_selected", foreground="#b91c1c", font=("Segoe UI", 9)
        )
        self.tree_dup.tag_configure(
            "copy_unselected", foreground="#475569", font=("Segoe UI", 9)
        )

        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_dup.yview)
        self.tree_dup.configure(yscrollcommand=sb.set)
        self.tree_dup.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_logs_tab(self):
        container = tk.Frame(self.tab_logs, bg="#f8fafc")
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        self.txt_logs = tk.Text(
            container,
            bg="#0f172a",
            fg="#f8fafc",
            font=("Consolas", 9),
            relief=tk.FLAT,
            padx=10,
            pady=10,
        )
        sb = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.txt_logs.yview)
        self.txt_logs.configure(yscrollcommand=sb.set)
        self.txt_logs.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_message("Sistema de Otimizacao iniciado com sucesso.")
        self.log_message(
            "Pronto para varredura. Escolha o que examinar nos botoes acima."
        )

    # ─── Helpers ────────────────────────────────────────────────────

    def log_message(self, text):
        """Escreve no log (deve ser chamado na thread principal)."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        msg = f"[{timestamp}] {text}\n"
        self.txt_logs.insert(tk.END, msg)
        self.txt_logs.see(tk.END)

    def add_custom_folder(self):
        folder = filedialog.askdirectory(
            title="Selecione uma pasta para buscar duplicados"
        )
        if folder and folder not in self.duplicate_dirs_vars:
            label = os.path.basename(folder) or folder
            var = tk.BooleanVar(value=True)
            self.duplicate_dirs_vars[folder] = (label, var)

            # Cria o checkbox na UI dinamicamente
            chk = tk.Checkbutton(
                self.cb_row, text=label, variable=var, bg="#f8fafc",
                font=("Segoe UI", 9)
            )
            chk.pack(side=tk.LEFT, padx=8)

            self.log_message(f"Pasta personalizada adicionada para busca: {folder}")
            messagebox.showinfo(
                "Pasta Adicionada",
                f"A pasta '{folder}' foi adicionada a busca de duplicados.",
            )

    def select_all_duplicate_copies(self):
        if not self.duplicate_data or not self.duplicate_data.get("groups"):
            return
        self.selected_duplicate_paths.clear()
        for group in self.duplicate_data["groups"]:
            for c in group["copies"]:
                self.selected_duplicate_paths.add(c["path"])
        self._refresh_duplicate_tree()
        self.log_message(
            f"Todas as copias duplicadas foram marcadas "
            f"({len(self.selected_duplicate_paths)} copias)."
        )

    def deselect_all_duplicate_copies(self):
        self.selected_duplicate_paths.clear()
        if self.duplicate_data:
            self._refresh_duplicate_tree()
        self.log_message("Todas as copias duplicadas foram desmarcadas.")

    def _set_menu_buttons_state(self, state):
        """Habilita ou desabilita todos os botões de menu."""
        for btn in (
            self.btn_scan_recycle, self.btn_scan_temp,
            self.btn_scan_dup, self.btn_scan_all,
        ):
            btn.config(state=state)

    # ─── Scan orchestration ─────────────────────────────────────────

    def _start_scan(self, scan_type):
        """Inicia uma varredura em background. scan_type: recycle/temp/duplicates/all"""
        if self._scan_in_progress:
            messagebox.showinfo(
                "Varredura em Andamento",
                "Aguarde a varredura atual terminar antes de iniciar outra.",
            )
            return

        self._scan_in_progress = True
        self._set_menu_buttons_state(tk.DISABLED)
        self.btn_execute.config(state=tk.DISABLED)
        self.progress_bar.pack(side=tk.RIGHT, padx=15)
        self.progress_bar.start(10)
        self._update_status(f"Executando varredura ({scan_type})...")

        thread = threading.Thread(
            target=self._run_scan_worker, args=(scan_type,), daemon=True
        )
        thread.start()

    def _run_scan_worker(self, scan_type):
        """Worker thread para varredura."""
        try:
            if scan_type in ("recycle", "all"):
                self._log_safe("--- Escaneando Lixeira do Windows ---")
                recycle_res = RecycleBinScanner.scan(self._progress_cb)
                self.recycle_data = recycle_res
                self._log_safe(
                    f"Lixeira: {recycle_res['total_items']} itens "
                    f"({recycle_res['total_size_formatted']})"
                )

            if scan_type in ("temp", "all"):
                self._log_safe("--- Escaneando Arquivos Temporarios ---")
                temp_res = TempScanner.scan(self._progress_cb)
                self.temp_data = temp_res
                self._log_safe(
                    f"Temporarios: {temp_res['total_files']} arquivos "
                    f"({temp_res['total_size_formatted']})"
                )

            if scan_type in ("duplicates", "all"):
                self._log_safe("--- Escaneando Arquivos Duplicados ---")
                selected_dirs = [
                    p for p, (_, var) in self.duplicate_dirs_vars.items()
                    if var.get()
                ]
                dup_res = DuplicateScanner.scan(
                    selected_dirs, progress_callback=self._progress_cb
                )
                self.duplicate_data = dup_res
                self._log_safe(
                    f"Duplicados: {dup_res['total_groups']} grupos, "
                    f"{dup_res['total_duplicate_copies']} copias "
                    f"({dup_res['total_wasted_formatted']})"
                )

        except Exception:
            self._log_safe(f"ERRO na varredura: {traceback.format_exc()}")

        # Atualiza a interface na thread principal
        self.after(0, lambda: self._scan_completed(scan_type))

    def _scan_completed(self, scan_type):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self._set_menu_buttons_state(tk.NORMAL)
        self._scan_in_progress = False
        self.status_label.config(
            text="Varredura concluida! Marque as funcoes que deseja autorizar."
        )

        # Atualiza Card Lixeira
        if self.recycle_data:
            r_items = self.recycle_data["total_items"]
            r_size = self.recycle_data["total_size_formatted"]
            self.lbl_recycle_stat.config(text=f"{r_items} itens | {r_size}")
            if r_items > 0:
                self.chk_recycle.config(state=tk.NORMAL)
            else:
                self.chk_recycle.config(state=tk.DISABLED)
                self.auth_recycle_var.set(False)
            # Navega para aba da lixeira se foi scan individual
            if scan_type == "recycle":
                self._populate_recycle_table()
                self.notebook.select(self.tab_recycle)

        # Atualiza Card Temporários
        if self.temp_data:
            t_items = self.temp_data["total_files"]
            t_size = self.temp_data["total_size_formatted"]
            self.lbl_temp_stat.config(text=f"{t_items} arquivos | {t_size}")
            if t_items > 0:
                self.chk_temp.config(state=tk.NORMAL)
            else:
                self.chk_temp.config(state=tk.DISABLED)
                self.auth_temp_var.set(False)
            if scan_type == "temp":
                self._populate_temp_table()
                self.notebook.select(self.tab_temp)

        # Atualiza Card Duplicados
        if self.duplicate_data:
            d_groups = self.duplicate_data["total_groups"]
            d_copies = self.duplicate_data["total_duplicate_copies"]
            d_wasted = self.duplicate_data["total_wasted_formatted"]
            self.lbl_dup_stat.config(
                text=f"{d_groups} grupos ({d_copies} copias) | {d_wasted}"
            )
            if d_copies > 0:
                self.chk_dup.config(state=tk.NORMAL)
                self.select_all_duplicate_copies()
            else:
                self.chk_dup.config(state=tk.DISABLED)
                self.auth_duplicates_var.set(False)
            if scan_type == "duplicates":
                self._refresh_duplicate_tree()
                self.notebook.select(self.tab_duplicates)

        # Calcula espaço total recuperável
        total_recuperavel = 0
        if self.recycle_data:
            total_recuperavel += self.recycle_data["total_size"]
        if self.temp_data:
            total_recuperavel += self.temp_data["total_size"]
        if self.duplicate_data:
            total_recuperavel += self.duplicate_data["total_wasted_bytes"]

        self.lbl_total_space.config(
            text=f"Espaco Total Estimado para Recuperar: "
                 f"{format_size(total_recuperavel)}",
            fg="#16a34a" if total_recuperavel > 0 else "#0f172a",
        )

        if total_recuperavel > 0:
            self.btn_execute.config(state=tk.NORMAL)

        # Popula todas as tabelas no scan completo
        if scan_type == "all":
            if self.recycle_data:
                self._populate_recycle_table()
            if self.temp_data:
                self._populate_temp_table()
            if self.duplicate_data:
                self._refresh_duplicate_tree()
            self.notebook.select(self.tab_overview)

        self.log_message(
            f"--- VARREDURA FINALIZADA: "
            f"{format_size(total_recuperavel)} recuperaveis ---"
        )

    # ─── Table population ───────────────────────────────────────────

    def _populate_recycle_table(self):
        for item in self.tree_recycle.get_children():
            self.tree_recycle.delete(item)
        if not self.recycle_data:
            return
        for it in self.recycle_data["items"]:
            self.tree_recycle.insert(
                "", tk.END,
                values=(it["name"], it["size_formatted"], it["type"]),
            )

    def _populate_temp_table(self):
        for item in self.tree_temp.get_children():
            self.tree_temp.delete(item)
        if not self.temp_data:
            return
        # Exibe até 2000 itens para performance na UI
        for it in self.temp_data["items"][:2000]:
            if not it.get("is_dir"):
                self.tree_temp.insert(
                    "", tk.END,
                    values=(
                        it["filename"],
                        it["category"],
                        it["size_formatted"],
                        it["mtime"],
                        it["path"],
                    ),
                )

    def _refresh_duplicate_tree(self):
        for item in self.tree_dup.get_children():
            self.tree_dup.delete(item)
        if not self.duplicate_data:
            return

        for idx, grp in enumerate(self.duplicate_data.get("groups", []), 1):
            orig = grp["original"]
            copies = grp["copies"]
            sz = grp["file_size_formatted"]

            parent_id = self.tree_dup.insert(
                "", tk.END,
                text=f"Grupo {idx}",
                values=("Grupo", orig["name"], sz, f"{len(copies)} copias", ""),
                open=True,
            )

            # Original
            self.tree_dup.insert(
                parent_id, tk.END,
                text="ORIGINAL",
                values=("MANTER", orig["name"], sz, orig["mtime"], orig["path"]),
                tags=("original",),
            )

            # Cópias
            for c in copies:
                is_sel = c["path"] in self.selected_duplicate_paths
                tag = "copy_selected" if is_sel else "copy_unselected"
                act_text = "EXCLUIR COPIA" if is_sel else "IGNORAR"
                status_text = "[X] COPIA" if is_sel else "[ ] COPIA"

                self.tree_dup.insert(
                    parent_id, tk.END,
                    text=status_text,
                    values=(act_text, c["name"], sz, c["mtime"], c["path"]),
                    tags=(tag,),
                )

    # ─── Cleaning execution ─────────────────────────────────────────

    def confirm_and_execute(self):
        auth_temp = self.auth_temp_var.get()
        auth_recycle = self.auth_recycle_var.get()
        auth_dup = self.auth_duplicates_var.get()

        if not any([auth_temp, auth_recycle, auth_dup]):
            messagebox.showwarning(
                "Nenhuma Funcao Autorizada",
                "Voce precisa autorizar ao menos uma funcao marcando as caixas de "
                "selecao na aba 'Visao Geral e Autorizacoes'.",
            )
            return

        # Verifica se tem dados válidos para o que foi autorizado
        if auth_temp and not self.temp_data:
            messagebox.showwarning(
                "Varredura Necessaria",
                "Voce precisa executar a varredura de Temporarios antes de limpar.",
            )
            return
        if auth_recycle and not self.recycle_data:
            messagebox.showwarning(
                "Varredura Necessaria",
                "Voce precisa executar a varredura da Lixeira antes de esvaziar.",
            )
            return
        if auth_dup and not self.duplicate_data:
            messagebox.showwarning(
                "Varredura Necessaria",
                "Voce precisa executar a varredura de Duplicados antes de excluir.",
            )
            return

        # Resumo para confirmação
        summary_lines = ["CONFIRMACAO DE AUTORIZACAO DE LIMPEZA\n"]
        summary_lines.append(
            "Voce autoriza a realizacao das seguintes operacoes:\n"
        )

        total_bytes = 0

        if auth_temp:
            t_size = self.temp_data["total_size_formatted"]
            t_count = self.temp_data["total_files"]
            total_bytes += self.temp_data["total_size"]
            summary_lines.append(
                f"  [AUTORIZADO] Limpeza de Temporarios (%TEMP%):"
            )
            summary_lines.append(f"    - {t_count} arquivos ({t_size})\n")

        if auth_recycle:
            r_size = self.recycle_data["total_size_formatted"]
            r_count = self.recycle_data["total_items"]
            total_bytes += self.recycle_data["total_size"]
            summary_lines.append(
                f"  [AUTORIZADO] Esvaziamento da Lixeira do Windows:"
            )
            summary_lines.append(f"    - {r_count} itens ({r_size})\n")

        if auth_dup:
            dup_paths = list(self.selected_duplicate_paths)
            dup_bytes = sum(
                grp["file_size"]
                for grp in self.duplicate_data["groups"]
                for c in grp["copies"]
                if c["path"] in self.selected_duplicate_paths
            )
            total_bytes += dup_bytes
            summary_lines.append(
                f"  [AUTORIZADO] Exclusao de Copias Duplicadas:"
            )
            summary_lines.append(
                f"    - {len(dup_paths)} copias ({format_size(dup_bytes)})\n"
            )

        summary_lines.append(
            f"Total estimado: {format_size(total_bytes)}\n"
        )
        summary_lines.append(
            "Deseja realmente prosseguir com a exclusao definitiva?"
        )

        confirm = messagebox.askyesno(
            "Confirmar Autorizacao de Limpeza",
            "\n".join(summary_lines),
            icon=messagebox.WARNING,
        )

        if not confirm:
            self.log_message("Operacao de limpeza cancelada pelo usuario.")
            return

        # Inicia a limpeza em background
        self.btn_execute.config(state=tk.DISABLED)
        self._set_menu_buttons_state(tk.DISABLED)
        self._scan_in_progress = True
        self.progress_bar.pack(side=tk.RIGHT, padx=15)
        self.progress_bar.start(10)
        self._update_status("Executando limpeza autorizada...")

        thread = threading.Thread(
            target=self._run_cleaning,
            args=(auth_temp, auth_recycle, auth_dup),
            daemon=True,
        )
        thread.start()

    def _run_cleaning(self, auth_temp, auth_recycle, auth_dup):
        self._log_safe("--- INICIANDO EXECUCAO DA LIMPEZA AUTORIZADA ---")
        freed_total = 0

        try:
            # 1. Temporários
            if auth_temp and self.temp_data:
                self._log_safe("Iniciando limpeza de temporarios...")
                res_temp = Cleaner.clean_temp_files(
                    self.temp_data["items"], self._progress_cb
                )
                freed_total += res_temp["freed_bytes"]
                self._log_safe(
                    f"Temporarios limpos: {res_temp['deleted_count']} apagados "
                    f"({res_temp['freed_formatted']} liberados, "
                    f"{res_temp['skipped_count']} em uso preservados)."
                )

            # 2. Lixeira
            if auth_recycle and self.recycle_data:
                self._log_safe("Esvaziando Lixeira do Windows...")
                res_rec = Cleaner.empty_recycle_bin(self._progress_cb)
                if res_rec["success"]:
                    freed_total += self.recycle_data["total_size"]
                    self._log_safe(
                        f"Lixeira esvaziada com sucesso "
                        f"({self.recycle_data['total_size_formatted']} liberados)."
                    )
                else:
                    self._log_safe(
                        f"Aviso ao esvaziar lixeira: {res_rec['error']}"
                    )

            # 3. Duplicados
            if auth_dup and self.duplicate_data:
                dup_paths = list(self.selected_duplicate_paths)
                self._log_safe(
                    f"Iniciando exclusao de {len(dup_paths)} copias duplicadas..."
                )
                res_dup = Cleaner.delete_duplicate_copies(
                    dup_paths, self._progress_cb
                )
                freed_total += res_dup["freed_bytes"]
                self._log_safe(
                    f"Copias duplicadas excluidas: {res_dup['deleted_count']} "
                    f"removidas ({res_dup['freed_formatted']} liberados)."
                )
        except Exception:
            self._log_safe(f"ERRO na limpeza: {traceback.format_exc()}")

        self.after(0, self._cleaning_completed, freed_total)

    def _cleaning_completed(self, freed_total):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self._set_menu_buttons_state(tk.NORMAL)
        self._scan_in_progress = False
        self.status_label.config(
            text=f"Limpeza concluida com sucesso! "
                 f"{format_size(freed_total)} liberados."
        )

        self.log_message(
            f"--- LIMPEZA FINALIZADA COM SUCESSO: "
            f"{format_size(freed_total)} LIBERADOS NO TOTAL ---"
        )

        messagebox.showinfo(
            "Limpeza Concluida",
            f"A limpeza autorizada foi concluida com sucesso!\n\n"
            f"Espaco total liberado no disco: {format_size(freed_total)}\n\n"
            f"O relatorio completo pode ser visualizado na aba "
            f"'Historico / Logs'.",
        )

        # Reseta dados para forçar nova varredura com contadores atualizados
        self.temp_data = None
        self.recycle_data = None
        self.duplicate_data = None
        self.selected_duplicate_paths.clear()
        self.auth_temp_var.set(False)
        self.auth_recycle_var.set(False)
        self.auth_duplicates_var.set(False)
        self.chk_temp.config(state=tk.DISABLED)
        self.chk_recycle.config(state=tk.DISABLED)
        self.chk_dup.config(state=tk.DISABLED)
        self.btn_execute.config(state=tk.DISABLED)
        self.lbl_recycle_stat.config(text="Execute nova varredura para atualizar.")
        self.lbl_temp_stat.config(text="Execute nova varredura para atualizar.")
        self.lbl_dup_stat.config(text="Execute nova varredura para atualizar.")
        self.lbl_total_space.config(
            text="Espaco Total Recuperavel: 0 B", fg="#0f172a"
        )


def start_gui():
    app = CleanerApp()
    app.mainloop()


if __name__ == "__main__":
    start_gui()
