# 🔌 **Guía de Integración Frontend - Agente Vendedor**

## 📋 **Información General**

**Backend URL**: `http://localhost:8001`  
**API Docs**: `http://localhost:8001/docs`  
**Estado**: ✅ **100% Operativo** - Todos los endpoints funcionando  
**Última verificación**: 2025-05-29

---

## 🎯 **Endpoints Principales**

### 📱 **CHAT & CONVERSACIÓN**
```javascript
// Enviar mensaje al agente IA
POST /chat/texto
Body: {
    "mensaje": "¿Qué productos tienen disponibles?",
    "chat_id": "usuario-123"
}
```

### 🛍️ **PRODUCTOS**
```javascript
// Listar todos los productos
GET /productos/

// Obtener producto específico
GET /productos/{id}

// Crear/actualizar producto
POST /productos/
Body: {
    "nombre": "Producto Ejemplo",
    "descripcion": "Descripción detallada",
    "precio": 199.99,    // ⚠️ IMPORTANTE: Float, no int
    "stock": 50,
    "categoria": "Categoria"
}
```

### 💰 **VENTAS**
```javascript
// ⚠️ IMPORTANTE: URL es /venta/ (NO /ventas/)
POST /venta/
Body: {
    "chat_id": "venta-123",
    "productos": [
        {
            "producto_id": 1,
            "cantidad": 2,
            "precio_unitario": 199.99
        }
    ],
    "total": 399.98,
    "cliente_cedula": "12345678",
    "cliente_nombre": "Juan Pérez",
    "cliente_telefono": "3001234567"
}
```

### 👥 **CLIENTES**
```javascript
// Listar clientes
GET /clientes/

// Crear cliente
POST /clientes/
Body: {
    "cedula": "12345678",
    "nombre": "Juan Pérez",
    "telefono": "3001234567",
    "email": "juan@email.com"
}
```

### 📦 **PEDIDOS**
```javascript
// Crear pedido completo
POST /pedidos/
Body: {
    "chat_id": "pedido-123",
    "productos": [
        {
            "id": 1,
            "cantidad": 3
        }
    ],
    "cliente": {
        "cedula": "12345678",
        "nombre": "Cliente Ejemplo",
        "telefono": "3001234567"
    }
}
```

---

## 🔧 **Configuración Base de JavaScript**

### **Setup Inicial**
```javascript
const API_BASE_URL = "http://localhost:8001";

const defaultHeaders = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
};

// Helper para peticiones
const apiRequest = async (endpoint, options = {}) => {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
        headers: defaultHeaders,
        ...options
    };
    
    try {
        const response = await fetch(url, config);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`Error en ${endpoint}:`, error);
        throw error;
    }
};
```

---

## 💬 **Implementación del Chat**

### **Componente Chat Básico**
```javascript
class ChatComponent {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.chatId = `chat-${Date.now()}`;
        this.initializeChat();
    }
    
    initializeChat() {
        this.container.innerHTML = `
            <div id="messages" class="chat-messages"></div>
            <div class="chat-input">
                <input type="text" id="messageInput" placeholder="Escribe tu mensaje...">
                <button onclick="chat.sendMessage()">Enviar</button>
            </div>
        `;
    }
    
    async sendMessage() {
        const input = document.getElementById('messageInput');
        const mensaje = input.value.trim();
        
        if (!mensaje) return;
        
        // Mostrar mensaje del usuario
        this.addMessage(mensaje, 'user');
        input.value = '';
        
        try {
            // Enviar al backend
            const response = await apiRequest('/chat/texto', {
                method: 'POST',
                body: JSON.stringify({
                    mensaje: mensaje,
                    chat_id: this.chatId
                })
            });
            
            // Mostrar respuesta del agente
            this.addMessage(response.respuesta, 'bot');
            
            // Si hay productos en la respuesta, mostrarlos
            if (response.productos) {
                this.showProducts(response.productos);
            }
            
        } catch (error) {
            this.addMessage('Error al comunicarse con el servidor', 'error');
        }
    }
    
    addMessage(text, sender) {
        const messagesDiv = document.getElementById('messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.textContent = text;
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    
    showProducts(productos) {
        const messagesDiv = document.getElementById('messages');
        const productDiv = document.createElement('div');
        productDiv.className = 'productos-list';
        
        let html = '<div class="productos-container">';
        productos.forEach(producto => {
            html += `
                <div class="producto-card">
                    <h4>${producto.nombre}</h4>
                    <p>${producto.descripcion}</p>
                    <p class="precio">$${producto.precio}</p>
                    <p class="stock">Stock: ${producto.stock}</p>
                    <button onclick="chat.addToCart(${producto.id})">
                        Agregar al carrito
                    </button>
                </div>
            `;
        });
        html += '</div>';
        
        productDiv.innerHTML = html;
        messagesDiv.appendChild(productDiv);
    }
}

// Inicializar chat
const chat = new ChatComponent('chat-container');
```

