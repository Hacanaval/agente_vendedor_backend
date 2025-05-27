-- Migración: Crear tabla de clientes y actualizar tabla de ventas
-- Fecha: 2024-12-19
-- Descripción: Sistema completo de gestión de clientes con historial de compras

-- 1. Crear tabla de clientes
CREATE TABLE IF NOT EXISTS clientes (
    cedula VARCHAR(20) PRIMARY KEY,
    nombre_completo VARCHAR(200) NOT NULL,
    telefono VARCHAR(20) NOT NULL,
    direccion TEXT NOT NULL,
    barrio VARCHAR(100) NOT NULL,
    indicaciones_adicionales TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_ultima_compra TIMESTAMP,
    total_compras INTEGER DEFAULT 0,
    valor_total_compras INTEGER DEFAULT 0,
    activo BOOLEAN DEFAULT TRUE,
    notas TEXT
);

-- 2. Crear índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_clientes_telefono ON clientes(telefono);
CREATE INDEX IF NOT EXISTS idx_clientes_nombre ON clientes(nombre_completo);
CREATE INDEX IF NOT EXISTS idx_clientes_fecha_ultima_compra ON clientes(fecha_ultima_compra);
CREATE INDEX IF NOT EXISTS idx_clientes_valor_total ON clientes(valor_total_compras);
CREATE INDEX IF NOT EXISTS idx_clientes_activo ON clientes(activo);

-- 3. Agregar columna cliente_cedula a tabla de ventas (si no existe)
ALTER TABLE venta ADD COLUMN IF NOT EXISTS cliente_cedula VARCHAR(20);

-- 4. Crear índice para la relación venta-cliente
CREATE INDEX IF NOT EXISTS idx_venta_cliente_cedula ON venta(cliente_cedula);

-- 5. Agregar foreign key constraint (opcional, comentado por compatibilidad)
-- ALTER TABLE venta ADD CONSTRAINT fk_venta_cliente 
-- FOREIGN KEY (cliente_cedula) REFERENCES clientes(cedula) ON DELETE SET NULL;

-- 6. Comentarios en las columnas para documentación
COMMENT ON TABLE clientes IS 'Tabla de clientes con información completa y estadísticas de compras';
COMMENT ON COLUMN clientes.cedula IS 'Cédula del cliente (ID principal único)';
COMMENT ON COLUMN clientes.nombre_completo IS 'Nombre completo del cliente';
COMMENT ON COLUMN clientes.telefono IS 'Teléfono de contacto';
COMMENT ON COLUMN clientes.direccion IS 'Dirección completa de entrega';
COMMENT ON COLUMN clientes.barrio IS 'Barrio de residencia';
COMMENT ON COLUMN clientes.indicaciones_adicionales IS 'Indicaciones adicionales para entrega';
COMMENT ON COLUMN clientes.fecha_registro IS 'Fecha de primer registro';
COMMENT ON COLUMN clientes.fecha_ultima_compra IS 'Fecha de la última compra';
COMMENT ON COLUMN clientes.total_compras IS 'Número total de compras realizadas';
COMMENT ON COLUMN clientes.valor_total_compras IS 'Valor total acumulado de todas las compras';
COMMENT ON COLUMN clientes.activo IS 'Cliente activo en el sistema';
COMMENT ON COLUMN clientes.notas IS 'Notas adicionales sobre el cliente';

COMMENT ON COLUMN venta.cliente_cedula IS 'Cédula del cliente que realizó la compra';

-- 7. Datos de ejemplo (opcional, comentado)
/*
INSERT INTO clientes (cedula, nombre_completo, telefono, direccion, barrio, fecha_registro, activo) VALUES
('12345678', 'Juan Pérez García', '3001234567', 'Calle 123 #45-67', 'Centro', CURRENT_TIMESTAMP, TRUE),
('87654321', 'María López Rodríguez', '3009876543', 'Carrera 45 #12-34', 'Norte', CURRENT_TIMESTAMP, TRUE),
('11223344', 'Carlos Martínez Silva', '3005551234', 'Avenida 68 #23-45', 'Sur', CURRENT_TIMESTAMP, TRUE);
*/ 