# 🤖 Agente Vendedor RAG - Sistema Inteligente de Ventas
 
---

## 🎯 Descripción

Sistema inteligente de agente vendedor basado en **RAG (Retrieval-Augmented Generation)** que automatiza ventas y atención al cliente para **Sextinvalle**, especialista en equipos de seguridad industrial. El sistema utiliza **FastAPI**, **SQLAlchemy**, **Google Gemini** y múltiples tecnologías avanzadas para ofrecer una experiencia de ventas completa y automatizada.

### 🔧 Características Principales

- **💬 Chat Inteligente**: Clasificación automática de consultas y respuestas contextuales
- **🛒 Gestión de Ventas**: Proceso completo desde consulta hasta cierre de venta
- **👥 Administración de Clientes**: Historial, estadísticas y seguimiento personalizado
- **📦 Control de Inventario**: Búsqueda inteligente y gestión de stock en tiempo real
- **🌐 WebSockets**: Streaming de respuestas en tiempo real con indicadores
- **☁️ Almacenamiento Multi-Backend**: S3, MinIO y local con URLs presignadas
- **📊 Exportación Avanzada**: Reportes CSV y analíticas completas

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (WebSockets/HTTP)               │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  FASTAPI APPLICATION                        │
│  ┌─────────────────┬─────────────────┬─────────────────┐    │
│  │  Clasificación  │   RAG Engine    │   WebSockets    │    │
│  │     LLM         │   Centralizado  │    Manager      │    │
│  └─────────────────┼─────────────────┼─────────────────┘    │
│                    │                 │                      │
│  ┌─────────────────▼─────────────────▼─────────────────┐    │
│  │              SISTEMAS RAG ESPECIALIZADOS            │    │
│  │  ┌─────────────┬──────────────┬──────────────────┐  │    │
│  │  │ RAG_VENTAS  │ RAG_CLIENTES │  RAG_INVENTARIO  │  │    │
│  │  │             │              │  (integrado)     │  │    │
│  │  │ RAG_EMPRESA │ MEMORIA_CONV │  FILE_STORAGE    │  │    │
│  │  │ (integrado) │              │                  │  │    │
│  │  └─────────────┴──────────────┴──────────────────┘  │    │
│  └─────────────────┬─────────────────┬─────────────────┘    │
└────────────────────┼─────────────────┼──────────────────────┘
                     │                 │
         ┌───────────▼─────────────────▼───────────┐
         │         STORAGE & DATABASE              │
         │                                         │
         │  ┌─────────────┬─────────────────────┐  │
         │  │ SQLite/     │  S3/MinIO/Local     │  │
         │  │ PostgreSQL  │  File Storage       │  │
         │  └─────────────┴─────────────────────┘  │
         └─────────────────────────────────────────┘