---

## 🛒 **Sistema de Carrito y Ventas**

### **Gestor de Carrito**
```javascript
class CartManager {
    constructor() {
        this.items = [];
        this.chatId = `cart-${Date.now()}`;
    }
    
    async addProduct(productId, cantidad = 1) {
        try {
            // Obtener datos del producto
            const producto = await apiRequest(`/productos/${productId}`);
            
            // Verificar si ya está en el carrito
            const existingItem = this.items.find(item => item.producto_id === productId);
            
            if (existingItem) {
                existingItem.cantidad += cantidad;
            } else {
                this.items.push({
                    producto_id: productId,
                    nombre: producto.nombre,
                    precio_unitario: producto.precio,
                    cantidad: cantidad
                });
            }
            
            this.updateCartDisplay();
            
        } catch (error) {
            console.error('Error agregando producto:', error);
            alert('Error al agregar producto al carrito');
        }
    }
    
    removeProduct(productId) {
        this.items = this.items.filter(item => item.producto_id !== productId);
        this.updateCartDisplay();
    }
    
    getTotalPrice() {
        return this.items.reduce((total, item) => {
            return total + (item.precio_unitario * item.cantidad);
        }, 0);
    }
    
    async processPurchase(clienteData) {
        if (this.items.length === 0) {
            alert('El carrito está vacío');
            return;
        }
        
        try {
            const ventaData = {
                chat_id: this.chatId,
                productos: this.items.map(item => ({
                    producto_id: item.producto_id,
                    cantidad: item.cantidad,
                    precio_unitario: item.precio_unitario
                })),
                total: this.getTotalPrice(),
                cliente_cedula: clienteData.cedula,
                cliente_nombre: clienteData.nombre,
                cliente_telefono: clienteData.telefono
            };
            
            const response = await apiRequest('/venta/', {
                method: 'POST',
                body: JSON.stringify(ventaData)
            });
            
            if (response.success) {
                alert('¡Venta procesada exitosamente!');
                this.clearCart();
                return response;
            } else {
                throw new Error(response.message || 'Error procesando la venta');
            }
            
        } catch (error) {
            console.error('Error procesando venta:', error);
            alert('Error al procesar la venta: ' + error.message);
        }
    }
    
    clearCart() {
        this.items = [];
        this.updateCartDisplay();
    }
    
    updateCartDisplay() {
        const cartDiv = document.getElementById('cart');
        if (!cartDiv) return;
        
        let html = '<h3>Carrito de Compras</h3>';
        
        if (this.items.length === 0) {
            html += '<p>Carrito vacío</p>';
        } else {
            html += '<div class="cart-items">';
            this.items.forEach(item => {
                const subtotal = item.precio_unitario * item.cantidad;
                html += `
                    <div class="cart-item">
                        <span>${item.nombre}</span>
                        <span>$${item.precio_unitario} x ${item.cantidad}</span>
                        <span>$${subtotal.toFixed(2)}</span>
                        <button onclick="cart.removeProduct(${item.producto_id})">
                            Eliminar
                        </button>
                    </div>
                `;
            });
            html += '</div>';
            html += `
                <div class="cart-total">
                    <strong>Total: $${this.getTotalPrice().toFixed(2)}</strong>
                </div>
                <button onclick="cart.showCheckout()" class="checkout-btn">
                    Proceder al Pago
                </button>
            `;
        }
        
        cartDiv.innerHTML = html;
    }
    
    showCheckout() {
        const modal = document.createElement('div');
        modal.className = 'checkout-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>Finalizar Compra</h3>
                <form id="checkoutForm">
                    <input type="text" id="clienteCedula" placeholder="Cédula" required>
                    <input type="text" id="clienteNombre" placeholder="Nombre completo" required>
                    <input type="tel" id="clienteTelefono" placeholder="Teléfono" required>
                    <div class="form-buttons">
                        <button type="submit">Finalizar Compra</button>
                        <button type="button" onclick="this.closest('.checkout-modal').remove()">
                            Cancelar
                        </button>
                    </div>
                </form>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        document.getElementById('checkoutForm').onsubmit = async (e) => {
            e.preventDefault();
            
            const clienteData = {
                cedula: document.getElementById('clienteCedula').value,
                nombre: document.getElementById('clienteNombre').value,
                telefono: document.getElementById('clienteTelefono').value
            };
            
            const result = await this.processPurchase(clienteData);
            if (result) {
                modal.remove();
            }
        };
    }
}

// Inicializar carrito
const cart = new CartManager();
```

