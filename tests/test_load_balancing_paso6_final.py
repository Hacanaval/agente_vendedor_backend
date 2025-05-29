#!/usr/bin/env python3
"""
🧪 Test Suite Final - Paso 6: Load Balancing & Auto-scaling
Tests simplificados usando solo funciones existentes
"""
import pytest
import asyncio
import time
import logging
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===============================
# TESTS DE IMPORTACIÓN
# ===============================

def test_load_balancer_import():
    """Test de importación del Load Balancer"""
    from app.core.load_balancer import (
        LoadBalancerManager,
        ServiceInstance,
        LoadBalancingAlgorithm,
        InstanceStatus,
        CircuitBreakerState,
        load_balancer,
        get_load_balancer_stats
    )
    
    assert LoadBalancerManager is not None
    assert ServiceInstance is not None
    assert LoadBalancingAlgorithm is not None
    assert InstanceStatus is not None
    assert CircuitBreakerState is not None
    assert load_balancer is not None
    assert get_load_balancer_stats is not None
    
    print("✅ Load Balancer components imported successfully")

def test_auto_scaler_import():
    """Test de importación del Auto-scaler"""
    from app.core.auto_scaler import (
        AutoScalerService,
        MetricsCollector,
        ScalingPolicy,
        ScalingMetrics,
        ScalingDecision,
        ScalingAction,
        auto_scaler,
        get_auto_scaler_stats,
        enable_auto_scaling,
        disable_auto_scaling
    )
    
    assert AutoScalerService is not None
    assert MetricsCollector is not None
    assert ScalingPolicy is not None
    assert ScalingMetrics is not None
    assert ScalingDecision is not None
    assert ScalingAction is not None
    assert auto_scaler is not None
    assert get_auto_scaler_stats is not None
    assert enable_auto_scaling is not None
    assert disable_auto_scaling is not None
    
    print("✅ Auto-scaler components imported successfully")

def test_apis_import():
    """Test de importación de APIs"""
    from app.api.monitoring_load_balancing import router
    
    assert router is not None
    assert len(router.routes) > 0
    
    # Verificar que hay rutas
    routes = [route.path for route in router.routes]
    assert len(routes) >= 10, f"Expected at least 10 routes, found {len(routes)}"
    
    print(f"✅ APIs imported successfully with {len(router.routes)} routes")

# ===============================
# TESTS BÁSICOS DE FUNCIONALIDAD
# ===============================

def test_load_balancer_stats():
    """Test de estadísticas del Load Balancer"""
    from app.core.load_balancer import get_load_balancer_stats
    
    # Obtener estadísticas
    stats = get_load_balancer_stats()
    assert stats is not None
    assert isinstance(stats, dict)
    
    # Verificar estructura básica
    assert "load_balancer" in stats
    assert "performance" in stats
    assert "instances" in stats
    
    print("✅ Load Balancer stats working")

def test_auto_scaler_stats():
    """Test de estadísticas del Auto-scaler"""
    from app.core.auto_scaler import get_auto_scaler_stats
    
    # Obtener estadísticas
    stats = get_auto_scaler_stats()
    assert stats is not None
    assert isinstance(stats, dict)
    
    # Verificar estructura básica
    assert "auto_scaler" in stats
    assert "metrics" in stats
    assert "scaling" in stats
    
    print("✅ Auto-scaler stats working")

def test_auto_scaler_control():
    """Test de control del Auto-scaler"""
    from app.core.auto_scaler import (
        enable_auto_scaling,
        disable_auto_scaling,
        get_auto_scaler_stats
    )
    
    # Test enable/disable
    enable_auto_scaling()
    stats_enabled = get_auto_scaler_stats()
    
    disable_auto_scaling()
    stats_disabled = get_auto_scaler_stats()
    
    # Verificar que las funciones no fallan
    assert stats_enabled is not None
    assert stats_disabled is not None
    
    print("✅ Auto-scaler control working")

