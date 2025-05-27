# 📋 Guía: Verificación CSV Frontend → RAG Inventario

## ✅ **Backend CONFIRMADO Funcionando**

Hemos verificado que el backend está procesando CSV correctamente:
- ✅ Productos nuevos se agregan al RAG
- ✅ Productos existentes se actualizan  
- ✅ Productos no presentes se ponen stock=0
- ✅ Sincronización RAG funciona inmediatamente

## 🔍 **Cómo Verificar desde el Frontend**

### 1. **Verificar la Carga del CSV**

```bash
# Iniciar servidor
cd /Users/hacanaval/Documents/agente_vendedor
python -m uvicorn app.main:app --reload --port 8000

# En otra terminal, verificar endpoint
curl -X GET "http://localhost:8000/productos/" | python -m json.tool | grep -E '"activo": true' -A 5 -B 5
```

### 2. **Probar CSV desde Frontend**

**CSV de Ejemplo para Probar:**
```csv
nombre,descripcion,precio,stock
"Extintor Test Frontend","Extintor cargado desde frontend para verificar sincronización",50000,10
"Casco Test Frontend","Casco de prueba cargado desde frontend",25000,15
"EPP Test Frontend","Equipo de protección personal de prueba",30000,20
```

### 3. **Verificar Sincronización con RAG**

Después de cargar el CSV desde el frontend:

```bash
# Probar consultas específicas
curl -X POST "http://localhost:8000/chat/texto" \
  -H "Content-Type: application/json" \
  -d '{"mensaje": "¿Tienen Extintor Test Frontend?", "chat_id": "test_frontend"}'

curl -X POST "http://localhost:8000/chat/texto" \
  -H "Content-Type: application/json" \
  -d '{"mensaje": "¿Qué productos tienen disponibles?", "chat_id": "test_general"}'
```

### 4. **Signos de Éxito**

**✅ CSV Cargado Correctamente:**
- API responde 200 con `{"message": "Inventario reemplazado correctamente."}`
- Productos aparecen en `/productos/` con `activo: true`

**✅ RAG Sincronizado:**
- Consultas específicas encuentran los productos nuevos
- Consulta general incluye todos los productos activos
- Productos antiguos no aparecen (tienen `activo: false`)

## 🐛 **Diagnóstico de Problemas Comunes**

### **Problema 1: CSV no se carga**
```bash
# Verificar formato del archivo
head -5 tu_archivo.csv

# Debe tener exactamente estas columnas:
# nombre,descripcion,precio,stock
```

**Solución:**
- Verificar que el CSV tenga las 4 columnas requeridas
- Sin caracteres especiales en los nombres de columnas
- Datos válidos (números en precio y stock)

### **Problema 2: Productos no aparecen en RAG**
```bash
# Verificar que los productos estén activos
curl "http://localhost:8000/productos/" | grep -E "activo.*true" -B 5 -A 5

# Verificar que el RAG esté sincronizado
curl -X POST "http://localhost:8000/chat/texto" \
  -H "Content-Type: application/json" \
  -d '{"mensaje": "¿Qué productos tienen?", "chat_id": "test_sync"}'
```

**Solución:**
- Si productos están en BD pero no en RAG → Problema de sincronización
- Si productos no están en BD → Problema en carga CSV

### **Problema 3: Productos antiguos siguen apareciendo**
```bash
# Verificar que productos antiguos tengan stock=0
curl "http://localhost:8000/productos/" | grep -E "stock.*[1-9]" -B 5 -A 5
```

**Solución:**
- Solo productos con `stock > 0` y `activo: true` deberían aparecer
- Si aparecen productos viejos, verificar lógica de reemplazo

## 🚀 **Script de Verificación Automática**

