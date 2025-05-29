#!/usr/bin/env python3
"""
🧪 Test Suite Pytest - Paso 6: Load Balancing & Auto-scaling
Tests compatibles con pytest para verificar funcionalidad principal
"""
import pytest
import asyncio
import time
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===============================
# TESTS DE IMPORTACIÓN
# ===============================

def test_load_balancer_import():
    """Test de importación del Load Balancer"""
    try:
        from app.core.load_balancer import (
            LoadBalancerManager,
            ServiceInstance,
            LoadBalancingAlgorithm,
            InstanceStatus,
            CircuitBreakerState,
            load_balancer
        )
        
        assert LoadBalancerManager is not None
        assert ServiceInstance is not None
        assert LoadBalancingAlgorithm is not None
        assert InstanceStatus is not None
        assert CircuitBreakerState is not None
        assert load_balancer is not None
        
        print("✅ Load Balancer components imported successfully")
        return True
        
    except Exception as e:
        print(f"❌ Load Balancer import failed: {e}")
        pytest.fail(f"Load Balancer import failed: {e}")

def test_auto_scaler_import():
    """Test de importación del Auto-scaler"""
    try:
        from app.core.auto_scaler import (
            AutoScalerService,
            MetricsCollector,
            ScalingPolicy,
            ScalingMetrics,
            ScalingDecision,
            ScalingAction,
            auto_scaler
        )
        
        assert AutoScalerService is not None
        assert MetricsCollector is not None
        assert ScalingPolicy is not None
        assert ScalingMetrics is not None
        assert ScalingDecision is not None
        assert ScalingAction is not None
        assert auto_scaler is not None
        
        print("✅ Auto-scaler components imported successfully")
        return True
        
    except Exception as e:
        print(f"❌ Auto-scaler import failed: {e}")
        pytest.fail(f"Auto-scaler import failed: {e}")

def test_apis_import():
    """Test de importación de APIs"""
    try:
        from app.api.monitoring_load_balancing import router
        
        assert router is not None
        assert len(router.routes) > 0
        
        # Verificar algunas rutas clave
        routes = [route.path for route in router.routes]
        key_routes = [
            "/monitoring/load-balancing/health",
            "/monitoring/load-balancing/stats",
            "/monitoring/load-balancing/auto-scaling/health"
        ]
        
        found_routes = 0
        for route in key_routes:
            if any(route in r for r in routes):
                found_routes += 1
        
        assert found_routes >= 2, f"Expected at least 2 key routes, found {found_routes}"
        
        print(f"✅ APIs imported successfully with {len(router.routes)} routes")
        return True
        
    except Exception as e:
        print(f"❌ APIs import failed: {e}")
        pytest.fail(f"APIs import failed: {e}")

# ===============================
# TESTS BÁSICOS DE FUNCIONALIDAD
# ===============================

@pytest.mark.asyncio
async def test_load_balancer_basic():
    """Test básico del Load Balancer"""
    try:
        from app.core.load_balancer import (
            initialize_load_balancer,
            get_load_balancer_stats,
            register_service_instance,
            LoadBalancingAlgorithm,
            load_balancer
        )
        
        # Inicializar load balancer
        await initialize_load_balancer()
        
        # Obtener estadísticas
        stats = get_load_balancer_stats()
        assert "load_balancer" in stats
        assert "performance" in stats
        assert "instances" in stats
        
        # Verificar configuración inicial
        lb_stats = stats["load_balancer"]
        assert "algorithm" in lb_stats
        assert "total_instances" in lb_stats
        assert "healthy_instances" in lb_stats
        
        print("✅ Load Balancer basic functionality working")
        
    except Exception as e:
        print(f"❌ Load Balancer basic test failed: {e}")
        pytest.fail(f"Load Balancer basic test failed: {e}")

@pytest.mark.asyncio
async def test_auto_scaler_basic():
    """Test básico del Auto-scaler"""
    try:
        from app.core.auto_scaler import (
            initialize_auto_scaler,
            get_auto_scaler_stats,
            collect_metrics,
            auto_scaler
        )
        
        # Inicializar auto-scaler
        await initialize_auto_scaler()
        
        # Obtener estadísticas
        stats = get_auto_scaler_stats()
        assert "auto_scaler" in stats
        assert "metrics" in stats
        assert "scaling" in stats
        
        # Verificar configuración inicial
        as_stats = stats["auto_scaler"]
        assert "enabled" in as_stats
        assert "policy" in as_stats
        assert "current_instances" in as_stats
        
        print("✅ Auto-scaler basic functionality working")
        
    except Exception as e:
        print(f"❌ Auto-scaler basic test failed: {e}")
        pytest.fail(f"Auto-scaler basic test failed: {e}")

