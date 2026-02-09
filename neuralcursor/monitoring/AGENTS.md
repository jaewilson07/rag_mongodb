# Monitoring - Health & VRAM Tracking

## Overview

The monitoring module provides real-time health monitoring and VRAM tracking for NeuralCursor's dual GPU setup. It includes GPU monitoring with NVIDIA Management Library (NVML) integration and a Rich-based terminal dashboard.

## Architecture

```
monitoring/
├── __init__.py
├── gpu_monitor.py      # GPU and VRAM monitoring
└── dashboard.py        # Rich terminal UI
```

## GPU Monitor

### Purpose

Tracks GPU metrics for both 3090s:
- VRAM usage (used, free, total)
- GPU utilization percentage
- Temperature
- Power draw
- System CPU/RAM

### Usage

```python
from neuralcursor.monitoring.gpu_monitor import get_monitor

# Get singleton instance
monitor = get_monitor()

# Start background monitoring
await monitor.start_monitoring(interval_seconds=10)

# Get current status
status = monitor.get_system_status()

print(f"Total GPUs: {len(status.gpus)}")
print(f"CPU: {status.cpu_percent}%")
print(f"RAM: {status.ram_used_gb:.1f}GB / {status.ram_total_gb:.1f}GB")

for gpu in status.gpus:
    print(f"\nGPU {gpu.device_id}: {gpu.name}")
    print(f"  VRAM: {gpu.used_memory_gb:.1f}GB / {gpu.total_memory_gb:.1f}GB ({gpu.memory_utilization_percent:.1f}%)")
    print(f"  Temp: {gpu.temperature_celsius}°C")
    print(f"  Power: {gpu.power_draw_watts:.0f}W")
    print(f"  Utilization: {gpu.gpu_utilization_percent}%")

# Stop monitoring
await monitor.stop_monitoring()
```

### Configuration

```bash
NEURALCURSOR_MONITORING_ENABLED=true
NEURALCURSOR_MONITORING_INTERVAL_SECONDS=10
```

See [gpu_monitor.py](./gpu_monitor.py) for implementation.

## Dashboard

### Purpose

Provides a live terminal UI for monitoring system health.

### Usage

```python
from neuralcursor.monitoring.dashboard import HealthDashboard

dashboard = HealthDashboard()

# Run dashboard (blocking)
await dashboard.run(refresh_interval=2.0)

# Or run as standalone
python -m neuralcursor.monitoring.dashboard
```

### Dashboard Layout

```
┌────────────────────────────────────────────────┐
│ 🧠 NeuralCursor Health Dashboard              │
│                              2024-02-06 10:30  │
└────────────────────────────────────────────────┘

┌─────────────────────────────┬─────────────────┐
│ GPU Status (Dual 3090s)     │ System Resources│
│                             │                 │
│ GPU 0: NVIDIA RTX 3090      │ CPU: 25.3%      │
│   VRAM: 18.2GB / 24.0GB     │ RAM: 12.5GB     │
│   Util: 75.3%               │      (31.2%)    │
│   Temp: 68°C                │ Process: 2.1GB  │
│   Power: 320W               │                 │
│                             │ Connections     │
│ GPU 1: NVIDIA RTX 3090      │                 │
│   VRAM: 3.8GB / 24.0GB      │ Neo4j: ✓        │
│   Util: 15.8%               │ MongoDB: ✓      │
│   Temp: 55°C                │ Reasoning: ✓    │
│   Power: 180W               │ Embedding: ✓    │
└─────────────────────────────┴─────────────────┘

Press Ctrl+C to exit
```

See [dashboard.py](./dashboard.py) for implementation.

## Models

### GPUStatus

```python
from neuralcursor.monitoring.gpu_monitor import GPUStatus

gpu = GPUStatus(
    device_id=0,
    name="NVIDIA GeForce RTX 3090",
    total_memory_gb=24.0,
    used_memory_gb=18.2,
    free_memory_gb=5.8,
    memory_utilization_percent=75.8,
    temperature_celsius=68,
    power_draw_watts=320,
    gpu_utilization_percent=75
)
```

### SystemStatus

```python
from neuralcursor.monitoring.gpu_monitor import SystemStatus

status = SystemStatus(
    cpu_percent=25.3,
    ram_total_gb=32.0,
    ram_used_gb=10.1,
    ram_percent=31.5,
    gpus=[gpu0, gpu1],
    process_memory_gb=2.1
)
```

## Design Patterns

### Pattern 1: Background Monitoring Loop

