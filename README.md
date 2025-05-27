# 🤖 Agente Vendedor Inteligente

## 📋 Descripción

Sistema completo de agente vendedor inteligente con capacidades de RAG (Retrieval-Augmented Generation), gestión de clientes, procesamiento de pedidos y exportación de datos. El sistema utiliza IA para proporcionar respuestas contextuales sobre productos y gestionar el proceso de ventas de manera automatizada.

## 🚀 Características Principales

### 🧠 Sistema RAG Inteligente
- **RAG de Productos**: Búsqueda semántica en catálogo de productos
- **RAG de Clientes**: Gestión inteligente de información de clientes
- **Embeddings Vectoriales**: Búsqueda por similitud usando OpenAI embeddings
- **Respuestas Contextuales**: IA que comprende el contexto de ventas

### 👥 Gestión de Clientes
- **CRUD Completo**: Crear, leer, actualizar y eliminar clientes
- **Búsqueda Inteligente**: Búsqueda por nombre, email, teléfono
- **Historial de Compras**: Seguimiento completo de pedidos por cliente
- **Segmentación**: Clasificación automática de clientes

### 📦 Procesamiento de Pedidos
- **Creación Automática**: Procesamiento de pedidos desde conversaciones
- **Validación Inteligente**: Verificación de productos y cantidades
- **Cálculo Automático**: Totales, impuestos y descuentos
- **Estados de Pedido**: Seguimiento completo del ciclo de vida

### 📊 Exportación y Reportes
- **Exportación CSV**: Clientes, productos, pedidos
- **Reportes Personalizados**: Filtros por fecha, cliente, producto
- **Análisis de Ventas**: Métricas y estadísticas de rendimiento
- **Formatos Múltiples**: CSV, JSON, Excel (próximamente)

## 🏗️ Arquitectura del Sistema

```
agente_vendedor/
├── app/
│   ├── api/                    # Endpoints de la API
│   │   ├── clientes.py        # API de gestión de clientes
│   │   ├── exportar.py        # API de exportación de datos
│   │   ├── pedidos.py         # API de gestión de pedidos
│   │   └── rag.py             # API del sistema RAG
│   ├── models/                 # Modelos de datos
│   │   ├── cliente.py         # Modelo de cliente
│   │   ├── producto.py        # Modelo de producto
│   │   └── venta.py           # Modelo de venta/pedido
│   ├── services/               # Lógica de negocio
│   │   ├── cliente_manager.py # Gestión de clientes
│   │   ├── csv_exporter.py    # Exportación CSV
│   │   ├── pedidos.py         # Procesamiento de pedidos
│   │   ├── prompts.py         # Prompts de IA
│   │   ├── rag.py             # Sistema RAG principal
│   │   └── rag_clientes.py    # RAG específico para clientes
│   └── main.py                 # Aplicación principal FastAPI
├── migrations/                 # Migraciones de base de datos
├── tests/                      # Tests automatizados
├── scripts/                    # Scripts de utilidad
└── docs/                       # Documentación adicional
```

## 🛠️ Tecnologías Utilizadas

### Backend
- **FastAPI**: Framework web moderno y rápido
- **SQLAlchemy**: ORM para base de datos
- **SQLite**: Base de datos ligera y eficiente
- **Alembic**: Migraciones de base de datos

### IA y Machine Learning
- **OpenAI GPT-4**: Modelo de lenguaje principal
- **OpenAI Embeddings**: Vectorización de texto
- **ChromaDB**: Base de datos vectorial
- **LangChain**: Framework para aplicaciones de IA

### Utilidades
- **Pandas**: Manipulación de datos
- **Pydantic**: Validación de datos
- **Python-dotenv**: Gestión de variables de entorno
- **Uvicorn**: Servidor ASGI

## 📦 Instalación

### Prerrequisitos
- Python 3.8+
- pip
- Git

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone https://github.com/tu-usuario/agente_vendedor.git
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
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Acceder a la Documentación
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints Principales

#### Sistema RAG
- `POST /rag/query` - Consulta al sistema RAG
- `POST /rag/add-product` - Añadir producto al catálogo
- `GET /rag/products` - Listar productos

#### Gestión de Clientes
- `GET /clientes/` - Listar clientes
- `POST /clientes/` - Crear cliente
- `GET /clientes/{id}` - Obtener cliente
- `PUT /clientes/{id}` - Actualizar cliente
- `DELETE /clientes/{id}` - Eliminar cliente
- `GET /clientes/buscar` - Buscar clientes