```bash
#!/bin/bash
echo "🧪 VERIFICACIÓN AUTOMÁTICA CSV → RAG"
echo "=================================="

echo "1. Verificando servidor..."
if curl -s "http://localhost:8000/" > /dev/null; then
    echo "✅ Servidor funcionando"
else
    echo "❌ Servidor no disponible"
    exit 1
fi

echo "2. Productos activos en BD:"
ACTIVOS=$(curl -s "http://localhost:8000/productos/" | python3 -c "
import sys, json
data = json.load(sys.stdin)
activos = [p for p in data if p['activo']]
print(f'{len(activos)} productos activos')
for p in activos:
    print(f'  • {p[\"nombre\"]} - Stock: {p[\"stock\"]}')
")
echo "$ACTIVOS"

echo "3. Probando RAG..."
RESPUESTA=$(curl -s -X POST "http://localhost:8000/chat/texto" \
  -H "Content-Type: application/json" \
  -d '{"mensaje": "¿Qué productos tienen disponibles?", "chat_id": "test_verificacion"}' | \
  python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'Tipo: {data.get(\"tipo_mensaje\", \"N/A\")}')
    print(f'Respuesta: {data.get(\"respuesta\", \"N/A\")[:100]}...')
except:
    print('Error procesando respuesta')
")
echo "$RESPUESTA"

echo "✅ Verificación completada"
```

## 📱 **Verificación desde Frontend (JavaScript)**

```javascript
// Función para verificar después de cargar CSV
async function verificarCargaCSV() {
    console.log('🧪 Verificando carga CSV...');
    
    try {
        // 1. Verificar productos en BD
        const productosResp = await fetch('/api/productos/');
        const productos = await productosResp.json();
        const activos = productos.filter(p => p.activo);
        
        console.log(`✅ ${activos.length} productos activos encontrados`);
        activos.forEach(p => {
            console.log(`  • ${p.nombre} - Stock: ${p.stock}`);
        });
        
        // 2. Probar RAG
        const chatResp = await fetch('/api/chat/texto', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mensaje: '¿Qué productos tienen disponibles?',
                chat_id: 'test_frontend_verificacion'
            })
        });
        
        const chatResult = await chatResp.json();
        console.log(`✅ RAG responde: ${chatResult.tipo_mensaje}`);
        console.log(`Productos encontrados en respuesta: ${chatResult.respuesta.length > 100 ? 'Sí' : 'Verificar'}`);
        
        return {
            productosEnBD: activos.length,
            ragFunciona: chatResult.tipo_mensaje === 'inventario',
            respuestaCompleta: chatResult.respuesta.length > 100
        };
        
    } catch (error) {
        console.error('❌ Error verificando CSV:', error);
        return { error: error.message };
    }
}

// Usar después de cargar CSV
document.getElementById('upload-csv').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/productos/reemplazar_csv', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            console.log('✅ CSV cargado exitosamente');
            
            // Esperar 2 segundos y verificar
            setTimeout(async () => {
                const verificacion = await verificarCargaCSV();
                if (verificacion.error) {
                    alert(`Error en verificación: ${verificacion.error}`);
                } else if (verificacion.ragFunciona) {
                    alert(`¡Éxito! ${verificacion.productosEnBD} productos cargados y disponibles en el chatbot`);
                } else {
                    alert('Productos cargados pero hay problemas con el RAG');
                }
            }, 2000);
        } else {
            console.error('❌ Error cargando CSV');
        }
    } catch (error) {
        console.error('❌ Error:', error);
    }
});
```

## 🎯 **Resumen de Verificación**

### ✅ **Sistema Funcionando:**
1. CSV se carga sin errores (200 response)
2. Productos aparecen en `/productos/` con `activo: true`
3. Consulta general RAG incluye productos nuevos
4. Consultas específicas encuentran productos por nombre
5. Productos antiguos tienen `activo: false`

### ❌ **Problemas Posibles:**
1. Error 400/500 al cargar CSV → Problema formato archivo
2. Productos en BD pero `activo: false` → Problema stock=0 
3. Productos en BD pero no en RAG → Problema sincronización
4. RAG no responde tipo "inventario" → Problema servicio RAG

¡El backend está funcionando perfectamente! Si hay problemas, probablemente sean del lado del frontend o formato del archivo CSV. 