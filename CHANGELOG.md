# 📝 Changelog - Agente Vendedor Inteligente

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-12-19

### 🎉 Añadido
- **Sistema RAG con FAISS**: Implementación de búsqueda semántica usando FAISS en lugar de ChromaDB
- **Google Gemini Integration**: Migración completa de OpenAI a Google Gemini para LLM y embeddings
- **Gestión Completa de Clientes**: CRUD completo con cédula como identificador único
- **Sistema de Exportación CSV**: Exportación avanzada con filtros para clientes, productos y pedidos
- **Chat Multimodal**: Procesamiento de texto, imágenes (Gemini Vision) y audio (OpenAI Whisper)
- **Bot de Telegram**: Integración completa con Telegram para atención 24/7
- **API REST Completa**: 9 módulos de API (auth, admin, chat, clientes, exportar, logs, pedidos, producto, venta)
- **Sistema de Clasificación**: Clasificación automática de mensajes en inventario, venta o contexto
- **Transcripción de Audio**: Integración con OpenAI Whisper para convertir audio a texto
- **Tests Automatizados**: Suite completa de tests para RAG, clientes y exportación
- **Documentación Técnica**: Documentación completa y precisa del sistema

### 🔧 Técnico
- **FAISS Retriever**: Sistema de búsqueda vectorial optimizado con fallback a búsqueda por texto
- **Gemini Embeddings**: Uso de `text-embedding-004` para generación de vectores semánticos
- **SQLAlchemy ORM**: Modelos de datos optimizados con relaciones y validaciones
- **Pydantic Schemas**: Validación robusta de datos de entrada y salida
- **Async Operations**: Operaciones asíncronas para mejor performance
- **Logging Estructurado**: Sistema de logging detallado para debugging y monitoreo
- **Alembic Migrations**: Sistema de migraciones de base de datos
- **Factory Pattern**: Patrón factory para retrievers (FAISS/Pinecone)

### 🗄️ Base de Datos
- **Modelo Cliente**: Cédula como PK, información completa de contacto y dirección
- **Modelo Producto**: Gestión de inventario con stock y categorías
- **Modelo Venta**: Relación con cliente por cédula, detalles de transacción
- **Modelo Mensaje**: Historial completo de conversaciones multimodales
- **Índices Optimizados**: Índices para búsquedas rápidas por cédula, nombre, teléfono

### 📊 APIs Implementadas
- **Chat API**: `/chat/texto`, `/chat/imagen`, `/chat/audio`, `/chat/historial`
- **Clientes API**: CRUD completo con búsqueda inteligente
- **Productos API**: Gestión de catálogo con stock
- **Pedidos API**: Procesamiento de órdenes de venta
- **Exportación API**: CSV con filtros avanzados
- **Admin API**: Estadísticas y sincronización de índices
- **Logs API**: Métricas de uso del sistema

### 🚀 Integraciones
- **Google Gemini**: LLM principal (gemini-2.0-flash)
- **Google Gemini Vision**: Procesamiento de imágenes
- **Google Gemini Embeddings**: Vectorización de texto
- **OpenAI Whisper**: Transcripción de audio (único uso de OpenAI)
- **Telegram Bot**: Bot completo con webhook support
- **FAISS**: Base de datos vectorial para búsqueda semántica

### 🔄 Migrado
- **De OpenAI a Gemini**: Migración completa del LLM principal
- **De ChromaDB a FAISS**: Cambio de base de datos vectorial
- **Sistema de Clientes**: Migración de ID numérico a cédula como PK
- **Arquitectura de Servicios**: Refactorización en servicios especializados

### 🛠️ Mejorado
- **Performance RAG**: Optimización con FAISS y embeddings de Gemini
- **Búsqueda de Clientes**: Búsqueda por cédula, nombre, teléfono
- **Validación de Datos**: Validaciones robustas con Pydantic
- **Manejo de Errores**: Sistema de manejo de errores mejorado
- **Logging**: Logging estructurado y detallado
- **Documentación**: Documentación técnica completa y precisa

