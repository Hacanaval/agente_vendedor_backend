# 📋 Documentación Técnica - Agente Vendedor Inteligente

## 🏗️ Arquitectura del Sistema

### Diagrama de Arquitectura

```mermaid
graph TB
    subgraph "Frontend/Cliente"
        A[API Client]
        B[Swagger UI]
        C[Tests]
    end
    
    subgraph "API Layer"
        D[FastAPI Router]
        E[Middleware]
        F[Authentication]
    end
    
    subgraph "Business Logic"
        G[RAG Service]
        H[Cliente Manager]
        I[Pedidos Service]
        J[CSV Exporter]
    end
    
    subgraph "Data Layer"
        K[SQLAlchemy ORM]
        L[ChromaDB]
        M[SQLite DB]
    end
    
    subgraph "External Services"
        N[OpenAI API]
        O[File System]
    end
    
    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
    F --> H
    F --> I
    F --> J
    G --> K
    G --> L
    G --> N
    H --> K
    I --> K
    J --> K
    J --> O
    K --> M
```

### Componentes Principales

#### 1. API Layer (FastAPI)
- **Router Principal**: Gestión de rutas y endpoints
- **Middleware**: CORS, logging, manejo de errores
- **Validación**: Pydantic models para request/response

#### 2. Business Logic Layer
- **RAG Service**: Sistema de recuperación y generación aumentada
- **Cliente Manager**: Gestión completa de clientes
- **Pedidos Service**: Procesamiento de órdenes de venta
- **CSV Exporter**: Exportación de datos en múltiples formatos

#### 3. Data Layer
- **SQLAlchemy ORM**: Mapeo objeto-relacional
- **ChromaDB**: Base de datos vectorial para embeddings
- **SQLite**: Base de datos principal

## 🔧 Detalles de Implementación

### Sistema RAG (Retrieval-Augmented Generation)

#### Arquitectura RAG
```python
class RAGService:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.openai_client = OpenAI()
        self.collection = self.chroma_client.get_or_create_collection("productos")
    
    async def query(self, query: str, chat_id: str) -> str:
        # 1. Generar embedding de la consulta
        embedding = await self.generate_embedding(query)
        
        # 2. Buscar documentos similares
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=5
        )
        
        # 3. Construir contexto
        context = self.build_context(results)
        
        # 4. Generar respuesta con OpenAI
        response = await self.generate_response(query, context)
        
        return response
```

#### Flujo de Datos RAG
1. **Input**: Consulta del usuario
2. **Embedding**: Conversión a vector usando OpenAI
3. **Retrieval**: Búsqueda en ChromaDB por similitud
4. **Context Building**: Construcción del contexto relevante
5. **Generation**: Generación de respuesta con GPT-4
6. **Output**: Respuesta contextualizada

### Gestión de Clientes

#### Modelo de Datos
```python
class Cliente(Base):
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True)
    telefono = Column(String(20))
    direccion = Column(Text)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    activo = Column(Boolean, default=True)
    
    # Relaciones
    pedidos = relationship("Venta", back_populates="cliente")
```

#### Operaciones CRUD
```python
class ClienteManager:
    async def crear_cliente(self, cliente_data: ClienteCreate) -> Cliente:
        # Validación de datos
        # Verificación de duplicados
        # Creación en base de datos
        # Indexación en RAG de clientes
        
    async def buscar_clientes(self, query: str) -> List[Cliente]:
        # Búsqueda por nombre, email, teléfono
        # Búsqueda semántica usando RAG
        # Combinación de resultados
```

### Sistema de Exportación

#### Arquitectura de Exportación
```python
class CSVExporter:
    def __init__(self):
        self.export_dir = "./exports"
        
    async def exportar_clientes(self, filtros: dict) -> str:
        # 1. Consulta con filtros
        query = self.build_query(Cliente, filtros)
        
        # 2. Ejecución de consulta
        results = await self.db.execute(query)
        
        # 3. Transformación a DataFrame
        df = pd.DataFrame(results)
        
        # 4. Generación de CSV
        filename = self.generate_filename("clientes")
        filepath = os.path.join(self.export_dir, filename)
        df.to_csv(filepath, index=False)
        
        return filepath
```

#### Formatos Soportados
- **CSV**: Formato principal con configuración personalizable
- **JSON**: Para integraciones API
- **Excel**: En desarrollo

## 🗄️ Esquema de Base de Datos

### Tablas Principales

#### Clientes
```sql
CREATE TABLE clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    telefono VARCHAR(20),
    direccion TEXT,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE
);
```

