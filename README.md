# 🤖 Agente Vendedor Inteligente

## 📋 Descripción

Sistema completo de agente vendedor inteligente con capacidades de RAG (Retrieval-Augmented Generation), gestión de clientes, procesamiento de pedidos y exportación de datos. El sistema utiliza IA para proporcionar respuestas contextuales sobre productos y gestionar el proceso de ventas de manera automatizada.

## 🚀 Características Principales

### 🧠 Sistema RAG Inteligente
- **RAG de Productos**: Búsqueda semántica en catálogo usando FAISS
- **RAG de Clientes**: Gestión inteligente de información de clientes
- **Embeddings Vectoriales**: Búsqueda por similitud usando Google Gemini embeddings
- **Respuestas Contextuales**: IA que comprende el contexto de ventas

### 👥 Gestión de Clientes
- **CRUD Completo**: Crear, leer, actualizar y eliminar clientes
- **Búsqueda Inteligente**: Búsqueda por nombre, email, teléfono, cédula
- **Historial de Compras**: Seguimiento completo de pedidos por cliente
- **Identificación por Cédula**: Sistema basado en cédula como identificador único

### 📦 Procesamiento de Pedidos
- **Creación Automática**: Procesamiento de pedidos desde conversaciones
- **Validación Inteligente**: Verificación de productos y cantidades
- **Cálculo Automático**: Totales y gestión de inventario
- **Estados de Pedido**: Seguimiento completo del ciclo de vida

### 📊 Exportación y Reportes
- **Exportación CSV**: Clientes, productos, pedidos
- **Reportes Personalizados**: Filtros por fecha, cliente, producto
- **Análisis de Ventas**: Métricas y estadísticas de rendimiento
- **Formatos Múltiples**: CSV con diferentes configuraciones

### 🎙️ Capacidades Multimodales
- **Chat de Texto**: Procesamiento de mensajes de texto
- **Procesamiento de Imágenes**: Análisis de imágenes con Google Gemini Vision
- **Transcripción de Audio**: Conversión de audio a texto usando OpenAI Whisper
- **Bot de Telegram**: Integración completa con Telegram

## 🏗️ Arquitectura del Sistema

```
agente_vendedor/
├── app/
│   ├── api/                    # Endpoints de la API
│   │   ├── auth.py            # Autenticación (básica)
│   │   ├── admin.py           # Administración del sistema
│   │   ├── chat.py            # Chat multimodal (texto, imagen, audio)
│   │   ├── clientes.py        # API de gestión de clientes
│   │   ├── exportar.py        # API de exportación de datos
│   │   ├── logs.py            # Logs y métricas del sistema
│   │   ├── pedidos.py         # API de gestión de pedidos
│   │   ├── producto.py        # API de gestión de productos
│   │   └── venta.py           # API de gestión de ventas
│   ├── core/                   # Configuración central
│   │   └── database.py        # Configuración de base de datos
│   ├── integrations/           # Integraciones externas
│   │   └── telegram_bot.py    # Bot de Telegram
│   ├── models/                 # Modelos de datos
│   │   ├── cliente.py         # Modelo de cliente
│   │   ├── mensaje.py         # Modelo de mensajes de chat
│   │   ├── producto.py        # Modelo de producto
│   │   ├── usuario.py         # Modelo de usuario
│   │   └── venta.py           # Modelo de venta/pedido
│   ├── schemas/                # Schemas de validación
│   │   ├── auth.py            # Schemas de autenticación
│   │   ├── mensaje.py         # Schemas de mensajes
│   │   ├── producto.py        # Schemas de productos
│   │   └── venta.py           # Schemas de ventas
│   ├── services/               # Lógica de negocio
│   │   ├── audio_transcription.py  # Transcripción de audio
│   │   ├── auth.py            # Servicios de autenticación
│   │   ├── clasificacion_tipo_llm.py  # Clasificación de mensajes
│   │   ├── cliente_manager.py # Gestión de clientes
│   │   ├── contextos.py       # Contextos de la empresa
│   │   ├── csv_exporter.py    # Exportación CSV
│   │   ├── llm.py             # Cliente LLM (Gemini)
│   │   ├── llm_client.py      # Cliente LLM principal
│   │   ├── pedidos.py         # Procesamiento de pedidos
│   │   ├── prompts.py         # Prompts de IA
│   │   ├── rag.py             # Sistema RAG principal
│   │   ├── rag_clientes.py    # RAG específico para clientes
│   │   └── retrieval/         # Sistema de búsqueda vectorial
│   │       ├── embeddings.py  # Generación de embeddings
│   │       ├── faiss_retriever.py  # Retriever FAISS
│   │       ├── pinecone_retriever.py  # Retriever Pinecone (placeholder)
│   │       └── retriever_factory.py  # Factory de retrievers
│   └── main.py                 # Aplicación principal FastAPI
├── migrations/                 # Migraciones de base de datos
├── tests/                      # Tests automatizados
├── scripts/                    # Scripts de utilidad
└── alembic/                    # Configuración de Alembic
```