### 🐛 Corregido
- **Búsqueda Semántica**: Implementación correcta con FAISS
- **Gestión de Archivos**: Validación y sanitización de uploads
- **Relaciones de DB**: Relaciones correctas entre modelos
- **Async Operations**: Operaciones asíncronas optimizadas
- **Memory Management**: Gestión optimizada de memoria para FAISS

## [1.5.0] - 2024-12-15

### 🎉 Añadido
- **RAG Básico**: Primera implementación del sistema RAG
- **Gestión de Productos**: CRUD básico de productos
- **API FastAPI**: Estructura básica de la API
- **Base de Datos**: Modelos iniciales con SQLAlchemy

### 🔧 Técnico
- **SQLite**: Base de datos inicial
- **FastAPI**: Framework web principal
- **SQLAlchemy**: ORM para base de datos
- **Uvicorn**: Servidor ASGI

## [1.0.0] - 2024-12-10

### 🎉 Añadido
- **Proyecto Inicial**: Estructura básica del proyecto
- **Configuración**: Setup inicial con Python y dependencias
- **Git Repository**: Inicialización del repositorio

### 🔧 Técnico
- **Python 3.9+**: Versión mínima de Python
- **Virtual Environment**: Configuración de entorno virtual
- **Requirements**: Dependencias básicas del proyecto

## 📋 Notas de Migración

### De v1.5.0 a v2.0.0

#### Cambios Críticos
1. **Base de Datos**: 
   - Clientes ahora usan cédula como PK en lugar de ID numérico
   - Nuevos campos en modelo Cliente (barrio, indicaciones_adicionales, etc.)
   - Modelo Mensaje añadido para historial de chat

2. **APIs**:
   - Endpoints de clientes cambiaron de `/clientes/{id}` a `/clientes/{cedula}`
   - Nuevos endpoints multimodales en `/chat/`
   - Estructura de respuesta actualizada

3. **Configuración**:
   - `OPENAI_API_KEY` ahora opcional (solo para audio)
   - `GOOGLE_API_KEY` ahora requerida
   - Nuevas variables de entorno para Telegram

#### Script de Migración
```bash
# Migrar datos de clientes existentes
python migrate_clientes.py

# Actualizar índices FAISS
python -c "from app.services.retrieval.faiss_retriever import FAISSRetriever; import asyncio; asyncio.run(FAISSRetriever(db).build_index())"

# Verificar migración
python test_sistema_clientes.py
```

## 🔮 Roadmap

### v2.1.0 (Próxima Release)
- [ ] **Autenticación JWT**: Sistema completo de autenticación
- [ ] **PostgreSQL**: Migración de SQLite a PostgreSQL
- [ ] **Dashboard Web**: Interfaz web de administración
- [ ] **Exportación Excel**: Soporte para archivos Excel
- [ ] **Cache Redis**: Sistema de caché distribuido
- [ ] **Health Checks**: Endpoints de salud del sistema

### v2.2.0 (Futuro)
- [ ] **Multi-empresa**: Soporte completo para múltiples empresas
- [ ] **Webhooks**: Sistema de webhooks para integraciones
- [ ] **Analytics**: Dashboard de analytics avanzado
- [ ] **Mobile App**: Aplicación móvil nativa
- [ ] **WhatsApp Bot**: Integración con WhatsApp Business

### v3.0.0 (Visión)
- [ ] **Microservicios**: Arquitectura de microservicios
- [ ] **Kubernetes**: Despliegue en Kubernetes
- [ ] **Machine Learning**: Modelos personalizados de ML
- [ ] **Real-time**: Comunicación en tiempo real
- [ ] **Multi-idioma**: Soporte para múltiples idiomas

## 📊 Métricas de Release

