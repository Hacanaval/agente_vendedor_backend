# Agente Vendedor SaaS Backend

Backend profesional y modular para un Agente Vendedor de WhatsApp dirigido a PYMES. Permite gestionar inventario, ventas, clientes y consultas inteligentes vía chat, integrando RAG (Retrieval-Augmented Generation) con LLMs (OpenAI por defecto) y arquitectura multi-tenant.

## 🚀 Objetivo
Desarrollar una plataforma SaaS robusta para que pequeñas y medianas empresas gestionen su inventario, ventas y atención al cliente vía WhatsApp, con soporte de IA conversacional y administración multi-empresa.

## ✅ Estado actual
- Arquitectura multi-tenant lista para escalar y robusta (nunca se mezclan datos de empresas)
- Modelos de datos completos (empresa, usuario, producto, venta, logs, etc.)
- Autenticación JWT, roles (admin, vendedor, observador), endpoints protegidos
- CRUD de productos y ventas, validaciones estrictas
- Carga y reemplazo masivo de inventario vía CSV (transacción atómica, validaciones, límite 2MB/1000 productos)
- Sistema de logs/auditoría extensible y métricas de uso
- Pipeline RAG modular: retrieval semántico (FAISS), prompts desacoplados, LLM pluggable
- Endpoint `/chat` funcional para consultas inteligentes
- Endpoints de métricas y administración para pruebas y control
- Cache de embeddings y reintentos automáticos en LLM y retrieval

## 🏗️ Arquitectura y tecnologías
- **FastAPI** (backend async, modular, tipado)
- **PostgreSQL** + **SQLAlchemy async** (ORM, relaciones, transacciones)
- **FAISS** (vector DB local, retrieval semántico)
- **OpenAI** (embeddings y LLM, arquitectura pluggable para otros modelos)
- **JWT** (autenticación y roles)
- **Pandas** (procesamiento de CSV)
- **Docker-ready** (estructura preparada para contenerización)

## 📂 Estructura principal
```
app/
  api/           # Endpoints FastAPI
  models/        # Modelos SQLAlchemy
  services/      # Lógica de negocio, RAG, LLM, prompts, logs
  core/          # Configuración, base de datos
  schemas/       # Pydantic
```

## ⚙️ Instalación y despliegue local
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
5. Crea las tablas:
   ```bash
   python create_tables.py
   ```
6. Ejecuta el servidor:
   ```bash
   uvicorn app.main:app --reload
   ```

## 🧑‍💻 Ejemplo de uso: endpoint `/chat`
Consulta inteligente de inventario o contexto empresarial:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer TU_TOKEN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "mensaje": "¿Qué laptops tienen en stock?",
    "tipo": "inventario",
    "tono": "formal",
    "instrucciones": "Responde siempre en español.",
    "llm": "openai"
  }'
```

## 📊 Endpoints de métricas y administración

- **Métricas de uso (solo admin):**
  ```bash
  curl -X GET "http://localhost:8000/logs/metrics/uso" -H "Authorization: Bearer TU_TOKEN_JWT"
  # Parámetros opcionales: usuario_id, fecha_inicio, fecha_fin
  ```
- **Reset de empresa (solo admin):**
  ```bash
  curl -X POST "http://localhost:8000/logs/admin/reset_empresa" -H "Authorization: Bearer TU_TOKEN_JWT"
  ```
- **Reset global (solo superadmin):**
  ```bash
  curl -X POST "http://localhost:8000/logs/admin/reset_global" -H "Authorization: Bearer TU_TOKEN_JWT"
  # Solo emails: hacanaval@hotmail.com, hugocanaval34@gmail.com
  ```

## 📝 Personalización de prompts y pipeline RAG
- Todos los prompts (ventas, empresa, clasificación) están en `app/services/prompts.py`.
- Puedes editar fácilmente el tono, instrucciones, ejemplos y reglas anti-alucinaciones.
- Para cambiar el comportamiento del agente, solo ajusta los prompts en ese archivo.
- El pipeline RAG está en `app/services/rag.py` y es modular: puedes cambiar retrieval, prompts o LLM con mínima edición.

## 🔒 Seguridad y robustez multi-tenant
- Todos los endpoints y queries filtran por empresa_id del usuario autenticado.
- No es posible acceder a datos de otra empresa.
- Endpoints críticos protegidos por rol y JWT.
- Variables sensibles solo en `.env`.

## ⚠️ Límite de carga de CSV
- El endpoint `/productos/reemplazar_csv` acepta archivos de hasta 2MB y máximo 1000 productos por carga.
- Si se excede, devuelve error 400.

## 🧠 Mejoras recientes
- Cache de embeddings para evitar recomputos y reducir costos.
- Reintentos automáticos y logs en servicios LLM y retrieval.
- Manejo robusto de errores y validaciones en todos los endpoints.
- Endpoints de administración para pruebas y limpieza de datos.

## 🔄 Extensibilidad
- **LLM pluggable**: Cambia de OpenAI a Gemini, Cohere, etc. editando una línea de config
- **Retrieval**: Arquitectura lista para migrar de FAISS a Pinecone u otros
- **Prompts**: Separados y personalizables por empresa, canal, etc.
- **Logs**: Sistema de auditoría extensible y filtrable
- **Multi-tenant**: Todo endpoint y modelo validado por empresa

## 📝 Próximos pasos
- Integración WhatsApp/Telegram (webhook, sesión, multimedia)
- Frontend administrativo y dashboard
- Reportes, analítica y exportación de datos
- Dockerización y CI/CD
- Seguridad avanzada (2FA, cifrado, retención de logs)
- Escalabilidad: migración a LangGraph, Pinecone, balanceo de carga

---

**Contacto:** [@Hacanaval](https://github.com/Hacanaval)