---

## 📊 **Panel de Administración**

### **Dashboard de Métricas**
```javascript
class AdminDashboard {
    constructor() {
        this.loadDashboard();
    }
    
    async loadDashboard() {
        try {
            const [ventasData, inventarioData, estadisticas] = await Promise.all([
                apiRequest('/admin/dashboard/ventas'),
                apiRequest('/admin/inventario'),
                apiRequest('/admin/estadisticas')
            ]);
            
            this.renderDashboard({
                ventas: ventasData,
                inventario: inventarioData,
                stats: estadisticas
            });
            
        } catch (error) {
            console.error('Error cargando dashboard:', error);
        }
    }
    
    renderDashboard(data) {
        const container = document.getElementById('admin-dashboard');
        if (!container) return;
        
        container.innerHTML = `
            <div class="dashboard-grid">
                <div class="metric-card">
                    <h3>Ventas Hoy</h3>
                    <p class="metric-value">${data.ventas.ventas_hoy || 0}</p>
                </div>
                
                <div class="metric-card">
                    <h3>Total Productos</h3>
                    <p class="metric-value">${data.inventario.total_productos || 0}</p>
                </div>
                
                <div class="metric-card">
                    <h3>Stock Bajo</h3>
                    <p class="metric-value">${data.inventario.productos_stock_bajo || 0}</p>
                </div>
                
                <div class="metric-card">
                    <h3>Clientes Registrados</h3>
                    <p class="metric-value">${data.stats.total_clientes || 0}</p>
                </div>
            </div>
            
            <div class="dashboard-section">
                <h3>Productos con Stock Bajo</h3>
                <div id="low-stock-products"></div>
            </div>
            
            <div class="dashboard-section">
                <h3>Últimas Ventas</h3>
                <div id="recent-sales"></div>
            </div>
        `;
        
        this.renderLowStockProducts(data.inventario.productos_stock_bajo_detalle || []);
        this.renderRecentSales(data.ventas.ventas_recientes || []);
    }
    
    renderLowStockProducts(productos) {
        const container = document.getElementById('low-stock-products');
        if (!container) return;
        
        if (productos.length === 0) {
            container.innerHTML = '<p>No hay productos con stock bajo</p>';
            return;
        }
        
        let html = '<div class="products-list">';
        productos.forEach(producto => {
            html += `
                <div class="product-item ${producto.stock === 0 ? 'out-of-stock' : ''}">
                    <span class="product-name">${producto.nombre}</span>
                    <span class="product-stock">Stock: ${producto.stock}</span>
                    <span class="product-category">${producto.categoria}</span>
                </div>
            `;
        });
        html += '</div>';
        
        container.innerHTML = html;
    }
    
    renderRecentSales(ventas) {
        const container = document.getElementById('recent-sales');
        if (!container) return;
        
        if (ventas.length === 0) {
            container.innerHTML = '<p>No hay ventas recientes</p>';
            return;
        }
        
        let html = '<div class="sales-list">';
        ventas.forEach(venta => {
            html += `
                <div class="sale-item">
                    <span class="sale-id">Venta #${venta.id}</span>
                    <span class="sale-date">${new Date(venta.fecha).toLocaleDateString()}</span>
                    <span class="sale-total">$${venta.total}</span>
                    <span class="sale-status">${venta.estado}</span>
                </div>
            `;
        });
        html += '</div>';
        
        container.innerHTML = html;
    }
}
```

