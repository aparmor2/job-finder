@echo off
rem Abre un navegador propio de Job Finder (perfil data\sesion-brave, con sus sesiones guardadas) en modo controlable por Claude.
rem Usa Brave si esta instalado; si no, Chrome; si no, Edge.
set "PERFIL=%~dp0data\sesion-brave"
set "NAV="
for %%N in (
  "%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"
  "%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"
  "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
  "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
  "%LocalAppData%\Google\Chrome\Application\chrome.exe"
  "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
) do if not defined NAV if exist %%N set "NAV=%%~N"
if not defined NAV (
  echo No encuentro Brave, Chrome ni Edge. Instala uno o edita la ruta en este archivo.
  pause
  exit /b 1
)
start "" "%NAV%" --user-data-dir="%PERFIL%" --remote-debugging-port=9223 --no-first-run --no-default-browser-check "https://www.tecnoempleo.com/"
