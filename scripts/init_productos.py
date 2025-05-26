import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import SessionLocal
from app.models.producto import Producto
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Productos de seguridad industrial para Sextinvalle
PRODUCTOS_SEXTINVALLE = [
    # Productos existentes actualizados
    {
        "nombre": "Casco de Seguridad Industrial",
        "descripcion": "Casco de seguridad industrial con barboquejo ajustable, resistente a impactos. Cumple normas ANSI Z89.1",
        "precio": 25000.0,
        "stock": 50,
        "categoria": "Protección Cabeza"
    },
    {
        "nombre": "Guantes de Seguridad Nitrilo",
        "descripcion": "Guantes de nitrilo resistentes a químicos y cortes, ideales para manipulación de materiales peligrosos",
        "precio": 8500.0,
        "stock": 100,
        "categoria": "Protección Manos"
    },
    {
        "nombre": "Botas de Seguridad Punta de Acero",
        "descripcion": "Botas industriales con punta de acero, suela antideslizante y resistente a perforaciones",
        "precio": 85000.0,
        "stock": 30,
        "categoria": "Protección Pies"
    },
    {
        "nombre": "Extintor PQS 10 libras",
        "descripcion": "Extintor de polvo químico seco de 10 libras, ideal para fuegos clase ABC",
        "precio": 120000.0,
        "stock": 25,
        "categoria": "Contra Incendios"
    },
    {
        "nombre": "Chaleco Reflectivo Alta Visibilidad",
        "descripcion": "Chaleco reflectivo con cintas de alta visibilidad, cumple norma ANSI/ISEA 107",
        "precio": 15000.0,
        "stock": 75,
        "categoria": "Señalización"
    },
    {
        "nombre": "Respirador N95",
        "descripcion": "Mascarilla respiratoria N95 para protección contra partículas y aerosoles",
        "precio": 3500.0,
        "stock": 200,
        "categoria": "Protección Respiratoria"
    },
    {
        "nombre": "Gafas de Seguridad Transparentes",
        "descripcion": "Gafas de seguridad con lentes transparentes, protección lateral y tratamiento anti-empañante",
        "precio": 12000.0,
        "stock": 60,
        "categoria": "Protección Visual"
    },
    {
        "nombre": "Arnés de Seguridad Completo",
        "descripcion": "Arnés de cuerpo completo para trabajo en alturas, con anillos D y hebillas de ajuste rápido",
        "precio": 180000.0,
        "stock": 20,
        "categoria": "Trabajo en Alturas"
    },
    {
        "nombre": "Detector de Humo Fotoeléctrico",
        "descripcion": "Detector de humo fotoeléctrico con batería de larga duración, ideal para oficinas e industrias",
        "precio": 45000.0,
        "stock": 40,
        "categoria": "Detección Incendios"
    },
    {
        "nombre": "Señal de Evacuación LED",
        "descripcion": "Señal de evacuación con iluminación LED de emergencia, batería recargable incluida",
        "precio": 65000.0,
        "stock": 35,
        "categoria": "Señalización Emergencia"
    },
    # Productos adicionales para mayor variedad
    {
        "nombre": "Cinta de Seguridad Amarilla",
        "descripcion": "Cinta de seguridad amarilla para demarcación de áreas peligrosas, rollo de 100 metros",
        "precio": 8000.0,
        "stock": 80,
        "categoria": "Demarcación"
    },
    {
        "nombre": "Botiquín Industrial Completo",
        "descripcion": "Botiquín de primeros auxilios para industrias, incluye vendas, antisépticos y medicamentos básicos",
        "precio": 95000.0,
        "stock": 15,
        "categoria": "Primeros Auxilios"
    },
    {
        "nombre": "Linterna LED Recargable",
        "descripcion": "Linterna LED de alta potencia con batería recargable, resistente al agua IP65",
        "precio": 35000.0,
        "stock": 45,
        "categoria": "Iluminación"
    },
    {
        "nombre": "Candado de Seguridad LOTO",
        "descripcion": "Candado de seguridad para bloqueo y etiquetado (LOTO), cuerpo de aluminio resistente",
        "precio": 28000.0,
        "stock": 55,
        "categoria": "Bloqueo Energías"
    },
    {
        "nombre": "Manta Ignífuga Industrial",
        "descripcion": "Manta ignífuga de fibra de vidrio para extinción de fuegos pequeños y protección personal",
        "precio": 75000.0,
        "stock": 20,
        "categoria": "Contra Incendios"
    }
]

