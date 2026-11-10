@echo off
rem Conecta tu Gmail (solo lectura) para que el dashboard lea las respuestas de las empresas.
cd /d "%~dp0"
python -m jobfinder.mail --configurar
pause
