#!/usr/bin/env python3
"""
🧪 Test Suite Completo - Paso 7: Monitoring & Observability Enterprise
Tests para verificar funcionalidad completa del sistema de observabilidad
"""
import pytest
import asyncio
import time
import logging
from datetime import datetime, timedelta

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===============================
# TESTS DE IMPORTACIÓN
# ===============================

def test_metrics_collector_imports():
    """Test de importación del Metrics Collector Enterprise"""
    try:
        from app.core.metrics_collector_enterprise import (
            MetricsCollectorEnterprise,
            MetricType,
            MetricCategory,
            SystemMetrics,
            ApplicationMetrics,
            BusinessMetrics,
            RAGPerformanceMetrics,
            PrometheusClient,
            CustomMetricsRegistry,
            BusinessMetricsCollector,
            metrics_collector,
            initialize_metrics_collector,
            register_custom_metric,
            record_custom_metric,
            get_latest_metrics,
            get_metrics_stats,
            get_prometheus_metrics
        )
        
        assert MetricsCollectorEnterprise is not None
        assert MetricType is not None
        assert metrics_collector is not None
        
        logger.info("✅ Metrics Collector Enterprise imports OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en imports de Metrics Collector: {e}")
        return False

def test_dashboard_service_imports():
    """Test de importación del Dashboard Service"""
    try:
        from app.core.dashboard_service import (
            DashboardService,
            ChartType,
            DashboardType,
            ChartConfig,
            DashboardConfig,
            WebSocketManager,
            ChartGenerator,
            DataAggregator,
            dashboard_service,
            initialize_dashboard_service,
            create_custom_dashboard,
            get_dashboard_config,
            list_available_dashboards,
            add_dashboard_connection,
            remove_dashboard_connection,
            get_dashboard_stats
        )
        
        assert DashboardService is not None
        assert ChartType is not None
        assert dashboard_service is not None
        
        logger.info("✅ Dashboard Service imports OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en imports de Dashboard Service: {e}")
        return False

def test_monitoring_apis_imports():
    """Test de importación de APIs de Monitoring"""
    try:
        from app.api.monitoring_observability import (
            router,
            MetricQuery,
            CustomMetricRequest,
            MetricValueRequest,
            DashboardRequest,
            AlertRuleRequest,
            HealthCheckResponse
        )
        
        assert router is not None
        assert MetricQuery is not None
        assert DashboardRequest is not None
        
        logger.info("✅ Monitoring APIs imports OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en imports de Monitoring APIs: {e}")
        return False

# ===============================
# TESTS DE FUNCIONALIDAD BÁSICA
# ===============================

def test_metrics_collector_creation():
    """Test de creación del Metrics Collector"""
    try:
        from app.core.metrics_collector_enterprise import MetricsCollectorEnterprise
        
        collector = MetricsCollectorEnterprise()
        
        assert collector is not None
        assert collector.enabled == True
        assert collector.collection_interval > 0
        assert hasattr(collector, 'prometheus_client')
        assert hasattr(collector, 'custom_metrics')
        assert hasattr(collector, 'business_metrics')
        
        logger.info("✅ Metrics Collector creation OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creando Metrics Collector: {e}")
        return False

def test_dashboard_service_creation():
    """Test de creación del Dashboard Service"""
    try:
        from app.core.dashboard_service import DashboardService
        
        service = DashboardService()
        
        assert service is not None
        assert service.enabled == True
        assert service.update_interval > 0
        assert hasattr(service, 'websocket_manager')
        assert hasattr(service, 'chart_generator')
        assert hasattr(service, 'dashboards')
        
        # Verificar dashboards predefinidos
        assert len(service.dashboards) >= 3  # executive, operations, development
        assert 'executive' in service.dashboards
        assert 'operations' in service.dashboards
        assert 'development' in service.dashboards
        
        logger.info("✅ Dashboard Service creation OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creando Dashboard Service: {e}")
        return False

def test_metric_types_and_categories():
    """Test de tipos y categorías de métricas"""
    try:
        from app.core.metrics_collector_enterprise import MetricType, MetricCategory
        
        # Verificar tipos de métricas
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.SUMMARY.value == "summary"
        
        # Verificar categorías
        assert MetricCategory.SYSTEM.value == "system"
        assert MetricCategory.APPLICATION.value == "application"
        assert MetricCategory.BUSINESS.value == "business"
        assert MetricCategory.CUSTOM.value == "custom"
        
        logger.info("✅ Metric types and categories OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en tipos de métricas: {e}")
        return False

