@echo off
rem Busca ofertas y revisa el correo sin abrir el panel (para el Programador de tareas).
cd /d "%~dp0"
python -m jobfinder --solo-buscar