### v2.0.0 Estadísticas
- **Líneas de Código**: ~15,000 líneas
- **Archivos Python**: 45+ archivos
- **Endpoints API**: 25+ endpoints
- **Modelos de Datos**: 7 modelos principales
- **Tests**: 15+ tests automatizados
- **Documentación**: 5 archivos de documentación

### Performance Benchmarks
- **Tiempo de Respuesta RAG**: 2-7 segundos
- **Búsqueda FAISS**: < 100ms
- **Consultas DB**: < 200ms
- **Transcripción Audio**: 1-3 segundos
- **Procesamiento Imagen**: 2-5 segundos

## 🏷️ Tags y Releases

### Convención de Tags
- **v2.0.0**: Release principal con cambios mayores
- **v2.0.1**: Hotfix para bugs críticos
- **v2.1.0-beta**: Pre-release para testing
- **v2.1.0-rc1**: Release candidate

### Proceso de Release
1. **Development**: Desarrollo en ramas feature
2. **Testing**: Tests automatizados y manuales
3. **Documentation**: Actualización de documentación
4. **Tagging**: Creación de tag con versión
5. **Deployment**: Despliegue a producción

## 🤝 Contribuciones

### Tipos de Cambios
- **feat**: Nueva funcionalidad
- **fix**: Corrección de bugs
- **docs**: Cambios en documentación
- **style**: Cambios de formato (no afectan código)
- **refactor**: Refactorización de código
- **test**: Añadir o modificar tests
- **chore**: Cambios en build o herramientas

### Ejemplo de Commit
```
feat(rag): implementar búsqueda semántica con FAISS

- Añadir FAISSRetriever para búsqueda vectorial
- Integrar con Gemini embeddings
- Implementar fallback a búsqueda por texto
- Optimizar performance para datasets medianos

Closes #123
```

---

**Changelog v2.0 - Agente Vendedor Inteligente**
**Documentación precisa de todos los cambios implementados**

## 🚀 [v2.3.0] - 2025-05-27

### ✨ **Nuevas Funcionalidades**

#### 🏷️ **Sistema de Categorías para Productos**
- **Agregado campo `categoria`** al modelo de productos
- **Migración automática** para agregar columna categoria a la BD
- **Categorización automática** basada en nombres de productos existentes
- **Exportador CSV actualizado** para incluir categorías

#### 📤 **Reglas Inteligentes para Carga CSV**
- **REGLA 1**: CSV sin columna categoria → categoria = "General"
- **REGLA 2**: Celdas vacías de categoria → categoria = "General"  
- **REGLA 3**: Actualización completa (stock, precio, categoria) para productos existentes
- **Validación robusta** de valores NULL, vacíos y NaN

#### 🔘 **Sistema AI Botón - Persistencia Completa**
- **Estado por defecto**: Botón Sistema AI siempre inicia en ON
- **Persistencia total**: Estado se mantiene entre recargas y cierres de página
- **Inicialización automática** al arrancar el servidor
- **Hook React y componente** documentados para implementación frontend

### 🛠️ **Mejoras Técnicas**

#### 🗄️ **Base de Datos**
- Agregada columna `categoria VARCHAR(100)` a tabla productos
- Migración SQLite compatible con `PRAGMA table_info`
- Asignación automática de categorías por defecto a productos existentes

#### 📊 **CSV Exporter**
- Corregido error de campos inexistentes (`fecha_creacion`)
- Agregada columna Categoría al export de inventario
- Headers optimizados y campos validados

#### 🔧 **API Endpoints**
- `/productos/reemplazar_csv` mejorado con nuevas reglas
- Documentación actualizada con casos de uso
- Validación robusta de formatos CSV

### 📚 **Documentación Agregada**

#### 📖 **Guías Completas**
- `GUIA_BOTON_SISTEMA_AI.md` - Implementación completa del botón persistente
- `GUIA_REGLAS_CATEGORIA_CSV.md` - Reglas y ejemplos de categorización
- `GUIA_VERIFICACION_CSV_FRONTEND.md` - Verificación de sincronización CSV→RAG

