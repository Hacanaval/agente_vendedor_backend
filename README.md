# Agente Vendedor SaaS Backend

Backend profesional y modular para un Agente Vendedor de WhatsApp dirigido a PYMES. Permite gestionar inventario, ventas, clientes y consultas inteligentes vía chat, integrando RAG (Retrieval-Augmented Generation) con LLMs (OpenAI por defecto) y arquitectura multi-tenant.

## 🚀 Objetivo
Desarrollar una plataforma SaaS robusta para que pequeñas y medianas empresas gestionen su inventario, ventas y atención al cliente vía WhatsApp, con soporte de IA conversacional y administración multi-empresa.

## ✅ Estado actual
- Arquitectura multi-tenant lista para escalar
- Modelos de datos completos (empresa, usuario, producto, venta, logs, etc.)
- Autenticación JWT, roles (admin, vendedor, observador), endpoints protegidos
- CRUD de productos y ventas, validaciones estrictas
- Carga y reemplazo masivo de inventario vía CSV (transacción atómica, validaciones)
- Sistema de logs/auditoría extensible
- Pipeline RAG modular: retrieval semántico (FAISS), prompts desacoplados, LLM pluggable
- Endpoint `/chat` funcional para consultas inteligentes

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
   git clone https://github.com/Hacanaval/agente_vendedor.git
   cd agente_vendedor
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
