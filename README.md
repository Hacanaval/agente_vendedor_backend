# Agente Vendedor SaaS Backend

Backend profesional, modular y multi-tenant para un Agente Vendedor conversacional orientado a PYMES. Permite gestionar inventario, ventas, clientes y consultas inteligentes vía chat, integrando RAG (Retrieval-Augmented Generation) con LLMs (OpenAI por defecto) y arquitectura lista para multiempresa.

## 🚀 Características Principales

### Sistema de Chat Inteligente
- **RAG (Retrieval Augmented Generation)**: Búsqueda semántica de productos + generación de respuestas
- **Memoria de Conversación**: Mantiene contexto de los últimos 5 mensajes por chat
- **Multi-modal**: Soporta texto, imágenes (visión) y audio (transcripción)
- **Clasificación Automática**: Detecta si la consulta es sobre inventario, ventas o contexto general
- **Anti-alucinación**: Filtrado estricto de productos activos y con stock > 0

### Gestión de Inventario
- **Carga Masiva**: Importación vía CSV con validaciones
- **Búsqueda Semántica**: FAISS para encontrar productos relevantes
- **Actualización en Tiempo Real**: Índice FAISS se reconstruye tras cada cambio
- **Filtrado Inteligente**: Solo productos activos y con stock > 0

### Arquitectura Técnica

#### 1. Capas Principales
```
app/
├── api/              # Endpoints FastAPI
│   ├── chat.py      # Endpoints de chat (texto, imagen, audio)
│   ├── producto.py  # Gestión de inventario
│   ├── venta.py     # Procesamiento de ventas
│   └── logs.py      # Auditoría y métricas
├── models/          # Modelos SQLAlchemy
│   ├── producto.py  # Producto, stock, precios
│   ├── venta.py     # Ventas y pedidos
│   ├── mensaje.py   # Historial de chat
│   └── logs.py      # Logs y auditoría
├── services/        # Lógica de negocio
│   ├── rag.py       # Pipeline RAG
│   ├── retrieval/   # Búsqueda semántica
│   │   ├── faiss_retriever.py
│   │   └── pinecone_retriever.py
│   ├── llm_client.py # Integración con LLMs
│   └── prompts.py   # Templates de prompts
└── core/           # Configuración
    └── database.py # Conexión DB y sesiones
```

#### 2. Flujo de Datos
1. **Entrada de Usuario**:
   - Texto → Clasificación → RAG → Respuesta
   - Imagen → Visión → RAG → Respuesta
   - Audio → Transcripción → RAG → Respuesta

2. **Pipeline RAG**:
   ```
   Mensaje → Retrieval → Filtrado → Contexto → LLM → Respuesta
   ```

3. **Gestión de Inventario**:
   ```
   CSV → Validación → DB → FAISS Index → Búsqueda Semántica
   ```

### Guía de Escalamiento

#### 1. Escalamiento Horizontal
Para escalar horizontalmente:

1. **Base de Datos**:
   - Modificar `app/core/database.py`:
     ```python
     # Agregar soporte para replicación
     DATABASE_URL_MASTER = os.getenv("DATABASE_URL_MASTER")
     DATABASE_URL_REPLICA = os.getenv("DATABASE_URL_REPLICA")
     
     # Crear engines separados
     engine_master = create_async_engine(DATABASE_URL_MASTER)
     engine_replica = create_async_engine(DATABASE_URL_REPLICA)
     ```

2. **Retrieval**:
   - Migrar de FAISS a Pinecone:
     1. Actualizar `app/services/retrieval/retriever_factory.py`
     2. Implementar `PineconeRetriever` en `app/services/retrieval/pinecone_retriever.py`
     3. Configurar variables de entorno:
        ```
        RETRIEVER_BACKEND=pinecone
        PINECONE_API_KEY=xxx
        PINECONE_ENVIRONMENT=xxx
        ```

3. **LLM**:
   - Agregar más proveedores en `app/services/llm_client.py`:
     ```python
     async def generar_respuesta(
         prompt: str,
         llm: str = "openai",
         **kwargs
     ) -> str:
         if llm == "openai":
             return await generar_respuesta_openai(prompt, **kwargs)
         elif llm == "gemini":
             return await generar_respuesta_gemini(prompt, **kwargs)
         elif llm == "cohere":
             return await generar_respuesta_cohere(prompt, **kwargs)
     ```

#### 2. Escalamiento Vertical

1. **Caché**:
   - Implementar Redis para:
     - Caché de embeddings
     - Caché de respuestas frecuentes
     - Rate limiting
   - Agregar en `app/core/cache.py`:
     ```python
     from redis import asyncio as aioredis
     
     redis = aioredis.from_url(os.getenv("REDIS_URL"))
     ```