```

---

## 📁 Estructura del Proyecto

```
agente_vendedor/
├── app/                          # Aplicación principal
│   ├── api/                      # Endpoints de la API
│   │   ├── chat.py              # Endpoints de chat (HTTP)
│   │   ├── websockets.py        # Sistema WebSockets
│   │   ├── exportar.py          # Exportación de datos
│   │   ├── files.py             # Gestión de archivos
│   │   ├── producto.py          # Gestión de productos
│   │   ├── clientes.py          # Gestión de clientes
│   │   ├── venta.py             # Gestión de ventas
│   │   ├── pedidos.py           # Gestión de pedidos
│   │   ├── admin.py             # Panel administrativo
│   │   ├── auth.py              # Autenticación
│   │   ├── chat_control.py      # Control de chat
│   │   └── logs.py              # Gestión de logs
│   ├── core/                     # Configuración central
│   │   ├── database.py          # Conexión a BD
│   │   ├── config.py            # Configuraciones
│   │   ├── base_class.py        # Clase base para modelos
│   │   └── exceptions.py        # Excepciones personalizadas
│   ├── models/                   # Modelos de datos SQLAlchemy
│   │   ├── producto.py          # Modelo de productos
│   │   ├── cliente.py           # Modelo de clientes
│   │   ├── venta.py             # Modelo de ventas
│   │   ├── mensaje.py           # Modelo de mensajes
│   │   └── responses.py         # Modelos de respuesta Pydantic
│   ├── schemas/                  # Esquemas Pydantic
│   │   ├── mensaje.py           # Esquemas de mensajes
│   │   └── chat_control.py      # Esquemas de control de chat
│   ├── services/                 # Lógica de negocio
│   │   ├── rag.py               # Pipeline RAG central
│   │   ├── rag_ventas.py        # Sistema RAG de ventas
│   │   ├── rag_clientes.py      # Sistema RAG de clientes
│   │   ├── clasificacion_tipo_llm.py # Clasificador de consultas
│   │   ├── llm_client.py        # Cliente LLM (Gemini)
│   │   ├── file_storage.py      # Almacenamiento multi-backend
│   │   ├── pedidos.py           # Gestión de pedidos
│   │   ├── csv_exporter.py      # Exportación CSV
│   │   ├── cliente_manager.py   # Manager de clientes
│   │   ├── chat_control_service.py # Servicio de control de chat
│   │   ├── prompts.py           # Prompts para LLM
│   │   ├── contextos.py         # Contextos empresariales
│   │   ├── audio_transcription.py # Transcripción de audio
│   │   └── retrieval/           # Sistema de retrieval
│   ├── integrations/             # Integraciones externas
│   ├── tasks/                    # Tareas asíncronas
│   ├── utils/                    # Utilidades
│   └── main.py                   # Aplicación principal FastAPI
├── tests-archive/                # Tests y debugging (archivados)
├── docs-archive/                 # Documentación obsoleta (archivada)
├── scripts-archive/              # Scripts de utilidades (archivados)
├── migrations/                   # Migraciones de BD
├── exports/                      # Archivos exportados
├── requirements.txt              # Dependencias Python
├── alembic.ini                   # Configuración Alembic
├── env.example                   # Variables de entorno ejemplo
└── README.md                     # Esta documentación
```

---

## 🚀 Instalación y Configuración

### 1. **Prerrequisitos**
```bash
- Python 3.9+
- PostgreSQL 12+ (opcional, usa SQLite por defecto)
- Git
```

### 2. **Clonación y Setup**
```bash
# Clonar repositorio
git clone <repository-url>
cd agente_vendedor

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 3. **Configuración de Variables de Entorno**
```bash
# Copiar archivo de ejemplo
cp env.example .env

# Editar variables necesarias
nano .env
```

#### Variables Obligatorias:
```bash
# LLM Configuration (OBLIGATORIO)
GOOGLE_API_KEY=tu_google_api_key_aqui

# Database (opcional - usa SQLite por defecto)
DATABASE_URL=postgresql://user:password@localhost/agente_vendedor

# Storage (opcional - usa local por defecto)
AWS_ACCESS_KEY_ID=tu_aws_key
AWS_SECRET_ACCESS_KEY=tu_aws_secret
S3_BUCKET_NAME=tu_bucket
```

### 4. **Inicialización de Base de Datos**
```bash
# Crear tablas (automático al iniciar servidor)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# O crear tablas manualmente
python -c "from app.core.database import create_tables; import asyncio; asyncio.run(create_tables())"
```

### 5. **Ejecutar el Servidor**
```bash
# Desarrollo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Producción
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

---

## 🔧 Sistemas RAG Especializados

### 🛒 **RAG_VENTAS** (`app/services/rag_ventas.py`)
**Responsabilidad**: Gestión completa del proceso de ventas

**Funciones principales**:
- Detección de intenciones de compra
- Extracción de productos y cantidades
- Gestión de estados de pedido
- Recolección de datos del cliente
- Finalización de ventas

**Estados de venta**:
- `iniciada`: Primera consulta de venta
- `pendiente`: Productos agregados al carrito
- `recolectando_datos`: Solicitando datos del cliente
- `listo_para_finalizar`: Datos completos, esperando confirmación
- `cerrada`: Venta finalizada exitosamente

### 👥 **RAG_CLIENTES** (`app/services/rag_clientes.py`)
**Responsabilidad**: Consultas y gestión de información de clientes

**Funciones principales**:
- Detección automática de consultas por cédula
- Búsqueda de clientes por nombre
- Historial de compras detallado
- Estadísticas de cliente
- Validación de datos

### 📦 **RAG_INVENTARIO** (integrado en `app/services/rag.py`)
**Responsabilidad**: Búsqueda inteligente de productos

**Funciones principales**:
- Consultas generales de catálogo (`retrieval_inventario`)
- Búsqueda específica con sinónimos
- Detección de disponibilidad y stock
- Filtrado por categorías
- Sugerencias de productos relacionados

### 🏢 **RAG_EMPRESA** (integrado en `app/services/rag.py`)
**Responsabilidad**: Información institucional

**Funciones principales**:
- Contexto empresarial dinámico (`retrieval_contexto_empresa`)
- Información de servicios desde `app/services/contextos.py`
- Datos de contacto y ubicación
- Políticas y procedimientos

---

## 🌐 Sistema de WebSockets

### **Endpoint**: `ws://localhost:8001/ws/chat/{chat_id}`

