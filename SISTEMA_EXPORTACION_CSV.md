# 📊 Sistema de Exportación CSV - Sextinvalle

## 📋 Resumen Ejecutivo

El sistema de exportación CSV permite descargar todos los datos del sistema en formato CSV para análisis, reportes, respaldos y integración con herramientas externas. Incluye filtros avanzados, validaciones y soporte completo para Excel.

## 🎯 Características Principales

### ✅ **Exportaciones Disponibles**
- **📦 Inventario**: Productos completos con stock y categorías
- **👥 Clientes**: Base de datos completa con estadísticas
- **💰 Ventas**: Transacciones con detalles de cliente y producto
- **🤖 Conversaciones RAG**: Logs de interacciones del chatbot
- **📊 Reporte Completo**: Estadísticas generales del sistema

### ✅ **Filtros Avanzados**
- **Filtros por fecha**: Rangos personalizables
- **Filtros por estado**: Activos/inactivos, completadas/pendientes
- **Filtros por contenido**: Con/sin stock, con/sin compras
- **Inclusión selectiva**: Metadatos, detalles de cliente/producto

### ✅ **Compatibilidad Total**
- **UTF-8 con BOM**: Compatible con Excel en español
- **Nombres automáticos**: Archivos con timestamp
- **Validaciones robustas**: Formatos de fecha y parámetros
- **Streaming**: Descarga eficiente de archivos grandes

## 🚀 Endpoints de API

### 📦 **Exportar Inventario**

#### `GET /exportar/inventario`
Exporta el inventario completo de productos.

**Parámetros:**
- `incluir_inactivos` (bool): Incluir productos inactivos (default: false)
- `solo_con_stock` (bool): Solo productos con stock > 0 (default: false)

**Ejemplo:**
```bash
GET /exportar/inventario?incluir_inactivos=false&solo_con_stock=true
```

**Columnas del CSV:**
- ID, Nombre, Descripción, Precio, Stock, Categoría, Activo, Fecha Creación, Última Actualización

---

### 👥 **Exportar Clientes**

#### `GET /exportar/clientes`
Exporta la base de datos de clientes con estadísticas.

**Parámetros:**
- `incluir_inactivos` (bool): Incluir clientes inactivos (default: false)
- `con_compras` (bool): Solo clientes que han comprado (default: false)
- `fecha_desde` (string): Fecha desde en formato YYYY-MM-DD
- `fecha_hasta` (string): Fecha hasta en formato YYYY-MM-DD

**Ejemplo:**
```bash
GET /exportar/clientes?con_compras=true&fecha_desde=2024-01-01&fecha_hasta=2024-12-31
```

**Columnas del CSV:**
- Cédula, Nombre Completo, Teléfono, Dirección, Barrio, Indicaciones Adicionales, Fecha Registro, Fecha Última Compra, Total Compras, Valor Total Compras, Promedio por Compra, Activo, Notas

---

### 💰 **Exportar Ventas**

#### `GET /exportar/ventas`
Exporta las ventas con detalles completos de cliente y producto.

**Parámetros:**
- `fecha_desde` (string): Fecha desde en formato YYYY-MM-DD
- `fecha_hasta` (string): Fecha hasta en formato YYYY-MM-DD
- `estado` (string): Filtrar por estado específico
- `incluir_detalles_cliente` (bool): Incluir info del cliente (default: true)
- `incluir_detalles_producto` (bool): Incluir info del producto (default: true)

**Ejemplo:**
```bash
GET /exportar/ventas?fecha_desde=2024-12-01&incluir_detalles_cliente=true&incluir_detalles_producto=true
```

**Columnas del CSV (con detalles completos):**
- ID Venta, Fecha, Cantidad, Total, Estado, Chat ID, Producto ID, Producto Nombre, Producto Descripción, Precio Unitario, Cliente Cédula, Cliente Nombre, Cliente Teléfono, Cliente Dirección, Cliente Barrio

