-- Migración: Agregar campo correo a tabla clientes
-- Fecha: 2024-01-24
-- Descripción: Agregar columna correo electrónico con índice para búsquedas

ALTER TABLE clientes ADD COLUMN correo VARCHAR(200);
CREATE INDEX idx_clientes_correo ON clientes(correo);

-- Comentario en la columna
COMMENT ON COLUMN clientes.correo IS 'Correo electrónico del cliente'; 