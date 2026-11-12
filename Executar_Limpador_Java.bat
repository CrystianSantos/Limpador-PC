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

echo Iniciando Limpador-PC Pro. Mantenha esta janela aberta enquanto usar o aplicativo.
java -jar "%JAR%"
if errorlevel 1 (
    echo O Limpador-PC Pro foi encerrado com erro. Consulte a mensagem acima.
)
pause