---

### 🤖 **Exportar Conversaciones RAG**

#### `GET /exportar/conversaciones-rag`
Exporta las conversaciones y consultas del sistema RAG.

**Parámetros:**
- `fecha_desde` (string): Fecha desde en formato YYYY-MM-DD
- `fecha_hasta` (string): Fecha hasta en formato YYYY-MM-DD
- `tipo_mensaje` (string): Filtrar por tipo (inventario, venta, contexto, cliente)
- `solo_con_rag` (bool): Solo mensajes que usaron RAG (default: true)
- `incluir_metadatos` (bool): Incluir metadatos detallados (default: true)

**Ejemplo:**
```bash
GET /exportar/conversaciones-rag?tipo_mensaje=cliente&incluir_metadatos=true
```

**Columnas del CSV (con metadatos):**
- ID, Chat ID, Timestamp, Remitente, Mensaje, Tipo Mensaje, Estado Venta, Respuesta, Metadatos JSON, Productos Mencionados, Cliente Detectado, Valor Venta

---

### 📊 **Exportar Reporte Completo**

#### `GET /exportar/reporte-completo`
Exporta un reporte con estadísticas generales del sistema.

**Parámetros:**
- `fecha_desde` (string): Fecha desde para filtrar ventas
- `fecha_hasta` (string): Fecha hasta para filtrar ventas

**Ejemplo:**
```bash
GET /exportar/reporte-completo?fecha_desde=2024-01-01&fecha_hasta=2024-12-31
```

**Columnas del CSV:**
- Métrica, Valor

---

### ℹ️ **Información de Exportación**

#### `GET /exportar/info`
Obtiene información sobre los datos disponibles para exportación.

**Respuesta:**
```json
{
  "info_exportacion": {
    "total_productos": 150,
    "productos_activos": 145,
    "productos_con_stock": 120,
    "total_clientes": 85,
    "clientes_activos": 80,
    "clientes_con_compras": 65,
    "total_ventas": 320,
    "ventas_completadas": 310,
    "total_mensajes": 1250,
    "mensajes_con_rag": 890,
    "rango_fechas_ventas": {
      "fecha_minima": "2024-01-15T10:30:00",
      "fecha_maxima": "2024-12-19T16:45:00"
    }
  },
  "formatos_disponibles": ["CSV"],
  "endpoints_disponibles": [
    "/exportar/inventario",
    "/exportar/clientes",
    "/exportar/ventas",
    "/exportar/conversaciones-rag",
    "/exportar/reporte-completo"
  ]
}
```

## 🔧 Integración con Frontend

### **JavaScript/TypeScript**

```javascript
// Función para descargar CSV
async function descargarCSV(endpoint, parametros = {}) {
    const url = new URL(`${BASE_URL}/exportar/${endpoint}`);
    
    // Agregar parámetros
    Object.keys(parametros).forEach(key => {
        if (parametros[key] !== null && parametros[key] !== undefined) {
            url.searchParams.append(key, parametros[key]);
        }
    });
    
    try {
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        
        // Obtener nombre del archivo desde headers
        const contentDisposition = response.headers.get('Content-Disposition');
        const filename = contentDisposition 
            ? contentDisposition.split('filename=')[1].replace(/"/g, '')
            : `export_${Date.now()}.csv`;
        
        // Crear blob y descargar
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        // Limpiar
        window.URL.revokeObjectURL(downloadUrl);
        document.body.removeChild(a);
        
        return { success: true, filename };
        
    } catch (error) {
        console.error('Error descargando CSV:', error);
        return { success: false, error: error.message };
    }
}

// Ejemplos de uso
async function ejemplosDescarga() {
    // Descargar inventario completo
    await descargarCSV('inventario', {
        incluir_inactivos: false,
        solo_con_stock: true
    });
    
    // Descargar clientes con compras
    await descargarCSV('clientes', {
        con_compras: true,
        fecha_desde: '2024-01-01',
        fecha_hasta: '2024-12-31'
    });
    
    // Descargar ventas del último mes
    const fechaHasta = new Date().toISOString().split('T')[0];
    const fechaDesde = new Date(Date.now() - 30*24*60*60*1000).toISOString().split('T')[0];
    
    await descargarCSV('ventas', {
        fecha_desde: fechaDesde,
        fecha_hasta: fechaHasta,
        incluir_detalles_cliente: true,
        incluir_detalles_producto: true
    });
    
    // Descargar conversaciones RAG
    await descargarCSV('conversaciones-rag', {
        solo_con_rag: true,
        incluir_metadatos: true
    });
    
    // Descargar reporte completo
    await descargarCSV('reporte-completo');
}
```