2. **Optimización de Búsqueda**:
   - Modificar `app/services/retrieval/faiss_retriever.py`:
     ```python
     # Usar índices más eficientes
     self.index = faiss.IndexIVFFlat(
         quantizer,
         dimension,
         nlist=100,
         metric=faiss.METRIC_INNER_PRODUCT
     )
     ```

3. **Batch Processing**:
   - Implementar colas para:
     - Procesamiento de CSV
     - Generación de embeddings
     - Envío de notificaciones
   - Usar Celery o RQ en `app/core/tasks.py`

#### 3. Multi-tenant

1. **Seguridad**:
   - Reactivar JWT en `app/core/auth.py`
   - Implementar middleware de empresa en `app/core/middleware.py`
   - Agregar filtros por empresa_id en todos los modelos

2. **Aislamiento**:
   - Modificar modelos para incluir empresa_id
   - Actualizar queries para filtrar por empresa
   - Implementar límites por empresa

### Variables de Entorno Requeridas

```env
# API Keys
GOOGLE_API_KEY=your_google_api_key_here

# Base de datos
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname

# Configuración de seguridad
SECRET_KEY=your_secret_key_here
BOT_SECRET_KEY=your_bot_secret_key_here

# Configuración del servidor
HOST=0.0.0.0
PORT=8001

# Configuración de Telegram
BOT_TOKEN_FIXED=your_telegram_bot_token_here

# Configuración de LLM
DEFAULT_MODEL=gemini-2.0-flash

# Configuración de logging
LOG_LEVEL=INFO
LOG_FILE=app.log
```

### Configuración Inicial

1. **Clonar el repositorio**:
   ```bash
   git clone <url-del-repositorio>
   cd agente_vendedor
   ```

2. **Configurar entorno virtual**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno**:
   ```bash
   cp .env.example .env
   # Editar .env con tu GOOGLE_API_KEY y demás credenciales
   ```

4. **Verificar la configuración**:
   ```bash
   python tests/test_clasificacion.py
   ```

### Cambios Recientes

1. **Memoria de Conversación**:
   - Implementado en `app/api/chat.py`
   - Mantiene últimos 5 mensajes por chat_id
   - Persiste en DB para contexto histórico

2. **Filtrado de Productos**:
   - Actualizado en `app/services/retrieval/faiss_retriever.py`
   - Solo productos activos y con stock > 0
   - Reconstrucción automática del índice

3. **Anti-alucinación**:
   - Mejorado en `app/services/rag.py`
   - Instrucciones especiales cuando no hay productos
   - Logging detallado del contexto

4. **Gestión de Inventario**:
   - Actualizado en `app/api/producto.py`
   - Sincronización automática con FAISS
   - Validaciones mejoradas

5. **Seguridad Mejorada**:
   - Implementado `.gitignore` para proteger archivos sensibles
   - Agregada verificación segura de API Keys
   - Mejorado el manejo de logs para evitar exposición de datos sensibles
   - Actualizado sistema de pruebas para validación segura

6. **Integración con Gemini**:
   - Migrado a Gemini 2.0 Flash como modelo principal (Google Generative AI)
   - Eliminada dependencia de OpenAI
   - Implementada clasificación de mensajes, generación de respuestas, embeddings y visión con Gemini
   - Optimizado sistema de prompts para mejor rendimiento
   - **[MIGRACIÓN]** Todo el sistema ahora usa Gemini (Google) como LLM principal en vez de OpenAI

### Próximos Pasos

1. **Corto Plazo**:
   - Implementar caché de embeddings
   - Agregar más proveedores LLM
   - Mejorar logging y monitoreo
   - Implementar pruebas de integración
   - Agregar documentación de API con Swagger

2. **Medio Plazo**:
   - Implementar sistema de caché con Redis
   - Agregar soporte para más modelos de Gemini
   - Mejorar el sistema de clasificación de mensajes
   - Implementar métricas de rendimiento

3. **Largo Plazo**:
   - Escalar a múltiples regiones
   - Implementar sistema de backup automático
   - Agregar soporte para más idiomas
   - Implementar sistema de A/B testing

## ⚠️ MODO ABIERTO PARA PRUEBAS/MVP ⚠️

Este backend está configurado actualmente en modo ABIERTO para pruebas/MVP:
- No requiere autenticación JWT ni login en ningún endpoint
- Usa una única empresa (ID=1)
- FAISS en memoria (no persistente)
- Sin límites de rate