def test_chart_types():
    """Test de tipos de gráficos"""
    try:
        from app.core.dashboard_service import ChartType, DashboardType
        
        # Verificar tipos de gráficos
        assert ChartType.LINE.value == "line"
        assert ChartType.BAR.value == "bar"
        assert ChartType.GAUGE.value == "gauge"
        assert ChartType.PIE.value == "pie"
        assert ChartType.BIG_NUMBER.value == "big_number"
        assert ChartType.TABLE.value == "table"
        assert ChartType.STATUS_GRID.value == "status_grid"
        
        # Verificar tipos de dashboard
        assert DashboardType.EXECUTIVE.value == "executive"
        assert DashboardType.OPERATIONS.value == "operations"
        assert DashboardType.DEVELOPMENT.value == "development"
        assert DashboardType.CUSTOM.value == "custom"
        
        logger.info("✅ Chart types OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en tipos de gráficos: {e}")
        return False

# ===============================
# TESTS DE MÉTRICAS
# ===============================

@pytest.mark.asyncio
async def test_system_metrics_collection():
    """Test de recolección de métricas del sistema"""
    try:
        from app.core.metrics_collector_enterprise import metrics_collector
        
        # Recolectar métricas del sistema
        system_metrics = await metrics_collector.collect_system_metrics()
        
        assert system_metrics is not None
        assert hasattr(system_metrics, 'cpu_usage_total')
        assert hasattr(system_metrics, 'memory_usage_percent')
        assert hasattr(system_metrics, 'disk_usage_percent')
        assert hasattr(system_metrics, 'timestamp')
        
        # Verificar que los valores están en rangos razonables
        assert 0 <= system_metrics.cpu_usage_total <= 100
        assert 0 <= system_metrics.memory_usage_percent <= 100
        assert 0 <= system_metrics.disk_usage_percent <= 100
        
        logger.info("✅ System metrics collection OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en recolección de métricas del sistema: {e}")
        return False

@pytest.mark.asyncio
async def test_application_metrics_collection():
    """Test de recolección de métricas de aplicación"""
    try:
        from app.core.metrics_collector_enterprise import metrics_collector
        
        # Recolectar métricas de aplicación
        app_metrics = await metrics_collector.collect_application_metrics()
        
        assert app_metrics is not None
        assert hasattr(app_metrics, 'request_count')
        assert hasattr(app_metrics, 'request_duration_avg')
        assert hasattr(app_metrics, 'error_rate')
        assert hasattr(app_metrics, 'cache_hit_ratio')
        assert hasattr(app_metrics, 'timestamp')
        
        # Verificar que los valores están en rangos razonables
        assert app_metrics.request_count >= 0
        assert app_metrics.request_duration_avg >= 0
        assert 0 <= app_metrics.error_rate <= 100
        assert 0 <= app_metrics.cache_hit_ratio <= 100
        
        logger.info("✅ Application metrics collection OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en recolección de métricas de aplicación: {e}")
        return False

def test_custom_metrics_registration():
    """Test de registro de métricas personalizadas"""
    try:
        from app.core.metrics_collector_enterprise import register_custom_metric, MetricType
        
        # Registrar métrica personalizada
        register_custom_metric(
            name="test_custom_metric",
            metric_type=MetricType.GAUGE,
            description="Métrica de prueba",
            unit="count",
            labels=["environment", "service"]
        )
        
        logger.info("✅ Custom metrics registration OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error registrando métrica personalizada: {e}")
        return False

def test_custom_metrics_recording():
    """Test de registro de valores de métricas personalizadas"""
    try:
        from app.core.metrics_collector_enterprise import record_custom_metric
        
        # Registrar valor de métrica personalizada
        record_custom_metric(
            name="test_custom_metric",
            value=42.5,
            labels={"environment": "test", "service": "monitoring"}
        )
        
        logger.info("✅ Custom metrics recording OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error registrando valor de métrica: {e}")
        return False

def test_prometheus_client():
    """Test del cliente Prometheus"""
    try:
        from app.core.metrics_collector_enterprise import PrometheusClient, MetricType
        
        client = PrometheusClient()
        
        # Registrar métrica
        client.register_metric(
            name="test_prometheus_metric",
            metric_type=MetricType.COUNTER,
            description="Test metric for Prometheus",
            labels=["status"]
        )
        
        # Registrar valor
        client.record_metric(
            name="test_prometheus_metric",
            value=10.0,
            labels={"status": "success"}
        )
        
        # Exportar métricas
        metrics_text = client.export_metrics()
        
        if client.enabled:
            assert "test_prometheus_metric" in metrics_text
        
        logger.info("✅ Prometheus client OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en cliente Prometheus: {e}")
        return False

