@echo off
REM Activa el entorno virtual si existe en la carpeta muestra_sin_fallos\.venv
set VENV_PATH=.\Descarga_Todo\muestra_sin_fallos\.venv\Scripts\activate.bat
if exist "%VENV_PATH%" (
    echo Activando entorno virtual...
    call "%VENV_PATH%"
) else (
    echo Entorno virtual no encontrado, se usara el interprete global de python.
    echo Asegurate de tener las dependencias instaladas con 'pip install -r requirements.txt'
)

echo.
echo ==================================================
echo  Lanzando la aplicacion de Analisis de Partidos (Version DEFINITIVA)
echo ==================================================
echo.

REM Ejecuta el script final de Streamlit
py -m streamlit run streamlit_app_final.py

pause