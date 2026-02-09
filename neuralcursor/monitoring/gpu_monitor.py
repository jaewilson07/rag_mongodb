"""
GPU and VRAM monitoring for dual 3090 setup.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

import psutil
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GPUStatus(BaseModel):
    """Status of a single GPU."""

    device_id: int
    name: str
    total_memory_gb: float
    used_memory_gb: float
    free_memory_gb: float
    memory_utilization_percent: float
    temperature_celsius: Optional[float] = None
    power_draw_watts: Optional[float] = None
    gpu_utilization_percent: Optional[float] = None


class SystemStatus(BaseModel):
    """Overall system status."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cpu_percent: float
    ram_total_gb: float
    ram_used_gb: float
    ram_percent: float
    gpus: list[GPUStatus]
    process_memory_gb: float


class GPUMonitor:
    """
    Monitors GPU VRAM usage and system health.
    
    Tracks dual 3090 usage for reasoning and embedding LLMs.
    """

    def __init__(self):
        """Initialize GPU monitor."""
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

        # Try to import pynvml for NVIDIA GPU monitoring
        try:
            import pynvml
            pynvml.nvmlInit()
            self._nvml_available = True
            self._nvml = pynvml
            logger.info("nvml_initialized")
        except Exception as e:
            logger.warning("nvml_unavailable", extra={"error": str(e)})
            self._nvml_available = False
            self._nvml = None

    def _get_gpu_status(self, device_id: int) -> Optional[GPUStatus]:
        """
        Get status for a specific GPU.
        
        Args:
            device_id: GPU device ID (0 or 1)
            
        Returns:
            GPU status or None if unavailable
        """
        if not self._nvml_available or not self._nvml:
            return None

        try:
            handle = self._nvml.nvmlDeviceGetHandleByIndex(device_id)

            # Get memory info
            mem_info = self._nvml.nvmlDeviceGetMemoryInfo(handle)
            total_gb = mem_info.total / (1024**3)
            used_gb = mem_info.used / (1024**3)
            free_gb = mem_info.free / (1024**3)
            memory_utilization = (used_gb / total_gb) * 100

            # Get GPU name
            name = self._nvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8")

            # Get temperature (optional)
            try:
                temp = self._nvml.nvmlDeviceGetTemperature(
                    handle, self._nvml.NVML_TEMPERATURE_GPU
                )
            except Exception:
                temp = None

            # Get power draw (optional)
            try:
                power = self._nvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # mW to W
            except Exception:
                power = None

            # Get GPU utilization (optional)
            try:
                util = self._nvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_util = float(util.gpu)
            except Exception:
                gpu_util = None

            return GPUStatus(
                device_id=device_id,
                name=name,
                total_memory_gb=total_gb,
                used_memory_gb=used_gb,
                free_memory_gb=free_gb,
                memory_utilization_percent=memory_utilization,
                temperature_celsius=temp,
                power_draw_watts=power,
                gpu_utilization_percent=gpu_util,
            )

        except Exception as e:
            logger.warning(
                "gpu_status_failed", extra={"device_id": device_id, "error": str(e)}
            )
            return None

    def get_system_status(self) -> SystemStatus:
        """
        Get current system status including both GPUs.
        
        Returns:
            System status
        """
        # CPU and RAM
        cpu_percent = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        ram_total_gb = ram.total / (1024**3)
        ram_used_gb = ram.used / (1024**3)
        ram_percent = ram.percent

        # Process memory
        process = psutil.Process()
        process_memory_gb = process.memory_info().rss / (1024**3)

        # GPU statuses
        gpus = []
        if self._nvml_available:
            for device_id in [0, 1]:  # Dual 3090s
                gpu_status = self._get_gpu_status(device_id)
                if gpu_status:
                    gpus.append(gpu_status)

        return SystemStatus(
            cpu_percent=cpu_percent,
            ram_total_gb=ram_total_gb,
            ram_used_gb=ram_used_gb,
            ram_percent=ram_percent,
            gpus=gpus,
            process_memory_gb=process_memory_gb,
        )

    async def start_monitoring(self, interval_seconds: int = 10) -> None:
        """
        Start background monitoring loop.
        
        Args:
            interval_seconds: Monitoring interval
        """
        if self._monitoring:
            logger.warning("monitoring_already_running")
            return

        self._monitoring = True

        async def monitor_loop():
            while self._monitoring:
                try:
                    status = self.get_system_status()

                    # Log GPU VRAM usage
                    for gpu in status.gpus:
                        logger.info(
                            "gpu_status",
                            extra={
                                "device_id": gpu.device_id,
                                "name": gpu.name,
                                "vram_used_gb": round(gpu.used_memory_gb, 2),
                                "vram_free_gb": round(gpu.free_memory_gb, 2),
                                "vram_percent": round(gpu.memory_utilization_percent, 1),
                                "temp_c": gpu.temperature_celsius,
                                "power_w": gpu.power_draw_watts,
                            },
                        )

                    # Log system stats
                    logger.info(
                        "system_status",
                        extra={
                            "cpu_percent": round(status.cpu_percent, 1),
                            "ram_used_gb": round(status.ram_used_gb, 2),
                            "ram_percent": round(status.ram_percent, 1),
                            "process_memory_gb": round(status.process_memory_gb, 2),
                        },
                    )

                except Exception as e:
                    logger.exception("monitoring_error", extra={"error": str(e)})

                await asyncio.sleep(interval_seconds)

        self._monitor_task = asyncio.create_task(monitor_loop())
        logger.info("monitoring_started", extra={"interval_seconds": interval_seconds})

    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._monitoring = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("monitoring_stopped")

    def __del__(self):
        """Cleanup NVML on destruction."""
        if self._nvml_available and self._nvml:
            try:
                self._nvml.nvmlShutdown()
            except Exception:
                pass


# Global monitor instance
_monitor: Optional[GPUMonitor] = None


def get_monitor() -> GPUMonitor:
    """
    Get or create the global GPU monitor.
    
    Returns:
        GPUMonitor instance
    """
    global _monitor
    if _monitor is None:
        _monitor = GPUMonitor()
    return _monitor
