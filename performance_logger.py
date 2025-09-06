#!/usr/bin/env python3
"""
Performance Logger for Evolution Simulation
Tracks frame rates, population sizes, and performance metrics
"""

import json
import time
import sys
import os
from collections import deque
from typing import Dict, List, Any

# Import centralized frame rate constant
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from main import FRAME_RATE
except ImportError:
    FRAME_RATE = 60  # Fallback if import fails

class PerformanceLogger:
    def __init__(self, log_file="performance_log.json"):
        self.log_file = log_file
        self.start_time = time.time()
        self.frame_times = deque(maxlen=60)  # Last 60 frame times for rolling average
        self.last_frame_time = time.time()
        
        self.data = {
            "start_time": self.start_time,
            "performance_samples": [],
            "metadata": {
                "target_fps": FRAME_RATE,
                "sample_interval": FRAME_RATE  # Log every second (frames per second)
            }
        }
        
    def log_frame_start(self):
        """Call at the start of each frame"""
        current_time = time.time()
        frame_time = current_time - self.last_frame_time
        self.frame_times.append(frame_time)
        self.last_frame_time = current_time
        
    def log_performance_sample(self, frame_count: int, current_fps: float, 
                              prey_count: int, predator_count: int, 
                              entities_drawn: int = None, vision_casts: int = None,
                              sprite_cache_stats: dict = None):
        """Log a performance sample"""
        
        # Calculate rolling frame time statistics
        if len(self.frame_times) > 1:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            min_frame_time = min(self.frame_times)
            max_frame_time = max(self.frame_times)
            rolling_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        else:
            avg_frame_time = min_frame_time = max_frame_time = 0
            rolling_fps = current_fps
            
        sample = {
            "frame": frame_count,
            "timestamp": time.time() - self.start_time,
            "fps": {
                "current": round(current_fps, 2),
                "rolling_avg": round(rolling_fps, 2),
                "target": self.data["metadata"]["target_fps"]
            },
            "frame_times_ms": {
                "avg": round(avg_frame_time * 1000, 2),
                "min": round(min_frame_time * 1000, 2),
                "max": round(max_frame_time * 1000, 2)
            },
            "populations": {
                "prey": prey_count,
                "predator": predator_count,
                "total": prey_count + predator_count
            }
        }
        
        # Add optional metrics
        if entities_drawn is not None:
            sample["rendering"] = {"entities_drawn": entities_drawn}
        if vision_casts is not None:
            sample["ai"] = {"vision_casts": vision_casts}
        if sprite_cache_stats is not None:
            sample["sprite_cache"] = sprite_cache_stats
            
        self.data["performance_samples"].append(sample)
        
    def get_recent_avg_fps(self, samples=10) -> float:
        """Get average FPS from recent samples"""
        if len(self.data["performance_samples"]) == 0:
            return 0.0
        recent_samples = self.data["performance_samples"][-samples:]
        return sum(s["fps"]["rolling_avg"] for s in recent_samples) / len(recent_samples)
        
    def save_to_file(self):
        """Save performance data to JSON file"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving performance data: {e}")
            
    def print_summary(self):
        """Print performance summary"""
        if not self.data["performance_samples"]:
            print("No performance data collected")
            return
            
        samples = self.data["performance_samples"]
        fps_values = [s["fps"]["rolling_avg"] for s in samples]
        populations = [s["populations"]["total"] for s in samples]
        
        print(f"\n=== Performance Summary ===")
        print(f"Duration: {samples[-1]['timestamp']:.1f}s")
        print(f"Samples collected: {len(samples)}")
        print(f"FPS - Avg: {sum(fps_values)/len(fps_values):.1f}, Min: {min(fps_values):.1f}, Max: {max(fps_values):.1f}")
        print(f"Population - Max: {max(populations)}, Final: {populations[-1]}")
        print(f"Performance log saved to: {self.log_file}")


def analyze_performance_log(log_file="performance_log.json"):
    """Analyze performance log and generate insights"""
    try:
        with open(log_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Performance log {log_file} not found")
        return
        
    samples = data["performance_samples"]
    if not samples:
        print("No performance data to analyze")
        return
        
    print(f"\n=== Performance Analysis ===")
    
    # FPS analysis
    fps_data = [s["fps"]["rolling_avg"] for s in samples]
    target_fps = data["metadata"]["target_fps"]
    
    print(f"Target FPS: {target_fps}")
    print(f"Average FPS: {sum(fps_data)/len(fps_data):.1f}")
    print(f"Min FPS: {min(fps_data):.1f}")
    print(f"Max FPS: {max(fps_data):.1f}")
    print(f"Samples below target ({target_fps} FPS): {len([f for f in fps_data if f < target_fps])}/{len(fps_data)}")
    
    # Population correlation
    populations = [s["populations"]["total"] for s in samples]
    print(f"\nPopulation Range: {min(populations)} - {max(populations)}")
    
    # Find performance bottlenecks
    worst_samples = sorted(samples, key=lambda s: s["fps"]["rolling_avg"])[:5]
    print(f"\nWorst Performance Samples:")
    for i, sample in enumerate(worst_samples):
        print(f"{i+1}. Frame {sample['frame']}: {sample['fps']['rolling_avg']:.1f} FPS, "
              f"{sample['populations']['total']} entities")
              
    
if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_performance_log(sys.argv[1])
    else:
        analyze_performance_log()