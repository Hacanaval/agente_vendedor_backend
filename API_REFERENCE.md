# 📚 API Reference - Agente Vendedor

## 🌐 Información General

- **Base URL**: `http://localhost:8001` (desarrollo) / `https://yourdomain.com` (producción)
- **Formato de respuesta**: JSON
- **Autenticación**: No requerida (v2.0.0)
- **Rate Limiting**: 100 requests/minuto por IP

## 📋 Tabla de Contenidos

- [Chat API](#chat-api)
- [Productos API](#productos-api)
- [Clientes API](#clientes-api)
- [Ventas API](#ventas-api)
- [Sistema API](#sistema-api)
- [Modelos de Datos](#modelos-de-datos)
- [Códigos de Error](#códigos-de-error)

## 💬 Chat API

### POST /api/chat/
Procesa un mensaje del usuario y devuelve una respuesta del chatbot.

#### Request Body
```json
{
    "mensaje": "qué productos tienen disponibles",
    "session_id": "unique-session-id-here"
}
```

#### Response Success (200)
```json
{
    "respuesta": "📦 **CATÁLOGO DE PRODUCTOS DISPONIBLES**\n\n🦺 **EPP**\n• Casco de Seguridad Amarillo\n  💰 Precio: $25,000\n...",
    "estado": "consultando_productos",
    "session_id": "unique-session-id-here",
    "pedido_actual": {},
    "timestamp": "2024-12-10T15:30:00Z"
}
```

#### Response Error (400)
```json
{
    "detail": "El mensaje no puede estar vacío"
}
```

#### Ejemplos de Uso

**Consulta de Inventario**
```bash
curl -X POST "http://localhost:8001/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "mensaje": "qué productos tienen disponibles",
    "session_id": "demo_session_001"
  }'
```

**Intención de Compra**
```bash
curl -X POST "http://localhost:8001/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "mensaje": "necesito 5 extintores de 10 libras",
    "session_id": "demo_session_001"
  }'
```

**Ver Pedido Actual**
```bash
curl -X POST "http://localhost:8001/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "mensaje": "mostrar mi pedido actual",
    "session_id": "demo_session_001"
  }'
```

## 🛍️ Productos API

### GET /api/productos/
Obtiene lista de todos los productos disponibles.

#### Query Parameters
- `categoria` (optional): Filtrar por categoría (EPP, Extintores, Señalización)
- `disponible` (optional): Filtrar por disponibilidad (true/false)
- `limit` (optional): Número máximo de resultados (default: 100)
- `offset` (optional): Número de resultados a omitir (default: 0)

#### Response Success (200)
```json
{
    "productos": [
        {
            "id": 1,
            "nombre": "Extintor 10 Libras ABC",
            "descripcion": "Extintor de polvo químico seco ABC, ideal para todo tipo de fuegos",
            "precio": 15000.0,
            "categoria": "Extintores",
            "disponible": true,
            "stock": 50,
            "imagen_url": null,
            "fecha_creacion": "2024-12-01T10:00:00Z",
            "fecha_actualizacion": "2024-12-01T10:00:00Z"
        }
    ],
    "total": 7,
    "limit": 100,
    "offset": 0
}
```

### GET /api/productos/{id}
Obtiene un producto específico por ID.

#### Response Success (200)
```json
{
    "id": 1,
    "nombre": "Extintor 10 Libras ABC",
    "descripcion": "Extintor de polvo químico seco ABC",
    "precio": 15000.0,
    "categoria": "Extintores",
    "disponible": true,
    "stock": 50,
    "imagen_url": null
}
```

#### Response Error (404)
```json
{
    "detail": "Producto no encontrado"
}
```

### POST /api/productos/
Crea un nuevo producto.

#### Request Body
```json
{
    "nombre": "Nuevo Producto",
    "descripcion": "Descripción del producto",
    "precio": 25000.0,
    "categoria": "EPP",
    "disponible": true,
    "stock": 100,
    "imagen_url": "https://example.com/image.jpg"
}
```

### PUT /api/productos/{id}
Actualiza un producto existente.

### DELETE /api/productos/{id}
Elimina un producto.

## 👥 Clientes API

### GET /api/clientes/
Obtiene lista de clientes con paginación.

#### Query Parameters
- `limit` (optional): Número máximo de resultados (default: 50)
- `offset` (optional): Número de resultados a omitir (default: 0)
- `buscar` (optional): Buscar por nombre, cédula, email o teléfono

#### Response Success (200)
```json
{
    "clientes": [
        {
            "id": 1,
            "nombre": "María Fernanda López",
            "cedula": "1098765432",
            "telefono": "3001234567",
            "email": "maria.lopez@empresa.com",
            "direccion": "Carrera 15 #45-67",
            "barrio": "La Candelaria",
            "indicaciones_entrega": "Edificio azul, portón café, timbre #301",
            "fecha_registro": "2024-12-10T14:30:00Z"
        }
    ],
    "total": 1,
    "limit": 50,
    "offset": 0
}
```

### GET /api/clientes/{id}
Obtiene un cliente específico por ID.

### GET /api/clientes/cedula/{cedula}
Obtiene un cliente por número de cédula.

#### Response Success (200)
```json
{
    "id": 1,
    "nombre": "María Fernanda López",
    "cedula": "1098765432",
    "telefono": "3001234567",
    "email": "maria.lopez@empresa.com",
    "direccion": "Carrera 15 #45-67",
    "barrio": "La Candelaria",
    "indicaciones_entrega": "Edificio azul, portón café, timbre #301",
    "fecha_registro": "2024-12-10T14:30:00Z",
    "ventas": [
        {
            "id": 1,
            "total": 300000.0,
            "fecha_venta": "2024-12-10T15:00:00Z",
            "estado": "confirmada"
        }
    ]
}
```

### POST /api/clientes/
Crea un nuevo cliente.

#### Request Body
```json
{
    "nombre": "Juan Pérez García",
    "cedula": "1234567890",
    "telefono": "3009876543",
    "email": "juan.perez@email.com",
    "direccion": "Calle 123 #45-67",
    "barrio": "Centro",
    "indicaciones_entrega": "Apartamento 302, intercomunicador"
}
```

#### Validaciones
- `cedula`: Debe tener entre 7 y 10 dígitos, debe ser única
- `telefono`: Debe tener 10 dígitos y comenzar con 3
- `email`: Debe tener formato válido de email
- `nombre`: Mínimo 2 caracteres, máximo 100

### PUT /api/clientes/{id}
Actualiza un cliente existente.

### DELETE /api/clientes/{id}
Elimina un cliente.

## 💰 Ventas API

### GET /api/ventas/
Obtiene lista de ventas con filtros.

#### Query Parameters
- `cliente_id` (optional): Filtrar por ID de cliente
- `estado` (optional): Filtrar por estado (pendiente, confirmada, entregada)
- `fecha_inicio` (optional): Fecha de inicio (YYYY-MM-DD)
- `fecha_fin` (optional): Fecha de fin (YYYY-MM-DD)
- `limit` (optional): Número máximo de resultados (default: 50)
- `offset` (optional): Número de resultados a omitir (default: 0)

#### Response Success (200)
```json
{
    "ventas": [
        {
            "id": 1,
            "cliente_id": 1,
            "cliente": {
                "nombre": "María Fernanda López",
                "cedula": "1098765432"
            },
            "productos": [
                {
                    "producto_id": 1,
                    "nombre": "Extintor 10 Libras ABC",
                    "cantidad": 5,
                    "precio_unitario": 15000.0,
                    "subtotal": 75000.0
                },
                {
                    "producto_id": 3,
                    "nombre": "Casco de Seguridad Amarillo",
                    "cantidad": 3,
                    "precio_unitario": 25000.0,
                    "subtotal": 75000.0
                }
            ],
            "total": 150000.0,
            "estado": "confirmada",
            "fecha_venta": "2024-12-10T15:00:00Z",
            "session_id": "demo_session_001",
            "notas": null
        }
    ],
    "total": 1,
    "estadisticas": {
        "total_ventas": 150000.0,
        "cantidad_ventas": 1,
        "promedio_venta": 150000.0
    }
}
```

### GET /api/ventas/{id}
Obtiene una venta específica por ID.

### POST /api/ventas/
Crea una nueva venta manualmente.

#### Request Body
```json
{
    "cliente_id": 1,
    "productos": [
        {
            "producto_id": 1,
            "cantidad": 2,
            "precio_unitario": 15000.0
        }
    ],
    "notas": "Entrega urgente"
}
```

### PUT /api/ventas/{id}/estado
Actualiza el estado de una venta.

#### Request Body
```json
{
    "estado": "entregada",
    "notas": "Entregado exitosamente"
}
```

### GET /api/ventas/exportar-csv
Exporta ventas a formato CSV.

#### Query Parameters
- `fecha_inicio` (optional): Fecha de inicio (YYYY-MM-DD)
- `fecha_fin` (optional): Fecha de fin (YYYY-MM-DD)
- `cliente_id` (optional): Filtrar por cliente específico

#### Response Success (200)
```
Content-Type: text/csv
Content-Disposition: attachment; filename="ventas_2024-12-10.csv"

ID,Cliente,Cedula,Total,Estado,Fecha,Productos
1,"María Fernández","1098765432",150000.0,"confirmada","2024-12-10 15:00:00","Extintor 10 Libras ABC (5), Casco de Seguridad Amarillo (3)"
```

## 🔧 Sistema API

### GET /health
Endpoint de health check para monitoreo.

#### Response Success (200)
```json
{
    "status": "healthy",
    "database": "connected",
    "openai": "configured",
    "version": "2.0.0",
    "timestamp": "2024-12-10T15:30:00Z"
}
```

#### Response Error (503)
```json
{
    "status": "unhealthy",
    "error": "Database connection failed",
    "timestamp": "2024-12-10T15:30:00Z"
}
```

### GET /metrics
Obtiene métricas básicas del sistema.

#### Response Success (200)
```json
{
    "cpu_percent": 25.5,
    "memory_percent": 45.2,
    "disk_percent": 60.8,
    "requests_total": 1250,
    "requests_last_hour": 45,
    "active_sessions": 12,
    "database_connections": 5
}
```

### GET /api/chat/sessions/{session_id}/historial
Obtiene el historial de conversación de una sesión.

#### Response Success (200)
```json
{
    "session_id": "demo_session_001",
    "historial": [
        {
            "timestamp": "2024-12-10T14:30:00Z",
            "tipo": "usuario",
            "mensaje": "qué productos tienen disponibles"
        },
        {
            "timestamp": "2024-12-10T14:30:01Z",
            "tipo": "bot",
            "mensaje": "📦 **CATÁLOGO DE PRODUCTOS DISPONIBLES**..."
        }
    ],
    "estado_actual": "consultando_productos",
    "pedido_actual": {},
    "fecha_creacion": "2024-12-10T14:30:00Z"
}
```

### DELETE /api/chat/sessions/{session_id}
Elimina una sesión de chat y su historial.

#### Response Success (200)
```json
{
    "mensaje": "Sesión eliminada exitosamente",
    "session_id": "demo_session_001"
}
```

## 📊 Modelos de Datos

### Producto
```typescript
interface Producto {
    id: number;
    nombre: string;
    descripcion?: string;
    precio: number;
    categoria: "EPP" | "Extintores" | "Señalización";
    disponible: boolean;
    stock: number;
    imagen_url?: string;
    fecha_creacion: string; // ISO 8601
    fecha_actualizacion: string; // ISO 8601
}
```

### Cliente
```typescript
interface Cliente {
    id: number;
    nombre: string;
    cedula: string; // Único, 7-10 dígitos
    telefono: string; // 10 dígitos, inicia con 3
    email: string;
    direccion: string;
    barrio?: string;
    indicaciones_entrega?: string;
    fecha_registro: string; // ISO 8601
}
```

### Venta
```typescript
interface Venta {
    id: number;
    cliente_id: number;
    cliente?: Cliente;
    productos: ProductoVenta[];
    total: number;
    estado: "pendiente" | "confirmada" | "entregada" | "cancelada";
    fecha_venta: string; // ISO 8601
    session_id?: string;
    notas?: string;
}

interface ProductoVenta {
    producto_id: number;
    nombre: string;
    cantidad: number;
    precio_unitario: number;
    subtotal: number;
}
```

### ChatControl
```typescript
interface ChatControl {
    id: number;
    session_id: string;
    estado_actual: "inicio" | "consultando_productos" | "agregando_productos" | 
                   "confirmando_pedido" | "recolectando_datos_cliente" | 
                   "finalizando_venta" | "venta_completada";
    pedido_actual: PedidoActual;
    datos_cliente: DatosCliente;
    historial_conversacion: MensajeHistorial[];
    fecha_creacion: string; // ISO 8601
    fecha_actualizacion: string; // ISO 8601
    activo: boolean;
}

interface PedidoActual {
    productos: { [producto_id: string]: { cantidad: number; precio: number } };
    total: number;
}

interface DatosCliente {
    nombre?: string;
    cedula?: string;
    telefono?: string;
    email?: string;
    direccion?: string;
    barrio?: string;
    indicaciones?: string;
}

interface MensajeHistorial {
    timestamp: string;
    tipo: "usuario" | "bot";
    mensaje: string;
}
```

## ⚠️ Códigos de Error

### 400 - Bad Request
```json
{
    "detail": "El mensaje no puede estar vacío"
}
```

### 404 - Not Found
```json
{
    "detail": "Producto no encontrado"
}
```

### 422 - Validation Error
```json
{
    "detail": [
        {
            "loc": ["body", "cedula"],
            "msg": "Cédula debe tener entre 7 y 10 dígitos",
            "type": "value_error"
        }
    ]
}
```

### 500 - Internal Server Error
```json
{
    "detail": "Error interno del servidor",
    "error_id": "uuid-error-id"
}
```

### 503 - Service Unavailable
```json
{
    "detail": "Servicio temporalmente no disponible",
    "retry_after": 30
}
```

## 🔄 Ejemplos de Flujos Completos

### Flujo de Venta Completa

#### 1. Consulta Inicial
```bash
curl -X POST "http://localhost:8001/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "mensaje": "necesito 2 extintores de 10 libras",
    "session_id": "venta_completa_001"
  }'
```

#### 2. Confirmación de Pedido
```bash
curl -X POST "http://localhost:8001/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "mensaje": "sí, procedamos con el pedido",
    "session_id": "venta_completa_001"
  }'
```

#### 3. Proporcionar Datos del Cliente
```bash
curl -X POST "http://localhost:8001/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "mensaje": "Juan Pérez, 1234567890, 3009876543, juan@email.com, Calle 123 #45-67, Centro",
    "session_id": "venta_completa_001"
  }'
```

#### 4. Verificar Venta Creada
```bash
curl -X GET "http://localhost:8001/api/ventas/?session_id=venta_completa_001"
```

### Flujo de Consulta de Cliente

#### 1. Buscar Cliente por Cédula
```bash
curl -X GET "http://localhost:8001/api/clientes/cedula/1234567890"
```

#### 2. Consultar Historial de Compras
```bash
curl -X GET "http://localhost:8001/api/ventas/?cliente_id=1"
```

## 📋 Rate Limiting

### Límites por Endpoint

| Endpoint | Límite | Ventana |
|----------|--------|---------|
| `/api/chat/` | 60 requests | 1 minuto |
| `/api/productos/` | 100 requests | 1 minuto |
| `/api/clientes/` | 100 requests | 1 minuto |
| `/api/ventas/` | 100 requests | 1 minuto |
| `/health` | Sin límite | - |

### Headers de Rate Limiting

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1670681400
```

## 🔐 Seguridad

### Headers de Seguridad Requeridos

```
Content-Type: application/json
Accept: application/json
User-Agent: Your-App/1.0
```

### Sanitización de Datos
- Todos los inputs son sanitizados automáticamente
- Caracteres peligrosos (`<`, `>`, `"`, `'`) son removidos
- Longitud máxima de 1000 caracteres por mensaje

### CORS
```
Access-Control-Allow-Origin: https://yourdomain.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

---

**API Reference Completa**  
**Versión**: 2.0.0  
**Actualizada**: Diciembre 2024  
**Cobertura**: 100% de endpoints documentados 