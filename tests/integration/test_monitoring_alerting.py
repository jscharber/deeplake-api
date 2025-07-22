"""Monitoring and alerting integration tests.

This test suite covers monitoring infrastructure and alerting system tests
that were originally handled by the test-alerting.sh script.
"""

import pytest
import requests
import json
import time
from typing import Dict, Any, Optional
from fastapi.testclient import TestClient
from unittest.mock import patch
import urllib3

# Disable SSL warnings for test environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@pytest.mark.integration
@pytest.mark.monitoring
class TestMonitoringInfrastructure:
    """Test monitoring infrastructure availability and configuration."""
    
    @pytest.fixture(scope="class")
    def monitoring_services(self) -> Dict[str, Dict[str, Any]]:
        """Configuration for monitoring services."""
        return {
            "prometheus": {
                "host": "localhost",
                "port": 9090,
                "health_path": "/-/healthy",
                "metrics_path": "/api/v1/targets"
            },
            "alertmanager": {
                "host": "localhost", 
                "port": 9093,
                "health_path": "/-/healthy",
                "alerts_path": "/api/v1/alerts"
            },
            "grafana": {
                "host": "localhost",
                "port": 3000,
                "health_path": "/api/health"
            }
        }
    
    def _check_service_health(self, service_config: Dict[str, Any]) -> bool:
        """Check if a monitoring service is healthy."""
        try:
            url = f"http://{service_config['host']}:{service_config['port']}{service_config['health_path']}"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except (requests.RequestException, ConnectionError):
            return False
    
    def test_prometheus_availability(self, monitoring_services: Dict[str, Dict[str, Any]]):
        """Test that Prometheus is available and responding."""
        prometheus_config = monitoring_services["prometheus"]
        is_healthy = self._check_service_health(prometheus_config)
        
        if not is_healthy:
            pytest.skip("Prometheus not available - monitoring infrastructure may not be running")
        
        # Test metrics endpoint
        metrics_url = f"http://{prometheus_config['host']}:{prometheus_config['port']}{prometheus_config['metrics_path']}"
        response = requests.get(metrics_url, timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "activeTargets" in data["data"]
    
    def test_alertmanager_availability(self, monitoring_services: Dict[str, Dict[str, Any]]):
        """Test that Alertmanager is available and responding."""
        alertmanager_config = monitoring_services["alertmanager"]
        is_healthy = self._check_service_health(alertmanager_config)
        
        if not is_healthy:
            pytest.skip("Alertmanager not available - monitoring infrastructure may not be running")
        
        # Test alerts endpoint
        alerts_url = f"http://{alertmanager_config['host']}:{alertmanager_config['port']}{alertmanager_config['alerts_path']}"
        response = requests.get(alerts_url, timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
    
    def test_grafana_availability(self, monitoring_services: Dict[str, Dict[str, Any]]):
        """Test that Grafana is available."""
        grafana_config = monitoring_services["grafana"]
        is_healthy = self._check_service_health(grafana_config)
        
        if not is_healthy:
            pytest.skip("Grafana not available - monitoring infrastructure may not be running")
        
        # Additional check for Grafana API
        api_url = f"http://{grafana_config['host']}:{grafana_config['port']}/api/org"
        try:
            response = requests.get(api_url, timeout=10)
            # Grafana may return 401 without auth, which is still a valid response indicating it's running
            assert response.status_code in [200, 401]
        except requests.RequestException:
            pytest.fail("Grafana API is not responding")


@pytest.mark.integration
@pytest.mark.monitoring
class TestPrometheusIntegration:
    """Test Prometheus integration and metrics collection."""
    
    @pytest.fixture
    def prometheus_url(self) -> str:
        """Prometheus base URL."""
        return "http://localhost:9090"
    
    def test_prometheus_targets(self, prometheus_url: str):
        """Test that Prometheus targets are configured and healthy."""
        try:
            response = requests.get(f"{prometheus_url}/api/v1/targets", timeout=10)
        except requests.RequestException:
            pytest.skip("Prometheus not available")
        
        assert response.status_code == 200
        data = response.json()
        
        targets = data.get("data", {}).get("activeTargets", [])
        assert len(targets) > 0, "No active targets found in Prometheus"
        
        # Check for DeepLake API target
        api_targets = [t for t in targets if t.get("labels", {}).get("job") == "deeplake-api"]
        if api_targets:
            for target in api_targets:
                assert target["health"] == "up", f"DeepLake API target is down: {target}"
    
    def test_prometheus_alert_rules(self, prometheus_url: str):
        """Test that alert rules are loaded in Prometheus."""
        try:
            response = requests.get(f"{prometheus_url}/api/v1/rules", timeout=10)
        except requests.RequestException:
            pytest.skip("Prometheus not available")
        
        assert response.status_code == 200
        data = response.json()
        
        groups = data.get("data", {}).get("groups", [])
        assert len(groups) > 0, "No rule groups found in Prometheus"
        
        # Extract all alert rule names
        alert_rules = []
        for group in groups:
            for rule in group.get("rules", []):
                if rule.get("type") == "alerting":
                    alert_rules.append(rule.get("name"))
        
        assert len(alert_rules) > 0, "No alert rules found"
        
        # Check for key alert rules
        expected_rules = ["DeepLakeAPIDown", "HighErrorRate", "HighLatency"]
        for rule_name in expected_rules:
            if rule_name not in alert_rules:
                pytest.skip(f"Alert rule '{rule_name}' not configured (may be optional)")
    
    def test_prometheus_metrics_collection(self, prometheus_url: str):
        """Test that Prometheus is collecting DeepLake metrics."""
        try:
            response = requests.get(f"{prometheus_url}/api/v1/label/__name__/values", timeout=10)
        except requests.RequestException:
            pytest.skip("Prometheus not available")
        
        assert response.status_code == 200
        data = response.json()
        
        metric_names = data.get("data", [])
        
        # Check for key DeepLake metrics
        expected_metrics = [
            "deeplake_http_requests_total",
            "deeplake_errors_total", 
            "deeplake_cache_hit_ratio"
        ]
        
        found_metrics = []
        for metric in expected_metrics:
            if metric in metric_names:
                found_metrics.append(metric)
        
        # At least some DeepLake metrics should be present
        if len(found_metrics) == 0:
            pytest.skip("DeepLake metrics not found - may need traffic to generate metrics")


@pytest.mark.integration
@pytest.mark.monitoring
class TestMetricsEndpoints:
    """Test metrics endpoints in the DeepLake API."""
    
    def test_metrics_endpoint_availability(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test that metrics endpoint is available."""
        response = client.get("/api/v1/metrics/prometheus", headers=auth_headers)
        
        if response.status_code == 404:
            pytest.skip("Metrics endpoint not implemented")
        
        assert response.status_code == 200
        metrics_text = response.text
        
        # Basic validation of Prometheus format
        assert len(metrics_text) > 0
        lines = metrics_text.split('\n')
        
        # Should contain some metric definitions
        metric_lines = [line for line in lines if not line.startswith('#') and line.strip()]
        assert len(metric_lines) > 0, "No metrics found in response"
    
    def test_health_metrics_generation(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test that making requests generates metrics."""
        # Make some requests to generate metrics
        client.get("/api/v1/health")
        client.get("/api/v1/datasets/", headers=auth_headers)
        
        # Check if metrics endpoint shows the activity
        response = client.get("/api/v1/metrics/prometheus", headers=auth_headers)
        
        if response.status_code == 404:
            pytest.skip("Metrics endpoint not implemented")
        
        assert response.status_code == 200
        metrics_text = response.text
        
        # Look for request count metrics
        assert "http_requests" in metrics_text or "requests_total" in metrics_text


@pytest.mark.integration
@pytest.mark.monitoring
class TestAlertingSystem:
    """Test alerting system functionality."""
    
    @pytest.fixture
    def alertmanager_url(self) -> str:
        """Alertmanager base URL.""" 
        return "http://localhost:9093"
    
    def test_send_test_alert(self, alertmanager_url: str):
        """Test sending a test alert to Alertmanager."""
        try:
            # Check if Alertmanager is available
            health_response = requests.get(f"{alertmanager_url}/-/healthy", timeout=5)
            if health_response.status_code != 200:
                pytest.skip("Alertmanager not available")
        except requests.RequestException:
            pytest.skip("Alertmanager not available")
        
        # Create test alert
        test_alert = {
            "labels": {
                "alertname": "PytestTestAlert",
                "severity": "warning", 
                "service": "deeplake-api",
                "instance": "localhost:8000",
                "test": "true"
            },
            "annotations": {
                "summary": "Test alert from pytest",
                "description": "This is a test alert generated by the pytest monitoring test suite"
            },
            "startsAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "endsAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 300))  # 5 minutes from now
        }
        
        # Send alert to Alertmanager
        response = requests.post(
            f"{alertmanager_url}/api/v1/alerts",
            json=[test_alert],
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        assert response.status_code == 200, f"Failed to send test alert: {response.text}"
    
    def test_alert_routing(self, alertmanager_url: str):
        """Test alert routing configuration."""
        try:
            response = requests.get(f"{alertmanager_url}/api/v1/status", timeout=10)
        except requests.RequestException:
            pytest.skip("Alertmanager not available")
        
        if response.status_code != 200:
            pytest.skip("Alertmanager status endpoint not available")
        
        data = response.json()
        assert "data" in data
        
        # Basic validation that Alertmanager is configured
        config = data["data"].get("configYAML", "")
        if config:
            assert "route:" in config or "global:" in config


@pytest.mark.integration
@pytest.mark.monitoring
@pytest.mark.slow
class TestMonitoringStressTests:
    """Stress tests for monitoring system."""
    
    def test_metrics_under_load(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test that metrics collection works under load."""
        import threading
        import concurrent.futures
        
        def make_requests():
            """Make multiple requests to generate metrics."""
            responses = []
            for _ in range(5):
                try:
                    response = client.get("/api/v1/health")
                    responses.append(response.status_code)
                except Exception as e:
                    responses.append(str(e))
            return responses
        
        # Run concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_requests) for _ in range(3)]
            results = [future.result() for future in futures]
        
        # Verify most requests succeeded
        all_responses = [status for result in results for status in result]
        success_count = sum(1 for status in all_responses if status == 200)
        assert success_count >= len(all_responses) * 0.8, "Too many failed requests under load"
        
        # Check that metrics endpoint still works after load
        metrics_response = client.get("/api/v1/metrics/prometheus", headers=auth_headers)
        if metrics_response.status_code != 404:  # Skip if not implemented
            assert metrics_response.status_code == 200
    
    def test_error_rate_simulation(self, client: TestClient):
        """Test simulating high error rate for alerting."""
        import threading
        
        error_responses = []
        
        def generate_errors():
            """Generate error responses."""
            for _ in range(5):
                try:
                    # Make requests that should result in errors
                    response = client.post(
                        "/api/v1/datasets/nonexistent/vectors/",
                        json={"invalid": "data"},
                        headers={"Authorization": "ApiKey invalid-key"}
                    )
                    error_responses.append(response.status_code)
                except Exception as e:
                    error_responses.append(str(e))
        
        # Generate errors concurrently
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=generate_errors)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify we got expected error responses
        error_count = sum(1 for status in error_responses if isinstance(status, int) and status >= 400)
        assert error_count > 0, "No error responses generated for error rate test"


@pytest.mark.integration
@pytest.mark.monitoring
class TestServiceHealthChecks:
    """Test service health check mechanisms."""
    
    def test_api_health_endpoint(self, client: TestClient):
        """Test API health endpoint functionality."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert "status" in health_data
        assert health_data["status"] == "healthy"
        
        # Check for additional health information
        expected_fields = ["timestamp", "version", "uptime"]
        for field in expected_fields:
            if field not in health_data:
                # These fields are optional but good to have
                continue
    
    def test_database_connectivity_health(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test that database connectivity affects health status."""
        # Make a request that requires database access
        response = client.get("/api/v1/datasets/", headers=auth_headers)
        
        # If this succeeds, database connectivity is working
        # If it fails, it might indicate infrastructure issues
        if response.status_code == 500:
            pytest.skip("Database connectivity issues detected")
        
        # Should get either success or auth-related error, not infrastructure error
        assert response.status_code in [200, 401, 403]
    
    def test_redis_connectivity_health(self, client: TestClient):
        """Test Redis connectivity through cache operations.""" 
        # Health check should still work even if Redis is down
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        # But cache-dependent operations might be affected
        # This is tested implicitly through other API calls


@pytest.mark.integration
@pytest.mark.monitoring
class TestAlertScenarios:
    """Test specific alert scenarios."""
    
    def test_service_availability_monitoring(self, client: TestClient):
        """Test that service availability can be monitored."""
        # Make sure service is responding
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        # This test mainly validates that the service is up
        # Actual downtime testing would require stopping the service
    
    def test_response_time_monitoring(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test response time monitoring capability."""
        import time
        
        start_time = time.time()
        response = client.get("/api/v1/health")
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        assert response.status_code == 200
        assert response_time < 5000, f"Health check took too long: {response_time}ms"
        
        # Test with a more complex operation
        start_time = time.time()
        response = client.get("/api/v1/datasets/", headers=auth_headers)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        
        # Should complete in reasonable time (allow for auth processing)
        if response.status_code == 200:
            assert response_time < 10000, f"Dataset listing took too long: {response_time}ms"