### **React Component**

```jsx
import React, { useState } from 'react';

const ExportacionCSV = () => {
    const [loading, setLoading] = useState(false);
    const [filtros, setFiltros] = useState({
        fecha_desde: '',
        fecha_hasta: '',
        incluir_inactivos: false,
        con_compras: false
    });
    
    const descargarCSV = async (tipo) => {
        setLoading(true);
        try {
            const resultado = await descargarCSV(tipo, filtros);
            if (resultado.success) {
                alert(`Archivo ${resultado.filename} descargado exitosamente`);
            } else {
                alert(`Error: ${resultado.error}`);
            }
        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <div className="exportacion-csv">
            <h2>📊 Exportar Datos a CSV</h2>
            
            {/* Filtros */}
            <div className="filtros">
                <h3>Filtros</h3>
                <div className="filtro-grupo">
                    <label>
                        Fecha Desde:
                        <input 
                            type="date" 
                            value={filtros.fecha_desde}
                            onChange={(e) => setFiltros({...filtros, fecha_desde: e.target.value})}
                        />
                    </label>
                    <label>
                        Fecha Hasta:
                        <input 
                            type="date" 
                            value={filtros.fecha_hasta}
                            onChange={(e) => setFiltros({...filtros, fecha_hasta: e.target.value})}
                        />
                    </label>
                </div>
                <div className="filtro-grupo">
                    <label>
                        <input 
                            type="checkbox" 
                            checked={filtros.incluir_inactivos}
                            onChange={(e) => setFiltros({...filtros, incluir_inactivos: e.target.checked})}
                        />
                        Incluir inactivos
                    </label>
                    <label>
                        <input 
                            type="checkbox" 
                            checked={filtros.con_compras}
                            onChange={(e) => setFiltros({...filtros, con_compras: e.target.checked})}
                        />
                        Solo con compras
                    </label>
                </div>
            </div>
            
            {/* Botones de descarga */}
            <div className="botones-descarga">
                <button 
                    onClick={() => descargarCSV('inventario')}
                    disabled={loading}
                    className="btn-exportar"
                >
                    📦 Exportar Inventario
                </button>
                
                <button 
                    onClick={() => descargarCSV('clientes')}
                    disabled={loading}
                    className="btn-exportar"
                >
                    👥 Exportar Clientes
                </button>
                
                <button 
                    onClick={() => descargarCSV('ventas')}
                    disabled={loading}
                    className="btn-exportar"
                >
                    💰 Exportar Ventas
                </button>
                
                <button 
                    onClick={() => descargarCSV('conversaciones-rag')}
                    disabled={loading}
                    className="btn-exportar"
                >
                    🤖 Exportar Conversaciones RAG
                </button>
                
                <button 
                    onClick={() => descargarCSV('reporte-completo')}
                    disabled={loading}
                    className="btn-exportar"
                >
                    📊 Exportar Reporte Completo
                </button>
            </div>
            
            {loading && <div className="loading">⏳ Generando archivo CSV...</div>}
        </div>
    );
};

export default ExportacionCSV;
```

## 🔒 Validaciones y Seguridad

