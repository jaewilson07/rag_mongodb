"""VRAM monitoring dashboard for dual GPU setup."""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path

try:
    import pynvml
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False

from .vllm_config import VRAMMonitorConfig

logger = logging.getLogger(__name__)


class VRAMMonitor:
    """
    Real-time VRAM monitoring for dual 3090 GPUs.
    
    Tracks:
    - GPU memory usage
    - GPU utilization
    - Temperature
    - Power draw
    - Alert thresholds
    """

    def __init__(self, config: VRAMMonitorConfig):
        """
        Initialize VRAM monitor.
        
        Args:
            config: Monitor configuration
        """
        self.config = config
        self._running = False
        self._nvml_initialized = False
        
        if not NVML_AVAILABLE:
            logger.warning("pynvml_not_available", extra={
                "message": "Install pynvml for GPU monitoring: pip install nvidia-ml-py"
            })

    async def initialize(self) -> None:
        """Initialize NVML for GPU monitoring."""
        if not NVML_AVAILABLE:
            return
        
        try:
            pynvml.nvmlInit()
            self._nvml_initialized = True
            logger.info("vram_monitor_initialized")
        except Exception as e:
            logger.exception("vram_monitor_init_failed", extra={"error": str(e)})

    async def shutdown(self) -> None:
        """Shutdown NVML."""
        if self._nvml_initialized:
            try:
                pynvml.nvmlShutdown()
                self._nvml_initialized = False
                logger.info("vram_monitor_shutdown")
            except Exception as e:
                logger.exception("vram_monitor_shutdown_failed", extra={"error": str(e)})

    def get_gpu_metrics(self, gpu_id: int) -> Dict[str, Any]:
        """
        Get metrics for a specific GPU.
        
        Args:
            gpu_id: GPU device ID (0 or 1)
            
        Returns:
            Dictionary of GPU metrics
        """
        if not self._nvml_initialized:
            return {"error": "NVML not initialized"}

        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
            
            # Memory info
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            memory_used_gb = mem_info.used / (1024 ** 3)
            memory_total_gb = mem_info.total / (1024 ** 3)
            memory_percent = (mem_info.used / mem_info.total) * 100
            
            # Utilization
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            
            # Temperature
            temperature = pynvml.nvmlDeviceGetTemperature(
                handle, pynvml.NVML_TEMPERATURE_GPU
            )
            
            # Power
            power_draw = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # mW to W
            
            # GPU name
            gpu_name = pynvml.nvmlDeviceGetName(handle)
            
            return {
                "gpu_id": gpu_id,
                "gpu_name": gpu_name,
                "memory_used_gb": round(memory_used_gb, 2),
                "memory_total_gb": round(memory_total_gb, 2),
                "memory_percent": round(memory_percent, 2),
                "gpu_utilization_percent": utilization.gpu,
                "memory_utilization_percent": utilization.memory,
                "temperature_celsius": temperature,
                "power_draw_watts": round(power_draw, 2),
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.exception("vram_metrics_failed", extra={"gpu_id": gpu_id, "error": str(e)})
            return {"error": str(e), "gpu_id": gpu_id}

    async def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get metrics for all GPUs.
        
        Returns:
            Dictionary with metrics for GPU 0 and GPU 1
        """
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "gpus": {},
        }
        
        if not self._nvml_initialized:
            await self.initialize()
        
        if not self._nvml_initialized:
            return {"error": "NVML not available"}
        
        try:
            device_count = pynvml.nvmlDeviceGetCount()
            for gpu_id in range(min(device_count, 2)):  # Only monitor first 2 GPUs
                metrics["gpus"][f"gpu_{gpu_id}"] = self.get_gpu_metrics(gpu_id)
            
            # Check alert thresholds
            alerts = []
            for gpu_id, gpu_metrics in metrics["gpus"].items():
                if "memory_percent" in gpu_metrics:
                    if gpu_metrics["memory_percent"] >= (self.config.alert_threshold_percent * 100):
                        alerts.append({
                            "gpu": gpu_id,
                            "type": "memory_high",
                            "value": gpu_metrics["memory_percent"],
                            "threshold": self.config.alert_threshold_percent * 100,
                        })
            
            metrics["alerts"] = alerts
            
        except Exception as e:
            logger.exception("vram_all_metrics_failed", extra={"error": str(e)})
            metrics["error"] = str(e)
        
        return metrics

    async def log_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Log metrics to file.
        
        Args:
            metrics: Metrics dictionary to log
        """
        if not self.config.log_metrics:
            return
        
        try:
            metrics_file = Path(self.config.metrics_file)
            metrics_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(metrics_file, "a") as f:
                f.write(json.dumps(metrics) + "\n")
        except Exception as e:
            logger.exception("vram_log_metrics_failed", extra={"error": str(e)})

    async def monitor_loop(self) -> None:
        """
        Continuous monitoring loop.
        
        Run this in the background to continuously monitor GPUs.
        """
        self._running = True
        await self.initialize()
        
        logger.info("vram_monitor_started", extra={
            "update_interval": self.config.update_interval_seconds
        })
        
        while self._running:
            try:
                metrics = await self.get_all_metrics()
                
                # Log to file
                await self.log_metrics(metrics)
                
                # Log alerts
                if metrics.get("alerts"):
                    for alert in metrics["alerts"]:
                        logger.warning("vram_alert", extra=alert)
                
                # Wait for next update
                await asyncio.sleep(self.config.update_interval_seconds)
                
            except Exception as e:
                logger.exception("vram_monitor_loop_error", extra={"error": str(e)})
                await asyncio.sleep(self.config.update_interval_seconds)
        
        await self.shutdown()
        logger.info("vram_monitor_stopped")

    async def stop(self) -> None:
        """Stop the monitoring loop."""
        self._running = False


async def create_vram_dashboard_html(output_path: str = "data/vram_dashboard.html") -> None:
    """
    Create a simple HTML dashboard for VRAM monitoring.
    
    Args:
        output_path: Path to save HTML file
    """
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>NeuralCursor VRAM Monitor</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1e1e1e;
            color: #d4d4d4;
            margin: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #4ec9b0;
        }
        .gpu-card {
            background: #252526;
            border: 1px solid #3e3e42;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        .gpu-header {
            font-size: 1.5em;
            color: #569cd6;
            margin-bottom: 10px;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #3e3e42;
        }
        .metric-label {
            color: #9cdcfe;
        }
        .metric-value {
            color: #ce9178;
            font-weight: bold;
        }
        .alert {
            background: #5a1d1d;
            border: 1px solid #f48771;
            border-radius: 4px;
            padding: 10px;
            margin: 10px 0;
            color: #f48771;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #3e3e42;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4ec9b0, #569cd6);
            transition: width 0.3s ease;
        }
        .timestamp {
            color: #858585;
            font-size: 0.9em;
            text-align: right;
            margin-top: 20px;
        }
    </style>
    <script>
        async function updateMetrics() {
            try {
                const response = await fetch('/api/health/vram');
                const data = await response.json();
                
                // Update GPU 0
                updateGPU('gpu0', data.gpus.gpu_0);
                
                // Update GPU 1
                updateGPU('gpu1', data.gpus.gpu_1);
                
                // Update alerts
                updateAlerts(data.alerts);
                
                // Update timestamp
                document.getElementById('timestamp').textContent = 
                    new Date(data.timestamp).toLocaleString();
                
            } catch (error) {
                console.error('Failed to fetch metrics:', error);
            }
        }
        
        function updateGPU(elementId, metrics) {
            const element = document.getElementById(elementId);
            if (!element || !metrics) return;
            
            element.querySelector('.gpu-name').textContent = metrics.gpu_name || 'Unknown';
            element.querySelector('.memory-used').textContent = 
                `${metrics.memory_used_gb} GB / ${metrics.memory_total_gb} GB`;
            element.querySelector('.memory-percent').textContent = 
                `${metrics.memory_percent}%`;
            element.querySelector('.gpu-util').textContent = 
                `${metrics.gpu_utilization_percent}%`;
            element.querySelector('.temperature').textContent = 
                `${metrics.temperature_celsius}°C`;
            element.querySelector('.power').textContent = 
                `${metrics.power_draw_watts} W`;
            
            // Update progress bar
            const progressBar = element.querySelector('.progress-fill');
            progressBar.style.width = `${metrics.memory_percent}%`;
            
            // Color code based on usage
            if (metrics.memory_percent > 90) {
                progressBar.style.background = 'linear-gradient(90deg, #f48771, #ce9178)';
            } else if (metrics.memory_percent > 70) {
                progressBar.style.background = 'linear-gradient(90deg, #dcdcaa, #ce9178)';
            } else {
                progressBar.style.background = 'linear-gradient(90deg, #4ec9b0, #569cd6)';
            }
        }
        
        function updateAlerts(alerts) {
            const container = document.getElementById('alerts');
            if (!alerts || alerts.length === 0) {
                container.innerHTML = '<p style="color: #4ec9b0;">✓ All systems nominal</p>';
                return;
            }
            
            container.innerHTML = alerts.map(alert => `
                <div class="alert">
                    ⚠️ ${alert.gpu}: ${alert.type} - ${alert.value}% (threshold: ${alert.threshold}%)
                </div>
            `).join('');
        }
        
        // Update every 5 seconds
        setInterval(updateMetrics, 5000);
        updateMetrics();
    </script>
