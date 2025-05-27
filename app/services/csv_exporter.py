"""
Servicio de exportación de datos a CSV
Permite exportar inventarios, clientes, ventas y logs de RAG
"""

import csv
import io
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, and_, or_

from app.models.producto import Producto
from app.models.cliente import Cliente
from app.models.venta import Venta
from app.models.mensaje import Mensaje

class CSVExporter:
    """
    Exportador de datos a CSV con múltiples formatos y filtros
    """
    
    @staticmethod
    async def exportar_inventario(
        db: AsyncSession,
        incluir_inactivos: bool = False,
        solo_con_stock: bool = False
    ) -> Dict[str, Any]:
        """
        Exporta el inventario completo a CSV
        
        Args:
            db: Sesión de base de datos
            incluir_inactivos: Incluir productos inactivos
            solo_con_stock: Solo productos con stock > 0
        """
        try:
            # Construir consulta con filtros
            query = select(Producto)
            
            if not incluir_inactivos:
                query = query.where(Producto.activo == True)
            
            if solo_con_stock:
                query = query.where(Producto.stock > 0)
            
            query = query.order_by(Producto.nombre)
            
            result = await db.execute(query)
            productos = result.scalars().all()
            
            # Crear CSV en memoria
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Encabezados
            headers = [
                'ID',
                'Nombre',
                'Descripción',
                'Precio',
                'Stock',
                'Categoría',
                'Activo',
                'Fecha Creación',
                'Última Actualización'
            ]
            writer.writerow(headers)
            
            # Datos
            for producto in productos:
                row = [
                    producto.id,
                    producto.nombre,
                    producto.descripcion or '',
                    producto.precio,
                    producto.stock,
                    producto.categoria or '',
                    'Sí' if producto.activo else 'No',
                    producto.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if producto.fecha_creacion else '',
                    producto.fecha_actualizacion.strftime('%Y-%m-%d %H:%M:%S') if producto.fecha_actualizacion else ''
                ]
                writer.writerow(row)
            
            csv_content = output.getvalue()
            output.close()
            
            return {
                "exito": True,
                "csv_content": csv_content,
                "total_registros": len(productos),
                "nombre_archivo": f"inventario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "filtros_aplicados": {
                    "incluir_inactivos": incluir_inactivos,
                    "solo_con_stock": solo_con_stock
                }
            }
            
        except Exception as e:
            logging.error(f"Error exportando inventario: {e}")
            return {"exito": False, "error": str(e)}
    
    @staticmethod
    async def exportar_clientes(
        db: AsyncSession,
        incluir_inactivos: bool = False,
        con_compras: bool = False,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Exporta la base de clientes a CSV
        
        Args:
            db: Sesión de base de datos
            incluir_inactivos: Incluir clientes inactivos
            con_compras: Solo clientes que han realizado compras
            fecha_desde: Filtrar por fecha de registro desde
            fecha_hasta: Filtrar por fecha de registro hasta
        """
        try:
            # Construir consulta con filtros
            query = select(Cliente)
            
            if not incluir_inactivos:
                query = query.where(Cliente.activo == True)
            
            if con_compras:
                query = query.where(Cliente.total_compras > 0)
            
            if fecha_desde:
                query = query.where(Cliente.fecha_registro >= fecha_desde)
            
            if fecha_hasta:
                query = query.where(Cliente.fecha_registro <= fecha_hasta)
            
            query = query.order_by(desc(Cliente.valor_total_compras))
            
            result = await db.execute(query)
            clientes = result.scalars().all()
            
            # Crear CSV en memoria
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Encabezados
            headers = [
                'Cédula',
                'Nombre Completo',
                'Teléfono',
                'Dirección',
                'Barrio',
                'Indicaciones Adicionales',
                'Fecha Registro',
                'Fecha Última Compra',
                'Total Compras',
                'Valor Total Compras',
                'Promedio por Compra',
                'Activo',
                'Notas'
            ]
            writer.writerow(headers)
            
            # Datos
            for cliente in clientes:
                promedio_compra = (cliente.valor_total_compras / cliente.total_compras) if cliente.total_compras > 0 else 0
                
                row = [
                    cliente.cedula,
                    cliente.nombre_completo,
                    cliente.telefono,
                    cliente.direccion,
                    cliente.barrio,
                    cliente.indicaciones_adicionales or '',
                    cliente.fecha_registro.strftime('%Y-%m-%d %H:%M:%S') if cliente.fecha_registro else '',
                    cliente.fecha_ultima_compra.strftime('%Y-%m-%d %H:%M:%S') if cliente.fecha_ultima_compra else '',
                    cliente.total_compras,
                    cliente.valor_total_compras,
                    f"{promedio_compra:.2f}",
                    'Sí' if cliente.activo else 'No',
                    cliente.notas or ''
                ]
                writer.writerow(row)
            
            csv_content = output.getvalue()
            output.close()
            
            return {
                "exito": True,
                "csv_content": csv_content,
                "total_registros": len(clientes),
                "nombre_archivo": f"clientes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "filtros_aplicados": {
                    "incluir_inactivos": incluir_inactivos,
                    "con_compras": con_compras,
                    "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                    "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None
                }
            }
            
        except Exception as e:
            logging.error(f"Error exportando clientes: {e}")
            return {"exito": False, "error": str(e)}
    
    @staticmethod
    async def exportar_ventas(
        db: AsyncSession,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        estado: Optional[str] = None,
        incluir_detalles_cliente: bool = True,
        incluir_detalles_producto: bool = True
    ) -> Dict[str, Any]:
        """
        Exporta las ventas a CSV con detalles completos
        
        Args:
            db: Sesión de base de datos
            fecha_desde: Filtrar ventas desde esta fecha
            fecha_hasta: Filtrar ventas hasta esta fecha
            estado: Filtrar por estado específico
            incluir_detalles_cliente: Incluir información del cliente
            incluir_detalles_producto: Incluir información del producto
        """
        try:
            # Construir consulta con joins
            if incluir_detalles_cliente and incluir_detalles_producto:
                query = select(Venta, Cliente, Producto).outerjoin(
                    Cliente, Venta.cliente_cedula == Cliente.cedula
                ).join(
                    Producto, Venta.producto_id == Producto.id
                )
            elif incluir_detalles_cliente:
                query = select(Venta, Cliente).outerjoin(
                    Cliente, Venta.cliente_cedula == Cliente.cedula
                )
            elif incluir_detalles_producto:
                query = select(Venta, Producto).join(
                    Producto, Venta.producto_id == Producto.id
                )
            else:
                query = select(Venta)
            
            # Aplicar filtros
            if fecha_desde:
                query = query.where(Venta.fecha >= fecha_desde)
            
            if fecha_hasta:
                query = query.where(Venta.fecha <= fecha_hasta)
            
            if estado:
                query = query.where(Venta.estado == estado)
            
            query = query.order_by(desc(Venta.fecha))
            
            result = await db.execute(query)
            
            # Crear CSV en memoria
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Encabezados dinámicos
            headers = [
                'ID Venta',
                'Fecha',
                'Cantidad',
                'Total',
                'Estado',
                'Chat ID'
            ]
            
            if incluir_detalles_producto:
                headers.extend([
                    'Producto ID',
                    'Producto Nombre',
                    'Producto Descripción',
                    'Precio Unitario'
                ])
            
            if incluir_detalles_cliente:
                headers.extend([
                    'Cliente Cédula',
                    'Cliente Nombre',
                    'Cliente Teléfono',
                    'Cliente Dirección',
                    'Cliente Barrio'
                ])
            
            writer.writerow(headers)
            
            # Procesar datos según el tipo de consulta
            registros_procesados = 0
            
            if incluir_detalles_cliente and incluir_detalles_producto:
                for venta, cliente, producto in result.all():
                    row = [
                        venta.id,
                        venta.fecha.strftime('%Y-%m-%d %H:%M:%S') if venta.fecha else '',
                        venta.cantidad,
                        venta.total,
                        venta.estado or '',
                        venta.chat_id or '',
                        producto.id if producto else '',
                        producto.nombre if producto else '',
                        producto.descripcion if producto else '',
                        producto.precio if producto else '',
                        cliente.cedula if cliente else '',
                        cliente.nombre_completo if cliente else '',
                        cliente.telefono if cliente else '',
                        cliente.direccion if cliente else '',
                        cliente.barrio if cliente else ''
                    ]
                    writer.writerow(row)
                    registros_procesados += 1
            
            elif incluir_detalles_cliente:
                for venta, cliente in result.all():
                    row = [
                        venta.id,
                        venta.fecha.strftime('%Y-%m-%d %H:%M:%S') if venta.fecha else '',
                        venta.cantidad,
                        venta.total,
                        venta.estado or '',
                        venta.chat_id or '',
                        cliente.cedula if cliente else '',
                        cliente.nombre_completo if cliente else '',
                        cliente.telefono if cliente else '',
                        cliente.direccion if cliente else '',
                        cliente.barrio if cliente else ''
                    ]
                    writer.writerow(row)
                    registros_procesados += 1
            
            elif incluir_detalles_producto:
                for venta, producto in result.all():
                    row = [
                        venta.id,
                        venta.fecha.strftime('%Y-%m-%d %H:%M:%S') if venta.fecha else '',
                        venta.cantidad,
                        venta.total,
                        venta.estado or '',
                        venta.chat_id or '',
                        producto.id if producto else '',
                        producto.nombre if producto else '',
                        producto.descripcion if producto else '',
                        producto.precio if producto else ''
                    ]
                    writer.writerow(row)
                    registros_procesados += 1
            
            else:
                for venta in result.scalars().all():
                    row = [
                        venta.id,
                        venta.fecha.strftime('%Y-%m-%d %H:%M:%S') if venta.fecha else '',
                        venta.cantidad,
                        venta.total,
                        venta.estado or '',
                        venta.chat_id or ''
                    ]
                    writer.writerow(row)
                    registros_procesados += 1
            
            csv_content = output.getvalue()
            output.close()
            
            return {
                "exito": True,
                "csv_content": csv_content,
                "total_registros": registros_procesados,
                "nombre_archivo": f"ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "filtros_aplicados": {
                    "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                    "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
                    "estado": estado,
                    "incluir_detalles_cliente": incluir_detalles_cliente,
                    "incluir_detalles_producto": incluir_detalles_producto
                }
            }
            
        except Exception as e:
            logging.error(f"Error exportando ventas: {e}")
            return {"exito": False, "error": str(e)}
    
    @staticmethod
    async def exportar_conversaciones_rag(
        db: AsyncSession,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        tipo_mensaje: Optional[str] = None,
        solo_con_rag: bool = True,
        incluir_metadatos: bool = True
    ) -> Dict[str, Any]:
        """
        Exporta las conversaciones y consultas RAG a CSV
        
        Args:
            db: Sesión de base de datos
            fecha_desde: Filtrar mensajes desde esta fecha
            fecha_hasta: Filtrar mensajes hasta esta fecha
            tipo_mensaje: Filtrar por tipo específico
            solo_con_rag: Solo mensajes que usaron RAG
            incluir_metadatos: Incluir metadatos en columnas separadas
        """
        try:
            # Construir consulta
            query = select(Mensaje)
            
            if fecha_desde:
                query = query.where(Mensaje.timestamp >= fecha_desde)
            
            if fecha_hasta:
                query = query.where(Mensaje.timestamp <= fecha_hasta)
            
            if tipo_mensaje:
                query = query.where(Mensaje.tipo_mensaje == tipo_mensaje)
            
            if solo_con_rag:
                query = query.where(Mensaje.tipo_mensaje.in_(['inventario', 'venta', 'contexto', 'cliente']))
            
            query = query.order_by(desc(Mensaje.timestamp))
            
            result = await db.execute(query)
            mensajes = result.scalars().all()
            
            # Crear CSV en memoria
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Encabezados
            headers = [
                'ID',
                'Chat ID',
                'Timestamp',
                'Remitente',
                'Mensaje',
                'Tipo Mensaje',
                'Estado Venta',
                'Respuesta'
            ]
            
            if incluir_metadatos:
                headers.extend([
                    'Metadatos JSON',
                    'Productos Mencionados',
                    'Cliente Detectado',
                    'Valor Venta'
                ])
            
            writer.writerow(headers)
            
            # Datos
            for mensaje in mensajes:
                row = [
                    mensaje.id,
                    mensaje.chat_id or '',
                    mensaje.timestamp.strftime('%Y-%m-%d %H:%M:%S') if mensaje.timestamp else '',
                    mensaje.remitente or '',
                    mensaje.mensaje or '',
                    mensaje.tipo_mensaje or '',
                    mensaje.estado_venta or '',
                    mensaje.respuesta or ''
                ]
                
                if incluir_metadatos:
                    import json
                    metadatos_str = ''
                    productos_mencionados = ''
                    cliente_detectado = ''
                    valor_venta = ''
                    
                    if mensaje.metadatos:
                        try:
                            metadatos = mensaje.metadatos if isinstance(mensaje.metadatos, dict) else json.loads(mensaje.metadatos)
                            metadatos_str = json.dumps(metadatos, ensure_ascii=False)
                            
                            # Extraer información específica
                            if 'productos' in metadatos:
                                productos = metadatos['productos']
                                if isinstance(productos, list):
                                    productos_mencionados = '; '.join([p.get('producto', '') for p in productos])
                            
                            if 'datos_cliente' in metadatos:
                                datos_cliente = metadatos['datos_cliente']
                                if isinstance(datos_cliente, dict):
                                    cliente_detectado = datos_cliente.get('nombre_completo', datos_cliente.get('cedula', ''))
                            
                            if 'total' in metadatos:
                                valor_venta = str(metadatos['total'])
                                
                        except Exception as e:
                            metadatos_str = f"Error procesando metadatos: {e}"
                    
                    row.extend([
                        metadatos_str,
                        productos_mencionados,
                        cliente_detectado,
                        valor_venta
                    ])
                
                writer.writerow(row)
            
            csv_content = output.getvalue()
            output.close()
            
            return {
                "exito": True,
                "csv_content": csv_content,
                "total_registros": len(mensajes),
                "nombre_archivo": f"conversaciones_rag_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "filtros_aplicados": {
                    "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                    "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
                    "tipo_mensaje": tipo_mensaje,
                    "solo_con_rag": solo_con_rag,
                    "incluir_metadatos": incluir_metadatos
                }
            }
            
        except Exception as e:
            logging.error(f"Error exportando conversaciones RAG: {e}")
            return {"exito": False, "error": str(e)}
    
    @staticmethod
    async def exportar_reporte_completo(
        db: AsyncSession,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Exporta un reporte completo con estadísticas generales
        """
        try:
            # Obtener estadísticas generales
            stats = {}
            
            # Total productos
            result = await db.execute(select(func.count(Producto.id)))
            stats['total_productos'] = result.scalar()
            
            # Total clientes
            result = await db.execute(select(func.count(Cliente.cedula)))
            stats['total_clientes'] = result.scalar()
            
            # Total ventas
            query = select(func.count(Venta.id), func.sum(Venta.total))
            if fecha_desde:
                query = query.where(Venta.fecha >= fecha_desde)
            if fecha_hasta:
                query = query.where(Venta.fecha <= fecha_hasta)
            
            result = await db.execute(query)
            total_ventas, valor_total_ventas = result.first()
            stats['total_ventas'] = total_ventas or 0
            stats['valor_total_ventas'] = valor_total_ventas or 0
            
            # Crear CSV de resumen
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Encabezados
            writer.writerow(['Métrica', 'Valor'])
            
            # Datos de resumen
            writer.writerow(['Total Productos', stats['total_productos']])
            writer.writerow(['Total Clientes', stats['total_clientes']])
            writer.writerow(['Total Ventas', stats['total_ventas']])
            writer.writerow(['Valor Total Ventas', f"${stats['valor_total_ventas']:,.2f}"])
            writer.writerow(['Fecha Generación', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            
            if fecha_desde:
                writer.writerow(['Filtro Fecha Desde', fecha_desde.strftime('%Y-%m-%d')])
            if fecha_hasta:
                writer.writerow(['Filtro Fecha Hasta', fecha_hasta.strftime('%Y-%m-%d')])
            
            csv_content = output.getvalue()
            output.close()
            
            return {
                "exito": True,
                "csv_content": csv_content,
                "estadisticas": stats,
                "nombre_archivo": f"reporte_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
            
        except Exception as e:
            logging.error(f"Error exportando reporte completo: {e}")
            return {"exito": False, "error": str(e)} 