Para producción, revisar TODOs en el código y seguir la guía de escalamiento.

---

## 🚀 Objetivo
Desarrollar una plataforma SaaS robusta para que pequeñas y medianas empresas gestionen su inventario, ventas y atención al cliente vía chat (WhatsApp, Telegram, web), con soporte de IA conversacional, administración multiempresa y registro completo de la experiencia de usuario.

---

## 🏗️ Arquitectura y tecnologías
- **FastAPI** (backend async, modular, tipado)
- **PostgreSQL** + **SQLAlchemy async** (ORM, relaciones, transacciones)
- **FAISS** (vector DB local, retrieval semántico)
- **OpenAI** (embeddings y LLM, arquitectura pluggable para otros modelos)
- **JWT** (autenticación y roles, desactivado en modo MVP)
- **Pandas** (procesamiento de CSV)
- **python-telegram-bot** (integración Telegram)
- **Docker-ready** (estructura preparada para contenerización)

---

## 📂 Estructura principal
```
app/
  api/           # Endpoints FastAPI (chat, ventas, productos, logs, etc.)
  models/        # Modelos SQLAlchemy (empresa, usuario, producto, venta, mensaje, etc.)
  services/      # Lógica de negocio, RAG, LLM, prompts, logs
  core/          # Configuración, base de datos
  schemas/       # Pydantic
  integrations/  # Bots y canales externos (ej: Telegram)
alembic/          # Migraciones de base de datos
```

---

## ✅ Estado actual y módulos implementados
- **Multi-tenant listo**: arquitectura preparada para múltiples empresas (filtros por empresa_id, TODOs para reactivar seguridad)
- **Modelos completos**: empresa, usuario, producto, venta, mensaje (persistencia de conversación), logs, etc.
- **Autenticación JWT y roles**: implementado pero desactivado en modo MVP/pruebas
- **CRUD de productos y ventas**: validaciones estrictas, carga masiva por CSV
- **Logs/auditoría y métricas**: endpoints para monitoreo y administración
- **Pipeline RAG modular**: retrieval semántico (FAISS), prompts desacoplados, LLM pluggable
- **Persistencia de conversación**: cada mensaje de usuario y bot se guarda con chat_id, remitente, mensaje, timestamp y estado de venta
- **Registro automático de ventas**: detección de confirmación, registro en base de datos, cierre de ciclo conversacional
- **Integración Telegram**: bot funcional, logs de entrada/salida, soporte para texto, imagen y audio
- **Endpoints de historial**: consulta de mensajes y ventas por chat_id para frontend o auditoría
- **Cache de embeddings y reintentos automáticos**
- **Validaciones robustas y manejo de errores**

---

## 🔄 Flujo conversacional y persistencia
- Cada mensaje enviado y recibido (usuario/bot) se guarda en la tabla `mensaje` con `chat_id`, `remitente`, `mensaje`, `timestamp` y `estado_venta`.
- El backend detecta automáticamente confirmaciones de venta ("sí", "confirmo", "ok", etc.) y registra la venta en la tabla `venta` asociada al `chat_id`.
- El ciclo de venta se cierra con un mensaje de cierre y no se vuelve a pedir confirmación.
- Todo el historial de conversación y ventas puede ser consultado por el frontend para reconstruir la experiencia del usuario.

---

## 🧑‍💻 Endpoints principales

### Chat y conversación
- `POST /chat/texto` — Procesa mensajes de texto, integra RAG y LLM, guarda cada mensaje y gestiona el flujo de venta.
- `GET /chat/historial/{chat_id}` — Devuelve el historial completo de mensajes de un usuario/chat.

### Ventas
- `POST /ventas/` — Registra una venta (usado automáticamente al confirmar en el chat).
- `GET /ventas/historial/{chat_id}` — Devuelve el historial de ventas de un usuario/chat.

### Productos
- `POST /productos/reemplazar_csv` — Carga masiva de inventario vía CSV (validaciones de tamaño y formato).
- `GET /productos/` — Lista todos los productos activos y con stock.

### Logs y métricas
- `GET /logs/` — Consulta logs/auditoría.
- `GET /logs/metrics/uso` — Métricas de uso (consultas, ventas, etc.).
- `POST /logs/admin/reset_empresa` — Borra todos los datos de la empresa actual (solo admin).
- `POST /logs/admin/reset_global` — Borra todos los datos globales (solo superadmin).

---

## 🤖 Integración con Telegram
- Bot funcional usando `python-telegram-bot`.
- Soporta texto, imágenes y audio.
- Cada mensaje del usuario y la respuesta del bot se loguean y persisten.
- El bot usa un `chat_id` único por usuario para asociar la conversación y las ventas.
- El bot puede funcionar 24/7 con un token fijo y sin login manual.

