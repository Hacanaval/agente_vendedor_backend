from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
import logging
import re

from app.models.cliente import Cliente
from app.models.venta import Venta
from app.models.producto import Producto

class ClienteManager:
    """
    Gestor de clientes con funcionalidades completas:
    - Creación y actualización de clientes
    - Gestión de historial de compras
    - Estadísticas y métricas de clientes
    - Búsqueda y filtrado
    """
    
    @staticmethod
    async def crear_o_actualizar_cliente(
        datos_cliente: Dict[str, str], 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Crea un nuevo cliente o actualiza uno existente basado en la cédula.
        
        Args:
            datos_cliente: Diccionario con los datos del cliente
            db: Sesión de base de datos
            
        Returns:
            Dict con información del resultado de la operación
        """
        try:
            cedula = datos_cliente.get("cedula", "").strip()
            
            if not cedula:
                return {"exito": False, "error": "Cédula es requerida"}
            
            # Validar cédula
            if not re.match(r'^\d{6,12}$', cedula):
                return {"exito": False, "error": "Cédula debe tener entre 6 y 12 dígitos"}
            
            # Buscar cliente existente
            result = await db.execute(
                select(Cliente).where(Cliente.cedula == cedula)
            )
            cliente_existente = result.scalar_one_or_none()
            
            if cliente_existente:
                # Actualizar cliente existente
                cliente_existente.nombre_completo = datos_cliente.get("nombre_completo", cliente_existente.nombre_completo)
                cliente_existente.telefono = datos_cliente.get("telefono", cliente_existente.telefono)
                cliente_existente.direccion = datos_cliente.get("direccion", cliente_existente.direccion)
                cliente_existente.barrio = datos_cliente.get("barrio", cliente_existente.barrio)
                cliente_existente.indicaciones_adicionales = datos_cliente.get("indicaciones_adicionales", cliente_existente.indicaciones_adicionales)
                
                await db.commit()
                await db.refresh(cliente_existente)
                
                logging.info(f"Cliente actualizado: {cedula} - {cliente_existente.nombre_completo}")
                
                return {
                    "exito": True,
                    "cliente": cliente_existente.to_dict(),
                    "accion": "actualizado"
                }
            else:
                # Crear nuevo cliente
                nuevo_cliente = Cliente.from_datos_pedido(datos_cliente, cedula)
                
                db.add(nuevo_cliente)
                await db.commit()
                await db.refresh(nuevo_cliente)
                
                logging.info(f"Cliente creado: {cedula} - {nuevo_cliente.nombre_completo}")
                
                return {
                    "exito": True,
                    "cliente": nuevo_cliente.to_dict(),
                    "accion": "creado"
                }
                
        except Exception as e:
            await db.rollback()
            logging.error(f"Error creando/actualizando cliente: {e}")
            return {"exito": False, "error": str(e)}
    
    @staticmethod
    async def obtener_cliente_por_cedula(cedula: str, db: AsyncSession) -> Optional[Cliente]:
        """Obtiene un cliente por su cédula"""
        try:
            result = await db.execute(
                select(Cliente).where(Cliente.cedula == cedula)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logging.error(f"Error obteniendo cliente {cedula}: {e}")
            return None
    
    @staticmethod
    async def registrar_venta_cliente(
        cedula: str,
        venta_id: int,
        valor_venta: float,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Registra una venta para un cliente y actualiza sus estadísticas.
        
        Args:
            cedula: Cédula del cliente
            venta_id: ID de la venta
            valor_venta: Valor de la venta
            db: Sesión de base de datos
        """
        try:
            cliente = await ClienteManager.obtener_cliente_por_cedula(cedula, db)
            
            if not cliente:
                return {"exito": False, "error": "Cliente no encontrado"}
            
            # Actualizar estadísticas del cliente
            cliente.total_compras += 1
            cliente.valor_total_compras += int(valor_venta)
            cliente.fecha_ultima_compra = datetime.now()
            
            # Actualizar la venta con la cédula del cliente
            result = await db.execute(
                select(Venta).where(Venta.id == venta_id)
            )
            venta = result.scalar_one_or_none()
            
            if venta:
                venta.cliente_cedula = cedula
            
            await db.commit()
            
            logging.info(f"Venta registrada para cliente {cedula}: ${valor_venta}")
            
            return {
                "exito": True,
                "cliente": cliente.to_dict(),
                "venta_id": venta_id
            }
            
        except Exception as e:
            await db.rollback()
            logging.error(f"Error registrando venta para cliente {cedula}: {e}")
            return {"exito": False, "error": str(e)}
    
    @staticmethod
    async def obtener_historial_compras(
        cedula: str, 
        db: AsyncSession,
        limite: int = 50
    ) -> Dict[str, Any]:
        """
        Obtiene el historial completo de compras de un cliente.
        
        Args:
            cedula: Cédula del cliente
            db: Sesión de base de datos
            limite: Número máximo de ventas a retornar
        """
        try:
            # Obtener cliente
            cliente = await ClienteManager.obtener_cliente_por_cedula(cedula, db)
            
            if not cliente:
                return {"exito": False, "error": "Cliente no encontrado"}
            
            # Obtener ventas del cliente con información del producto
            result = await db.execute(
                select(Venta, Producto)
                .join(Producto, Venta.producto_id == Producto.id)
                .where(Venta.cliente_cedula == cedula)
                .order_by(desc(Venta.fecha))
                .limit(limite)
            )
            
            ventas_productos = result.all()
            
            # Formatear historial
            historial = []
            for venta, producto in ventas_productos:
                historial.append({
                    "venta_id": venta.id,
                    "fecha": venta.fecha.isoformat() if venta.fecha else None,
                    "producto": {
                        "id": producto.id,
                        "nombre": producto.nombre,
                        "descripcion": producto.descripcion
                    },
                    "cantidad": venta.cantidad,
                    "precio_unitario": venta.total / venta.cantidad if venta.cantidad > 0 else 0,
                    "total": venta.total,
                    "estado": venta.estado,
                    "chat_id": venta.chat_id
                })
            
            return {
                "exito": True,
                "cliente": cliente.to_dict(),
                "historial": historial,
                "total_registros": len(historial)
            }
            
        except Exception as e:
            logging.error(f"Error obteniendo historial de cliente {cedula}: {e}")
            return {"exito": False, "error": str(e)}
    
    @staticmethod
    async def obtener_estadisticas_cliente(cedula: str, db: AsyncSession) -> Dict[str, Any]:
        """Obtiene estadísticas detalladas de un cliente"""
        try:
            cliente = await ClienteManager.obtener_cliente_por_cedula(cedula, db)
            
            if not cliente:
                return {"exito": False, "error": "Cliente no encontrado"}
            
            # Estadísticas de compras por mes (últimos 12 meses)
            hace_12_meses = datetime.now() - timedelta(days=365)
            
            result = await db.execute(
                select(
                    func.date_trunc('month', Venta.fecha).label('mes'),
                    func.count(Venta.id).label('cantidad_compras'),
                    func.sum(Venta.total).label('valor_total')
                )
                .where(
                    and_(
                        Venta.cliente_cedula == cedula,
                        Venta.fecha >= hace_12_meses
                    )
                )
                .group_by(func.date_trunc('month', Venta.fecha))
                .order_by(func.date_trunc('month', Venta.fecha))
            )
            
            compras_por_mes = [
                {
                    "mes": row.mes.isoformat() if row.mes else None,
                    "cantidad_compras": row.cantidad_compras,
                    "valor_total": float(row.valor_total) if row.valor_total else 0
                }
                for row in result.all()
            ]
            
            # Productos más comprados
            result = await db.execute(
                select(
                    Producto.nombre,
                    func.sum(Venta.cantidad).label('cantidad_total'),
                    func.sum(Venta.total).label('valor_total')
                )
                .join(Producto, Venta.producto_id == Producto.id)
                .where(Venta.cliente_cedula == cedula)
                .group_by(Producto.id, Producto.nombre)
                .order_by(desc(func.sum(Venta.cantidad)))
                .limit(10)
            )
            
            productos_favoritos = [
                {
                    "producto": row.nombre,
                    "cantidad_total": row.cantidad_total,
                    "valor_total": float(row.valor_total) if row.valor_total else 0
                }
                for row in result.all()
            ]
            
            return {
                "exito": True,
                "cliente": cliente.to_dict(),
                "estadisticas": {
                    "compras_por_mes": compras_por_mes,
                    "productos_favoritos": productos_favoritos,
                    "promedio_compra": cliente.valor_total_compras / cliente.total_compras if cliente.total_compras > 0 else 0,
                    "dias_desde_ultima_compra": (datetime.now() - cliente.fecha_ultima_compra).days if cliente.fecha_ultima_compra else None
                }
            }
            
        except Exception as e:
            logging.error(f"Error obteniendo estadísticas de cliente {cedula}: {e}")
            return {"exito": False, "error": str(e)}
    
    @staticmethod
    async def buscar_clientes(
        termino: str,
        db: AsyncSession,
        limite: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Busca clientes por nombre, cédula o teléfono.
        
        Args:
            termino: Término de búsqueda
            db: Sesión de base de datos
            limite: Número máximo de resultados
        """
        try:
            # Construir consulta de búsqueda
            result = await db.execute(
                select(Cliente)
                .where(
                    Cliente.activo == True,
                    (
                        Cliente.nombre_completo.ilike(f"%{termino}%") |
                        Cliente.cedula.ilike(f"%{termino}%") |
                        Cliente.telefono.ilike(f"%{termino}%")
                    )
                )
                .order_by(desc(Cliente.fecha_ultima_compra))
                .limit(limite)
            )
            
            clientes = result.scalars().all()
            
            return [cliente.to_dict() for cliente in clientes]
            
        except Exception as e:
            logging.error(f"Error buscando clientes con término '{termino}': {e}")
            return []
    
    @staticmethod
    async def obtener_clientes_top(db: AsyncSession, limite: int = 10) -> List[Dict[str, Any]]:
        """Obtiene los clientes con mayor valor de compras"""
        try:
            result = await db.execute(
                select(Cliente)
                .where(Cliente.activo == True)
                .order_by(desc(Cliente.valor_total_compras))
                .limit(limite)
            )
            
            clientes = result.scalars().all()
            
            return [cliente.to_dict() for cliente in clientes]
            
        except Exception as e:
            logging.error(f"Error obteniendo clientes top: {e}")
            return [] 