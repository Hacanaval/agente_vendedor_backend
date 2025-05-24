# Agente Vendedor SaaS Backend

Backend profesional, modular y multi-tenant para un Agente Vendedor conversacional orientado a PYMES. Permite gestionar inventario, ventas, clientes y consultas inteligentes vía chat, integrando RAG (Retrieval-Augmented Generation) con LLMs (OpenAI por defecto) y arquitectura lista para multiempresa.

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

## ⚠️ Seguridad y advertencias
- **Modo MVP/pruebas:**
  - No requiere autenticación JWT ni login en ningún endpoint.
  - No soporta multiempresa: todos los endpoints trabajan únicamente con la empresa de id=1.
  - Cualquier usuario o bot puede acceder y modificar datos sin restricciones.
- **¡NO USAR ESTE MODO EN PRODUCCIÓN!**
- Para pasar a producción: reactiva autenticación, roles y filtros por empresa_id siguiendo los TODOs y comentarios en el código.

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