```python
async def monitor_loop():
    """Background monitoring loop."""
    monitor = get_monitor()
    
    await monitor.start_monitoring(interval_seconds=10)
    
    try:
        # Keep running
        await asyncio.Future()
    except asyncio.CancelledError:
        await monitor.stop_monitoring()
```

### Pattern 2: Alert on High VRAM

```python
async def monitor_with_alerts():
    """Monitor with alerting."""
    monitor = get_monitor()
    
    while True:
        status = monitor.get_system_status()
        
        for gpu in status.gpus:
            if gpu.memory_utilization_percent > 90:
                logger.warning("vram_critical", extra={
                    "device_id": gpu.device_id,
                    "used_gb": gpu.used_memory_gb,
                    "percent": gpu.memory_utilization_percent
                })
                
                # Take action (e.g., clear cache)
                if gpu.device_id == 0:
                    await clear_reasoning_cache()
        
        await asyncio.sleep(30)
```

### Pattern 3: Export Metrics

```python
async def export_metrics_to_prometheus():
    """Export metrics in Prometheus format."""
    from prometheus_client import Gauge
    
    vram_used = Gauge('neuralcursor_vram_used_bytes', 'VRAM used', ['device_id'])
    vram_total = Gauge('neuralcursor_vram_total_bytes', 'VRAM total', ['device_id'])
    gpu_temp = Gauge('neuralcursor_gpu_temp_celsius', 'GPU temperature', ['device_id'])
    
    monitor = get_monitor()
    
    while True:
        status = monitor.get_system_status()
        
        for gpu in status.gpus:
            vram_used.labels(device_id=gpu.device_id).set(gpu.used_memory_gb * 1024**3)
            vram_total.labels(device_id=gpu.device_id).set(gpu.total_memory_gb * 1024**3)
            gpu_temp.labels(device_id=gpu.device_id).set(gpu.temperature_celsius or 0)
        
        await asyncio.sleep(10)
```

### Pattern 4: Health Check Endpoint

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/monitoring/gpu")
async def get_gpu_status():
    """Get GPU status for health checks."""
    monitor = get_monitor()
    status = monitor.get_system_status()
    
    return {
        "gpus": [
            {
                "device_id": gpu.device_id,
                "name": gpu.name,
                "vram_used_gb": gpu.used_memory_gb,
                "vram_total_gb": gpu.total_memory_gb,
                "vram_percent": gpu.memory_utilization_percent,
                "temperature": gpu.temperature_celsius,
                "power_watts": gpu.power_draw_watts
            }
            for gpu in status.gpus
        ],
        "system": {
            "cpu_percent": status.cpu_percent,
            "ram_used_gb": status.ram_used_gb,
            "ram_percent": status.ram_percent
        }
    }
```

## Dashboard Customization

### Custom Layout

```python
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table