#### Productos
```sql
CREATE TABLE productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(200) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10,2),
    stock INTEGER DEFAULT 0,
    categoria VARCHAR(100),
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### Ventas/Pedidos
```sql
CREATE TABLE ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER REFERENCES clientes(id),
    fecha_venta DATETIME DEFAULT CURRENT_TIMESTAMP,
    total DECIMAL(10,2),
    estado VARCHAR(50) DEFAULT 'pendiente',
    productos_json TEXT,
    metadatos_json TEXT
);
```

### Índices y Optimizaciones
```sql
-- Índices para búsquedas rápidas
CREATE INDEX idx_clientes_email ON clientes(email);
CREATE INDEX idx_clientes_nombre ON clientes(nombre);
CREATE INDEX idx_ventas_cliente ON ventas(cliente_id);
CREATE INDEX idx_ventas_fecha ON ventas(fecha_venta);
CREATE INDEX idx_productos_categoria ON productos(categoria);
```

## 🔌 API Endpoints

### Documentación de Endpoints

#### RAG System
```python
@router.post("/rag/query")
async def query_rag(request: RAGQueryRequest) -> RAGResponse:
    """
    Procesa consulta usando sistema RAG
    
    Args:
        request: Consulta del usuario y chat_id
        
    Returns:
        Respuesta generada por IA con contexto
    """
```

#### Gestión de Clientes
```python
@router.get("/clientes/")
async def listar_clientes(
    skip: int = 0,
    limit: int = 100,
    activo: bool = None
) -> List[ClienteResponse]:
    """Lista clientes con paginación y filtros"""

@router.post("/clientes/")
async def crear_cliente(cliente: ClienteCreate) -> ClienteResponse:
    """Crea nuevo cliente"""

@router.get("/clientes/buscar")
async def buscar_clientes(q: str) -> List[ClienteResponse]:
    """Búsqueda inteligente de clientes"""
```

#### Exportación
```python
@router.get("/exportar/clientes")
async def exportar_clientes(
    formato: str = "csv",
    fecha_desde: datetime = None,
    fecha_hasta: datetime = None
) -> FileResponse:
    """Exporta clientes con filtros"""
```

### Códigos de Respuesta
- **200**: Operación exitosa
- **201**: Recurso creado
- **400**: Error de validación
- **404**: Recurso no encontrado
- **422**: Error de procesamiento
- **500**: Error interno del servidor

## 🧪 Testing Strategy

### Tipos de Tests

#### 1. Unit Tests
```python
def test_crear_cliente():
    """Test unitario para creación de cliente"""
    cliente_data = ClienteCreate(
        nombre="Test Cliente",
        email="test@example.com"
    )
    cliente = cliente_manager.crear_cliente(cliente_data)
    assert cliente.nombre == "Test Cliente"
```

#### 2. Integration Tests
```python
def test_rag_completo():
    """Test de integración del sistema RAG"""
    # Test de flujo completo: query -> embedding -> retrieval -> generation
```

#### 3. End-to-End Tests
```python
def test_flujo_venta_completo():
    """Test E2E: crear cliente -> consultar productos -> crear pedido -> exportar"""
```

### Coverage Goals
- **Unit Tests**: 90%+ coverage
- **Integration Tests**: Flujos críticos
- **E2E Tests**: Casos de uso principales

## 🚀 Deployment

### Configuración de Producción

#### Variables de Entorno
```env
# Producción
ENVIRONMENT=production
DEBUG=false

# Base de Datos
DATABASE_URL=postgresql://user:pass@host:5432/db

# APIs Externas
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...

# Configuración RAG
CHROMA_PERSIST_DIRECTORY=/app/data/chroma_db
EMBEDDING_MODEL=text-embedding-ada-002

# Configuración de Exportación
EXPORT_DIRECTORY=/app/exports
MAX_EXPORT_RECORDS=50000
```

#### Docker Configuration
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/agente_vendedor
    depends_on:
      - db
      
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: agente_vendedor
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 📊 Monitoring y Logging

### Logging Strategy
```python
import logging
import structlog

# Configuración de logging estructurado
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
```

### Métricas Clave
- **Latencia de RAG**: Tiempo de respuesta del sistema
- **Throughput**: Requests por segundo
- **Error Rate**: Porcentaje de errores
- **Database Performance**: Tiempo de consultas
- **Export Success Rate**: Éxito en exportaciones

## 🔒 Seguridad

### Medidas de Seguridad Implementadas

#### 1. Autenticación y Autorización
```python
from fastapi.security import HTTPBearer
from jose import JWTError, jwt

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username
```

#### 2. Validación de Datos
```python
from pydantic import BaseModel, validator, EmailStr

