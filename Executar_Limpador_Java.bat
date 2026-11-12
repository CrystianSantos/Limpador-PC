@echo off
setlocal
cd /d "%~dp0"

set "JAR=target\limpador-pc-1.0.0.jar"

where java >nul 2>nul
if errorlevel 1 (
    echo Java nao foi encontrado no PATH. Instale o JDK 21 e abra este launcher novamente.
    pause
    exit /b 1
)

if not exist "%JAR%" (
    echo JAR nao encontrado. Compilando o projeto...
    where mvn >nul 2>nul
    if errorlevel 1 (
        echo Maven nao foi encontrado no PATH. Instale o Maven e abra este launcher novamente.
        pause
        exit /b 1
    )
    call mvn clean package -DskipTests
    if errorlevel 1 (
        echo Falha ao compilar. Leia a mensagem acima para ver o erro.
        pause
        exit /b 1
    )
)

echo Iniciando Limpador-PC Pro...
start "Limpador-PC Pro" cmd /k java -jar "%JAR%"

echo Aguardando o servidor local iniciar...
for /L %%i in (1,1,30) do (
    curl.exe --silent --fail http://127.0.0.1:8080/ >nul 2>nul
    if not errorlevel 1 goto open_browser
    timeout /t 1 /nobreak >nul
)

echo O servidor nao respondeu em 30 segundos. Verifique a janela do Limpador-PC Pro.
pause
exit /b 1

:open_browser
start "" "http://127.0.0.1:8080/"
exit /b 0
