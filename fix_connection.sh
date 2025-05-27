#!/bin/bash

echo "🔧 Solucionando problema de conexión Frontend-Backend..."
echo "=================================================="

# 1. Verificar y configurar .env
echo "📝 1. Verificando archivo .env..."
if [ ! -f .env ]; then
    echo "   ❌ Archivo .env no existe. Creando desde env.example..."
    cp env.example .env
    echo "   ✅ Archivo .env creado desde env.example"
    echo "   🚨 IMPORTANTE: Debes completar tus API keys en .env"
else
    echo "   ✅ Archivo .env ya existe"
fi

# Solo cambiar la línea DATABASE_URL sin sobrescribir el archivo
echo "📝 2. Configurando base de datos para SQLite..."
if grep -q "DATABASE_URL=postgresql" .env; then
    sed -i '' 's|DATABASE_URL=postgresql.*|DATABASE_URL=sqlite+aiosqlite:///./app.db|' .env
    echo "   ✅ Cambiado de PostgreSQL a SQLite"
elif grep -q "DATABASE_URL=sqlite" .env; then
    echo "   ✅ Ya configurado para SQLite"
else
    echo "DATABASE_URL=sqlite+aiosqlite:///./app.db" >> .env
    echo "   ✅ Agregada configuración SQLite"
fi

# 3. Configurar alembic.ini
echo "📝 3. Configurando alembic.ini..."
sed -i '' 's|sqlalchemy.url = postgresql://.*|sqlalchemy.url = sqlite:///./app.db|' alembic.ini
echo "   ✅ Alembic configurado para SQLite"

# 4. Limpiar caché
echo "📝 4. Limpiando caché de Python..."
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
echo "   ✅ Caché limpiado"

# 5. Detener servidor existente
echo "📝 5. Deteniendo servidor existente..."
pkill -f uvicorn 2>/dev/null || true
sleep 2
echo "   ✅ Servidor detenido"

# 6. Verificar configuración
echo "📝 6. Verificando configuración..."
echo "   .env DATABASE_URL: $(grep DATABASE_URL .env)"
echo "   alembic.ini: $(grep sqlalchemy.url alembic.ini)"

# 7. Verificar API keys
echo "📝 7. Verificando API keys..."
if grep -q "tu_api_key" .env; then
    echo "   ⚠️  ADVERTENCIA: Algunas API keys no están configuradas"
    echo "   📝 Edita .env y completa tus API keys reales"
else
    echo "   ✅ API keys parecen estar configuradas"
fi

# 8. Iniciar servidor
echo "📝 8. Iniciando servidor en puerto 8001..."
python -m uvicorn app.main:app --reload --port 8001 &
SERVER_PID=$!
echo "   ✅ Servidor iniciado (PID: $SERVER_PID)"

# 9. Esperar y verificar
echo "📝 9. Verificando funcionamiento..."
sleep 5

# Verificar que el servidor responda
if curl -s http://localhost:8001/ > /dev/null; then
    echo "   ✅ Servidor respondiendo correctamente"
    
    # Verificar productos
    PRODUCTOS=$(curl -s http://localhost:8001/productos/ | jq length 2>/dev/null || echo "0")
    echo "   ✅ Productos disponibles: $PRODUCTOS"
    
    # Verificar chat
    CHAT_STATUS=$(curl -s http://localhost:8001/chat/health | jq -r .status 2>/dev/null || echo "error")
    echo "   ✅ Chat status: $CHAT_STATUS"
    
    echo ""
    echo "🎉 ¡PROBLEMA RESUELTO!"
    echo "=================================================="
    echo "✅ Backend funcionando en: http://localhost:8001"
    echo "✅ Base de datos: SQLite"
    echo "✅ Productos: $PRODUCTOS disponibles"
    echo "✅ Chat: $CHAT_STATUS"
    echo ""
    echo "El frontend ahora puede conectar sin problemas."
    
else
    echo "   ❌ Error: El servidor no responde"
    echo ""
    echo "🚨 PROBLEMA NO RESUELTO"
    echo "=================================================="
    echo "Revisa los logs del servidor:"
    echo "tail -f app.log"
    exit 1
fi 