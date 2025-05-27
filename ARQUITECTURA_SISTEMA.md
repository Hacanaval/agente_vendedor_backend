# 🏗️ Arquitectura del Sistema - Agente Vendedor Sextinvalle

## 📋 Índice
1. [Visión General](#visión-general)
2. [Arquitectura de Alto Nivel](#arquitectura-de-alto-nivel)
3. [Componentes del Backend](#componentes-del-backend)
4. [Componentes del Frontend](#componentes-del-frontend)
5. [Base de Datos](#base-de-datos)
6. [Sistema RAG (Retrieval-Augmented Generation)](#sistema-rag)
7. [Integración con Telegram](#integración-con-telegram)
8. [Flujos de Datos](#flujos-de-datos)
9. [Seguridad](#seguridad)
10. [Escalabilidad](#escalabilidad)

## 🎯 Visión General

El **Agente Vendedor Sextinvalle** es un sistema de ventas inteligente que combina:
- **Backend API REST** (FastAPI + Python)
- **Frontend Web** (React + TypeScript)
- **Bot de Telegram** (python-telegram-bot)
- **Sistema RAG** (Retrieval-Augmented Generation)
- **Base de Datos** (SQLite con SQLAlchemy)
- **Integración LLM** (OpenAI GPT + Google Gemini)

## 🏛️ Arquitectura de Alto Nivel

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend Web  │    │  Bot Telegram   │    │   Usuarios      │
│   (React TS)    │    │   (Python)      │    │   Externos      │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ HTTP/REST            │ Webhook              │ API Calls
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend API (FastAPI)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Rutas     │  │ Middleware  │  │ Validación  │             │
│  │   API       │  │ CORS/Auth   │  │ Pydantic    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
          ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Sistema RAG │ │ Base Datos  │ │ Servicios   │
│ (LLM + Vec) │ │ (SQLite)    │ │ Externos    │
└─────────────┘ └─────────────┘ └─────────────┘
```

## 🔧 Componentes del Backend

### 📁 Estructura de Directorios
```
app/
├── main.py                 # Punto de entrada FastAPI
├── config.py              # Configuración global
├── database.py            # Configuración de BD
├── models/                # Modelos SQLAlchemy
│   ├── producto.py
│   ├── mensaje.py
│   ├── venta.py
│   └── cliente.py
├── schemas/               # Esquemas Pydantic
│   ├── producto.py
│   ├── mensaje.py
│   └── venta.py
├── api/                   # Endpoints REST
│   ├── productos.py
│   ├── mensajes.py
│   ├── ventas.py
│   └── clientes.py
├── services/              # Lógica de negocio
│   ├── rag.py            # Sistema RAG principal
│   ├── llm_client.py     # Cliente LLM
│   ├── pedidos.py        # Gestión de pedidos
│   ├── rag_clientes.py   # RAG para clientes
│   └── retrieval/        # Sistema de recuperación
├── integrations/         # Integraciones externas
│   └── telegram_bot.py   # Bot de Telegram
└── utils/                # Utilidades
    └── validators.py     # Validadores
```

### 🚀 Servicios Principales

#### 1. **Sistema RAG** (`app/services/rag.py`)
- **Función**: Procesamiento inteligente de consultas
- **Componentes**:
  - Retrieval de inventario
  - Retrieval de contexto empresarial
  - Generación de respuestas con LLM
  - Gestión de estado de ventas

#### 2. **Cliente LLM** (`app/services/llm_client.py`)
- **Modelos soportados**: OpenAI GPT, Google Gemini
- **Funciones**: Generación de respuestas, clasificación de mensajes

#### 3. **Gestión de Pedidos** (`app/services/pedidos.py`)
- **Funciones**:
  - Creación y gestión de pedidos
  - Recolección de datos del cliente
  - Validación de información
  - Finalización de ventas

#### 4. **Sistema de Recuperación** (`app/services/retrieval/`)
- **Retrievers disponibles**:
  - `FaissRetriever`: Búsqueda vectorial local
  - `PineconeRetriever`: Búsqueda vectorial en la nube
  - `SimpleRetriever`: Búsqueda básica por texto

## 🎨 Componentes del Frontend

### 📁 Estructura del Frontend
```
frontend/
├── src/
│   ├── components/        # Componentes React
│   │   ├── Chat/         # Interfaz de chat
│   │   ├── Products/     # Gestión de productos
│   │   ├── Sales/        # Gestión de ventas
│   │   └── Clients/      # Gestión de clientes
│   ├── services/         # Servicios API
│   │   └── api.ts        # Cliente HTTP
│   ├── types/            # Tipos TypeScript
│   ├── hooks/            # Hooks personalizados
│   └── utils/            # Utilidades
├── public/               # Archivos estáticos
└── package.json          # Dependencias
```

### 🔄 Funcionalidades Principales
1. **Chat Inteligente**: Interfaz conversacional con el agente
2. **Gestión de Productos**: CRUD completo de inventario
3. **Gestión de Ventas**: Seguimiento y exportación
4. **Gestión de Clientes**: Historial y estadísticas
5. **Dashboard**: Métricas y reportes

## 🗄️ Base de Datos

### 📊 Modelo de Datos
```sql
-- Productos
CREATE TABLE productos (
    id INTEGER PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10,2) NOT NULL,
    stock INTEGER DEFAULT 0,
    activo BOOLEAN DEFAULT TRUE,
    categoria VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Clientes
CREATE TABLE clientes (
    id INTEGER PRIMARY KEY,
    nombre_completo VARCHAR(255),
    cedula VARCHAR(20) UNIQUE,
    telefono VARCHAR(20),
    correo VARCHAR(255),
    direccion TEXT,
    barrio VARCHAR(100),
    indicaciones_adicionales TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Ventas
CREATE TABLE ventas (
    id INTEGER PRIMARY KEY,
    cliente_id INTEGER REFERENCES clientes(id),
    producto_id INTEGER REFERENCES productos(id),
    cantidad INTEGER NOT NULL,
    precio_unitario DECIMAL(10,2) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    estado VARCHAR(50) DEFAULT 'pendiente',
    chat_id VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Mensajes
CREATE TABLE mensajes (
    id INTEGER PRIMARY KEY,
    chat_id VARCHAR(100) NOT NULL,
    remitente VARCHAR(50) NOT NULL,
    mensaje TEXT NOT NULL,
    tipo_mensaje VARCHAR(50),
    estado_venta VARCHAR(50),
    metadatos JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🧠 Sistema RAG (Retrieval-Augmented Generation)

### 🔄 Flujo del Sistema RAG
```
Usuario Input → Clasificación → Retrieval → LLM → Respuesta
     ↓              ↓            ↓         ↓        ↓
  "Quiero        "venta"    Productos   GPT/     "Tenemos
   cascos"                 relevantes  Gemini   cascos..."
```

### 📚 Componentes RAG

#### 1. **Clasificación de Mensajes**
- **Tipos**: `venta`, `inventario`, `contexto`, `cliente`
- **Método**: Análisis de palabras clave + LLM

#### 2. **Retrieval de Inventario**
- **Búsqueda híbrida**: Semántica + texto
- **Fuentes**: Base de datos de productos
- **Optimizaciones**: Manejo de plurales, sinónimos

#### 3. **Retrieval de Contexto**
- **Información empresarial**: Historia, valores, políticas
- **Contexto conversacional**: Últimos 10 mensajes

#### 4. **Generación de Respuestas**
- **Prompts especializados**: Ventas vs. información
- **Personalización**: Tono, nombre del agente
- **Validación**: Coherencia y relevancia

## 📱 Integración con Telegram

### 🤖 Bot de Telegram (`app/integrations/telegram_bot.py`)

#### Funcionalidades:
- **Recepción de mensajes**: Webhook + polling
- **Procesamiento**: Integración con sistema RAG
- **Gestión de estado**: Pedidos activos por chat
- **Comandos especiales**: `/start`, `/help`, `/pedido`

#### Flujo de Mensajes:
```
Telegram → Webhook → Bot Handler → RAG System → Respuesta → Telegram
```

## 🔄 Flujos de Datos

### 1. **Flujo de Venta Completa**
```
1. Cliente: "Quiero 2 extintores"
2. RAG: Clasifica como "venta"
3. Extracción: Producto="extintor", Cantidad=2
4. Búsqueda: Encuentra productos relevantes
5. Respuesta: Muestra opciones disponibles
6. Cliente: Confirma selección
7. Sistema: Crea pedido, solicita datos
8. Recolección: Nombre, cédula, teléfono, etc.
9. Validación: Verifica datos del cliente
10. Finalización: Crea venta en BD
```

### 2. **Flujo de Consulta de Inventario**
```
1. Cliente: "¿Qué productos tienen?"
2. RAG: Clasifica como "inventario"
3. Retrieval: Obtiene todos los productos activos
4. Agrupación: Por categorías
5. Respuesta: Lista formateada con precios
```

### 3. **Flujo de Consulta de Cliente**
```
1. Agente: "Historial del cliente 12345678"
2. RAG: Detecta consulta de cliente
3. Búsqueda: Por cédula en BD
4. Análisis: Compras, estadísticas
5. Respuesta: Resumen completo
```

## 🔒 Seguridad

### 🛡️ Medidas Implementadas

#### 1. **Autenticación y Autorización**
- **API Keys**: Variables de entorno
- **CORS**: Configurado para dominios específicos
- **Rate Limiting**: Prevención de abuso

#### 2. **Validación de Datos**
- **Pydantic**: Validación de esquemas
- **SQLAlchemy**: Prevención de SQL injection
- **Sanitización**: Limpieza de inputs

#### 3. **Gestión de Secretos**
- **Variables de entorno**: `.env` para configuración
- **Exclusión**: `.gitignore` para secretos
- **Rotación**: Procedimientos para cambio de keys

### 🔐 Variables de Entorno Críticas
```bash
# LLM APIs
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...

# Telegram
TELEGRAM_TOKEN=123456:ABC...

# Base de Datos
DATABASE_URL=sqlite+aiosqlite:///./app.db

# Vectorial Search
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=...

# Seguridad
SECRET_KEY=...
```

## 📈 Escalabilidad

### 🚀 Estrategias de Escalamiento

#### 1. **Base de Datos**
- **Actual**: SQLite (desarrollo/pequeña escala)
- **Escalamiento**: PostgreSQL + conexiones pool
- **Optimizaciones**: Índices, consultas optimizadas

#### 2. **Sistema RAG**
- **Vectorial**: Migración de FAISS a Pinecone
- **Caché**: Redis para respuestas frecuentes
- **Distribución**: Múltiples instancias LLM

#### 3. **API Backend**
- **Contenedores**: Docker + Kubernetes
- **Load Balancer**: Nginx/HAProxy
- **Monitoreo**: Prometheus + Grafana

#### 4. **Frontend**
- **CDN**: Distribución de assets estáticos
- **Optimización**: Code splitting, lazy loading
- **PWA**: Funcionalidad offline

### 📊 Métricas de Rendimiento
- **Tiempo de respuesta RAG**: < 2 segundos
- **Throughput API**: > 100 req/seg
- **Disponibilidad**: 99.9% uptime
- **Precisión RAG**: > 95% respuestas relevantes

## 🔧 Configuración y Despliegue

### 🐳 Docker
```dockerfile
# Backend
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/ ./app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

# Frontend
FROM node:18-alpine
COPY package.json .
RUN npm install
COPY src/ ./src/
RUN npm run build
CMD ["npm", "start"]
```

### 🚀 Comandos de Inicio
```bash
# Backend
python -m uvicorn app.main:app --reload --port 8001

# Bot Telegram
python app/integrations/telegram_bot.py

# Frontend
cd frontend && npm start
```

## 📝 Logs y Monitoreo

### 📊 Sistema de Logging
- **Nivel**: INFO, WARNING, ERROR
- **Formato**: JSON estructurado
- **Destinos**: Archivo + consola
- **Rotación**: Diaria con compresión

### 🔍 Métricas Clave
- **Mensajes procesados**: Total y por tipo
- **Ventas generadas**: Cantidad y valor
- **Errores**: Rate y tipos
- **Performance**: Latencia promedio

---

## 🎯 Próximos Pasos

### 🔮 Roadmap Técnico
1. **Migración a PostgreSQL**
2. **Implementación de Redis Cache**
3. **Monitoreo avanzado con Prometheus**
4. **Tests automatizados completos**
5. **CI/CD con GitHub Actions**
6. **Documentación API con OpenAPI**

### 🚀 Nuevas Funcionalidades
1. **Análisis de sentimientos**
2. **Recomendaciones personalizadas**
3. **Integración con WhatsApp**
4. **Dashboard de analytics avanzado**
5. **Sistema de notificaciones**

---

*Documentación actualizada: Diciembre 2024*
*Versión del sistema: 2.0.0* 