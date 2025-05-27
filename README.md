# 🤖 Agente Vendedor Sextinvalle - Sistema de Ventas con IA

Un sistema avanzado de ventas inteligente que utiliza **RAG (Retrieval-Augmented Generation)** e inteligencia artificial para automatizar el proceso comercial. Combina **FastAPI**, **React**, **Telegram Bot** y **LLMs** (OpenAI GPT + Google Gemini).

## 🚀 Características Principales

### 🧠 Inteligencia Artificial Avanzada
- **Sistema RAG Híbrido**: Búsqueda semántica + texto para inventario y clientes
- **Procesamiento de Lenguaje Natural**: Comprende intenciones de compra complejas
- **Gestión de Pedidos Conversacional**: Carrito de compras inteligente
- **Múltiples LLMs**: OpenAI GPT-4 y Google Gemini
- **Memoria Conversacional**: Contexto de últimos 10 mensajes

### 💼 Gestión Comercial Completa
- **Frontend Web**: Interfaz React con TypeScript
- **Bot de Telegram**: Integración nativa para ventas
- **API REST**: Backend robusto con FastAPI
- **Base de Datos**: SQLite con migración a PostgreSQL
- **Exportación CSV**: Reportes y análisis de ventas

### 🛡️ Seguridad y Validaciones
- **Validación de Datos**: Cédula, email, teléfono, cantidades
- **Control de Estados**: Flujo de conversación estructurado
- **Gestión de Secretos**: Variables de entorno seguras
- **Logging Completo**: Trazabilidad de todas las operaciones

## 📚 Documentación

- **[📖 Arquitectura Completa](ARQUITECTURA_SISTEMA.md)** - Documentación técnica detallada
- **[🔌 API Reference](API_REFERENCE.md)** - Endpoints y esquemas
- **[🚀 Deployment Guide](DEPLOYMENT_GUIDE.md)** - Guía de despliegue
- **[📝 Changelog](CHANGELOG.md)** - Historial de cambios

## ⚡ Inicio Rápido

### 1. Instalación
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

### 2. Configuración
```bash
# Copiar archivo de configuración
cp env.example .env

# Editar .env con tus credenciales
# OPENAI_API_KEY=sk-...
# GOOGLE_API_KEY=AIza...
# TELEGRAM_TOKEN=123456:ABC...
```

### 3. Inicialización
```bash
# Crear base de datos
python create_and_migrate.py

# Cargar productos de ejemplo (opcional)
python scripts/load_sample_data.py
```

### 4. Ejecución
```bash
# Backend API (puerto 8001)
python -m uvicorn app.main:app --reload --port 8001

# Bot de Telegram (terminal separada)
python app/integrations/telegram_bot.py

# Frontend (terminal separada)
cd frontend && npm start
```

## 🏗️ Arquitectura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend Web  │    │  Bot Telegram   │    │   API Externa   │
│   (React TS)    │    │   (Python)      │    │   (REST)        │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ HTTP/REST            │ Webhook              │ HTTP
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend API (FastAPI)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Sistema RAG │  │ Gestión     │  │ Validación  │             │
│  │ (LLM + Vec) │  │ Pedidos     │  │ & Seguridad │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
            ┌─────────────────┐
            │   Base de Datos │
            │    (SQLite)     │
            └─────────────────┘
```

## 🔌 API Principales

### Chat Inteligente
```http
POST /api/chat/
{
    "mensaje": "Quiero 2 extintores de 10 libras",
    "session_id": "user123"
}
```

### Gestión de Productos
```http
GET /api/productos/                    # Listar productos
POST /api/productos/reemplazar_csv     # Carga masiva CSV
```

### Gestión de Ventas
```http
GET /api/ventas/                       # Listar ventas
GET /api/ventas/exportar-csv          # Exportar CSV
```

## 🧪 Testing

```bash
# Tests completos
python test_rag_completo.py           # Sistema RAG
python test_ventas_completo.py        # Sistema de ventas
python test_sistema_clientes.py       # Gestión de clientes
python test_exportacion_csv.py        # Exportación CSV

# Test específico
python -m pytest tests/ -v
```

## 🚀 Despliegue

### Docker
```bash
# Construir imagen
docker build -t agente-vendedor .

# Ejecutar contenedor
docker run -p 8001:8001 --env-file .env agente-vendedor
```

### Producción
Ver [Deployment Guide](DEPLOYMENT_GUIDE.md) para instrucciones detalladas de:
- Configuración de PostgreSQL
- Nginx + SSL
- Docker Compose
- Variables de entorno de producción

## 📊 Estado del Proyecto

- ✅ **Backend API**: Completamente funcional
- ✅ **Sistema RAG**: Implementado y optimizado
- ✅ **Bot Telegram**: Integración completa
- ✅ **Gestión de Pedidos**: Flujo completo
- ✅ **Base de Datos**: Modelos y migraciones
- ✅ **Frontend Web**: Interfaz React funcional
- ✅ **Exportación CSV**: Reportes completos
- ✅ **Tests**: Cobertura principal
- 🔄 **Documentación**: En actualización continua

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 🆘 Soporte

- **Documentación**: [ARQUITECTURA_SISTEMA.md](ARQUITECTURA_SISTEMA.md)
- **Issues**: GitHub Issues
- **Email**: soporte@sextinvalle.com

---

**Versión**: 2.0.0  
**Última actualización**: Diciembre 2024  
**Desarrollado para**: Sextinvalle - Seguridad Industrial
