# 🏷️ Guía: Reglas de Categoría en CSV

## ✅ **Reglas Implementadas**

### **REGLA 1: Categoría por Defecto "General"**
- ❌ **Si CSV NO tiene columna `categoria`** → categoria = `"General"`
- ❌ **Si celda de categoria está vacía** → categoria = `"General"`
- ❌ **Si celda de categoria es NULL** → categoria = `"General"`

### **REGLA 2: Actualización Completa en Productos Existentes**
- ✅ **Si SKU existe y CSV tiene categoria válida** → Actualiza stock, precio Y categoria
- ✅ **Si SKU existe y CSV no tiene categoria** → Actualiza stock, precio y categoria = `"General"`

## 📝 **Ejemplos Prácticos**

### **Ejemplo 1: CSV Sin Columna Categoria**
```csv
nombre,descripcion,precio,stock
"Extintor 5kg","Extintor de polvo ABC",45000,20
"Casco Amarillo","Casco de seguridad",25000,15
```

**Resultado:**
- Extintor 5kg → categoria = `"General"`
- Casco Amarillo → categoria = `"General"`

### **Ejemplo 2: CSV Con Categorías Válidas**
```csv
nombre,descripcion,precio,stock,categoria
"Extintor 5kg","Extintor de polvo ABC",45000,20,"Contra Incendios"
"Casco Amarillo","Casco de seguridad",25000,15,"Protección Cabeza"
"Producto Nuevo","Producto sin categoria específica",10000,5,""
```

**Resultado:**
- Extintor 5kg → categoria = `"Contra Incendios"`
- Casco Amarillo → categoria = `"Protección Cabeza"`
- Producto Nuevo → categoria = `"General"` (celda vacía)

### **Ejemplo 3: Actualización de Productos Existentes**

**Estado Inicial en BD:**
```
Extintor 5kg - precio: 40000, categoria: "General"
```

**CSV de Actualización:**
```csv
nombre,descripcion,precio,stock,categoria
"Extintor 5kg","Extintor mejorado",50000,25,"Contra Incendios"
```

**Resultado:**
- Extintor 5kg → precio: 50000, categoria: `"Contra Incendios"` ✅ **ACTUALIZADA**

## 🧪 **Casos de Prueba**

### **Caso 1: CSV Mixto (con y sin categorías)**
```csv
nombre,descripcion,precio,stock,categoria
"Producto A","Con categoria válida",15000,10,"Electrónicos"
"Producto B","Con categoria vacía",20000,8,""
"Producto C","Con categoria NULL",25000,12,
"Producto D","Con categoria válida",30000,15,"Herramientas"
```

**Resultado Esperado:**
- Producto A → categoria = `"Electrónicos"`
- Producto B → categoria = `"General"`
- Producto C → categoria = `"General"`
- Producto D → categoria = `"Herramientas"`

## 📋 **Formato CSV Requerido**

### **Columnas Obligatorias:**
```csv
nombre,descripcion,precio,stock
```

### **Columnas Opcionales:**
```csv
categoria
```

### **Formato Completo:**
```csv
nombre,descripcion,precio,stock,categoria
"Nombre del Producto","Descripción detallada",precio_numerico,stock_numerico,"Categoria Válida"
```

## ⚡ **Validaciones Automáticas**

### **Detección de Categoria Vacía:**
- `""` (cadena vacía)
- `null` o `NULL`
- Celda sin valor
- `nan` (pandas NaN)

### **Procesamiento:**
1. **Verificar** si columna `categoria` existe
2. **Leer** valor de categoria de cada fila
3. **Validar** si categoria está vacía o es NULL
4. **Asignar** "General" si está vacía, o usar valor si es válido
5. **Actualizar** categoria en productos existentes

## 🎯 **Ventajas de las Nuevas Reglas**

### ✅ **Consistencia:**
- Todos los productos siempre tienen categoria
- No hay productos sin categoria

### ✅ **Flexibilidad:**
- CSV puede tener o no tener columna categoria
- Categoria se puede actualizar en productos existentes

### ✅ **Robustez:**
- Maneja casos edge (celdas vacías, NULL, etc.)
- No rompe si falta la columna categoria

### ✅ **Simplicidad:**
- Regla simple: Si no hay categoria válida → "General"
- Fácil de entender y predecir

## 🔧 **Verificación Rápida**

### **Después de cargar CSV:**
```bash
# Verificar productos y sus categorías
curl "http://localhost:8000/productos/" | jq '.[] | {nombre: .nombre, categoria: .categoria, activo: .activo}' | head -20
```

### **Contar productos por categoría:**
```bash
curl "http://localhost:8000/productos/" | jq '.[] | select(.activo == true) | .categoria' | sort | uniq -c
```

## 📚 **Casos de Uso Comunes**

### **Caso 1: Primera Carga de Inventario**
- Usuario sube CSV sin columna categoria
- ✅ Todos los productos quedan con categoria = "General"

### **Caso 2: Actualización con Categorización**
- Usuario agrega columna categoria a su CSV
- ✅ Productos existentes se actualizan con nuevas categorías

### **Caso 3: CSV Incompleto**
- Usuario olvida llenar algunas categorías
- ✅ Celdas vacías se llenan automáticamente con "General"

### **Caso 4: Reorganización de Categorías**
- Usuario cambia categorías existentes
- ✅ Productos se actualizan con las nuevas categorías

## 🚀 **Script de Prueba**

Para probar las reglas manualmente:

```bash
python test_reglas_categoria.py
```

Este script verifica:
1. CSV sin columna categoria
2. CSV con categorías válidas
3. CSV con categorías vacías
4. Actualización de productos existentes

¡Las reglas están funcionando perfectamente! 🎉 