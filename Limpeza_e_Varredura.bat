@echo off
chcp 65001 > nul
title Otimizador e Varredura de Arquivos
cd /d "%~dp0"

echo ===================================================
echo   Iniciando Limpeza e Varredura do Computador...
echo ===================================================

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Python nao foi encontrado no seu sistema.
    echo Por favor, instale o Python ou verifique se ele esta adicionado ao PATH.
    pause
    exit /b 1
)

python main.py
if %errorlevel% neq 0 (
    echo.
    echo A interface visual foi fechada ou encontrou uma excessao.
    echo Tentando iniciar no modo interativo via Prompt de Comando...
    python main.py --cli
    pause
)