## 🛠️ Tecnologías Utilizadas

### Backend
- **FastAPI**: Framework web moderno y rápido
- **SQLAlchemy**: ORM para base de datos
- **SQLite**: Base de datos ligera (desarrollo) / PostgreSQL (producción)
- **Alembic**: Migraciones de base de datos

### IA y Machine Learning
- **Google Gemini**: Modelo de lenguaje principal (gemini-2.0-flash)
- **Google Gemini Embeddings**: Vectorización de texto (text-embedding-004)
- **Google Gemini Vision**: Procesamiento de imágenes
- **FAISS**: Base de datos vectorial para búsqueda semántica
- **OpenAI Whisper**: Transcripción de audio (único uso de OpenAI)

### Integraciones
- **Telegram Bot API**: Bot de Telegram para atención 24/7
- **Python Telegram Bot**: Librería para integración con Telegram

### Utilidades
- **Pandas**: Manipulación de datos para exportaciones
- **Pydantic**: Validación de datos y schemas
- **Python-dotenv**: Gestión de variables de entorno
- **Uvicorn**: Servidor ASGI
- **Loguru**: Sistema de logging avanzado
- **Tenacity**: Reintentos automáticos
- **PyDub**: Procesamiento de audio (opcional)

## 📦 Instalación

### Prerrequisitos
- Python 3.9+
- pip
- Git
- API Key de Google Gemini
- Token de Bot de Telegram (opcional)
- API Key de OpenAI (solo para transcripción de audio)

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone https://github.com/Hacanaval/agente_vendedor_backend.git
cd agente_vendedor
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
```bash
cp env.example .env
# Editar .env con tus claves de API
```

Variables requeridas:
```env
# API Keys (Requeridas)
GOOGLE_API_KEY=tu_api_key_de_gemini

# Base de datos
DATABASE_URL=sqlite:///./app.db

# Telegram (Opcional)
TELEGRAM_TOKEN=tu_token_de_telegram
BOT_TOKEN_FIXED=tu_token_fijo_del_bot

# OpenAI (Solo para transcripción de audio)
OPENAI_API_KEY=tu_api_key_de_openai

# Configuración del servidor
BACKEND_URL=http://localhost:8001
HOST=0.0.0.0
PORT=8001
```

5. **Inicializar base de datos**
```bash
python create_tables.py
alembic upgrade head
```

6. **Ejecutar migraciones de clientes (opcional)**
```bash
python migrate_clientes.py
```

## 🚀 Uso

### Iniciar el Servidor
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Iniciar el Bot de Telegram (Opcional)
```bash
python app/integrations/telegram_bot.py
```

### Acceder a la Documentación
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

### Endpoints Principales

#### Chat Multimodal
- `POST /chat/texto` - Procesamiento de mensajes de texto
- `POST /chat/imagen` - Procesamiento de imágenes con Gemini Vision
- `POST /chat/audio` - Transcripción y procesamiento de audio
- `GET /chat/historial/{chat_id}` - Obtener historial de conversación

