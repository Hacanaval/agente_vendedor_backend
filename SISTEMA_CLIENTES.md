# 👥 Sistema de Gestión de Clientes - Sextinvalle

## 📋 Resumen Ejecutivo

El sistema de gestión de clientes de Sextinvalle es una solución completa que consolida la información de todos los clientes y mantiene un historial detallado de sus compras. Utiliza la **cédula como identificador principal único** y se integra perfectamente con el chatbot conversacional mediante un **RAG especializado**.

## 🎯 Características Principales

### ✅ **Gestión Completa de Clientes**
- **Identificación única**: Cédula como ID principal
- **Información completa**: Datos personales, contacto y dirección
- **Estadísticas automáticas**: Total de compras y valor acumulado
- **Historial detallado**: Todas las compras con fechas y productos

### ✅ **RAG de Clientes Integrado**
- **Consultas inteligentes**: El chatbot puede consultar historial de cualquier cliente
- **Respuestas contextualizadas**: Información personalizada basada en el historial
- **Búsqueda avanzada**: Por nombre, cédula o teléfono
- **Estadísticas automáticas**: Análisis de comportamiento de compra

### ✅ **API Completa para Frontend**
- **8 endpoints especializados** para gestión de clientes
- **Documentación automática** con FastAPI
- **Validaciones robustas** y manejo de errores
- **Paginación y filtros** para grandes volúmenes de datos

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    SISTEMA DE CLIENTES                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │   CHATBOT RAG   │    │   API FRONTEND  │                │
│  │                 │    │                 │                │
│  │ • Consultas     │    │ • CRUD Clientes │                │
│  │ • Historial     │    │ • Estadísticas  │                │
│  │ • Búsquedas     │    │ • Reportes      │                │
│  └─────────────────┘    └─────────────────┘                │
│           │                       │                        │
│           └───────────┬───────────┘                        │
│                       │                                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              CLIENTE MANAGER                            │ │
│  │                                                         │ │
│  │ • Crear/Actualizar clientes                            │ │
│  │ • Gestionar historial de compras                       │ │
│  │ • Calcular estadísticas                                │ │
│  │ • Búsquedas y filtros                                  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                       │                                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                BASE DE DATOS                            │ │
│  │                                                         │ │
│  │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │ │
│  │ │   CLIENTES  │  │    VENTAS   │  │  PRODUCTOS  │      │ │
│  │ │             │  │             │  │             │      │ │
│  │ │ • Cédula PK │  │ • Cliente FK│  │ • Info      │      │ │
│  │ │ • Info      │  │ • Producto  │  │ • Stock     │      │ │
│  │ │ • Stats     │  │ • Fecha     │  │ • Precio    │      │ │
│  │ └─────────────┘  └─────────────┘  └─────────────┘      │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Modelo de Datos

### 🏷️ **Tabla: `clientes`**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `cedula` | VARCHAR(20) **PK** | Cédula del cliente (ID único) |
| `nombre_completo` | VARCHAR(200) | Nombre completo del cliente |
| `telefono` | VARCHAR(20) | Teléfono de contacto |
| `direccion` | TEXT | Dirección completa de entrega |
| `barrio` | VARCHAR(100) | Barrio de residencia |
| `indicaciones_adicionales` | TEXT | Indicaciones para entrega |
| `fecha_registro` | TIMESTAMP | Fecha de primer registro |
| `fecha_ultima_compra` | TIMESTAMP | Fecha de la última compra |
| `total_compras` | INTEGER | Número total de compras |
| `valor_total_compras` | INTEGER | Valor total acumulado |
| `activo` | BOOLEAN | Cliente activo en el sistema |
| `notas` | TEXT | Notas adicionales |

### 🔗 **Relación con Ventas**

La tabla `venta` ahora incluye:
- `cliente_cedula` (FK) → Relaciona cada venta con un cliente
- Actualización automática de estadísticas del cliente
- Historial completo de compras por cliente

## 🚀 Endpoints de API

### 📋 **Gestión de Clientes**

#### `GET /clientes/`
Lista clientes con búsqueda opcional
```bash
GET /clientes/?limite=20&busqueda=Juan
```

#### `GET /clientes/{cedula}`
Obtiene información detallada de un cliente
```bash
GET /clientes/12345678
```

#### `GET /clientes/{cedula}/historial`
Obtiene historial completo de compras
```bash
GET /clientes/12345678/historial?limite=50
```

#### `GET /clientes/{cedula}/estadisticas`
Obtiene estadísticas detalladas del cliente
```bash
GET /clientes/12345678/estadisticas
```

### 📊 **Análisis y Reportes**

#### `GET /clientes/top/compradores`
Obtiene los mejores clientes por valor de compras
```bash
GET /clientes/top/compradores?limite=10
```

#### `POST /clientes/{cedula}/consulta`
Consulta RAG sobre historial del cliente
```bash
POST /clientes/12345678/consulta
{
  "pregunta": "¿Qué productos ha comprado en los últimos 3 meses?"
}
```

#### `POST /clientes/buscar`
Búsqueda avanzada de clientes
```bash
POST /clientes/buscar
{
  "nombre": "Juan Pérez",
  "limite": 20
}
```

## 🤖 Integración con Chatbot

### 🔍 **Detección Automática de Consultas**

El chatbot detecta automáticamente consultas sobre clientes:

**Ejemplos de consultas detectadas:**
- "Historial del cliente 12345678"
- "¿Qué ha comprado el cliente Juan Pérez?"
- "Estadísticas del cliente 87654321"
- "Buscar cliente María López"

### 💬 **Tipos de Consultas Soportadas**