# ===============================
# TESTS DE DASHBOARDS
# ===============================

def test_chart_config_creation():
    """Test de creación de configuración de gráficos"""
    try:
        from app.core.dashboard_service import ChartConfig, ChartType
        
        chart_config = ChartConfig(
            chart_id="test_chart",
            name="Test Chart",
            chart_type=ChartType.LINE,
            metrics=["cpu_usage", "memory_usage"],
            time_range="1h",
            refresh_interval=30,
            width=6,
            height=4,
            options={"color": "blue"}
        )
        
        assert chart_config.chart_id == "test_chart"
        assert chart_config.name == "Test Chart"
        assert chart_config.chart_type == ChartType.LINE
        assert len(chart_config.metrics) == 2
        
        # Test conversión a diccionario
        chart_dict = chart_config.to_dict()
        assert isinstance(chart_dict, dict)
        assert chart_dict["chart_id"] == "test_chart"
        
        logger.info("✅ Chart config creation OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creando configuración de gráfico: {e}")
        return False

def test_dashboard_config_creation():
    """Test de creación de configuración de dashboard"""
    try:
        from app.core.dashboard_service import DashboardConfig, DashboardType, ChartConfig, ChartType
        
        # Crear gráfico de prueba
        chart = ChartConfig(
            chart_id="test_chart",
            name="Test Chart",
            chart_type=ChartType.GAUGE,
            metrics=["cpu_usage"]
        )
        
        # Crear dashboard
        dashboard_config = DashboardConfig(
            dashboard_id="test_dashboard",
            name="Test Dashboard",
            dashboard_type=DashboardType.CUSTOM,
            charts=[chart],
            access_level="user",
            theme="dark"
        )
        
        assert dashboard_config.dashboard_id == "test_dashboard"
        assert dashboard_config.name == "Test Dashboard"
        assert dashboard_config.dashboard_type == DashboardType.CUSTOM
        assert len(dashboard_config.charts) == 1
        assert dashboard_config.theme == "dark"
        
        # Test conversión a diccionario
        dashboard_dict = dashboard_config.to_dict()
        assert isinstance(dashboard_dict, dict)
        assert dashboard_dict["dashboard_id"] == "test_dashboard"
        
        logger.info("✅ Dashboard config creation OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creando configuración de dashboard: {e}")
        return False

@pytest.mark.asyncio
async def test_chart_generation():
    """Test de generación de gráficos"""
    try:
        from app.core.dashboard_service import ChartGenerator, ChartConfig, ChartType
        
        generator = ChartGenerator()
        
        # Crear configuración de gráfico
        chart_config = ChartConfig(
            chart_id="test_line_chart",
            name="Test Line Chart",
            chart_type=ChartType.LINE,
            metrics=["cpu_usage"],
            time_range="1h"
        )
        
        # Generar gráfico
        chart_data = await generator.generate_chart(chart_config)
        
        assert chart_data is not None
        assert isinstance(chart_data, dict)
        
        if "error" not in chart_data:
            assert chart_data.get("type") == "line"
            assert "series" in chart_data
            assert "options" in chart_data
        
        logger.info("✅ Chart generation OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error generando gráfico: {e}")
        return False

def test_websocket_manager():
    """Test del gestor de WebSocket"""
    try:
        from app.core.dashboard_service import WebSocketManager
        
        manager = WebSocketManager()
        
        # Añadir conexión
        success = manager.add_connection(
            connection_id="test_conn_1",
            dashboard_id="test_dashboard",
            user_id="test_user"
        )
        
        assert success == True
        assert len(manager.connections) == 1
        assert "test_conn_1" in manager.connections
        
        # Obtener conexiones del dashboard
        connections = manager.get_dashboard_connections("test_dashboard")
        assert len(connections) == 1
        assert "test_conn_1" in connections
        
        # Remover conexión
        success = manager.remove_connection("test_conn_1")
        assert success == True
        assert len(manager.connections) == 0
        
        logger.info("✅ WebSocket manager OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en WebSocket manager: {e}")
        return False

# ===============================
# TESTS DE FUNCIONES GLOBALES
# ===============================