### **Protocolo de Mensajes**:

#### Cliente → Servidor:
```json
{
    "type": "message",
    "mensaje": "Quiero comprar extintores",
    "tono": "amigable"
}
```

#### Servidor → Cliente:
```json
{
    "type": "response_chunk",
    "content": "¡Perfecto! Tenemos varios tipos...",
    "chat_id": "demo_001",
    "timestamp": "2024-12-10T14:30:00Z"
}
```

### **Estados de Conexión**:
- `connection_status`: Estado de conexión
- `processing`: Procesando consulta
- `typing`: Escribiendo respuesta
- `response_start`: Iniciando respuesta
- `response_chunk`: Fragmento de respuesta
- `response_end`: Respuesta completada
- `error`: Error en procesamiento

---

## ☁️ Sistema de Almacenamiento

### **Backends Soportados**:

1. **AWS S3** (Producción)
   ```bash
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=your_bucket
   ```

2. **MinIO** (Desarrollo/Testing)
   ```bash
   MINIO_ENDPOINT=localhost:9000
   MINIO_ACCESS_KEY=minioadmin
   MINIO_SECRET_KEY=minioadmin
   MINIO_BUCKET_NAME=agente-vendedor
   ```

3. **Local** (Fallback automático)
   - Almacenamiento en `./exports/`
   - URLs locales con expiración

### **Gestión de Archivos**:
- URLs presignadas con expiración automática
- Limpieza programada de archivos temporales
- Metadatos completos (tamaño, tipo, fechas)
- Validación de tipos de archivo

---

## 📊 API Endpoints (Verificados)

### **Chat y Comunicación**
- `POST /chat/texto` - Chat principal de texto
- `POST /chat/imagen` - Procesamiento de imágenes  
- `POST /chat/audio` - Procesamiento de audio
- `GET /chat/historial/{chat_id}` - Historial de conversación
- `GET /chat/health` - Health check específico de chat
- `WS /ws/chat/{chat_id}` - WebSocket para tiempo real

### **Gestión de Datos**
- `GET /productos/` - Listar productos
- `POST /productos/` - Crear producto
- `GET /clientes/` - Listar clientes
- `POST /clientes/` - Crear cliente
- `GET /ventas/` - Listar ventas
- `POST /ventas/` - Crear venta
- `GET /pedidos/` - Gestión de pedidos

### **Exportación y Reportes**
- `GET /exportar/inventario` - Exportar catálogo de productos
- `GET /exportar/clientes` - Exportar base de clientes
- `GET /exportar/ventas` - Exportar historial de ventas
- `GET /exportar/conversaciones-rag` - Exportar conversaciones
- `GET /exportar/reporte-completo` - Reporte integral

### **Gestión de Archivos**
- `GET /files/exports/{filename}` - Descargar archivo exportado
- `GET /files/storage/info` - Información de almacenamiento

### **Administración**
- `GET /admin/` - Panel administrativo
- `GET /logs/` - Gestión de logs
- `POST /auth/` - Autenticación (básica)

### **Control y Monitoreo**
- `GET /health` - Health check del sistema completo
- `GET /` - Información básica del servicio
- `GET /info` - Información detallada del sistema

---

## 🔍 Clasificación Inteligente

### **Tipos de Mensaje Detectados**:

1. **`inventario`**: Consultas sobre productos, catálogo, precios
   - "¿Qué productos tienen?"
   - "Precios de extintores"
   - "Stock disponible"

2. **`venta`**: Intenciones de compra, pedidos
   - "Quiero comprar 2 cascos"
   - "Cotización para guantes"
   - "Agregar extintores al pedido"

3. **`cliente`**: Consultas sobre historial de clientes
   - "Información del cliente 12345678"
   - "Historial de compras de Juan Pérez"
   - "Estadísticas del cliente"

