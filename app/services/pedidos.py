from typing import Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.mensaje import Mensaje
from app.models.venta import Venta
from app.models.producto import Producto
from app.services.cliente_manager import ClienteManager
import json
import logging
from datetime import datetime
import re

class PedidoManager:
    """Maneja el estado de pedidos y recolección de datos del cliente"""
    
    CAMPOS_REQUERIDOS = [
        "nombre_completo",
        "cedula", 
        "telefono",
        "correo",
        "direccion",
        "barrio",
        "indicaciones_adicionales"
    ]
    
    @staticmethod
    async def obtener_estado_pedido(chat_id: str, db: AsyncSession) -> Dict:
        """Obtiene el estado actual del pedido para un chat"""
        try:
            # Buscar el mensaje del pedido que contiene los productos
            result = await db.execute(
                select(Mensaje)
                .where(
                    Mensaje.chat_id == chat_id,
                    Mensaje.estado_venta.in_(["pendiente", "recolectando_datos"]),
                    Mensaje.remitente == "sistema"  # Mensajes del sistema que contienen el pedido
                )
                .order_by(Mensaje.timestamp.desc())
                .limit(1)
            )
            mensaje = result.scalar_one_or_none()
            
            if not mensaje or not mensaje.metadatos:
                return {"tiene_pedido": False}
            
            # Forzar refresh para obtener la versión más reciente del mensaje
            await db.refresh(mensaje)
            
            metadatos = mensaje.metadatos if isinstance(mensaje.metadatos, dict) else json.loads(mensaje.metadatos)
            
            # Verificar que tiene productos (es un pedido válido)
            if "productos" not in metadatos:
                return {"tiene_pedido": False}
            
            return {
                "tiene_pedido": True,
                "estado": mensaje.estado_venta,
                "productos": metadatos.get("productos", []),
                "datos_cliente": metadatos.get("datos_cliente", {}),
                "campos_faltantes": PedidoManager._obtener_campos_faltantes(metadatos.get("datos_cliente", {}))
            }
        except Exception as e:
            logging.error(f"Error obteniendo estado de pedido: {e}")
            return {"tiene_pedido": False}
    
    @staticmethod
    def _obtener_campos_faltantes(datos_cliente: Dict) -> List[str]:
        """Obtiene los campos que faltan por recolectar"""
        return [campo for campo in PedidoManager.CAMPOS_REQUERIDOS if not datos_cliente.get(campo)]
    
    @staticmethod
    async def agregar_producto_pedido(chat_id: str, producto: str, cantidad: int, precio: float, db: AsyncSession, producto_id: int = None) -> Dict:
        """Agrega un producto al pedido actual o crea uno nuevo"""
        try:
            # VALIDACIÓN: Verificar cantidad válida
            if cantidad <= 0:
                return {"exito": False, "error": "La cantidad debe ser mayor a 0"}
            
            if cantidad > 1000:
                return {"exito": False, "error": "La cantidad máxima por producto es 1000 unidades. Para pedidos mayores, contacta directamente con ventas."}
            
            estado_actual = await PedidoManager.obtener_estado_pedido(chat_id, db)
            
            # Si no se proporciona producto_id, intentar encontrarlo por nombre
            if not producto_id:
                result_producto = await db.execute(
                    select(Producto).where(Producto.nombre.ilike(f"%{producto}%"))
                )
                producto_obj = result_producto.scalar_one_or_none()
                if producto_obj:
                    producto_id = producto_obj.id
                    precio = producto_obj.precio  # Usar precio real del producto
                    
                    # VALIDACIÓN: Verificar stock disponible
                    if cantidad > producto_obj.stock:
                        return {
                            "exito": False, 
                            "error": f"Stock insuficiente. Solo tenemos {producto_obj.stock} unidades disponibles de {producto}",
                            "stock_disponible": producto_obj.stock
                        }
                else:
                    return {"exito": False, "error": f"Producto '{producto}' no encontrado en nuestro inventario"}
            
            # VALIDACIÓN: Verificar que el precio es razonable
            if precio <= 0:
                return {"exito": False, "error": "Error en el precio del producto"}
            
            total_producto = cantidad * precio
            
            # VALIDACIÓN: Verificar que el total no sea excesivo
            if total_producto > 50000000:  # 50 millones
                return {"exito": False, "error": "El valor total del producto excede el límite permitido. Contacta directamente con ventas."}
            
            nuevo_producto = {
                "producto": producto,
                "producto_id": producto_id,
                "cantidad": cantidad,
                "precio": precio,
                "total": total_producto
            }
            
            if estado_actual["tiene_pedido"]:
                # Actualizar pedido existente
                productos = estado_actual["productos"]
                
                # VALIDACIÓN: Verificar que no se exceda el límite de productos por pedido
                if len(productos) >= 20:
                    return {"exito": False, "error": "Máximo 20 productos diferentes por pedido"}
                
                productos.append(nuevo_producto)
                
                # Buscar el último mensaje de pedido (debe ser del sistema)
                result = await db.execute(
                    select(Mensaje)
                    .where(
                        Mensaje.chat_id == chat_id,
                        Mensaje.estado_venta.in_(["pendiente", "recolectando_datos"]),
                        Mensaje.remitente == "sistema"  # Solo mensajes del sistema que contienen pedidos
                    )
                    .order_by(Mensaje.timestamp.desc())
                    .limit(1)
                )
                mensaje = result.scalar_one()
                
                metadatos = mensaje.metadatos if isinstance(mensaje.metadatos, dict) else json.loads(mensaje.metadatos)
                
                # SOLUCIÓN: Crear nueva instancia del diccionario para que SQLAlchemy detecte el cambio
                metadatos_nuevos = dict(metadatos)
                metadatos_nuevos["productos"] = productos
                mensaje.metadatos = metadatos_nuevos
                
                # Logging para debugging
                logging.info(f"Actualizando mensaje del sistema ID {mensaje.id} con {len(productos)} productos")
                for p in productos:
                    logging.info(f"  - {p['producto']} x{p['cantidad']}")
                
                # Forzar flush y refresh para asegurar que los cambios se persistan
                await db.flush()
                await db.refresh(mensaje)
                
            else:
                # Crear nuevo pedido
                metadatos = {
                    "productos": [nuevo_producto],
                    "datos_cliente": {}
                }
                
                mensaje = Mensaje(
                    chat_id=chat_id,
                    remitente="sistema",
                    mensaje=f"Pedido iniciado: {producto} x{cantidad}",
                    estado_venta="pendiente",
                    tipo_mensaje="venta",
                    metadatos=metadatos
                )
                db.add(mensaje)
            
            await db.commit()
            
            total_pedido = sum(p["total"] for p in metadatos["productos"])
            
            return {
                "exito": True,
                "productos": metadatos["productos"],
                "total": total_pedido,
                "cantidad_productos": len(metadatos["productos"])
            }
            
        except Exception as e:
            logging.error(f"Error agregando producto al pedido: {e}")
            await db.rollback()
            return {"exito": False, "error": str(e)}
    
    @staticmethod
    async def actualizar_datos_cliente(chat_id: str, campo: str, valor: str, db: AsyncSession) -> Dict:
        """Actualiza un campo de datos del cliente en el mensaje del pedido"""
        try:
            # VALIDACIÓN: Validar el dato antes de guardarlo
            validacion = PedidoManager.validar_dato_cliente(campo, valor)
            if not validacion["valido"]:
                return {
                    "exito": False, 
                    "error": validacion["error"],
                    "tipo_error": "validacion",
                    "campo": campo
                }
            
            # Usar el valor normalizado de la validación
            valor_normalizado = validacion["valor_normalizado"]
            
            # Buscar el mensaje del pedido que contiene los productos
            result = await db.execute(
                select(Mensaje)
                .where(
                    Mensaje.chat_id == chat_id,
                    Mensaje.estado_venta.in_(["pendiente", "recolectando_datos"]),
                    Mensaje.remitente == "sistema"  # Mensajes del sistema que contienen el pedido
                )
                .order_by(Mensaje.timestamp.desc())
                .limit(1)
            )
            mensaje_pedido = result.scalar_one_or_none()
            
            if not mensaje_pedido:
                return {"exito": False, "error": "No hay pedido activo"}
            
            metadatos = mensaje_pedido.metadatos if isinstance(mensaje_pedido.metadatos, dict) else json.loads(mensaje_pedido.metadatos)
            
            # Verificar que el mensaje tiene productos (es el pedido principal)
            if "productos" not in metadatos:
                return {"exito": False, "error": "Mensaje de pedido no válido"}
            
            # SOLUCIÓN: Crear nuevas instancias de diccionarios para que SQLAlchemy detecte los cambios
            metadatos_nuevos = dict(metadatos)
            
            if "datos_cliente" not in metadatos_nuevos:
                metadatos_nuevos["datos_cliente"] = {}
            
            # Crear nueva instancia del diccionario datos_cliente
            datos_cliente_nuevos = dict(metadatos_nuevos["datos_cliente"])
            datos_cliente_nuevos[campo] = valor_normalizado  # Usar valor normalizado
            metadatos_nuevos["datos_cliente"] = datos_cliente_nuevos
            
            # Asignar el nuevo diccionario completo
            mensaje_pedido.metadatos = metadatos_nuevos
            mensaje_pedido.estado_venta = "recolectando_datos"
            
            campos_faltantes = PedidoManager._obtener_campos_faltantes(metadatos_nuevos["datos_cliente"])
            
            # MEJORA: Verificar si se completaron todos los campos para finalizar automáticamente
            datos_completos = len(campos_faltantes) == 0
            
            if datos_completos:
                # Marcar el mensaje como listo para finalizar
                mensaje_pedido.estado_venta = "listo_para_finalizar"
                await db.commit()
                
                # Finalizar pedido automáticamente
                resultado_finalizacion = await PedidoManager.finalizar_pedido(chat_id, db)
                
                if resultado_finalizacion["exito"]:
                    logging.info(f"Pedido finalizado automáticamente para chat {chat_id}")
                    return {
                        "exito": True,
                        "campos_faltantes": [],
                        "datos_completos": True,
                        "pedido_finalizado": True,
                        "ventas_creadas": resultado_finalizacion.get("ventas_creadas", []),
                        "total_ventas": resultado_finalizacion.get("total_ventas", 0),
                        "mensaje_finalizacion": "Tu pedido ha sido registrado exitosamente. Pronto te contactaremos para coordinar la entrega. ¡Gracias por confiar en Sextinvalle!"
                    }
                else:
                    # Si falla la finalización, mantener el estado de recolección
                    logging.error(f"Error finalizando pedido automáticamente: {resultado_finalizacion.get('error')}")
                    return {
                        "exito": True,
                        "campos_faltantes": [],
                        "datos_completos": True,
                        "pedido_finalizado": False,
                        "error_finalizacion": resultado_finalizacion.get("error")
                    }
            else:
                await db.commit()
                
                logging.info(f"Datos del cliente actualizados: {campo} = {valor}")
                logging.info(f"Datos cliente actuales: {metadatos_nuevos['datos_cliente']}")
                logging.info(f"Campos faltantes: {campos_faltantes}")
                
                return {
                    "exito": True,
                    "campos_faltantes": campos_faltantes,
                    "datos_completos": False,
                    "pedido_finalizado": False,
                    "siguiente_campo": campos_faltantes[0] if campos_faltantes else None
                }
            
        except Exception as e:
            logging.error(f"Error actualizando datos del cliente: {e}")
            await db.rollback()
            return {"exito": False, "error": str(e)}
    
    @staticmethod
    async def finalizar_pedido(chat_id: str, db: AsyncSession) -> Dict:
        """Finaliza el pedido marcándolo como cerrado y crea las ventas correspondientes"""
        try:
            result = await db.execute(
                select(Mensaje)
                .where(
                    Mensaje.chat_id == chat_id,
                    Mensaje.estado_venta.in_(["pendiente", "recolectando_datos", "listo_para_finalizar"])
                )
                .order_by(Mensaje.timestamp.desc())
                .limit(1)
            )
            mensaje = result.scalar_one_or_none()
            
            if not mensaje:
                return {"exito": False, "error": "No hay pedido activo"}
            
            metadatos = mensaje.metadatos if isinstance(mensaje.metadatos, dict) else json.loads(mensaje.metadatos)
            campos_faltantes = PedidoManager._obtener_campos_faltantes(metadatos.get("datos_cliente", {}))
            
            if campos_faltantes:
                return {"exito": False, "error": "Faltan datos del cliente", "campos_faltantes": campos_faltantes}
            
            # NUEVO: Crear o actualizar cliente
            datos_cliente = metadatos.get("datos_cliente", {})
            cedula = datos_cliente.get("cedula")
            
            cliente_resultado = None
            if cedula:
                cliente_resultado = await ClienteManager.crear_o_actualizar_cliente(datos_cliente, db)
                if not cliente_resultado["exito"]:
                    logging.warning(f"No se pudo crear/actualizar cliente {cedula}: {cliente_resultado.get('error')}")
                else:
                    logging.info(f"Cliente {cliente_resultado['accion']}: {cedula} - {datos_cliente.get('nombre_completo')}")
            
            # Crear ventas para cada producto del pedido
            productos_pedido = metadatos.get("productos", [])
            ventas_creadas = []
            total_valor_ventas = 0
            
            for producto_info in productos_pedido:
                try:
                    nombre_producto = producto_info.get("producto", "")
                    cantidad = producto_info.get("cantidad", 0)
                    producto_id = producto_info.get("producto_id")
                    
                    # Buscar producto por ID si está disponible, sino por nombre
                    if producto_id:
                        result_producto = await db.execute(
                            select(Producto).where(Producto.id == producto_id)
                        )
                    else:
                        result_producto = await db.execute(
                            select(Producto).where(Producto.nombre.ilike(f"%{nombre_producto}%"))
                        )
                    
                    producto = result_producto.scalar_one_or_none()
                    
                    if producto and producto.stock >= cantidad:
                        # Crear venta
                        venta = Venta(
                            producto_id=producto.id,
                            cantidad=cantidad,
                            total=producto.precio * cantidad,
                            chat_id=chat_id,
                            estado="completada",
                            cliente_cedula=cedula,  # NUEVO: Asociar venta con cliente
                            detalle={
                                "datos_cliente": datos_cliente,
                                "pedido_id": mensaje.id
                            }
                        )
                        
                        # Descontar stock
                        producto.stock -= cantidad
                        
                        db.add(venta)
                        await db.flush()
                        await db.refresh(venta)
                        
                        total_valor_ventas += venta.total
                        
                        ventas_creadas.append({
                            "venta_id": venta.id,
                            "producto": nombre_producto,
                            "cantidad": cantidad,
                            "total": venta.total
                        })
                        
                        # NUEVO: Registrar venta en el historial del cliente
                        if cedula and cliente_resultado and cliente_resultado["exito"]:
                            await ClienteManager.registrar_venta_cliente(
                                cedula=cedula,
                                venta_id=venta.id,
                                valor_venta=venta.total,
                                db=db
                            )
                        
                        logging.info(f"Venta creada: ID {venta.id} para producto {nombre_producto} - Cliente: {cedula}")
                    else:
                        logging.warning(f"No se pudo crear venta para {nombre_producto}: producto no encontrado o stock insuficiente")
                        
                except Exception as e:
                    logging.error(f"Error creando venta para producto {producto_info}: {e}")
                    continue
            
            # Marcar pedido como cerrado
            mensaje.estado_venta = "cerrada"
            metadatos["ventas_creadas"] = ventas_creadas
            metadatos["fecha_finalizacion"] = datetime.now().isoformat()
            mensaje.metadatos = metadatos
            
            await db.commit()
            
            return {
                "exito": True,
                "pedido": metadatos,
                "ventas_creadas": ventas_creadas,
                "total_ventas": len(ventas_creadas)
            }
            
        except Exception as e:
            logging.error(f"Error finalizando pedido: {e}")
            await db.rollback()
            return {"exito": False, "error": str(e)}
    
    @staticmethod
    async def mostrar_pedido_actual(chat_id: str, db: AsyncSession) -> Optional[Dict]:
        """Muestra el resumen del pedido actual"""
        try:
            estado = await PedidoManager.obtener_estado_pedido(chat_id, db)
            
            if not estado["tiene_pedido"]:
                return None
            
            productos = estado["productos"]
            datos_cliente = estado["datos_cliente"]
            total = sum(p["total"] for p in productos)
            
            resumen = {
                "productos": productos,
                "total": total,
                "datos_cliente": datos_cliente,
                "estado": estado["estado"],
                "campos_faltantes": estado["campos_faltantes"]
            }
            
            return resumen
            
        except Exception as e:
            logging.error(f"Error mostrando pedido actual: {e}")
            return None
    
    @staticmethod
    def validar_dato_cliente(campo: str, valor: str) -> Dict[str, any]:
        """Valida un dato del cliente según el campo"""
        valor = valor.strip()
        
        if campo == "nombre_completo":
            if len(valor) < 3:
                return {"valido": False, "error": "El nombre debe tener al menos 3 caracteres"}
            if len(valor) > 100:
                return {"valido": False, "error": "El nombre es demasiado largo"}
            if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$", valor):
                return {"valido": False, "error": "El nombre solo puede contener letras y espacios"}
                
        elif campo == "cedula":
            if not valor.isdigit():
                return {"valido": False, "error": "La cédula debe contener solo números"}
            if len(valor) < 6 or len(valor) > 12:
                return {"valido": False, "error": "La cédula debe tener entre 6 y 12 dígitos"}
                
        elif campo == "telefono":
            # Limpiar formato de teléfono
            telefono_limpio = re.sub(r'[^\d]', '', valor)
            if len(telefono_limpio) < 10:
                return {"valido": False, "error": "El teléfono debe tener al menos 10 dígitos"}
            if len(telefono_limpio) > 15:
                return {"valido": False, "error": "El teléfono es demasiado largo"}
            if not telefono_limpio.startswith(('3', '1', '2', '4', '5', '6', '7', '8')):
                return {"valido": False, "error": "Formato de teléfono inválido"}
            # Normalizar formato
            valor = telefono_limpio
                
        elif campo == "direccion":
            if len(valor) < 10:
                return {"valido": False, "error": "La dirección debe ser más específica (mínimo 10 caracteres)"}
            if len(valor) > 200:
                return {"valido": False, "error": "La dirección es demasiado larga"}
                
        elif campo == "barrio":
            if len(valor) < 2:
                return {"valido": False, "error": "El barrio debe tener al menos 2 caracteres"}
            if len(valor) > 50:
                return {"valido": False, "error": "El nombre del barrio es demasiado largo"}
                
        elif campo == "correo":
            # Validación básica de correo electrónico
            patron_correo = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(patron_correo, valor):
                return {"valido": False, "error": "Formato de correo electrónico inválido"}
            if len(valor) > 100:
                return {"valido": False, "error": "El correo electrónico es demasiado largo"}
            # Normalizar a minúsculas
            valor = valor.lower()
                
        elif campo == "indicaciones_adicionales":
            if len(valor) > 300:
                return {"valido": False, "error": "Las indicaciones son demasiado largas"}
            # Las indicaciones pueden estar vacías, pero si se proporcionan deben ser útiles
            if len(valor) > 0 and len(valor) < 3:
                return {"valido": False, "error": "Si proporcionas indicaciones, deben ser más específicas"}
        
        return {"valido": True, "valor_normalizado": valor} 