def test_metrics_stats_function():
    """Test de función de estadísticas de métricas"""
    try:
        from app.core.metrics_collector_enterprise import get_metrics_stats
        
        stats = get_metrics_stats()
        
        assert stats is not None
        assert isinstance(stats, dict)
        assert "collector" in stats
        assert "performance" in stats
        assert "metrics_count" in stats
        assert "configuration" in stats
        
        # Verificar estructura de collector
        collector_stats = stats["collector"]
        assert "enabled" in collector_stats
        assert "collection_interval" in collector_stats
        assert "uptime_seconds" in collector_stats
        
        logger.info("✅ Metrics stats function OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en función de stats de métricas: {e}")
        return False

def test_dashboard_stats_function():
    """Test de función de estadísticas de dashboards"""
    try:
        from app.core.dashboard_service import get_dashboard_stats
        
        stats = get_dashboard_stats()
        
        assert stats is not None
        assert isinstance(stats, dict)
        assert "dashboard_service" in stats
        assert "dashboards" in stats
        assert "performance" in stats
        assert "websocket" in stats
        
        # Verificar estructura de dashboard_service
        service_stats = stats["dashboard_service"]
        assert "enabled" in service_stats
        assert "uptime_seconds" in service_stats
        assert "update_interval" in service_stats
        
        logger.info("✅ Dashboard stats function OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en función de stats de dashboards: {e}")
        return False

def test_list_dashboards_function():
    """Test de función para listar dashboards"""
    try:
        from app.core.dashboard_service import list_available_dashboards
        
        # Listar todos los dashboards
        all_dashboards = list_available_dashboards()
        
        assert all_dashboards is not None
        assert isinstance(all_dashboards, list)
        assert len(all_dashboards) >= 3  # executive, operations, development
        
        # Verificar estructura de dashboard
        if all_dashboards:
            dashboard = all_dashboards[0]
            assert "dashboard_id" in dashboard
            assert "name" in dashboard
            assert "dashboard_type" in dashboard
            assert "charts" in dashboard
            assert "active_connections" in dashboard
        
        # Listar dashboards por nivel de acceso
        executive_dashboards = list_available_dashboards("executive")
        assert isinstance(executive_dashboards, list)
        
        logger.info("✅ List dashboards function OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en función de listar dashboards: {e}")
        return False

# ===============================
# TESTS DE INTEGRACIÓN
# ===============================

@pytest.mark.asyncio
async def test_metrics_collection_integration():
    """Test de integración de recolección de métricas"""
    try:
        from app.core.metrics_collector_enterprise import metrics_collector
        
        # Simular una recolección completa
        await metrics_collector._collect_all_metrics()
        
        # Verificar que se recolectaron métricas
        latest_metrics = metrics_collector.get_latest_metrics()
        
        assert latest_metrics is not None
        assert isinstance(latest_metrics, dict)
        
        # Verificar categorías de métricas
        expected_categories = ["system", "application"]
        for category in expected_categories:
            if category in latest_metrics:
                assert "timestamp" in latest_metrics[category]
                assert "data" in latest_metrics[category]
        
        logger.info("✅ Metrics collection integration OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en integración de recolección de métricas: {e}")
        return False

@pytest.mark.asyncio
async def test_dashboard_update_integration():
    """Test de integración de actualización de dashboards"""
    try:
        from app.core.dashboard_service import dashboard_service
        
        # Obtener un dashboard existente
        dashboard_id = "development"  # Dashboard predefinido
        
        # Simular actualización de dashboard
        await dashboard_service.update_dashboard_data(dashboard_id)
        
        # Verificar que las estadísticas se actualizaron
        stats = dashboard_service.get_stats()
        
        assert stats is not None
        assert stats["performance"]["total_updates"] >= 0
        
        logger.info("✅ Dashboard update integration OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en integración de actualización de dashboards: {e}")
        return False

def test_prometheus_export_integration():
    """Test de integración de exportación Prometheus"""
    try:
        from app.core.metrics_collector_enterprise import get_prometheus_metrics
        
        # Obtener métricas en formato Prometheus
        prometheus_text = get_prometheus_metrics()
        
        assert prometheus_text is not None
        assert isinstance(prometheus_text, str)
        
        # Si Prometheus está habilitado, debería tener contenido
        # Si no está habilitado, debería estar vacío
        logger.info("✅ Prometheus export integration OK")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en integración de exportación Prometheus: {e}")
        return False

# ===============================
# TESTS DE CONFIGURACIÓN
# ===============================