@pytest.mark.asyncio
async def test_metrics_collection():
    """Test de recolección de métricas"""
    try:
        from app.core.auto_scaler import (
            collect_metrics,
            ScalingMetrics
        )
        
        # Recolectar métricas
        metrics = await collect_metrics()
        
        assert isinstance(metrics, ScalingMetrics)
        assert hasattr(metrics, 'cpu_usage')
        assert hasattr(metrics, 'memory_usage')
        assert hasattr(metrics, 'request_rate')
        assert hasattr(metrics, 'response_time')
        
        # Verificar que las métricas están en rangos válidos
        assert 0 <= metrics.cpu_usage <= 100
        assert 0 <= metrics.memory_usage <= 100
        assert metrics.request_rate >= 0
        assert metrics.response_time >= 0
        
        print("✅ Metrics collection working")
        
    except Exception as e:
        print(f"❌ Metrics collection test failed: {e}")
        pytest.fail(f"Metrics collection test failed: {e}")

def test_configuration():
    """Test de configuración por entorno"""
    try:
        import os
        from app.core.load_balancer import get_environment_config
        from app.core.auto_scaler import get_scaling_config
        
        # Test configuración development
        os.environ['ENVIRONMENT'] = 'development'
        dev_config = get_environment_config()
        assert dev_config is not None
        assert "algorithm" in dev_config
        assert "health_check_interval" in dev_config
        
        dev_scaling = get_scaling_config()
        assert dev_scaling is not None
        assert "min_instances" in dev_scaling
        assert "max_instances" in dev_scaling
        
        # Test configuración production
        os.environ['ENVIRONMENT'] = 'production'
        prod_config = get_environment_config()
        assert prod_config is not None
        
        prod_scaling = get_scaling_config()
        assert prod_scaling is not None
        
        # Verificar que production tiene más instancias que development
        assert prod_scaling["max_instances"] > dev_scaling["max_instances"]
        
        print("✅ Configuration by environment working")
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        pytest.fail(f"Configuration test failed: {e}")

@pytest.mark.asyncio
async def test_integration_basic():
    """Test de integración básica entre componentes"""
    try:
        from app.core.load_balancer import (
            initialize_load_balancer,
            get_load_balancer_stats
        )
        from app.core.auto_scaler import (
            initialize_auto_scaler,
            get_auto_scaler_stats
        )
        
        # Inicializar ambos componentes
        await initialize_load_balancer()
        await initialize_auto_scaler()
        
        # Obtener estadísticas de ambos
        lb_stats = get_load_balancer_stats()
        as_stats = get_auto_scaler_stats()
        
        # Verificar que ambos están funcionando
        assert lb_stats is not None
        assert as_stats is not None
        
        # Verificar que tienen información coherente
        lb_instances = lb_stats["load_balancer"]["total_instances"]
        as_instances = as_stats["auto_scaler"]["current_instances"]
        
        # Deberían tener el mismo número de instancias o estar cerca
        assert abs(lb_instances - as_instances) <= 1
        
        print("✅ Integration between Load Balancer and Auto-scaler working")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        pytest.fail(f"Integration test failed: {e}")

# ===============================
# TEST DE PERFORMANCE BÁSICO
# ===============================

@pytest.mark.asyncio
async def test_performance_basic():
    """Test básico de performance"""
    try:
        from app.core.load_balancer import (
            initialize_load_balancer,
            get_load_balancer_stats
        )
        
        # Inicializar
        start_time = time.time()
        await initialize_load_balancer()
        init_time = time.time() - start_time
        
        # Verificar que la inicialización es rápida
        assert init_time < 5.0, f"Initialization took too long: {init_time}s"
        
        # Test de obtención de estadísticas
        start_time = time.time()
        for _ in range(10):
            stats = get_load_balancer_stats()
            assert stats is not None
        stats_time = time.time() - start_time
        
        # Verificar que las estadísticas se obtienen rápidamente
        avg_stats_time = stats_time / 10
        assert avg_stats_time < 0.1, f"Stats retrieval too slow: {avg_stats_time}s"
        
        print(f"✅ Performance test passed - Init: {init_time:.2f}s, Stats: {avg_stats_time:.4f}s")
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        pytest.fail(f"Performance test failed: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 