class CustomDashboard(HealthDashboard):
    """Custom dashboard layout."""
    
    def _create_layout(self) -> Layout:
        """Create custom layout."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="main"),
        )
        
        layout["main"].split_row(
            Layout(name="gpus", ratio=2),
            Layout(name="stats", ratio=1),
        )
        
        return layout
    
    def _render_custom_panel(self) -> Panel:
        """Add custom panel."""
        content = "Custom monitoring data..."
        return Panel(content, title="Custom")
```

### Color Themes

```python
# Color code by threshold
def get_vram_color(utilization_percent: float) -> str:
    """Get color based on VRAM usage."""
    if utilization_percent > 90:
        return "red"
    elif utilization_percent > 75:
        return "yellow"
    elif utilization_percent > 50:
        return "cyan"
    else:
        return "green"

# Usage in dashboard
vram_color = get_vram_color(gpu.memory_utilization_percent)
console.print(f"[{vram_color}]{gpu.used_memory_gb:.1f}GB[/{vram_color}]")
```

## Performance Considerations

### NVML Overhead

NVML calls are lightweight:
- ~1-2ms per call
- Negligible CPU usage
- No GPU compute impact

### Monitoring Interval

Recommended intervals:
- **Development**: 2-5 seconds
- **Production**: 10-30 seconds
- **Alert-only**: 60+ seconds

```python
# Adjust based on needs
await monitor.start_monitoring(
    interval_seconds=10  # Good balance
)
```

### Memory Usage

Dashboard memory footprint:
- Base: ~10MB
- NVML library: ~5MB
- Total: < 20MB

## NVML Integration

### Requirements

```bash
# NVIDIA drivers must be installed
nvidia-smi

# Python package
pip install nvidia-ml-py3
```

### Fallback Handling

Monitor gracefully falls back if NVML unavailable:

```python
try:
    import pynvml
    pynvml.nvmlInit()
    self._nvml_available = True
except Exception as e:
    logger.warning("nvml_unavailable", extra={"error": str(e)})
    self._nvml_available = False
```

## Testing

### Unit Tests

```python
import pytest
from neuralcursor.monitoring.gpu_monitor import GPUMonitor

def test_gpu_monitor_initialization():
    """Test monitor initialization."""
    monitor = GPUMonitor()
    assert monitor is not None

def test_system_status():
    """Test getting system status."""
    monitor = GPUMonitor()
    status = monitor.get_system_status()
    
    assert status.cpu_percent >= 0
    assert status.ram_total_gb > 0
    assert isinstance(status.gpus, list)

@pytest.mark.skipif(not_nvidia_gpu(), reason="No NVIDIA GPU")
def test_gpu_status():
    """Test GPU status retrieval."""
    monitor = GPUMonitor()
    status = monitor.get_system_status()
    
    assert len(status.gpus) > 0
    
    for gpu in status.gpus:
        assert gpu.device_id >= 0
        assert gpu.total_memory_gb > 0
        assert 0 <= gpu.memory_utilization_percent <= 100
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_background_monitoring():
    """Test background monitoring loop."""
    monitor = GPUMonitor()
    
    await monitor.start_monitoring(interval_seconds=1)
    
    # Wait for a few cycles
    await asyncio.sleep(3)
    
    # Should have logged metrics
    status = monitor.get_system_status()
    assert status is not None
    
    await monitor.stop_monitoring()
```

## Troubleshooting

### NVML Not Available

**Check:**
```bash
# Verify NVIDIA drivers
nvidia-smi

# Check NVML library
python -c "import pynvml; pynvml.nvmlInit(); print('NVML OK')"

# Install if missing
pip install nvidia-ml-py3
```

### GPU Not Detected

**Check:**
```python
# List available GPUs
import pynvml
pynvml.nvmlInit()

device_count = pynvml.nvmlDeviceGetCount()
print(f"GPUs detected: {device_count}")

for i in range(device_count):
    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
    name = pynvml.nvmlDeviceGetName(handle)
    print(f"GPU {i}: {name}")
```

### Dashboard Not Updating

**Check:**
```python
# Verify monitoring is running
monitor = get_monitor()
print(f"Monitoring active: {monitor._monitoring}")

# Check interval
print(f"Interval: {monitor._interval_seconds}s")

# Manual status check
status = monitor.get_system_status()
print(status)
```

## Metrics Export

### Prometheus Format

```python
# /metrics endpoint
def format_prometheus_metrics(status: SystemStatus) -> str:
    """Format metrics in Prometheus format."""
    lines = []
    
    # GPU metrics
    for gpu in status.gpus:
        lines.append(f'neuralcursor_vram_used_bytes{{device_id="{gpu.device_id}"}} {gpu.used_memory_gb * 1024**3}')
        lines.append(f'neuralcursor_gpu_temp_celsius{{device_id="{gpu.device_id}"}} {gpu.temperature_celsius or 0}')
    
    # System metrics
    lines.append(f'neuralcursor_cpu_percent {status.cpu_percent}')
    lines.append(f'neuralcursor_ram_used_bytes {status.ram_used_gb * 1024**3}')
    
    return "\n".join(lines)
```

### JSON Export

```python
def export_status_json(status: SystemStatus) -> dict:
    """Export status as JSON."""
    return {
        "timestamp": status.timestamp.isoformat(),
        "cpu_percent": status.cpu_percent,
        "ram": {
            "used_gb": status.ram_used_gb,
            "total_gb": status.ram_total_gb,
            "percent": status.ram_percent
        },
        "gpus": [
            {
                "device_id": gpu.device_id,
                "name": gpu.name,
                "vram_used_gb": gpu.used_memory_gb,
                "vram_total_gb": gpu.total_memory_gb,
                "utilization_percent": gpu.memory_utilization_percent,
                "temperature_celsius": gpu.temperature_celsius,
                "power_watts": gpu.power_draw_watts
            }
            for gpu in status.gpus
        ]
    }
```

## Related Documentation

- [gpu_monitor.py](./gpu_monitor.py) - GPU monitoring implementation
- [dashboard.py](./dashboard.py) - Terminal dashboard UI
- [../llm/AGENTS.md](../llm/AGENTS.md) - LLM GPU usage
- [../orchestrator.py](../orchestrator.py) - Main orchestration
- [../AGENTS.md](../AGENTS.md) - Root documentation