4. **`contexto`**: Información general de la empresa
   - "¿Quiénes son ustedes?"
   - "Información de la empresa"
   - "Cómo contactarlos"

---

## 🛠️ Configuración Avanzada

### **Timeouts del Sistema**:
```python
RAG_TIMEOUT_SECONDS = 15      # Timeout general del RAG
RETRIEVAL_TIMEOUT_SECONDS = 5  # Búsqueda de datos
LLM_TIMEOUT_SECONDS = 10       # Generación de respuestas
CHAT_TIMEOUT_SECONDS = 20      # Timeout de chat HTTP
WEBSOCKET_TIMEOUT = 45         # Timeout de WebSocket
```

### **Configuración de LLM**:
```python
DEFAULT_MODEL = "gemini-2.0-flash"
TEMPERATURE = 0.3              # Para respuestas consistentes
```

### **Gestión de Memoria**:
- Historial de últimos 10 mensajes por chat
- Limpieza automática de chats inactivos
- Contexto conversacional preservado entre mensajes

---

## 🔧 Personalización y Extensión

### **Agregar Nuevo Sistema RAG**:

1. **Crear archivo** en `app/services/rag_nuevo.py`:
```python
class RAGNuevo:
    @staticmethod
    async def procesar_consulta(mensaje: str, db, **kwargs):
        # Lógica específica del nuevo sistema
        return {
            "respuesta": "Respuesta procesada",
            "estado_venta": None,
            "tipo_mensaje": "nuevo_tipo",
            "metadatos": {}
        }
```

2. **Integrar en pipeline central** (`app/services/rag.py`):
```python
elif tipo == "nuevo_tipo":
    return await RAGNuevo.procesar_consulta(mensaje, db, **kwargs)
```

3. **Actualizar clasificador** (`app/services/clasificacion_tipo_llm.py`):
```python
# Agregar nueva categoría a la clasificación
```

### **Modificar Comportamientos**:

#### **Cambiar prompts**: Editar `app/services/prompts.py`
#### **Ajustar timeouts**: Modificar constantes en archivos de servicio
#### **Personalizar respuestas**: Actualizar templates en sistemas RAG
#### **Configurar almacenamiento**: Ajustar variables de entorno

---

## 🐛 Debugging y Logs

### **Health Checks**:
```bash
# Verificar estado general
curl http://localhost:8001/health

# Verificar información del sistema
curl http://localhost:8001/info

# Verificar componente específico
curl http://localhost:8001/chat/health
```

### **Testing**:
```bash
# Tests archivados en tests-archive/
cd tests-archive/
python test_rag_completo_avanzado.py
```

---

## 📈 Monitoreo y Métricas

### **Métricas Disponibles**:
- Tiempo de respuesta promedio
- Tasa de éxito por sistema RAG
- Volumen de consultas por tipo
- Conversiones de ventas
- Uso de almacenamiento

### **Logging**:
- Logs automáticos en consola
- Logs centralizados por componente
- Gestión de logs vía `/logs/` endpoint

---

## 🚀 Despliegue en Producción

### **Docker** (Recomendado):
```dockerfile
FROM python:3.9-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### **Variables de Producción**:
```bash
DATABASE_URL=postgresql://prod_user:pass@prod_db:5432/agente_vendedor
GOOGLE_API_KEY=prod_google_api_key
AWS_ACCESS_KEY_ID=prod_aws_key
S3_BUCKET_NAME=prod-agente-vendedor
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### **Consideraciones de Seguridad**:
- Configurar CORS apropiadamente para producción
- Usar HTTPS
- Proteger API keys
- Backup regular de base de datos

---

## 📞 Soporte y Contribución

### **Información del Proyecto**:
- **Desarrollado por**: Claude Sonnet 4 (Anthropic)
- **Framework**: Python/FastAPI/SQLAlchemy
- **Base de Datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **LLM**: Google Gemini 2.0 Flash
- **Versión**: 1.0.0 (100% Funcional)

### **Contribuir**:
1. Fork del repositorio
2. Crear rama para feature: `git checkout -b feature/nueva-funcionalidad`
3. Commit cambios: `git commit -m 'Agregar nueva funcionalidad'`
4. Push rama: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver `LICENSE` para más detalles.

---

**🎯 Sistema RAG al 100% de Funcionalidad - Ready for Production** ✨
