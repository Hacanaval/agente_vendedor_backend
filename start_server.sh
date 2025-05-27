#!/bin/bash

# Script de inicio para el servidor backend
# Siempre usa puerto 8001 para compatibilidad con frontend

echo "🚀 Iniciando Agente Vendedor Backend..."
echo "📡 Puerto: 8001 (requerido por frontend)"
echo "🔄 Modo: Desarrollo con auto-reload"
echo ""

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo "🐍 Activando entorno virtual..."
    source venv/bin/activate
fi

# Verificar que estamos en el directorio correcto
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: No se encuentra app/main.py"
    echo "   Ejecuta este script desde el directorio raíz del proyecto"
    exit 1
fi

# Iniciar servidor en puerto 8001
echo "🎯 Iniciando servidor en http://localhost:8001"
python -m uvicorn app.main:app --reload --port 8001 --host 0.0.0.0

echo ""
echo "�� Servidor detenido" 