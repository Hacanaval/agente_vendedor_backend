# 🔴 Guía: Botón Sistema AI - Persistencia y Estado por Defecto

## 📋 Requisitos Cumplidos

✅ **Estado por defecto**: Siempre ON cuando no hay registro previo  
✅ **Persistencia**: El estado se mantiene entre recargas y cierres  
✅ **Base de datos**: Estado guardado permanentemente en BD  
✅ **Inicialización automática**: Estado por defecto creado al iniciar servidor  

## 🚀 Implementación Frontend

### 1. Hook React para Estado del Sistema AI

```typescript
// hooks/useSystemAI.ts
import { useState, useEffect } from 'react';

interface SystemAIState {
  isActive: boolean;
  loading: boolean;
  error: string | null;
}

export const useSystemAI = () => {
  const [state, setState] = useState<SystemAIState>({
    isActive: true, // Por defecto ON mientras carga
    loading: true,
    error: null
  });

  // Obtener estado inicial del servidor
  const fetchState = async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      
      const response = await fetch('/api/chat-control/sistema/estado');
      if (!response.ok) throw new Error('Error obteniendo estado');
      
      const data = await response.json();
      setState({
        isActive: data.sistema_ia_activo,
        loading: false,
        error: null
      });
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: 'Error conectando con servidor'
      }));
    }
  };

  // Toggle del estado
  const toggleSystemAI = async (motivo?: string) => {
    try {
      setState(prev => ({ ...prev, loading: true }));
      
      const response = await fetch('/api/chat-control/sistema/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          activar: !state.isActive,
          usuario: 'admin', // Puedes obtener del contexto de usuario
          motivo: motivo
        })
      });

      if (!response.ok) throw new Error('Error cambiando estado');
      
      const data = await response.json();
      setState({
        isActive: data.sistema_ia_activo,
        loading: false,
        error: null
      });
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: 'Error cambiando estado'
      }));
    }
  };

  // Cargar estado inicial
  useEffect(() => {
    fetchState();
  }, []);

  return {
    isActive: state.isActive,
    loading: state.loading,
    error: state.error,
    toggle: toggleSystemAI,
    refresh: fetchState
  };
};
```

### 2. Componente del Botón

```tsx
// components/SystemAIToggle.tsx
import React from 'react';
import { useSystemAI } from '../hooks/useSystemAI';

export const SystemAIToggle: React.FC = () => {
  const { isActive, loading, error, toggle } = useSystemAI();

  return (
    <div className="system-ai-toggle">
      <button
        onClick={() => toggle()}
        disabled={loading}
        className={`
          toggle-btn 
          ${isActive ? 'toggle-on' : 'toggle-off'}
          ${loading ? 'loading' : ''}
        `}
      >
        <div className="toggle-slider">
          <span className="toggle-icon">
            {loading ? '⏳' : isActive ? '🤖' : '⏸️'}
          </span>
        </div>
        <span className="toggle-label">
          Sistema AI: {loading ? 'Cargando...' : isActive ? 'ON' : 'OFF'}
        </span>
      </button>
      
      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}
    </div>
  );
};
```

### 3. Estilos CSS

```css
/* styles/SystemAIToggle.css */
.system-ai-toggle {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toggle-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border: 2px solid #ddd;
  border-radius: 25px;
  background: white;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 600;
}

.toggle-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.toggle-on {
  background: linear-gradient(135deg, #10b981, #059669);
  border-color: #059669;
  color: white;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.toggle-off {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  border-color: #dc2626;
  color: white;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.toggle-on:hover {
  background: linear-gradient(135deg, #059669, #047857);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4);
}

.toggle-off:hover {
  background: linear-gradient(135deg, #dc2626, #b91c1c);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(239, 68, 68, 0.4);
}

.toggle-slider {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.toggle-icon {
  font-size: 14px;
}

.loading .toggle-slider {
  animation: spin 1s linear infinite;
}

.error-message {
  color: #ef4444;
  font-size: 12px;
  font-weight: 500;
  padding: 4px 8px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 4px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

## 🔧 APIs Disponibles

### GET `/chat-control/sistema/estado`
Obtiene el estado actual del sistema AI.

**Respuesta:**
```json
{
  "sistema_ia_activo": true,
  "mensaje": "Sistema de IA está activo globalmente",
  "fecha_cambio": "2025-05-27T15:20:03",
  "usuario_que_desactivo": null
}
```

### POST `/chat-control/sistema/toggle`
Cambia el estado del sistema AI.

**Request:**
```json
{
  "activar": false,
  "usuario": "admin",
  "motivo": "Mantenimiento programado"
}
```

**Respuesta:**
```json
{
  "sistema_ia_activo": false,
  "mensaje": "Sistema de IA desactivado globalmente por admin. Motivo: Mantenimiento programado",
  "fecha_cambio": "2025-05-27T15:20:03",
  "usuario_que_desactivo": "admin"
}
```

## ✅ Garantías del Sistema

### 🔄 Estado por Defecto
- **Primera vez**: Cuando no existe registro, se crea automáticamente en ON
- **Servidor reiniciado**: Siempre crea registro por defecto si no existe
- **Base de datos limpia**: Automáticamente inicializa en ON

### 💾 Persistencia
- **Recarga página**: Estado se mantiene desde base de datos
- **Cerrar/abrir navegador**: Estado persiste
- **Cambios**: Se guardan inmediatamente en PostgreSQL
- **Múltiples usuarios**: Todos ven el mismo estado global

### 🛡️ Manejo de Errores
- **Error de conexión**: Mantiene último estado conocido
- **Error de servidor**: Estado por defecto ON
- **Error de BD**: Fallback a estado activo

## 🎯 Comportamiento Esperado

1. **Carga inicial**: Botón muestra "Cargando..." → Carga estado real desde BD
2. **Estado por defecto**: Si no hay registro previo → ON automáticamente  
3. **Toggle**: Clic cambia estado → Se guarda en BD inmediatamente
4. **Persistencia**: Recargar página → Mantiene último estado guardado
5. **Error handling**: Si falla API → Muestra error pero mantiene funcionalidad

## 🧪 Testing

```bash
# Obtener estado inicial
curl http://localhost:8000/chat-control/sistema/estado

# Cambiar a OFF
curl -X POST http://localhost:8000/chat-control/sistema/toggle \
  -H "Content-Type: application/json" \
  -d '{"activar": false, "usuario": "test"}'

# Verificar persistencia
curl http://localhost:8000/chat-control/sistema/estado

# Cambiar a ON
curl -X POST http://localhost:8000/chat-control/sistema/toggle \
  -H "Content-Type: application/json" \
  -d '{"activar": true, "usuario": "test"}'
```

## 📱 Integración en Layout Principal

```tsx
// App.tsx o Layout principal
import { SystemAIToggle } from './components/SystemAIToggle';

export const App = () => {
  return (
    <div className="app">
      <header className="app-header">
        <div className="header-controls">
          <SystemAIToggle />
          {/* Otros controles */}
        </div>
      </header>
      {/* Resto de la aplicación */}
    </div>
  );
};
```

¡Con esta implementación el botón Sistema AI tendrá persistencia completa y estado por defecto siempre ON! 🚀 