---

## 📝 Ejemplo de flujo conversacional
1. **Usuario:** "Quiero comprar 10 martillos."
2. **Bot:** "Puedo ofrecerte 7 martillos. ¿Deseas llevar esa cantidad?"
3. **Usuario:** "Sí."
4. **Bot:** "¡Listo! Pedido registrado. Pronto te contactaremos para coordinar la entrega."
5. **(El historial y la venta quedan registrados y pueden ser consultados por el frontend)**

---

## 📝 Personalización y extensibilidad
- **Prompts**: Edita los prompts en `app/services/prompts.py` para cambiar el tono, reglas anti-alucinación, cierre de venta, etc.
- **LLM**: Cambia el modelo de lenguaje (OpenAI, Gemini, Cohere, local, etc.) en la configuración.
- **Retrieval**: Arquitectura lista para migrar de FAISS a Pinecone u otros.
- **Multi-tenant**: TODOs y comentarios en el código para reactivar seguridad y multiempresa.
- **Integración de canales**: Listo para WhatsApp, Telegram, web y otros.

---

## 🛠️ Instalación y despliegue local
1. Clona el repo:
   ```bash
   git clone https://github.com/Hacanaval/agente_vendedor_backend.git
   cd agente_vendedor_backend
   ```
2. Crea y activa un entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Configura variables de entorno en `.env`:
   ```env
   OPENAI_API_KEY=tu_clave_openai
   DATABASE_URL=postgresql+asyncpg://usuario:password@localhost:5432/tu_db
   # ...otros parámetros opcionales
   ```
5. Crea las tablas y aplica migraciones:
   ```bash
   python create_tables.py
   alembic upgrade head
   ```
6. Ejecuta el servidor:
   ```bash
   uvicorn app.main:app --reload
   ```

---

## 📈 Consultas y administración
- Consulta historial de mensajes: `GET /chat/historial/{chat_id}`
- Consulta historial de ventas: `GET /ventas/historial/{chat_id}`
- Consulta métricas de uso: `GET /logs/metrics/uso`
- Reset de empresa o global: `POST /logs/admin/reset_empresa` y `POST /logs/admin/reset_global`

---

## 📝 Próximos pasos sugeridos
- Integración WhatsApp/Telegram (webhook, sesión, multimedia)
- Frontend administrativo y dashboard
- Reportes, analítica y exportación de datos
- Dockerización y CI/CD
- Seguridad avanzada (2FA, cifrado, retención de logs)
- Escalabilidad: migración a LangGraph, Pinecone, balanceo de carga

---

## ⚠️ NOTA IMPORTANTE / IMPORTANT NOTE

**ESPAÑOL:**
Este backend está configurado actualmente en modo ABIERTO para pruebas/MVP:
- No requiere autenticación JWT ni login en ningún endpoint.
- No soporta multiempresa: todos los endpoints trabajan únicamente con la empresa de id=1.
- Cualquier usuario o bot puede acceder y modificar datos sin restricciones.

**¡NO USAR ESTE MODO EN PRODUCCIÓN!**
No es seguro ni apto para entornos multiusuario o multiempresa.

**Para pasar a producción y activar seguridad/multiempresa:**
1. Reactiva la autenticación JWT en los endpoints administrativos y de negocio.
2. Vuelve a exigir y validar el token JWT en los requests.
3. Vuelve a requerir y filtrar por `empresa_id` en todos los endpoints y queries.
4. Haz que el frontend y los bots envíen el `empresa_id` y el token JWT en cada request.
5. Sigue los comentarios y TODOs en el código para restaurar la lógica multiempresa y de autenticación.

---

**ENGLISH:**
This backend is currently configured in OPEN mode for testing/MVP only:
- No JWT authentication or login is required for any endpoint.
- No multi-tenant support: all endpoints work only with the company with id=1.
- Any user or bot can access and modify data without restrictions.

**DO NOT USE THIS MODE IN PRODUCTION!**
It is not secure and not suitable for multi-user or multi-tenant environments.

**To move to production and enable security/multi-tenancy:**
1. Reactivate JWT authentication in all business/admin endpoints.
2. Require and validate the JWT token in all requests.
3. Require and filter by `empresa_id` in all endpoints and queries.
4. Make frontend and bots send `empresa_id` and JWT token in every request.
5. Follow the comments and TODOs in the code to restore multi-tenant and authentication logic.

---

**Contacto:** [@Hacanaval](https://github.com/Hacanaval)
