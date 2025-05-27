@echo off

REM Script de inicio para el servidor backend en Windows
REM Siempre usa puerto 8001 para compatibilidad con frontend

echo 🚀 Iniciando Agente Vendedor Backend...
echo 📡 Puerto: 8001 (requerido por frontend)
echo 🔄 Modo: Desarrollo con auto-reload
echo.

REM Activar entorno virtual si existe
if exist "venv\Scripts\activate.bat" (
    echo 🐍 Activando entorno virtual...
    call venv\Scripts\activate.bat
)

REM Verificar que estamos en el directorio correcto
if not exist "app\main.py" (
    echo ❌ Error: No se encuentra app\main.py
    echo    Ejecuta este script desde el directorio raíz del proyecto
    pause
    exit /b 1
)

REM Iniciar servidor en puerto 8001
echo 🎯 Iniciando servidor en http://localhost:8001
python -m uvicorn app.main:app --reload --port 8001 --host 0.0.0.0

echo.
echo 👋 Servidor detenido
pause 