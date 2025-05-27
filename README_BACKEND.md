# 🤖 Agente Vendedor - Backend API

Backend completo para chatbot vendedor conversacional con RAG, memoria y procesamiento multimodal.

## 🚀 **Características Principales**

### ✅ **Completamente Funcional**
- **💬 Chat de texto**: Conversación inteligente con memoria
- **🧠 RAG (Retrieval-Augmented Generation)**: Búsqueda semántica en inventario
- **📚 Memoria conversacional**: Historial completo de conversaciones
- **💰 Sistema de ventas**: Gestión completa de pedidos y ventas
- **📦 Inventario dinámico**: Stock actualizado automáticamente
- **🖼️ Procesamiento de imágenes**: Análisis con Gemini Vision
- **🎵 Transcripción de audio**: Whisper de OpenAI
- **📊 Dashboard de administración**: Métricas y estadísticas completas
- **👥 Sistema de clientes**: Gestión completa con historial de compras y RAG especializado
- **📊 Exportación CSV**: Descarga completa de datos con filtros avanzados

### 🔧 **Arquitectura**
- **FastAPI**: Framework web moderno y rápido
- **SQLAlchemy**: ORM asíncrono para base de datos
- **PostgreSQL**: Base de datos principal
- **FAISS**: Búsqueda vectorial para RAG
- **Gemini**: LLM principal para conversaciones
- **OpenAI Whisper**: Transcripción de audio

## 📋 **Endpoints Disponibles**

### 💬 **Chat**
- `POST /chat/texto` - Chat de texto principal
- `POST /chat/imagen` - Procesamiento de imágenes
- `POST /chat/audio` - Transcripción y procesamiento de audio
- `GET /chat/historial/{chat_id}` - Historial de conversación
- `GET /chat/health` - Health check del servicio

### 📊 **Administración**
- `GET /admin/dashboard/ventas` - Dashboard principal de ventas
- `GET /admin/ventas` - Lista de ventas con filtros
- `GET /admin/conversaciones` - Lista de conversaciones activas
- `GET /admin/inventario` - Estado del inventario
- `GET /admin/estadisticas` - Estadísticas generales del sistema

### 📦 **Productos y Ventas**
- `GET /productos/` - Lista de productos
- `GET /ventas/` - Lista de ventas
- `GET /pedidos/` - Gestión de pedidos

### 👥 **Clientes**
- `GET /clientes/` - Lista de clientes con búsqueda
- `GET /clientes/{cedula}` - Información detallada del cliente
- `GET /clientes/{cedula}/historial` - Historial de compras
- `GET /clientes/{cedula}/estadisticas` - Estadísticas del cliente
- `GET /clientes/top/compradores` - Top clientes por valor
- `POST /clientes/{cedula}/consulta` - Consulta RAG sobre historial
- `POST /clientes/buscar` - Búsqueda avanzada de clientes

### 📊 **Exportación CSV** (NUEVO)
- `GET /exportar/inventario` - Exportar inventario completo
- `GET /exportar/clientes` - Exportar base de clientes
- `GET /exportar/ventas` - Exportar ventas con detalles
- `GET /exportar/conversaciones-rag` - Exportar logs de conversaciones
- `GET /exportar/reporte-completo` - Reporte estadístico general
- `GET /exportar/info` - Información de datos disponibles

## 🛠️ **Instalación y Configuración**

### 1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd agente_vendedor
```

### 2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

### 3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

### 4. **Configurar variables de entorno**
Copia `env.example` a `.env` y configura:

```env
# API Keys (REQUERIDAS para funcionalidad completa)
GOOGLE_API_KEY=tu_api_key_de_gemini
OPENAI_API_KEY=tu_api_key_de_openai

# Base de datos
DATABASE_URL=postgresql+asyncpg://usuario:contraseña@localhost:5432/agente_vendedor

# Configuración del servidor
HOST=0.0.0.0
PORT=8001
```

### 5. **Configurar base de datos**
```bash
# Crear tablas
python create_tables.py

# Ejecutar migraciones (opcional)
alembic upgrade head
```

### 6. **Ejecutar servidor**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## 🧪 **Pruebas**

### **Prueba completa del backend**
```bash
python test_backend_completo.py
```

### **Pruebas individuales**
```bash
# Verificar que el servidor esté corriendo
curl http://localhost:8001/

# Probar chat de texto
curl -X POST "http://localhost:8001/chat/texto" \
  -H "Content-Type: application/json" \
  -d '{"mensaje": "Hola, ¿qué productos tienen?", "chat_id": "test"}'