#### Gestión de Clientes
- `GET /clientes/` - Listar clientes con paginación
- `POST /clientes/` - Crear nuevo cliente
- `GET /clientes/{cedula}` - Obtener cliente por cédula
- `PUT /clientes/{cedula}` - Actualizar cliente
- `DELETE /clientes/{cedula}` - Eliminar cliente
- `GET /clientes/buscar` - Búsqueda inteligente de clientes

#### Gestión de Productos
- `GET /productos/productos` - Listar productos
- `POST /productos/productos` - Crear producto
- `GET /productos/productos/{id}` - Obtener producto
- `PUT /productos/productos/{id}` - Actualizar producto
- `DELETE /productos/productos/{id}` - Eliminar producto

#### Gestión de Pedidos y Ventas
- `GET /pedidos/` - Listar pedidos
- `POST /pedidos/` - Crear pedido
- `GET /pedidos/{id}` - Obtener pedido
- `PUT /pedidos/{id}/estado` - Actualizar estado
- `GET /venta/ventas` - Listar ventas
- `POST /venta/ventas` - Registrar venta

#### Exportación
- `GET /exportar/clientes` - Exportar clientes a CSV
- `GET /exportar/productos` - Exportar productos a CSV
- `GET /exportar/pedidos` - Exportar pedidos a CSV

#### Administración
- `GET /admin/estadisticas` - Estadísticas del sistema
- `GET /admin/productos/sincronizar` - Sincronizar índice de productos
- `GET /logs/metrics/uso` - Métricas de uso del sistema

## 🧪 Testing

### Ejecutar Tests
```bash
# Tests básicos del sistema RAG
python test_rag_simple.py

# Tests del sistema de clientes
python test_sistema_clientes.py

# Tests de exportación CSV
python test_exportacion_csv.py

# Test completo de integración
python test_crear_cliente_y_rag.py
```

### Generar Reportes
```bash
python reporte_estado_rag.py
```

## 📊 Funcionalidades Avanzadas

### Sistema RAG con FAISS
El sistema implementa búsqueda semántica usando:

1. **FAISS (Facebook AI Similarity Search)**: Base de datos vectorial principal
2. **Google Gemini Embeddings**: Generación de vectores semánticos
3. **Fallback a búsqueda por texto**: Si la búsqueda semántica no encuentra resultados relevantes

### Clasificación Automática de Mensajes
- **Inventario**: Consultas sobre productos y catálogo
- **Venta**: Intenciones de compra y pedidos
- **Contexto**: Información general de la empresa

### Gestión de Estados
- **Pedidos**: Pendiente → Procesando → Enviado → Entregado
- **Clientes**: Activo → Inactivo
- **Productos**: Disponible → Agotado → Descontinuado

### Capacidades Multimodales
- **Texto**: Procesamiento de consultas de texto
- **Imágenes**: Análisis con Gemini Vision
- **Audio**: Transcripción con OpenAI Whisper

## 🔧 Configuración Avanzada

### Variables de Entorno Completas
```env
# API Keys
GOOGLE_API_KEY=tu_api_key_de_gemini
OPENAI_API_KEY=tu_api_key_de_openai
TELEGRAM_TOKEN=tu_token_de_telegram
BOT_TOKEN_FIXED=tu_token_fijo_del_bot

# Base de datos
DATABASE_URL=sqlite:///./app.db

# Configuración del servidor
BACKEND_URL=http://localhost:8001
HOST=0.0.0.0
PORT=8001

# Configuración de logging
LOG_LEVEL=INFO
LOG_FILE=app.log

# Configuración de seguridad
SECRET_KEY=tu_clave_secreta_aqui
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Configuración de LLM
DEFAULT_MODEL=gemini-2.0-flash
EMBEDDING_MODEL=models/text-embedding-004
MAX_TOKENS=300
TEMPERATURE=0.2

# Configuración de RAG
MAX_CONTEXT_LENGTH=2000
MAX_HISTORY_LENGTH=5
TOP_K=3
RETRIEVER_BACKEND=faiss

# Configuración de Telegram
TELEGRAM_WEBHOOK_URL=https://tu-dominio.com/webhook
TELEGRAM_WEBHOOK_SECRET=tu_secreto_webhook

# Configuración de caché
CACHE_TTL=3600
MAX_CACHE_SIZE=1000
```

