#!/usr/bin/env python3
"""
Sprite Caching System for Evolution Simulation
Pre-computes and caches rotated sprites to eliminate per-frame surface creation
"""

import math
import pygame
from typing import Dict, Tuple, Optional
import weakref

class SpriteCache:
    """Manages pre-computed sprite rotations and caching"""
    
    def __init__(self, rotation_steps=36):
        """Initialize sprite cache
        
        Args:
            rotation_steps: Number of rotation angles to pre-compute (36 = 10 degree increments)
        """
        self.rotation_steps = rotation_steps
        self.angle_step = 2 * math.pi / rotation_steps
        self.cache = {}  # Cache structure: {(entity_type, color, width, height): [rotated_surfaces]}
        self.cache_hits = 0
        self.cache_misses = 0
        
    def _get_cache_key(self, entity_type: str, color: Tuple[int, int, int], 
                      width: int, height: int) -> Tuple:
        """Generate cache key for sprite configuration"""
        return (entity_type, color, int(width), int(height))
    
    def _create_base_sprite(self, entity_type: str, color: Tuple[int, int, int], 
                          width: int, height: int) -> pygame.Surface:
        """Create the base sprite before rotation"""
        base = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # Both predators and prey use ellipses - they're distinguished by color, not shape
        pygame.draw.ellipse(base, color, (0, 0, width, height))
            
        return base
    
    def _pre_compute_rotations(self, base_sprite: pygame.Surface) -> list:
        """Pre-compute all rotation angles for a base sprite"""
        rotated_sprites = []
        
        for i in range(self.rotation_steps):
            angle_rad = i * self.angle_step
            angle_deg = math.degrees(angle_rad)
            rotated = pygame.transform.rotate(base_sprite, -angle_deg)
            rotated_sprites.append(rotated)
            
        return rotated_sprites
    
    def get_sprite(self, entity_type: str, color: Tuple[int, int, int], 
                  width: int, height: int, angle: float) -> pygame.Surface:
        """Get cached rotated sprite for given parameters
        
        Args:
            entity_type: "prey" or "predator"
            color: RGB color tuple
            width: Sprite width (accounting for stretch)
            height: Sprite height (accounting for stretch)  
            angle: Rotation angle in radians
            
        Returns:
            Pre-computed rotated pygame.Surface
        """
        cache_key = self._get_cache_key(entity_type, color, width, height)
        
        if cache_key not in self.cache:
            self.cache_misses += 1
            base_sprite = self._create_base_sprite(entity_type, color, width, height)
            self.cache[cache_key] = self._pre_compute_rotations(base_sprite)
        else:
            self.cache_hits += 1
            
        # Find closest rotation index
        normalized_angle = angle % (2 * math.pi)
        rotation_index = int(normalized_angle / self.angle_step + 0.5) % self.rotation_steps
        
        return self.cache[cache_key][rotation_index]
    
    def clear_cache(self):
        """Clear all cached sprites (useful for memory management)"""
        self.cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        
    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0.0
        
        return {
            "cache_entries": len(self.cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": hit_rate,
            "rotation_steps": self.rotation_steps
        }
    
    def estimate_memory_usage(self) -> int:
        """Estimate memory usage in bytes (approximate)"""
        total_surfaces = len(self.cache) * self.rotation_steps
        # Rough estimate: each surface ~4 bytes per pixel + overhead
        avg_pixels_per_surface = 25 * 25  # estimate for typical entity size
        return total_surfaces * avg_pixels_per_surface * 4


_sprite_cache = None

def get_sprite_cache() -> SpriteCache:
    """Get the global sprite cache instance"""
    global _sprite_cache
    if _sprite_cache is None:
        _sprite_cache = SpriteCache(rotation_steps=36)  # 10-degree increments
    return _sprite_cache

def clear_global_cache():
    """Clear the global sprite cache"""
    global _sprite_cache
    if _sprite_cache:
        _sprite_cache.clear_cache()