# Probar dashboard de admin
curl http://localhost:8001/admin/dashboard/ventas
```

## 📊 **Funcionalidades del Sistema**

### 🧠 **Memoria y Contexto**
- **Memoria a corto plazo**: Últimos 10 mensajes de la conversación
- **Memoria a mediano plazo**: Estado del pedido actual y datos del cliente
- **Memoria a largo plazo**: Todo el historial almacenado en BD
- **Contexto del RAG**: Historial incluido en prompts del LLM

### 💰 **Sistema de Ventas**
- **Gestión de pedidos**: Creación, actualización y finalización
- **Recolección de datos**: Validación automática de datos del cliente
- **Inventario dinámico**: Descuento automático de stock
- **Estados de venta**: `iniciada`, `pendiente`, `recolectando_datos`, `cerrada`

### 🔍 **RAG (Retrieval-Augmented Generation)**
- **Búsqueda semántica**: FAISS para encontrar productos relevantes
- **Fallback inteligente**: Búsqueda por texto si no hay resultados semánticos
- **Anti-alucinación**: Solo productos del inventario real
- **Clasificación automática**: Intención del usuario (inventario/venta/contexto)

### 🖼️ **Procesamiento Multimodal**
- **Imágenes**: Análisis con Gemini Vision (requiere GOOGLE_API_KEY)
- **Audio**: Transcripción con Whisper (requiere OPENAI_API_KEY)
- **Validaciones**: Tipos de archivo, tamaños máximos
- **Fallbacks**: Respuestas útiles cuando APIs no están disponibles

## 📈 **Dashboard de Administración**

### **Métricas Disponibles**
- Total de ventas y ingresos
- Productos más vendidos
- Ventas por día
- Conversaciones activas
- Estado del inventario
- Productos con stock bajo

### **Filtros y Paginación**
- Filtros por fecha, estado, tipo
- Paginación en todas las listas
- Búsqueda y ordenamiento

## 🔧 **Configuración Avanzada**

### **Variables de Entorno Opcionales**
```env
# Configuración de LLM
DEFAULT_MODEL=gemini-2.0-flash
TEMPERATURE=0.7
TOP_K=3

# Configuración de RAG
MAX_CONTEXT_LENGTH=2000
MAX_HISTORY_LENGTH=5

# Configuración de logging
LOG_LEVEL=INFO
LOG_FILE=app.log
```

### **Personalización de Prompts**
Los prompts se pueden personalizar en `app/services/prompts.py`:
- `prompt_ventas()`: Para conversaciones de venta
- `prompt_empresa()`: Para información de la empresa
- `prompt_vision()`: Para análisis de imágenes

## 🚨 **Solución de Problemas**

### **Problemas Comunes**

1. **Error de conexión a BD**
   ```bash
   # Verificar que PostgreSQL esté corriendo
   pg_ctl status
   
   # Verificar conexión
   psql -h localhost -U usuario -d agente_vendedor
   ```

2. **APIs no funcionan**
   ```bash
   # Verificar variables de entorno
   echo $GOOGLE_API_KEY
   echo $OPENAI_API_KEY
   ```

3. **Dependencias faltantes**
   ```bash
   # Reinstalar dependencias
   pip install -r requirements.txt --force-reinstall
   ```

### **Logs y Debugging**
```bash
# Ver logs en tiempo real
tail -f app.log

# Verificar estado de servicios
curl http://localhost:8001/chat/health
curl http://localhost:8001/admin/health
```

## 📚 **Estructura del Proyecto**

```
app/
├── api/                 # Endpoints de la API
│   ├── chat.py         # Endpoints de chat
│   ├── admin.py        # Dashboard de administración
│   ├── producto.py     # Gestión de productos
│   └── venta.py        # Gestión de ventas
├── models/             # Modelos de base de datos
├── services/           # Lógica de negocio
│   ├── rag.py         # Sistema RAG principal
│   ├── pedidos.py     # Gestión de pedidos
│   ├── audio_transcription.py  # Transcripción de audio
│   └── prompts.py     # Prompts del sistema
└── core/              # Configuración central
    └── database.py    # Configuración de BD
```

## 🎯 **Estado del Proyecto**

### ✅ **Completado**
- [x] Chat de texto con memoria
- [x] Sistema RAG completo
- [x] Gestión de pedidos y ventas
- [x] Procesamiento de imágenes
- [x] Transcripción de audio
- [x] Dashboard de administración
- [x] Inventario dinámico
- [x] Validaciones y manejo de errores

### 🔄 **Listo para Producción**
El backend está completamente funcional y listo para:
- Integración con frontend
- Despliegue en producción
- Escalamiento horizontal
- Monitoreo y métricas

## 📞 **Soporte**

Para soporte técnico o preguntas sobre la implementación, consulta:
- Documentación de la API: `http://localhost:8001/docs`
- Logs del sistema: `app.log`
- Health checks: `/chat/health`, `/admin/health` 