### Personalización de Prompts
Los prompts del sistema se pueden personalizar en `app/services/prompts.py`:

```python
# Prompt para ventas
SYSTEM_PROMPT_VENTAS = """
Eres un agente vendedor experto de Sextinvalle...
"""

# Prompt para clasificación
SYSTEM_PROMPT_CLASIFICACION = """
Clasifica el siguiente mensaje en una de estas categorías...
"""
```

## 📈 Métricas y Monitoreo

### Reportes Disponibles
- **Estado del Sistema RAG**: `STATUS_FINAL_RAG.md`
- **Sistema de Clientes**: `SISTEMA_CLIENTES.md`
- **Exportación CSV**: `SISTEMA_EXPORTACION_CSV.md`
- **Resumen de Exportación**: `RESUMEN_EXPORTACION_CSV.md`

### Logs y Debugging
El sistema incluye logging detallado para:
- Consultas RAG y clasificación de mensajes
- Operaciones de base de datos
- Exportaciones y reportes
- Errores y excepciones
- Interacciones con APIs externas

### Métricas del Sistema
- **Tiempo de respuesta RAG**: < 5 segundos promedio
- **Precisión de clasificación**: Monitoreada en logs
- **Uso de memoria**: Optimizado para FAISS
- **Throughput**: Requests por segundo

## 🤝 Contribución

### Guías de Desarrollo
1. Fork el repositorio
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Añadir nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

### Estándares de Código
- **PEP 8**: Estilo de código Python
- **Type Hints**: Tipado estático donde sea posible
- **Docstrings**: Documentación de funciones
- **Tests**: Cobertura mínima del 80%
- **Logging**: Uso de loguru para logging estructurado

## 📝 Changelog

### v2.0.0 (Actual)
- ✅ Sistema RAG con FAISS y Gemini embeddings
- ✅ Gestión completa de clientes con cédula como ID
- ✅ Exportación CSV avanzada con filtros
- ✅ API REST completa con 9 módulos
- ✅ Chat multimodal (texto, imagen, audio)
- ✅ Bot de Telegram integrado
- ✅ Tests automatizados y reportes de estado
- ✅ Documentación técnica completa

### v1.0.0
- ✅ Sistema RAG básico
- ✅ Procesamiento de pedidos
- ✅ API básica con FastAPI
- ✅ Base de datos SQLite

## 🐛 Problemas Conocidos

### Limitaciones Actuales
- **Base de datos**: SQLite para desarrollo (PostgreSQL recomendado para producción)
- **Autenticación**: Sistema básico (JWT completo en desarrollo)
- **Multi-empresa**: Preparado pero no activado
- **Exportación**: Solo CSV (Excel en roadmap)
- **Búsqueda vectorial**: Solo FAISS (Pinecone preparado)

### Roadmap v2.1.0
- [ ] Autenticación JWT completa
- [ ] Migración a PostgreSQL
- [ ] Dashboard web de administración
- [ ] Exportación a Excel
- [ ] Sistema de caché con Redis
- [ ] Health checks avanzados

## 📞 Soporte

### Documentación Adicional
- **Documentación Técnica**: `DOCUMENTACION_TECNICA.md`
- **Estado del Backend**: `ESTADO_BACKEND.md`
- **Changelog Completo**: `CHANGELOG.md`
- **Resumen de Release**: `RESUMEN_RELEASE_v2.0.0.md`

### Repositorio
- **GitHub**: https://github.com/Hacanaval/agente_vendedor_backend
- **Branch Principal**: main
- **Tag Actual**: v2.0.0

### Contacto
- **Issues**: GitHub Issues
- **Documentación**: Wiki del proyecto
- **Ejemplos**: Directorio `tests/`

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🙏 Agradecimientos

- Google por las APIs de Gemini (LLM, Vision, Embeddings)
- OpenAI por Whisper (transcripción de audio)
- Facebook por FAISS (búsqueda vectorial)
- FastAPI por el excelente framework
- La comunidad de Python por las librerías utilizadas

---

**Desarrollado con ❤️ para revolucionar las ventas con IA**
