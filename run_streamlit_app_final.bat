@echo off
setlocal

REM Ejecuta la versión Streamlit que replica Descarga_Todo
cd /d "%~dp0"

if not exist "%~dp0\streamlit_app_final.py" (
    echo [ERROR] No se encuentra streamlit_app_final.py en %~dp0
    goto :EOF
)

REM Usa el lanzador por defecto de Python instalado en Windows
py -m streamlit run streamlit_app_final.py

endlocal
