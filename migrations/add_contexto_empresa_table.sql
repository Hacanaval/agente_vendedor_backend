-- Migración: Agregar tabla contexto_empresa
-- Fecha: 2024-12-11
-- Descripción: Tabla para almacenar versiones del contexto de empresa con historial

CREATE TABLE IF NOT EXISTS contexto_empresa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_empresa VARCHAR(255) NOT NULL DEFAULT 'Sextinvalle',
    contenido TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    activo BOOLEAN NOT NULL DEFAULT 1,
    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usuario_actualizacion VARCHAR(255)
);

-- Índices para mejorar rendimiento
CREATE INDEX IF NOT EXISTS idx_contexto_activo ON contexto_empresa(activo);
CREATE INDEX IF NOT EXISTS idx_contexto_version ON contexto_empresa(version);
CREATE INDEX IF NOT EXISTS idx_contexto_fecha ON contexto_empresa(fecha_actualizacion);

-- Insertar contexto inicial si no existe
INSERT OR IGNORE INTO contexto_empresa (
    id, 
    nombre_empresa, 
    contenido, 
    version, 
    activo, 
    usuario_actualizacion
) 
SELECT 1, 'Sextinvalle', 'Contexto inicial a sincronizar', 1, 1, 'Sistema - Migración'
WHERE NOT EXISTS (SELECT 1 FROM contexto_empresa WHERE id = 1); 