#### 🧪 **Scripts de Verificación**
- Tests automáticos para reglas de categoría
- Verificación de sincronización CSV→RAG
- Diagnóstico de búsquedas específicas en RAG

### 🔄 **Cambios en Archivos Principales**

#### `app/models/producto.py`
```python
# Agregado campo categoria
categoria = Column(String(100), nullable=True)
```

#### `app/api/producto.py`
```python
# Nuevas reglas de categorización automática
def asignar_categoria_defecto(nombre, categoria_csv=None):
    if not categoria_csv or str(categoria_csv).strip() == '' or str(categoria_csv).lower() == 'nan':
        return "General"
    return str(categoria_csv).strip()
```

#### `app/services/chat_control_service.py`
```python
# Función para asegurar estado por defecto
async def ensure_default_global_state(db: AsyncSession):
    """Asegura que exista un registro por defecto con IA activa"""
```

### 🧹 **Módulos Eliminados**

#### 🗑️ **Limpieza de Código**
- Eliminado módulo completo de `contextos` API (mantenido solo para código interno)
- Archivos removidos:
  - `app/api/contexto.py`
  - `app/services/contexto_service.py`
  - `app/schemas/contexto.py`
  - `app/models/contexto_empresa.py`
  - Documentación relacionada

### ✅ **Verificaciones Exitosas**

#### 🧪 **Tests Pasados**
- ✅ Botón Sistema AI: Estado persistente ON por defecto
- ✅ CSV sin categoria: Asignación automática "General"
- ✅ CSV con categorías: Actualización completa de productos
- ✅ Exportador CSV: Funcionando sin errores
- ✅ Sincronización RAG: Productos disponibles inmediatamente

#### 📈 **Métricas de Calidad**
- **0 errores** en exportación CSV
- **100%** de productos con categoria asignada
- **Persistencia completa** del estado Sistema AI
- **Sincronización inmediata** CSV→RAG verificada

### 🎯 **Impacto para el Usuario**

#### 💼 **Frontend/UI**
- Botón Sistema AI siempre funcional y persistente
- Carga CSV más robusta con categorización automática
- Exportación de inventario con categorías incluidas

#### 🔧 **Backend/API**
- Endpoints más robustos y documentados
- Validaciones automáticas para casos edge
- Base de datos optimizada y migrada

#### 📊 **Gestión de Inventario**
- Categorización automática e inteligente
- Actualización completa de productos existentes
- Exportación mejorada con más información

### 🚀 **Próximos Pasos Sugeridos**

1. **Frontend**: Implementar botón Sistema AI usando la guía completa
2. **UX**: Probar carga CSV con diferentes formatos
3. **Analytics**: Utilizar exportación categorizada para reportes
4. **Optimización**: Considerar índices en campo categoria si el volumen crece

---

## 📋 **Resumen de Archivos Modificados**

### 🔄 **Archivos Principales**
- `app/models/producto.py` - Campo categoria agregado
- `app/schemas/producto.py` - Schema actualizado
- `app/api/producto.py` - Reglas CSV implementadas
- `app/services/csv_exporter.py` - Exportador corregido
- `app/services/chat_control_service.py` - Persistencia Sistema AI
- `app/main.py` - Inicialización automática

### 📚 **Documentación Nueva**
- `GUIA_BOTON_SISTEMA_AI.md` - Guía completa persistencia
- `GUIA_REGLAS_CATEGORIA_CSV.md` - Reglas categorización
- `GUIA_VERIFICACION_CSV_FRONTEND.md` - Verificación RAG
- `CHANGELOG.md` - Este archivo de cambios

### 🗑️ **Archivos Eliminados**
- Módulo completo de contextos API
- Scripts de migración temporales
- Archivos de prueba temporales

---

**Versión estable y completamente funcional** ✅ 