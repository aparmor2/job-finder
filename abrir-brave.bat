@echo off
rem Abre el Brave propio de Job Finder (perfil data\sesion-brave, con sus sesiones guardadas) en modo controlable por Claude.
start "" "%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe" --user-data-dir="%~dp0data\sesion-brave" --remote-debugging-port=9223 --no-first-run --no-default-browser-check "https://www.tecnoempleo.com/"