1. **Historial de Compras**
   ```
   Usuario: "Historial del cliente 12345678"
   Bot: "El cliente Juan Pérez (12345678) ha realizado 5 compras..."
   ```

2. **Estadísticas Detalladas**
   ```
   Usuario: "Estadísticas del cliente 12345678"
   Bot: "Análisis completo del cliente Juan Pérez..."
   ```

3. **Búsqueda por Nombre**
   ```
   Usuario: "Buscar cliente Juan"
   Bot: "Encontré 3 clientes con ese nombre..."
   ```

## 📈 Funcionalidades Avanzadas

### 🎯 **Estadísticas Automáticas**

Para cada cliente se calculan automáticamente:
- **Total de compras realizadas**
- **Valor total acumulado**
- **Promedio por compra**
- **Productos favoritos**
- **Compras por mes** (últimos 12 meses)
- **Días desde última compra**

### 🔄 **Actualización Automática**

El sistema se actualiza automáticamente cuando:
- Se completa un pedido → Se crea/actualiza el cliente
- Se registra una venta → Se actualiza el historial
- Se modifican datos → Se mantiene la consistencia

### 🔍 **Búsqueda Inteligente**

Búsqueda por múltiples criterios:
- **Nombre completo** (parcial o completo)
- **Cédula** (exacta o parcial)
- **Teléfono** (exacto o parcial)
- **Ordenamiento** por fecha de última compra o valor total

## 🛠️ Instalación y Configuración

### 1. **Ejecutar Migración de Base de Datos**
```bash
# Aplicar migración SQL
psql -d tu_base_datos -f migrations/create_clientes_table.sql
```

### 2. **Verificar Modelos**
Los modelos ya están integrados en el sistema:
- `app/models/cliente.py` ✅
- `app/models/venta.py` (actualizado) ✅

### 3. **Servicios Disponibles**
- `ClienteManager` → Gestión completa de clientes
- `RAGClientes` → Consultas inteligentes
- API endpoints → Integración con frontend

## 📝 Ejemplos de Uso

### 🔧 **Desde el Código**

```python
from app.services.cliente_manager import ClienteManager
from app.services.rag_clientes import RAGClientes

# Crear cliente
resultado = await ClienteManager.crear_o_actualizar_cliente({
    "cedula": "12345678",
    "nombre_completo": "Juan Pérez",
    "telefono": "3001234567",
    "direccion": "Calle 123 #45-67",
    "barrio": "Centro"
}, db)

# Consultar historial con RAG
respuesta = await RAGClientes.consultar_historial_cliente(
    "12345678", 
    "¿Qué productos ha comprado este año?", 
    db
)
```

### 🌐 **Desde la API**

```bash
# Obtener cliente
curl -X GET "http://localhost:8000/clientes/12345678"

# Consultar historial
curl -X POST "http://localhost:8000/clientes/12345678/consulta" \
  -H "Content-Type: application/json" \
  -d '{"pregunta": "¿Cuáles son sus productos favoritos?"}'

# Top compradores
curl -X GET "http://localhost:8000/clientes/top/compradores?limite=5"
```

### 💬 **Desde el Chatbot**

```
Usuario: "Historial del cliente 12345678"
Bot: "El cliente Juan Pérez García (Cédula: 12345678) ha realizado 8 compras por un valor total de $450,000. Sus productos favoritos son: Extintor 10 libras (3 unidades), Casco de seguridad amarillo (2 unidades)..."

Usuario: "¿Qué ha comprado María López?"
Bot: "Encontré al cliente María López Rodríguez (Cédula: 87654321) con 5 compras por un valor total de $280,000."
```

## 🔒 Seguridad y Validaciones

### ✅ **Validaciones Implementadas**
- **Cédula**: 6-12 dígitos, solo números
- **Teléfono**: Formato colombiano válido
- **Nombre**: Solo letras y espacios
- **Dirección**: Mínimo 10 caracteres
- **Datos requeridos**: Todos los campos obligatorios

### 🛡️ **Protecciones**
- **Manejo de errores robusto**
- **Logging completo** de operaciones
- **Transacciones atómicas** en base de datos
- **Validación de entrada** en todos los endpoints

## 📊 Métricas y Monitoreo

### 📈 **KPIs Disponibles**
- Total de clientes registrados
- Clientes activos vs inactivos
- Valor promedio por cliente
- Frecuencia de compra promedio
- Top 10 clientes por valor
- Distribución geográfica (por barrio)

### 🔍 **Logs y Auditoría**
- Creación/actualización de clientes
- Consultas RAG realizadas
- Errores y excepciones
- Rendimiento de consultas

## 🚀 Próximas Mejoras

### 🎯 **Funcionalidades Planificadas**
- [ ] **Segmentación de clientes** por comportamiento
- [ ] **Recomendaciones personalizadas** basadas en historial
- [ ] **Alertas automáticas** para clientes inactivos
- [ ] **Dashboard visual** con gráficos y métricas
- [ ] **Exportación de reportes** en PDF/Excel
- [ ] **Integración con CRM** externo

### 🔧 **Optimizaciones Técnicas**
- [ ] **Cache de consultas** frecuentes
- [ ] **Índices adicionales** para mejor rendimiento
- [ ] **Paginación avanzada** para grandes datasets
- [ ] **Compresión de datos** históricos antiguos

---

## 📞 Soporte

Para soporte técnico o consultas sobre el sistema de clientes:
- **Documentación API**: `/docs` (Swagger automático)
- **Logs del sistema**: Revisar archivos de log para debugging
- **Base de datos**: Consultar directamente las tablas `clientes` y `venta`

---

**✅ Sistema de Clientes - Completamente Implementado y Documentado**
*Integración perfecta con chatbot conversacional y frontend* 