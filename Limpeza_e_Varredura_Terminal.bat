@echo off
chcp 65001 > nul
title Otimizador de Arquivos (Modo Interativo Terminal)
cd /d "%~dp0"

python main.py --cli
if %errorlevel% neq 0 (
    echo.
    echo Ocorreu um erro durante a execucao.
    pause
)
