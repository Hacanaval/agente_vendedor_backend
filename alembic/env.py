from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

import os
import sys

# Añadimos el path del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importamos Base y todos los modelos explícitamente
from app.core.database import Base

# Importa todos los modelos para que se registren en Base.metadata
from app.models import (
    usuario,
    empresa,
    cliente_final,
    mensaje,
    logs,
    producto,
    inventario_log,
    venta,
)

# Configuración de Alembic
config = context.config

# Setup de logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Establecemos el metadata después de que todos los modelos se hayan importado
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Ejecutar migraciones en modo offline."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecutar migraciones en modo online."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# Ejecutamos según el modo
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