---

## 🎨 **Estilos CSS Recomendados**

```css
/* Chat Styles */
.chat-messages {
    height: 400px;
    overflow-y: auto;
    border: 1px solid #ddd;
    padding: 10px;
    margin-bottom: 10px;
}

.message {
    margin: 10px 0;
    padding: 8px 12px;
    border-radius: 8px;
    max-width: 80%;
}

.message.user {
    background: #007bff;
    color: white;
    margin-left: auto;
    text-align: right;
}

.message.bot {
    background: #f8f9fa;
    color: #333;
}

.message.error {
    background: #dc3545;
    color: white;
}

/* Product Cards */
.productos-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 15px;
    margin: 15px 0;
}

.producto-card {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
    background: #fff;
}

.producto-card h4 {
    margin: 0 0 10px 0;
    color: #333;
}

.precio {
    font-size: 1.2em;
    font-weight: bold;
    color: #28a745;
}

/* Cart Styles */
.cart-item {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr auto;
    gap: 10px;
    padding: 10px;
    border-bottom: 1px solid #eee;
    align-items: center;
}

.cart-total {
    text-align: right;
    padding: 15px;
    font-size: 1.2em;
}

.checkout-btn {
    width: 100%;
    background: #28a745;
    color: white;
    border: none;
    padding: 12px;
    border-radius: 5px;
    cursor: pointer;
}

/* Modal Styles */
.checkout-modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.modal-content {
    background: white;
    padding: 20px;
    border-radius: 8px;
    min-width: 400px;
}

.modal-content input {
    width: 100%;
    padding: 10px;
    margin: 10px 0;
    border: 1px solid #ddd;
    border-radius: 4px;
}

/* Dashboard Styles */
.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.metric-card {
    background: #fff;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    text-align: center;
}

.metric-value {
    font-size: 2em;
    font-weight: bold;
    color: #007bff;
    margin: 10px 0;
}

.dashboard-section {
    background: #fff;
    padding: 20px;
    border-radius: 8px;
    margin: 20px 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
```

---

## 🔍 **Manejo de Errores**

### **Error Handler Global**
```javascript
window.addEventListener('unhandledrejection', event => {
    console.error('Error no manejado:', event.reason);
    
    // Mostrar mensaje al usuario
    showNotification('Error de conexión con el servidor', 'error');
    
    event.preventDefault();
});

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Wrapper para requests con manejo de errores
const safeApiRequest = async (endpoint, options = {}) => {
    try {
        return await apiRequest(endpoint, options);
    } catch (error) {
        if (error.message.includes('404')) {
            showNotification('Recurso no encontrado', 'warning');
        } else if (error.message.includes('500')) {
            showNotification('Error interno del servidor', 'error');
        } else if (error.message.includes('400')) {
            showNotification('Datos inválidos enviados', 'warning');
        } else {
            showNotification('Error de conexión', 'error');
        }
        throw error;
    }
};
```

