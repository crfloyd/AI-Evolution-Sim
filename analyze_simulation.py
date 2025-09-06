#!/usr/bin/env python3
"""
Simulation Data Analyzer
Transforms raw simulation_log.json into analysis-ready structured format
"""

import json
import sys
from collections import defaultdict
from typing import Dict, List, Any, Optional

def load_simulation_data(filepath: str) -> Dict[str, Any]:
    """Load raw simulation data from JSON file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {filepath} not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        sys.exit(1)

def organize_entities(events: List[List[Any]]) -> Dict[str, Dict[str, Any]]:
    """Transform event stream into entity-centric view"""
    entities = {}
    
    for event in events:
        frame = event[0]
        event_type = event[1]
        
        if event_type.startswith("birth_"):
            child_id = str(event[2])
            parent_id = str(event[3])
            generation = event[4]
            mutations = event[5] if len(event) > 5 else {}
            species = "prey" if event_type == "birth_prey" else "predator"
            
            entities[child_id] = {
                "id": child_id,
                "species": species,
                "generation": generation,
                "parent_id": parent_id,
                "birth": {
                    "frame": frame,
                    "mutations": mutations
                },
                "death": None,
                "hunts": [],  # For predators
                "hunted_by": [],  # For prey
                "children": [],  # Will be populated later
                "lifespan_frames": None,
                "lifespan_seconds": None
            }
            
        elif event_type.startswith("death_"):
            entity_id = str(event[2])
            generation = event[3]
            age_seconds = event[4]
            
            if entity_id in entities:
                entity = entities[entity_id]
                
                if event_type == "death_prey":
                    energy_at_death = event[5]
                    children_spawned = event[6]
                    entity["death"] = {
                        "frame": frame,
                        "age_seconds": age_seconds,
                        "energy_at_death": energy_at_death,
                        "children_spawned": children_spawned
                    }
                    entity["children_count"] = children_spawned
                    
                elif event_type == "death_pred":
                    total_prey_eaten = event[5]
                    entity["death"] = {
                        "frame": frame,
                        "age_seconds": age_seconds,
                        "total_prey_eaten": total_prey_eaten
                    }
                    entity["total_prey_eaten"] = total_prey_eaten
                
                # Calculate lifespans
                birth_frame = entity["birth"]["frame"]
                entity["lifespan_frames"] = frame - birth_frame
                entity["lifespan_seconds"] = age_seconds
                
        elif event_type == "hunt":
            predator_id = str(event[2])
            predator_generation = event[3]
            prey_eaten_count = event[4]
            
            if predator_id in entities:
                entities[predator_id]["hunts"].append({
                    "frame": frame,
                    "prey_eaten_count": prey_eaten_count
                })
    
    return entities

def build_family_trees(entities: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Add parent-child relationships"""
    
    # First pass: collect children for each parent
    for entity_id, entity in entities.items():
        parent_id = entity.get("parent_id")
        if parent_id and parent_id in entities:
            entities[parent_id]["children"].append(entity_id)
    
    # Second pass: add family metrics
    for entity_id, entity in entities.items():
        entity["children_count"] = len(entity["children"])
        
        # Find all descendants (recursive)
        def count_descendants(eid):
            total = len(entities[eid]["children"])
            for child_id in entities[eid]["children"]:
                if child_id in entities:
                    total += count_descendants(child_id)
            return total
        
        entity["total_descendants"] = count_descendants(entity_id)
        
        # Find lineage depth
        def get_lineage_depth(eid):
            if not entities[eid]["children"]:
                return 0
            max_depth = 0
            for child_id in entities[eid]["children"]:
                if child_id in entities:
                    depth = 1 + get_lineage_depth(child_id)
                    max_depth = max(max_depth, depth)
            return max_depth
        
        entity["lineage_depth"] = get_lineage_depth(entity_id)
    
    return entities

