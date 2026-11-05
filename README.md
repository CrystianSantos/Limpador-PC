# 🧹 Limpador-PC Pro | Multiplatform Cleaner & Optimizer

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue?style=for-the-badge&logo=windows&logoColor=white" alt="Platforms" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-green?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Build-PyInstaller%20Standalone-purple?style=for-the-badge" alt="Build" />
  <img src="https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-orange?style=for-the-badge&logo=githubactions&logoColor=white" alt="GitHub Actions" />
</p>

Uma ferramenta moderna, transparente e **multiplataforma (Windows, macOS e Linux)** para varredura e limpeza segura de arquivos temporários, lixeira e cópias duplicadas com verificação criptográfica **SHA-256**, interface moderna e **sistema de auto-atualização direta pelo GitHub**.

---

## ✨ Principais Diferenciais

1. **🖥️ Multiplataforma Real (Windows, macOS e Linux)**:
   - **Windows**: Varre `%TEMP%`, `C:\Windows\Temp`, `CrashDumps` e Lixeira nativa via Shell32 / PowerShell.
   - **macOS**: Varre `$TMPDIR`, `~/Library/Caches`, `/tmp` e a lixeira `~/.Trash` (via AppleScript Finder).
   - **Linux**: Varre `/tmp`, `/var/tmp`, `~/.cache` e Lixeira padrão FreeDesktop (`~/.local/share/Trash`).

2. **🎨 Nova Interface Visual Moderna**:
   - Desenvolvida com design moderno (Glassmorphism, Dark Theme, visual limpo estilo SaaS/Linear/CleanMyMac).
   - Abre como uma **janela de aplicativo desktop nativa** (sem barra de URL do navegador ou abas).
   - Gráficos em tempo real, tabelas pesquisáveis e painel de autorização prévia.

3. **🛡️ 100% Seguro e Transparente**:
   - **Nenhum arquivo é apagado sem sua autorização explícita**.
   - Arquivos atualmente em uso por navegadores ou programas abertos são **ignorados e preservados automaticamente**.
   - Na detecção de duplicados, o arquivo **original mais antigo é protegido**, permitindo escolher quais cópias excluir.

4. **🔄 Sistema de Auto-Atualização via GitHub (Branch `main`)**:
   - Conta com botão integrado na interface para verificar novos commits no seu repositório GitHub.
   - Toda vez que você fizer `git push` para a `main`, quem estiver usando o app clica em **"Verificar Atualizações"** e instala a versão mais recente em 1 clique, sem perder configurações locais!

5. **📦 Executável Standalone Único (`.exe` no Windows / Binário no Linux e Mac)**:
   - Não requer que o usuário final instale Python ou dependências.
   - Inclui GitHub Actions pronto (`.github/workflows/build.yml`) que compila automaticamente os executáveis para Windows, Mac e Linux em cada Release!

---

## 🚀 Como Executar

### Opção 1: Pelo Executável Standalone (Recomendado para usuários)
Basta dar **duplo clique** no arquivo compilado:
👉 **`Limpador-PC.exe`** (disponível na pasta `dist/` ou na Área de Trabalho).

### Opção 2: Pelo Código-Fonte em Qualquer Sistema (Windows, Mac ou Linux)
```bash
# Clone o repositório
git clone https://github.com/SEU-USUARIO/Limpador-PC.git
cd Limpador-PC

# Execute diretamente (zero dependências obrigatórias!)
python main.py
```

### Outros Modos de Inicialização:
* `python main.py` -> Abre a interface visual desktop moderna.
* `python main.py --cli` -> Abre o modo interativo pelo terminal (console wizard).
* `python main.py --tkinter` -> Abre a interface clássica em Tkinter.

---

## 🛠️ Como Publicar no Seu GitHub

Para publicar este projeto no seu GitHub pessoal e habilitar as atualizações automáticas:

1. **Crie um repositório vazio no GitHub**:
   - Acesse [github.com/new](https://github.com/new).
   - Nomeie como `Limpador-PC` (público).

2. **Inicie o Git e faça o primeiro envio**:
   ```bash
   cd C:\Users\crystian\Desktop\Limpador_PC
   git init
   git add .
   git commit -m "feat: versão inicial multiplataforma v1.0.0"
   git branch -M main
   git remote add origin https://github.com/SEU-USUARIO/Limpador-PC.git
   git push -u origin main
   ```

3. **Configure seu repositório no aplicativo**:
   - No app, vá na aba **"Atualizações GitHub"** e digite `SEU-USUARIO/Limpador-PC`.
   - Pronto! Qualquer commit enviado para a `main` poderá ser instalado pelos usuários clicando em **"Verificar Atualizações"** -> **"Baixar e Instalar"**!

---

## 🔨 Como Compilar o Executável Localmente

Se você fizer alterações no código e quiser gerar um novo `.exe` standalone:

```bash
# Instale o PyInstaller (caso ainda não tenha)
pip install pyinstaller

# Execute o script de compilação automática
python build_executable.py
```
O arquivo final compilado estará na pasta `dist/Limpador-PC.exe`.

---

## 📁 Estrutura de Arquivos

```text
├── .github/workflows/
│   └── build.yml               # CI/CD automático para Windows, Mac e Linux
├── web/
│   └── index.html              # Interface moderna Glassmorphism Desktop
├── platform_utils.py           # Abstração de SO (Windows, macOS, Linux)
├── scanner.py                  # Varredura inteligente (Temp, Lixeira, Duplicados)
├── cleaner.py                  # Exclusão segura com preservação de arquivos em uso
├── updater.py                  # Motor de auto-atualização via GitHub API
├── web_server.py               # Servidor e API REST local nativa
├── app_launcher.py             # Inicializador da janela de aplicativo desktop
├── main.py                     # Ponto de entrada com seleção de modos
├── build_executable.py         # Script de compilação PyInstaller
├── version.json                # Metadados e controle de versão do GitHub
├── requirements.txt            # Dependências opcionais de desenvolvimento
└── README.md                   # Documentação completa
```

---

## 📄 Licença
Distribuído sob a licença MIT. Livre para uso pessoal, modificação e distribuição.