async def verificar_y_crear_productos():
    """Verifica productos existentes y crea los faltantes"""
    try:
        async with SessionLocal() as db:
            logger.info("🔍 Verificando productos existentes...")
            
            # Obtener productos existentes
            result = await db.execute(select(Producto))
            productos_existentes = result.scalars().all()
            
            nombres_existentes = {p.nombre for p in productos_existentes}
            logger.info(f"📦 Productos existentes: {len(nombres_existentes)}")
            
            productos_creados = 0
            productos_actualizados = 0
            
            for producto_data in PRODUCTOS_SEXTINVALLE:
                nombre = producto_data["nombre"]
                
                if nombre in nombres_existentes:
                    # Actualizar producto existente
                    result = await db.execute(
                        select(Producto).where(Producto.nombre == nombre)
                    )
                    producto_existente = result.scalar_one()
                    
                    # Actualizar solo si hay cambios significativos
                    cambios = False
                    if producto_existente.descripcion != producto_data["descripcion"]:
                        producto_existente.descripcion = producto_data["descripcion"]
                        cambios = True
                    
                    if producto_existente.categoria != producto_data["categoria"]:
                        producto_existente.categoria = producto_data["categoria"]
                        cambios = True
                    
                    # Actualizar precio solo si es diferente
                    if abs(producto_existente.precio - producto_data["precio"]) > 0.01:
                        logger.info(f"💰 Actualizando precio de {nombre}: ${producto_existente.precio:,.0f} → ${producto_data['precio']:,.0f}")
                        producto_existente.precio = producto_data["precio"]
                        cambios = True
                    
                    if cambios:
                        productos_actualizados += 1
                        logger.info(f"🔄 Actualizado: {nombre}")
                else:
                    # Crear nuevo producto
                    nuevo_producto = Producto(
                        nombre=producto_data["nombre"],
                        descripcion=producto_data["descripcion"],
                        precio=producto_data["precio"],
                        stock=producto_data["stock"],
                        categoria=producto_data["categoria"]
                    )
                    db.add(nuevo_producto)
                    productos_creados += 1
                    logger.info(f"✅ Creado: {nombre} - ${producto_data['precio']:,.0f} (Stock: {producto_data['stock']})")
            
            await db.commit()
            
            # Mostrar resumen final
            logger.info("\n" + "="*60)
            logger.info("📊 RESUMEN DE ACTUALIZACIÓN DE INVENTARIO")
            logger.info("="*60)
            logger.info(f"✅ Productos creados: {productos_creados}")
            logger.info(f"🔄 Productos actualizados: {productos_actualizados}")
            logger.info(f"📦 Total productos en inventario: {len(nombres_existentes) + productos_creados}")
            
            # Mostrar inventario actual
            result = await db.execute(select(Producto).order_by(Producto.categoria, Producto.nombre))
            todos_productos = result.scalars().all()
            
            logger.info(f"\n📋 INVENTARIO ACTUAL POR CATEGORÍAS:")
            categoria_actual = None
            total_valor = 0
            total_items = 0
            
            for producto in todos_productos:
                if producto.categoria != categoria_actual:
                    categoria_actual = producto.categoria
                    logger.info(f"\n🏷️  {categoria_actual}:")
                
                valor_categoria = producto.precio * producto.stock
                total_valor += valor_categoria
                total_items += producto.stock
                
                logger.info(f"   • {producto.nombre}")
                logger.info(f"     Precio: ${producto.precio:,.0f} | Stock: {producto.stock} | Valor: ${valor_categoria:,.0f}")
            
            logger.info(f"\n💰 VALOR TOTAL INVENTARIO: ${total_valor:,.0f}")
            logger.info(f"📦 TOTAL ITEMS EN STOCK: {total_items:,}")
            logger.info("="*60)
            
    except Exception as e:
        logger.error(f"❌ Error actualizando inventario: {e}")
        raise

async def actualizar_stock_producto(nombre_producto: str, nuevo_stock: int):
    """Actualiza el stock de un producto específico"""
    try:
        async with SessionLocal() as db:
            result = await db.execute(
                select(Producto).where(Producto.nombre.ilike(f"%{nombre_producto}%"))
            )
            producto = result.scalar_one_or_none()
            
            if producto:
                stock_anterior = producto.stock
                producto.stock = nuevo_stock
                await db.commit()
                
                logger.info(f"📦 Stock actualizado para {producto.nombre}:")
                logger.info(f"   Stock anterior: {stock_anterior}")
                logger.info(f"   Stock nuevo: {nuevo_stock}")
                logger.info(f"   Diferencia: {nuevo_stock - stock_anterior:+d}")
            else:
                logger.error(f"❌ Producto '{nombre_producto}' no encontrado")
                
    except Exception as e:
        logger.error(f"❌ Error actualizando stock: {e}")

async def mostrar_inventario_actual():
    """Muestra el inventario actual organizado por categorías"""
    try:
        async with SessionLocal() as db:
            result = await db.execute(select(Producto).order_by(Producto.categoria, Producto.nombre))
            productos = result.scalars().all()
            
            if not productos:
                logger.info("📦 No hay productos en el inventario")
                return
            
            logger.info("\n" + "="*60)
            logger.info("📋 INVENTARIO ACTUAL DE SEXTINVALLE")
            logger.info("="*60)
            
            categoria_actual = None
            total_valor = 0
            total_items = 0
            
            for producto in productos:
                if producto.categoria != categoria_actual:
                    categoria_actual = producto.categoria
                    logger.info(f"\n🏷️  {categoria_actual}:")
                
                valor_producto = producto.precio * producto.stock
                total_valor += valor_producto
                total_items += producto.stock
                
                logger.info(f"   • {producto.nombre}")
                logger.info(f"     💰 ${producto.precio:,.0f} | 📦 Stock: {producto.stock} | 💵 Valor: ${valor_producto:,.0f}")
            
            logger.info(f"\n💰 VALOR TOTAL INVENTARIO: ${total_valor:,.0f}")
            logger.info(f"📦 TOTAL ITEMS EN STOCK: {total_items:,}")
            logger.info("="*60)
            
    except Exception as e:
        logger.error(f"❌ Error mostrando inventario: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestión de inventario Sextinvalle")
    parser.add_argument("--accion", choices=["crear", "mostrar", "actualizar_stock"], 
                       default="crear", help="Acción a realizar")
    parser.add_argument("--producto", help="Nombre del producto (para actualizar stock)")
    parser.add_argument("--stock", type=int, help="Nuevo stock (para actualizar stock)")
    
    args = parser.parse_args()
    
    if args.accion == "crear":
        asyncio.run(verificar_y_crear_productos())
    elif args.accion == "mostrar":
        asyncio.run(mostrar_inventario_actual())
    elif args.accion == "actualizar_stock":
        if not args.producto or args.stock is None:
            logger.error("❌ Para actualizar stock necesitas --producto y --stock")
        else:
            asyncio.run(actualizar_stock_producto(args.producto, args.stock)) 