def test_load_balancer_manager():
    """Test del LoadBalancerManager"""
    from app.core.load_balancer import LoadBalancerManager, LoadBalancingAlgorithm
    
    # Crear instancia
    manager = LoadBalancerManager()
    assert manager is not None
    
    # Verificar algoritmo por defecto
    assert hasattr(manager, 'algorithm')
    assert hasattr(manager, 'instances')
    assert hasattr(manager, 'circuit_breakers')
    
    print("✅ LoadBalancerManager working")

def test_auto_scaler_service():
    """Test del AutoScalerService"""
    from app.core.auto_scaler import AutoScalerService
    
    # Crear instancia
    service = AutoScalerService()
    assert service is not None
    
    # Verificar atributos básicos
    assert hasattr(service, 'enabled')
    assert hasattr(service, 'policy')
    assert hasattr(service, 'metrics_collector')
    
    print("✅ AutoScalerService working")

def test_service_instance():
    """Test de ServiceInstance"""
    from app.core.load_balancer import ServiceInstance, InstanceStatus
    
    # Crear instancia
    instance = ServiceInstance(
        id="test-1",
        host="localhost",
        port=8000,
        weight=1.0,
        status=InstanceStatus.HEALTHY
    )
    
    assert instance.id == "test-1"
    assert instance.host == "localhost"
    assert instance.port == 8000
    assert instance.weight == 1.0
    assert instance.status == InstanceStatus.HEALTHY
    
    print("✅ ServiceInstance working")

def test_scaling_metrics():
    """Test de ScalingMetrics"""
    from app.core.auto_scaler import ScalingMetrics
    from datetime import datetime
    
    # Crear métricas
    metrics = ScalingMetrics(
        timestamp=datetime.now(),
        cpu_usage=50.0,
        memory_usage=60.0,
        request_rate=100.0,
        response_time=200.0,
        active_connections=50,
        error_rate=1.0
    )
    
    assert metrics.cpu_usage == 50.0
    assert metrics.memory_usage == 60.0
    assert metrics.request_rate == 100.0
    assert metrics.response_time == 200.0
    assert metrics.active_connections == 50
    assert metrics.error_rate == 1.0
    
    print("✅ ScalingMetrics working")

# ===============================
# TEST DE INTEGRACIÓN
# ===============================

def test_integration_basic():
    """Test de integración básica"""
    from app.core.load_balancer import get_load_balancer_stats, load_balancer
    from app.core.auto_scaler import get_auto_scaler_stats, auto_scaler
    
    # Obtener estadísticas de ambos componentes
    lb_stats = get_load_balancer_stats()
    as_stats = get_auto_scaler_stats()
    
    # Verificar que ambos funcionan
    assert lb_stats is not None
    assert as_stats is not None
    
    # Verificar que las instancias globales existen
    assert load_balancer is not None
    assert auto_scaler is not None
    
    print("✅ Integration working")

# ===============================
# TEST DE PERFORMANCE
# ===============================

def test_performance_stats():
    """Test de performance de estadísticas"""
    from app.core.load_balancer import get_load_balancer_stats
    from app.core.auto_scaler import get_auto_scaler_stats
    
    # Test múltiples llamadas
    start_time = time.time()
    for _ in range(10):
        lb_stats = get_load_balancer_stats()
        as_stats = get_auto_scaler_stats()
        assert lb_stats is not None
        assert as_stats is not None
    
    total_time = time.time() - start_time
    avg_time = total_time / 10
    
    # Verificar que es rápido (menos de 100ms por llamada)
    assert avg_time < 0.1, f"Stats too slow: {avg_time:.3f}s per call"
    
    print(f"✅ Performance test passed - Avg time: {avg_time:.3f}s per call")

# ===============================
# TEST DE CONFIGURACIÓN
# ===============================

def test_environment_variables():
    """Test de variables de entorno"""
    # Test con diferentes entornos
    environments = ['development', 'staging', 'production']
    
    for env in environments:
        os.environ['ENVIRONMENT'] = env
        
        # Verificar que las estadísticas funcionan en todos los entornos
        from app.core.load_balancer import get_load_balancer_stats
        from app.core.auto_scaler import get_auto_scaler_stats
        
        lb_stats = get_load_balancer_stats()
        as_stats = get_auto_scaler_stats()
        
        assert lb_stats is not None
        assert as_stats is not None
        
        print(f"✅ Environment {env} working")

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 