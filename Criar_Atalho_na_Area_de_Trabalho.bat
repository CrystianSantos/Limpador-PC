@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo Criando atalho na Area de Trabalho...

powershell -NoProfile -Command ^
  "$WshShell = New-Object -ComObject WScript.Shell; " ^
  "$Desktop = [Environment]::GetFolderPath('Desktop'); " ^
  "$Shortcut = $WshShell.CreateShortcut(\"$Desktop\Limpeza e Varredura.lnk\"); " ^
  "$Shortcut.TargetPath = (Resolve-Path '.\Limpeza_e_Varredura.bat').Path; " ^
  "$Shortcut.WorkingDirectory = (Resolve-Path '.').Path; " ^
  "$Shortcut.Description = 'Varredura de temporarios, lixeira e arquivos duplicados'; " ^
  "$Shortcut.IconLocation = 'shell32.dll,31'; " ^
  "$Shortcut.Save(); " ^
  "Write-Host 'Atalho criado com sucesso na Area de Trabalho!'"

pause
