# 🧹 Limpador-PC Pro | Java Spring Boot Edition

<p align="center">
  <img src="https://img.shields.io/badge/Java-21%20LTS-orange?style=for-the-badge&logo=openjdk&logoColor=white" alt="Java 21" />
  <img src="https://img.shields.io/badge/Spring%20Boot-3.2%2B-green?style=for-the-badge&logo=springboot&logoColor=white" alt="Spring Boot" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue?style=for-the-badge&logo=windows&logoColor=white" alt="Platforms" />
  <img src="https://img.shields.io/badge/Security-Safe%20Buffer%20%26%20Lock%20Check-success?style=for-the-badge" alt="Security" />
</p>

Reimplementação completa do **Limpador-PC** em **Java 21 com Spring Boot 3**, projetado para máxima compatibilidade multiplataforma nativa (Windows, macOS e Linux), varredura inteligente de pastas temporárias ampliadas sem afetar programas em execução, detecção de duplicados criptográfica via **SHA-256** e auto-atualização contínua pelo GitHub.

---

## 🎯 Por que a versão em Java com Spring Boot?

1. **☕ Multiplataforma Nativa Real (Write Once, Run Anywhere)**:
   - Roda exatamente da mesma forma no **Windows**, **macOS** e **Linux** sem necessidade de compilação condicional ou bibliotecas nativas proprietárias.
2. **⚡ Arquitetura Spring Boot 3 Robusta**:
   - Backend desacoplado com serviços Spring (`@Service`), injeção de dependências e endpoints REST modernos (`@RestController`).
   - Interface integrada (HTML5, CSS3 Glassmorphism, Vanilla JS) servida pelo Tomcat embutido em uma porta local escolhida pelo sistema.
   - Abre automaticamente em uma janela de aplicativo ao iniciar (Chromium em modo aplicativo, quando disponível).
3. **🛡️ Varredura Ampliada e 100% Segura de Temporários**:
   - **Além do `%TEMP%`**, o sistema agora também analisa de forma segura:
     - 💥 **Relatórios de Falhas de Programas (CrashDumps)**: Arquivos de despejo de memória deixados por programas que já fecharam.
     - 🌐 **Cache de Rede do Windows (INetCache)**: Resíduos temporários de conexões antigas.
     - 📦 **Resíduos de Instaladores Antigos**: Pastas temporárias criadas por instaladores concluídos.
     - 🍎 **macOS**: `$TMPDIR`, `~/Library/Caches`, `~/Library/Logs`.
     - 🐧 **Linux**: `~/.cache`, `/tmp`, `/var/tmp`.
   - **Dupla Camada de Proteção Ativa**:
     - 🔒 **Detecção de Bloqueio**: Se qualquer arquivo estiver aberto ou bloqueado por um programa em execução (Word, Chrome, etc.), ele é **ignorado e preservado imediatamente**.
     - ⏱️ **Buffer de Idade Segura (Safe Age Buffer)**: Arquivos modificados nos últimos 5 minutos são poupados para garantir que instalações ou processos recentes não sejam interrompidos.
4. **👥 Detecção Criptográfica de Duplicados (SHA-256)**:
   - Triagem rápida por tamanho $\rightarrow$ Hash de cabeçalho de 8 KB $\rightarrow$ Confirmação bit a bit com hash SHA-256 nativo do Java (`MessageDigest`).
   - O arquivo original mais antigo é **automaticamente protegido** (Manter), listando apenas as cópias para remoção.
5. **🔄 Auto-Atualização Direta do GitHub (Branch `main`)**:
   - O serviço `GithubUpdateService` consulta a API do GitHub com Java `HttpClient`, avisa sobre novos commits na `main` e permite atualizar os arquivos da aplicação em 1 clique!

---

## 🚀 Como Executar

### Pré-requisitos
* Java JDK 17 ou superior (Recomendado: Java 21 LTS).

### No Windows:
Basta dar **duplo clique** no arquivo:
👉 **`Executar_Limpador_Java.bat`**

### No macOS / Linux:
```bash
chmod +x executar_limpador.sh
./executar_limpador.sh
```

### Via Maven:
```bash
mvn spring-boot:run
```

A janela do aplicativo abrirá automaticamente. O servidor escolhe uma porta local disponível e a encerra junto com o processo Java.

---

## 🔨 Como Compilar o Pacote Executável (`JAR`)

```bash
mvn clean package
```
O pacote executável será gerado em:
📁 `target/limpador-pc-1.0.0.jar`

Para rodar o JAR diretamente em qualquer sistema operacional:
```bash
java -jar target/limpador-pc-1.0.0.jar
```

---

## 🌐 Publicando no GitHub e CI/CD Automático

O projeto já inclui a automação configurada em `.github/workflows/build-java.yml`. Toda vez que você fizer `push` para a `main` no seu GitHub, o GitHub Actions:
1. Compila o projeto no **Windows, Ubuntu e macOS**.
2. Roda a suíte de testes automatizados com JUnit 5.
3. Disponibiliza os downloads dos pacotes executáveis para download na aba **Releases** do repositório!

```bash
git init
git add .
git commit -m "feat: migração completa para Java 21 com Spring Boot 3"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/Limpador-PC.git
git push -u origin main
```

---

## 📁 Estrutura do Projeto

```text
├── src/
│   ├── main/
│   │   ├── java/com/limpador/
│   │   │   ├── LimpadorApplication.java        # Entry point Spring Boot e Launcher Desktop
│   │   │   ├── controller/
│   │   │   │   ├── CleanerApiController.java    # REST API dos serviços de limpeza e varredura
│   │   │   │   └── WebViewController.java       # Roteamento da interface
│   │   │   ├── service/
│   │   │   │   ├── TempScannerService.java      # Varredura inteligente de %TEMP% e caches seguros
│   │   │   │   ├── TrashScannerService.java     # Esvaziamento de Lixeira Multiplataforma
│   │   │   │   ├── DuplicateScannerService.java # Algoritmo de duplicados SHA-256 em 3 fases
│   │   │   │   ├── CleanerService.java          # Exclusão segura com preservação de travamento
│   │   │   │   └── GithubUpdateService.java     # Motor de auto-atualização pelo GitHub
│   │   │   ├── model/                           # DTOs e entidades de transferência de dados
│   │   │   └── util/                            # Utilitários de SO e formatação de bytes
│   │   └── resources/
│   │       ├── application.properties           # Configurações do servidor Spring Boot
│   │       └── static/index.html                # Interface moderna Glassmorphism integrada
│   └── test/
│       └── java/com/limpador/                   # Testes unitários JUnit 5
├── .github/workflows/build-java.yml             # Workflow CI/CD multiplataforma
├── pom.xml                                      # Configuração Maven e dependências
├── Executar_Limpador_Java.bat                   # Launcher para Windows
└── executar_limpador.sh                         # Launcher para macOS / Linux
```

---

## 📄 Licença
Distribuído sob a licença MIT. Livre para uso pessoal, modificação e distribuição.