#### Gestión de Pedidos
- `GET /pedidos/` - Listar pedidos
- `POST /pedidos/` - Crear pedido
- `GET /pedidos/{id}` - Obtener pedido
- `PUT /pedidos/{id}/estado` - Actualizar estado

#### Exportación
- `GET /exportar/clientes` - Exportar clientes a CSV
- `GET /exportar/productos` - Exportar productos a CSV
- `GET /exportar/pedidos` - Exportar pedidos a CSV

## 🧪 Testing

### Ejecutar Tests
```bash
# Tests básicos
python test_rag_simple.py
python test_sistema_clientes.py
python test_exportacion_csv.py

# Test completo de integración
python test_crear_cliente_y_rag.py
```

### Generar Reportes
```bash
python reporte_estado_rag.py
```

## 📊 Funcionalidades Avanzadas

### Sistema RAG Dual
El sistema implementa dos tipos de RAG:

1. **RAG de Productos**: Para consultas sobre catálogo
2. **RAG de Clientes**: Para información de clientes y historial

### Exportación Inteligente
- **Filtros Avanzados**: Por fecha, cliente, estado
- **Formatos Múltiples**: CSV con diferentes configuraciones
- **Datos Relacionados**: Exportación con joins automáticos

### Gestión de Estados
- **Pedidos**: Pendiente → Procesando → Enviado → Entregado
- **Clientes**: Activo → Inactivo → Suspendido
- **Productos**: Disponible → Agotado → Descontinuado

## 🔧 Configuración Avanzada

### Variables de Entorno
```env
# API Keys
OPENAI_API_KEY=tu_clave_openai

# Base de Datos
DATABASE_URL=sqlite:///./app.db

# Configuración RAG
CHROMA_PERSIST_DIRECTORY=./chroma_db
EMBEDDING_MODEL=text-embedding-ada-002

# Configuración de Exportación
EXPORT_DIRECTORY=./exports
MAX_EXPORT_RECORDS=10000
```

### Personalización de Prompts
Los prompts del sistema se pueden personalizar en `app/services/prompts.py`:

```python
SYSTEM_PROMPT = """
Eres un agente vendedor experto...
"""

PRODUCT_SEARCH_PROMPT = """
Busca productos relevantes para: {query}
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
- Consultas RAG
- Operaciones de base de datos
- Exportaciones
- Errores y excepciones

## 🤝 Contribución

### Guías de Desarrollo
1. Fork el repositorio
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Añadir nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

### Estándares de Código
- **PEP 8**: Estilo de código Python
- **Type Hints**: Tipado estático
- **Docstrings**: Documentación de funciones
- **Tests**: Cobertura mínima del 80%

## 📝 Changelog

### v2.0.0 (Actual)
- ✅ Sistema RAG dual (productos + clientes)
- ✅ Gestión completa de clientes
- ✅ Exportación CSV avanzada
- ✅ API REST completa
- ✅ Tests automatizados
- ✅ Documentación completa

### v1.0.0
- ✅ Sistema RAG básico
- ✅ Procesamiento de pedidos
- ✅ API básica
- ✅ Base de datos SQLite

## 🐛 Problemas Conocidos

### Limitaciones Actuales
- Exportación limitada a CSV (Excel en desarrollo)
- RAG de clientes en fase beta
- Búsqueda semántica solo en español

### Roadmap
- [ ] Exportación a Excel
- [ ] Dashboard web
- [ ] API de webhooks
- [ ] Integración con CRM externos
- [ ] Soporte multiidioma

## 📞 Soporte

### Documentación Adicional
- **Backend**: `README_BACKEND.md`
- **Estado del Sistema**: `ESTADO_BACKEND.md`
- **Migraciones**: `migrations/README.md`

### Contacto
- **Issues**: GitHub Issues
- **Documentación**: Wiki del proyecto
- **Ejemplos**: Directorio `tests/`

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🙏 Agradecimientos

- OpenAI por las APIs de GPT-4 y Embeddings
- FastAPI por el excelente framework
- ChromaDB por la base de datos vectorial
- La comunidad de Python por las librerías utilizadas

---

**Desarrollado con ❤️ para revolucionar las ventas con IA**