def test_environment_configuration():
    """Test de configuración por entorno"""
    try:
        from app.core.metrics_collector_enterprise import MC_CONFIG, ENVIRONMENT
        from app.core.dashboard_service import DASHBOARD_CONFIG
        
        # Verificar configuración de métricas
        assert MC_CONFIG is not None
        assert isinstance(MC_CONFIG, dict)
        assert "collection" in MC_CONFIG
        assert "custom_metrics" in MC_CONFIG
        
        # Verificar configuración de dashboards
        assert DASHBOARD_CONFIG is not None
        assert isinstance(DASHBOARD_CONFIG, dict)
        assert "real_time" in DASHBOARD_CONFIG
        assert "dashboards" in DASHBOARD_CONFIG
        
        # Verificar entorno
        assert ENVIRONMENT is not None
        assert isinstance(ENVIRONMENT, str)
        
        logger.info(f"✅ Environment configuration OK (env: {ENVIRONMENT})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en configuración de entorno: {e}")
        return False

# ===============================
# FUNCIÓN PRINCIPAL DE TESTS
# ===============================

def run_all_tests():
    """Ejecuta todos los tests del Paso 7"""
    logger.info("🧪 Iniciando Test Suite Completo - Paso 7: Monitoring & Observability")
    
    tests = [
        # Tests de importación
        ("Metrics Collector Imports", test_metrics_collector_imports),
        ("Dashboard Service Imports", test_dashboard_service_imports),
        ("Monitoring APIs Imports", test_monitoring_apis_imports),
        
        # Tests de funcionalidad básica
        ("Metrics Collector Creation", test_metrics_collector_creation),
        ("Dashboard Service Creation", test_dashboard_service_creation),
        ("Metric Types and Categories", test_metric_types_and_categories),
        ("Chart Types", test_chart_types),
        
        # Tests de métricas
        ("Custom Metrics Registration", test_custom_metrics_registration),
        ("Custom Metrics Recording", test_custom_metrics_recording),
        ("Prometheus Client", test_prometheus_client),
        
        # Tests de dashboards
        ("Chart Config Creation", test_chart_config_creation),
        ("Dashboard Config Creation", test_dashboard_config_creation),
        ("WebSocket Manager", test_websocket_manager),
        
        # Tests de funciones globales
        ("Metrics Stats Function", test_metrics_stats_function),
        ("Dashboard Stats Function", test_dashboard_stats_function),
        ("List Dashboards Function", test_list_dashboards_function),
        
        # Tests de integración
        ("Prometheus Export Integration", test_prometheus_export_integration),
        
        # Tests de configuración
        ("Environment Configuration", test_environment_configuration),
    ]
    
    # Tests async separados
    async_tests = [
        ("System Metrics Collection", test_system_metrics_collection),
        ("Application Metrics Collection", test_application_metrics_collection),
        ("Chart Generation", test_chart_generation),
        ("Metrics Collection Integration", test_metrics_collection_integration),
        ("Dashboard Update Integration", test_dashboard_update_integration),
    ]
    
    passed = 0
    failed = 0
    
    # Ejecutar tests síncronos
    for test_name, test_func in tests:
        try:
            logger.info(f"🔍 Ejecutando: {test_name}")
            result = test_func()
            if result:
                passed += 1
                logger.info(f"✅ {test_name}: PASSED")
            else:
                failed += 1
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            failed += 1
            logger.error(f"❌ {test_name}: ERROR - {e}")
    
    # Ejecutar tests asíncronos
    async def run_async_tests():
        nonlocal passed, failed
        
        for test_name, test_func in async_tests:
            try:
                logger.info(f"🔍 Ejecutando: {test_name}")
                result = await test_func()
                if result:
                    passed += 1
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    failed += 1
                    logger.error(f"❌ {test_name}: FAILED")
            except Exception as e:
                failed += 1
                logger.error(f"❌ {test_name}: ERROR - {e}")
    
    # Ejecutar tests async
    try:
        asyncio.run(run_async_tests())
    except Exception as e:
        logger.error(f"❌ Error ejecutando tests async: {e}")
        failed += len(async_tests)
    
    # Resumen final
    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0
    
    logger.info("=" * 60)
    logger.info("📊 RESUMEN DE TESTS - PASO 7")
    logger.info("=" * 60)
    logger.info(f"✅ Tests pasados: {passed}")
    logger.info(f"❌ Tests fallidos: {failed}")
    logger.info(f"📊 Total tests: {total}")
    logger.info(f"🎯 Tasa de éxito: {success_rate:.1f}%")
    logger.info("=" * 60)
    
    if failed == 0:
        logger.info("🎉 ¡TODOS LOS TESTS PASARON! Paso 7 implementado correctamente.")
    else:
        logger.warning(f"⚠️ {failed} tests fallaron. Revisar implementación.")
    
    return passed, failed, success_rate

if __name__ == "__main__":
    run_all_tests() 