### **Validaciones Implementadas**
- **Formatos de fecha**: Solo YYYY-MM-DD válidos
- **Parámetros booleanos**: true/false estrictos
- **Rangos de fecha**: fecha_desde <= fecha_hasta
- **Límites de memoria**: Streaming para archivos grandes
- **Encoding**: UTF-8 con BOM para compatibilidad

### **Manejo de Errores**
- **400 Bad Request**: Parámetros inválidos
- **404 Not Found**: Endpoint no existe
- **500 Internal Server Error**: Errores del servidor
- **Logs detallados**: Para debugging y monitoreo

## 📈 Casos de Uso

### **1. Análisis de Ventas**
```bash
# Exportar ventas del último trimestre con detalles completos
GET /exportar/ventas?fecha_desde=2024-10-01&fecha_hasta=2024-12-31&incluir_detalles_cliente=true&incluir_detalles_producto=true
```

### **2. Backup de Clientes**
```bash
# Exportar todos los clientes activos
GET /exportar/clientes?incluir_inactivos=false
```

### **3. Análisis de Inventario**
```bash
# Exportar solo productos con stock
GET /exportar/inventario?solo_con_stock=true&incluir_inactivos=false
```

### **4. Análisis de Conversaciones**
```bash
# Exportar conversaciones RAG del último mes
GET /exportar/conversaciones-rag?fecha_desde=2024-11-01&fecha_hasta=2024-12-01&incluir_metadatos=true
```

### **5. Reporte Ejecutivo**
```bash
# Reporte completo del año
GET /exportar/reporte-completo?fecha_desde=2024-01-01&fecha_hasta=2024-12-31
```

## 🛠️ Instalación y Configuración

### **1. Verificar Dependencias**
El sistema de exportación ya está incluido en el backend. No requiere dependencias adicionales.

### **2. Probar Endpoints**
```bash
# Verificar que el servidor esté corriendo
curl http://localhost:8001/

# Obtener información de exportación
curl http://localhost:8001/exportar/info

# Descargar inventario de prueba
curl -O -J http://localhost:8001/exportar/inventario
```

### **3. Integrar con Frontend**
1. Copiar las funciones JavaScript proporcionadas
2. Adaptar las URLs a tu configuración
3. Personalizar la UI según tu diseño
4. Agregar manejo de errores específico

## 📊 Métricas y Monitoreo

### **KPIs de Exportación**
- Número de exportaciones por día/mes
- Tipos de exportación más utilizados
- Tamaño promedio de archivos exportados
- Tiempo de generación de archivos
- Errores de exportación

### **Logs Disponibles**
- Solicitudes de exportación exitosas
- Errores de validación de parámetros
- Errores de generación de archivos
- Tiempo de procesamiento por tipo

## 🚀 Próximas Mejoras

### **Funcionalidades Planificadas**
- [ ] **Exportación programada**: Reportes automáticos
- [ ] **Múltiples formatos**: Excel, JSON, XML
- [ ] **Compresión**: ZIP para archivos grandes
- [ ] **Filtros avanzados**: Consultas SQL personalizadas
- [ ] **Templates**: Plantillas de exportación predefinidas
- [ ] **Notificaciones**: Email cuando la exportación esté lista

### **Optimizaciones Técnicas**
- [ ] **Cache de exportaciones**: Evitar regenerar archivos idénticos
- [ ] **Paginación**: Para datasets muy grandes
- [ ] **Compresión en tiempo real**: Reducir tamaño de descarga
- [ ] **Exportación asíncrona**: Para archivos muy grandes

---

## 📞 Soporte

Para soporte técnico o consultas sobre el sistema de exportación:
- **Documentación API**: `/docs` (Swagger automático)
- **Endpoint de información**: `/exportar/info`
- **Logs del sistema**: Revisar archivos de log para debugging

---

**✅ Sistema de Exportación CSV - Completamente Implementado**
*Listo para integración con frontend y uso en producción* 