def calculate_mutation_outcomes(entities: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Analyze mutation success rates"""
    
    for entity_id, entity in entities.items():
        mutations = entity["birth"]["mutations"]
        
        if mutations:
            # Calculate mutation success metrics
            mutation_success = {
                "had_children": entity["children_count"] > 0,
                "survival_time": entity["lifespan_seconds"] if entity["death"] else None,
                "reproductive_success": entity["children_count"],
                "mutation_types": list(mutations.keys())
            }
            
            # Special metrics for predators
            if entity["species"] == "predator" and entity["death"]:
                mutation_success["hunting_success"] = entity.get("total_prey_eaten", 0)
            
            entity["mutation_outcome"] = mutation_success
        else:
            entity["mutation_outcome"] = None
    
    return entities

def generate_summary_stats(entities: Dict[str, Dict[str, Any]], frame_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate high-level statistics without losing detail"""
    
    prey_entities = [e for e in entities.values() if e["species"] == "prey"]
    pred_entities = [e for e in entities.values() if e["species"] == "predator"]
    
    # Mutation statistics
    prey_with_mutations = [e for e in prey_entities if e["birth"]["mutations"]]
    pred_with_mutations = [e for e in pred_entities if e["birth"]["mutations"]]
    
    stats = {
        "simulation_overview": {
            "total_entities": len(entities),
            "total_prey": len(prey_entities),
            "total_predators": len(pred_entities),
            "final_frame": frame_data[-1]["frame"] if frame_data else 0,
            "simulation_time_seconds": frame_data[-1]["time_seconds"] if frame_data else 0
        },
        "mutation_overview": {
            "prey_mutation_rate": len(prey_with_mutations) / len(prey_entities) if prey_entities else 0,
            "pred_mutation_rate": len(pred_with_mutations) / len(pred_entities) if pred_entities else 0,
            "total_mutations": len(prey_with_mutations) + len(pred_with_mutations)
        },
        "generation_spread": {
            "prey_max_generation": max([e["generation"] for e in prey_entities], default=0),
            "pred_max_generation": max([e["generation"] for e in pred_entities], default=0),
        }
    }
    
    return stats

def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze_simulation.py simulation_log.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = input_file.replace('.json', '_analysis.json')
    
    print(f"Loading simulation data from {input_file}...")
    raw_data = load_simulation_data(input_file)
    
    print("Organizing entities...")
    entities = organize_entities(raw_data["events"])
    
    print("Building family trees...")
    entities = build_family_trees(entities)
    
    print("Analyzing mutation outcomes...")
    entities = calculate_mutation_outcomes(entities)
    
    print("Generating summary statistics...")
    summary_stats = generate_summary_stats(entities, raw_data["frame_data"])
    
    # Prepare final output
    analysis_data = {
        "metadata": {
            "original_file": input_file,
            "analysis_timestamp": raw_data["start_time"],
            "entities_analyzed": len(entities)
        },
        "summary": summary_stats,
        "entities": entities,
        "frame_data": raw_data["frame_data"],  # Preserve population/trait timelines
        "raw_events": raw_data["events"]  # Keep for deep analysis
    }
    
    print(f"Writing analysis to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(analysis_data, f, indent=2)
    
    print(f"\n=== Analysis Complete ===")
    print(f"Entities analyzed: {len(entities)}")
    print(f"Prey: {summary_stats['simulation_overview']['total_prey']}")
    print(f"Predators: {summary_stats['simulation_overview']['total_predators']}")
    print(f"Simulation time: {summary_stats['simulation_overview']['simulation_time_seconds']}s")
    print(f"Max generations: Prey={summary_stats['generation_spread']['prey_max_generation']}, Predators={summary_stats['generation_spread']['pred_max_generation']}")
    print(f"Mutation rates: Prey={summary_stats['mutation_overview']['prey_mutation_rate']:.1%}, Predators={summary_stats['mutation_overview']['pred_mutation_rate']:.1%}")
    print(f"\nOutput saved to: {output_file}")

if __name__ == "__main__":
    main()