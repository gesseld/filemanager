"""Memory profiling and monitoring utilities."""
import os
import psutil
from fastapi import Request, Response
from fastapi.routing import APIRoute
from loguru import logger
from typing import Callable, Any
from datetime import datetime

class MemoryProfiler:
    """Track and log memory usage of the application."""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.warning_threshold = 0.8  # 80% of 2GB limit
        self.critical_threshold = 0.9  # 90% of 2GB limit
        
    def get_memory_usage(self) -> dict:
        """Get current memory usage statistics."""
        mem = self.process.memory_info()
        return {
            "rss": mem.rss,  # Resident Set Size
            "vms": mem.vms,  # Virtual Memory Size
            "percent": self.process.memory_percent(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    def check_memory(self) -> bool:
        """Check if memory usage exceeds thresholds."""
        usage = self.get_memory_usage()
        if usage["rss"] > self.critical_threshold * 2 * 1024**3:  # 2GB limit
            logger.critical(f"Memory critical: {usage}")
            return False
        elif usage["rss"] > self.warning_threshold * 2 * 1024**3:
            logger.warning(f"Memory warning: {usage}")
        return True

class MemoryProfilerRoute(APIRoute):
    """FastAPI route that tracks memory usage per request."""
    
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request) -> Response:
            profiler = MemoryProfiler()
            try:
                response = await original_route_handler(request)
                mem = profiler.get_memory_usage()
                response.headers["X-Memory-Usage"] = str(mem["rss"])
                return response
            except Exception as e:
                mem = profiler.get_memory_usage()
                logger.error(f"Request failed with memory usage: {mem}")
                raise e
                
        return custom_route_handler

# Global profiler instance
memory_profiler = MemoryProfiler()

def log_memory_usage():
    """Periodic memory usage logging."""
    mem = memory_profiler.get_memory_usage()
    logger.info(f"Memory usage: {mem['rss']/1024/1024:.2f}MB ({mem['percent']:.1f}%)")