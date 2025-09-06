#!/usr/bin/env python3
"""
Vision Array Pooling System for Evolution Simulation
Reduces memory allocation overhead by reusing NumPy arrays for vision calculations
"""

import numpy as np
from collections import defaultdict
from typing import Tuple

class VisionArrayPool:
    """Pool of reusable NumPy arrays for vision calculations"""
    
    def __init__(self, max_arrays_per_size=50):
        """Initialize the array pool
        
        Args:
            max_arrays_per_size: Maximum number of arrays to cache per size
        """
        self.max_arrays_per_size = max_arrays_per_size
        
        # Pool structure: {num_rays: {'vision': [arrays], 'hits': [arrays], 'angles': [arrays]}}
        self.vision_pools = defaultdict(list)      # float32 arrays for vision distances
        self.hits_pools = defaultdict(list)        # int32 arrays for hit types  
        self.angles_pools = defaultdict(list)      # float64 arrays for ray angles
        
        # Statistics
        self.allocations_saved = 0
        self.allocations_made = 0
        
    def get_arrays(self, num_rays: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Get pooled arrays for vision calculation
        
        Args:
            num_rays: Number of rays (array size)
            
        Returns:
            Tuple of (vision, hits, ray_angles) arrays
        """
        vision_array = self._get_or_create_vision_array(num_rays)
        hits_array = self._get_or_create_hits_array(num_rays)  
        angles_array = self._get_or_create_angles_array(num_rays)
        
        return vision_array, hits_array, angles_array
    
    def return_arrays(self, vision: np.ndarray, hits: np.ndarray, 
                     angles: np.ndarray) -> None:
        """Return arrays to the pool for reuse
        
        Args:
            vision: Vision distance array to return
            hits: Hit type array to return  
            angles: Ray angles array to return
        """
        num_rays = len(vision)
        
        # Return to pools if not at capacity
        if len(self.vision_pools[num_rays]) < self.max_arrays_per_size:
            # Reset arrays to clean state
            vision.fill(1.0)  # Default vision distance
            hits.fill(0)      # HIT_NONE = 0
            self.vision_pools[num_rays].append(vision)
        
        if len(self.hits_pools[num_rays]) < self.max_arrays_per_size:
            self.hits_pools[num_rays].append(hits)
            
        if len(self.angles_pools[num_rays]) < self.max_arrays_per_size:
            self.angles_pools[num_rays].append(angles)
    
    def _get_or_create_vision_array(self, num_rays: int) -> np.ndarray:
        """Get pooled vision array or create new one"""
        pool = self.vision_pools[num_rays]
        if pool:
            self.allocations_saved += 1
            return pool.pop()
        else:
            self.allocations_made += 1
            return np.ones(num_rays, dtype=np.float32)
    
    def _get_or_create_hits_array(self, num_rays: int) -> np.ndarray:
        """Get pooled hits array or create new one"""
        pool = self.hits_pools[num_rays]
        if pool:
            self.allocations_saved += 1
            return pool.pop()
        else:
            self.allocations_made += 1
            return np.full(num_rays, 0, dtype=np.int32)  # HIT_NONE = 0
    
    def _get_or_create_angles_array(self, num_rays: int) -> np.ndarray:
        """Get pooled ray angles array or create new one"""
        pool = self.angles_pools[num_rays]
        if pool:
            self.allocations_saved += 1
            return pool.pop()
        else:
            self.allocations_made += 1
            return np.empty(num_rays, dtype=np.float64)
    
    def get_pool_stats(self) -> dict:
        """Get array pool performance statistics"""
        total_pooled_arrays = (
            sum(len(pool) for pool in self.vision_pools.values()) +
            sum(len(pool) for pool in self.hits_pools.values()) +
            sum(len(pool) for pool in self.angles_pools.values())
        )
        
        total_requests = self.allocations_saved + self.allocations_made
        reuse_rate = self.allocations_saved / total_requests if total_requests > 0 else 0.0
        
        return {
            "pooled_arrays": total_pooled_arrays,
            "array_sizes_cached": len(self.vision_pools),
            "allocations_saved": self.allocations_saved,
            "allocations_made": self.allocations_made,
            "reuse_rate": reuse_rate,
            "max_arrays_per_size": self.max_arrays_per_size
        }
    
    def clear_pools(self):
        """Clear all pooled arrays (for memory management)"""
        self.vision_pools.clear()
        self.hits_pools.clear()
        self.angles_pools.clear()
        self.allocations_saved = 0
        self.allocations_made = 0


# Global array pool instance  
_vision_array_pool = None

def get_vision_array_pool() -> VisionArrayPool:
    """Get the global vision array pool instance"""
    global _vision_array_pool
    if _vision_array_pool is None:
        _vision_array_pool = VisionArrayPool(max_arrays_per_size=100)  # Cache up to 100 per size
    return _vision_array_pool

def clear_global_array_pool():
    """Clear the global vision array pool"""
    global _vision_array_pool
    if _vision_array_pool:
        _vision_array_pool.clear_pools()