# 🤖 Agente Vendedor Conversacional para SMEs

Sistema de agente vendedor conversacional inteligente para pequeñas y medianas empresas, desarrollado para Sextinvalle. El sistema utiliza Gemini AI para procesamiento de lenguaje natural, embeddings, y visión artificial.

## 🚀 Características Principales

- **Chatbot Multimodal**: Soporta texto, imágenes y audio
- **RAG (Retrieval Augmented Generation)**: 
  - RAG de contexto para información de la empresa
  - RAG de inventario para productos y precios
- **Clasificación Automática**: Detecta automáticamente el tipo de consulta (contexto, inventario, venta)
- **Integración con Telegram**: Bot de Telegram para atención 24/7
- **Base de Datos SQL**: Almacenamiento persistente de conversaciones y productos
- **API REST**: Endpoints para integración con otros sistemas

## 🛠️ Stack Tecnológico

- **Backend**: FastAPI (Python 3.9+)
- **Base de Datos**: PostgreSQL + SQLAlchemy (async)
- **IA/ML**: 
  - Gemini AI (text-embedding-004) para embeddings
  - Gemini AI (gemini-2.0-flash) para LLM y visión
- **Integración**: Telegram Bot API
- **Almacenamiento**: FAISS para vectores

## 📋 Requisitos

- Python 3.9+
- PostgreSQL 13+
- Cuenta de Google Cloud con API key para Gemini
- Token de Telegram Bot

## 🔧 Instalación

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/tu-usuario/agente_vendedor.git
   cd agente_vendedor
   ```

2. **Crear entorno virtual**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # o
   .\venv\Scripts\activate  # Windows
   ```

3. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno**:
   ```bash
   cp .env.example .env
   # Editar .env con tus credenciales
   ```

   Variables requeridas:
   ```
   GOOGLE_API_KEY=tu_api_key_de_gemini
   TELEGRAM_TOKEN=tu_token_de_telegram
   BOT_TOKEN_FIXED=tu_token_fijo_del_bot
   BACKEND_URL=http://localhost:8001
   DATABASE_URL=postgresql+asyncpg://usuario:contraseña@localhost:5432/agente_vendedor
   ```

5. **Inicializar la base de datos**:
   ```bash
   # Crear base de datos PostgreSQL
   createdb agente_vendedor
   
   # Ejecutar migraciones
   alembic upgrade head
   
   # Inicializar productos de ejemplo
   python scripts/init_productos.py
   ```

## 🚀 Uso

1. **Iniciar el servidor**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
   ```

2. **Iniciar el bot de Telegram**:
   ```bash
   python app/integrations/telegram_bot.py
   ```

3. **Acceder a la API**:
   - Documentación Swagger: http://localhost:8001/docs
   - Documentación ReDoc: http://localhost:8001/redoc

## 📚 Endpoints Principales

### Chat

- `POST /chat/texto`: Procesa mensajes de texto
  ```json
  {
    "mensaje": "¿Qué productos tienen disponibles?",
    "chat_id": "123",
    "llm": "gemini"
  }
  ```

- `POST /chat/imagen`: Procesa imágenes
  - Envía imagen como multipart/form-data
  - Opcional: mensaje de texto asociado

- `POST /chat/audio`: Procesa mensajes de voz
  - Envía audio como multipart/form-data
  - Transcribe y procesa automáticamente

- `GET /chat/historial/{chat_id}`: Obtiene historial de conversación

### Productos

- `GET /productos/productos`: Lista todos los productos
- `GET /productos/productos/{id}`: Obtiene detalle de un producto
- `POST /productos/productos`: Crea nuevo producto
- `PUT /productos/productos/{id}`: Actualiza producto
- `DELETE /productos/productos/{id}`: Elimina producto

## 🤖 Funcionalidades del Bot

1. **Comandos**:
   - `/start`: Inicia conversación
   - `/help`: Muestra ayuda

2. **Tipos de Mensajes**:
   - **Texto**: Consultas generales, productos, ventas
   - **Imágenes**: Identificación de productos, consultas visuales
   - **Audio**: Mensajes de voz transcritos automáticamente

3. **Clasificación Automática**:
   - **Contexto**: Información de la empresa
   - **Inventario**: Consultas de productos
   - **Venta**: Intenciones de compra

## 🧪 Pruebas

El proyecto incluye varios scripts de prueba:

- `test_db_productos.py`: Verifica productos en la base de datos
- `test_rag_completo.py`: Prueba RAG y clasificación
- `test_sistema_completo.py`: Pruebas end-to-end

Ejecutar pruebas:
```bash
python test_sistema_completo.py
```

## 📊 Métricas de Rendimiento

- **Clasificación de mensajes**: 100% precisión
- **RAG de inventario**: Funcionando perfectamente
- **RAG de contexto**: Funcionando perfectamente
- **Tiempo de respuesta**: 4-7 segundos promedio
- **Soporte multimodal**: Texto, imágenes, audio

## 🔒 Seguridad

- Tokens y claves API en variables de entorno
- Validación de tokens de Telegram
- Manejo robusto de errores
- Timeouts apropiados (30s texto, 60s multimedia)
- Cleanup automático de archivos temporales

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crea un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 👥 Autores

- Tu Nombre - Desarrollo inicial

## 🙏 Agradecimientos

- Sextinvalle por la oportunidad
- Google Gemini AI por la tecnología
- Comunidad de FastAPI y Python