---

## 🧪 **Testing del Frontend**

### **Test de Conectividad**
```javascript
async function testBackendConnection() {
    console.log('🧪 Iniciando tests de conectividad...');
    
    const tests = [
        {
            name: 'Health Check',
            endpoint: '/health',
            method: 'GET'
        },
        {
            name: 'Listar Productos',
            endpoint: '/productos/',
            method: 'GET'
        },
        {
            name: 'Chat Test',
            endpoint: '/chat/texto',
            method: 'POST',
            body: {
                mensaje: 'Hola, test de conectividad',
                chat_id: 'test-frontend'
            }
        }
    ];
    
    for (const test of tests) {
        try {
            console.log(`Testing ${test.name}...`);
            
            const options = {
                method: test.method
            };
            
            if (test.body) {
                options.body = JSON.stringify(test.body);
            }
            
            const result = await apiRequest(test.endpoint, options);
            console.log(`✅ ${test.name}: OK`, result);
            
        } catch (error) {
            console.error(`❌ ${test.name}: FAILED`, error);
        }
    }
    
    console.log('🏁 Tests de conectividad completados');
}

// Ejecutar tests al cargar la página
document.addEventListener('DOMContentLoaded', () => {
    testBackendConnection();
});
```

---

## 🚀 **Ejemplo de Aplicación Completa**

### **HTML Base**
```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agente Vendedor IA</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header>
        <h1>🤖 Agente Vendedor IA</h1>
        <nav>
            <button onclick="showSection('chat')">Chat</button>
            <button onclick="showSection('products')">Productos</button>
            <button onclick="showSection('cart')">Carrito</button>
            <button onclick="showSection('admin')">Admin</button>
        </nav>
    </header>
    
    <main>
        <!-- Chat Section -->
        <section id="chat-section" class="section">
            <div id="chat-container"></div>
        </section>
        
        <!-- Products Section -->
        <section id="products-section" class="section">
            <div id="products-list"></div>
        </section>
        
        <!-- Cart Section -->
        <section id="cart-section" class="section">
            <div id="cart"></div>
        </section>
        
        <!-- Admin Section -->
        <section id="admin-section" class="section">
            <div id="admin-dashboard"></div>
        </section>
    </main>
    
    <script src="app.js"></script>
</body>
</html>
```

### **JavaScript Principal**
```javascript
// Variables globales
let currentSection = 'chat';
let chat, cart, admin;

// Inicialización
document.addEventListener('DOMContentLoaded', () => {
    // Inicializar componentes
    chat = new ChatComponent('chat-container');
    cart = new CartManager();
    admin = new AdminDashboard();
    
    // Mostrar sección inicial
    showSection('chat');
    
    // Test de conectividad
    testBackendConnection();
});

function showSection(sectionName) {
    // Ocultar todas las secciones
    document.querySelectorAll('.section').forEach(section => {
        section.style.display = 'none';
    });
    
    // Mostrar sección seleccionada
    document.getElementById(`${sectionName}-section`).style.display = 'block';
    currentSection = sectionName;
    
    // Actualizar navegación
    document.querySelectorAll('nav button').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
}
```

---

## ⚠️ **Puntos Importantes**

### **URLs Corregidas**
- ✅ `/venta/` (NO `/ventas/`)
- ✅ `/productos/` (precio como float)
- ✅ `/chat/texto` para conversaciones
- ✅ `/admin/dashboard` para métricas

### **Datos Requeridos**
- **Precio de productos**: Siempre `float`, nunca `int`
- **Chat ID**: String único para cada conversación
- **Múltiples productos**: Array en ventas y pedidos

### **Manejo de Errores**
- Validar respuestas antes de procesarlas
- Implementar fallbacks para conexiones fallidas
- Mostrar mensajes informativos al usuario

---

**¡Frontend listo para integración completa con el backend!** 🚀

---

*Guía actualizada: 2025-05-29* 