</head>
<body>
    <div class="container">
        <h1>🧠 NeuralCursor VRAM Monitor</h1>
        
        <div id="alerts"></div>
        
        <div class="gpu-card" id="gpu0">
            <div class="gpu-header">GPU 0 - Reasoning (<span class="gpu-name">Loading...</span>)</div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: 0%"></div>
            </div>
            <div class="metric">
                <span class="metric-label">Memory Usage:</span>
                <span class="metric-value memory-used">-- GB / -- GB</span>
            </div>
            <div class="metric">
                <span class="metric-label">Memory Percent:</span>
                <span class="metric-value memory-percent">--%</span>
            </div>
            <div class="metric">
                <span class="metric-label">GPU Utilization:</span>
                <span class="metric-value gpu-util">--%</span>
            </div>
            <div class="metric">
                <span class="metric-label">Temperature:</span>
                <span class="metric-value temperature">--°C</span>
            </div>
            <div class="metric">
                <span class="metric-label">Power Draw:</span>
                <span class="metric-value power">-- W</span>
            </div>
        </div>
        
        <div class="gpu-card" id="gpu1">
            <div class="gpu-header">GPU 1 - Embedding (<span class="gpu-name">Loading...</span>)</div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: 0%"></div>
            </div>
            <div class="metric">
                <span class="metric-label">Memory Usage:</span>
                <span class="metric-value memory-used">-- GB / -- GB</span>
            </div>
            <div class="metric">
                <span class="metric-label">Memory Percent:</span>
                <span class="metric-value memory-percent">--%</span>
            </div>
            <div class="metric">
                <span class="metric-label">GPU Utilization:</span>
                <span class="metric-value gpu-util">--%</span>
            </div>
            <div class="metric">
                <span class="metric-label">Temperature:</span>
                <span class="metric-value temperature">--°C</span>
            </div>
            <div class="metric">
                <span class="metric-label">Power Draw:</span>
                <span class="metric-value power">-- W</span>
            </div>
        </div>
        
        <div class="timestamp">Last updated: <span id="timestamp">--</span></div>
    </div>
</body>
</html>
"""
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w") as f:
        f.write(html_content)
    
    logger.info("vram_dashboard_created", extra={"path": output_path})