class ClienteCreate(BaseModel):
    nombre: str
    email: EmailStr
    telefono: Optional[str] = None
    
    @validator('nombre')
    def validate_nombre(cls, v):
        if len(v) < 2:
            raise ValueError('Nombre debe tener al menos 2 caracteres')
        return v.strip()
```

#### 3. Rate Limiting
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/rag/query")
@limiter.limit("10/minute")
async def query_rag(request: Request, query: RAGQueryRequest):
    # Endpoint con rate limiting
```

### Buenas Prácticas de Seguridad
- **Sanitización de Inputs**: Validación estricta de datos de entrada
- **SQL Injection Prevention**: Uso de ORM y queries parametrizadas
- **XSS Protection**: Escape de datos en respuestas
- **CORS Configuration**: Configuración restrictiva de CORS
- **Environment Variables**: Secrets en variables de entorno

## 📈 Performance Optimization

### Optimizaciones Implementadas

#### 1. Database Optimization
```python
# Uso de índices
class Cliente(Base):
    __tablename__ = "clientes"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True)  # Índice único
    nombre = Column(String(100), index=True)  # Índice para búsquedas

# Queries optimizadas
async def get_clientes_with_pedidos():
    return await db.execute(
        select(Cliente)
        .options(selectinload(Cliente.pedidos))  # Eager loading
        .where(Cliente.activo == True)
    )
```

#### 2. Caching Strategy
```python
from functools import lru_cache
import redis

# Cache en memoria para embeddings
@lru_cache(maxsize=1000)
def get_embedding(text: str) -> List[float]:
    return openai.Embedding.create(input=text)

# Cache Redis para consultas frecuentes
redis_client = redis.Redis(host='localhost', port=6379, db=0)

async def get_productos_cached():
    cached = redis_client.get("productos_list")
    if cached:
        return json.loads(cached)
    
    productos = await get_productos_from_db()
    redis_client.setex("productos_list", 300, json.dumps(productos))
    return productos
```

#### 3. Async Operations
```python
import asyncio
import aiofiles

async def process_multiple_exports(export_requests: List[ExportRequest]):
    """Procesamiento asíncrono de múltiples exportaciones"""
    tasks = [
        export_data(request) for request in export_requests
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Métricas de Performance
- **RAG Query Time**: < 2 segundos promedio
- **Database Query Time**: < 100ms promedio
- **Export Generation**: < 30 segundos para 10k registros
- **Memory Usage**: < 512MB en operación normal
- **CPU Usage**: < 50% en carga normal

## 🔄 Maintenance y Updates

### Estrategia de Mantenimiento

#### 1. Database Migrations
```python
# Alembic migration example
def upgrade():
    op.add_column('clientes', sa.Column('fecha_ultima_compra', sa.DateTime()))
    op.create_index('idx_clientes_ultima_compra', 'clientes', ['fecha_ultima_compra'])

def downgrade():
    op.drop_index('idx_clientes_ultima_compra')
    op.drop_column('clientes', 'fecha_ultima_compra')
```

#### 2. Data Backup Strategy
```bash
#!/bin/bash
# Backup script
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# Database backup
sqlite3 app.db ".backup $BACKUP_DIR/app_$DATE.db"

# ChromaDB backup
tar -czf "$BACKUP_DIR/chroma_$DATE.tar.gz" ./chroma_db/

# Exports backup
tar -czf "$BACKUP_DIR/exports_$DATE.tar.gz" ./exports/
```

#### 3. Health Checks
```python
@app.get("/health")
async def health_check():
    """Endpoint de health check"""
    checks = {
        "database": await check_database_connection(),
        "chromadb": await check_chromadb_connection(),
        "openai": await check_openai_api(),
        "disk_space": check_disk_space()
    }
    
    status = "healthy" if all(checks.values()) else "unhealthy"
    return {"status": status, "checks": checks}
```

## 📚 Referencias y Recursos

### Documentación Externa
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)

### Librerías Utilizadas
- **fastapi**: Framework web moderno
- **sqlalchemy**: ORM para Python
- **chromadb**: Base de datos vectorial
- **openai**: Cliente oficial de OpenAI
- **pandas**: Manipulación de datos
- **pydantic**: Validación de datos
- **alembic**: Migraciones de base de datos
- **uvicorn**: Servidor ASGI

### Recursos de Aprendizaje
- [RAG Implementation Guide](https://python.langchain.com/docs/use_cases/question_answering)
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
- [SQLAlchemy Performance Tips](https://docs.sqlalchemy.org/en/14/orm/loading_relationships.html)

---

**Documentación Técnica v2.0 - Agente Vendedor Inteligente** 