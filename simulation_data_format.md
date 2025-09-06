# Simulation Data Format

## Overview
The simulation generates `simulation_log.json` with evolutionary data in a compact array format for efficient parsing.

## Structure

```json
{
  "start_time": 1703123456.789,
  "frame_data": [
    {
      "frame": 30,
      "time_seconds": 1,
      "populations": {"prey_count": 250, "predator_count": 5},
      "generations": {
        "prey_avg": 0.0, "prey_max": 0,
        "predator_avg": 0.0, "predator_max": 0
      },
      "traits": {
        "prey_energy": {"avg": 45.2, "min": 12.3, "max": 78.9},
        "prey_speed": {"avg": 5.5, "min": 4.1, "max": 7.2},
        "predator_speed": {"avg": 4.0, "min": 3.2, "max": 5.1}
      }
    }
  ],
  "events": [
    [frame, "hunt", pred_id, pred_gen, prey_eaten_count],
    [frame, "birth_prey", child_id, parent_id, generation],
    [frame, "birth_pred", child_id, parent_id, generation],
    [frame, "death_prey", prey_id, generation, age_seconds, energy, children_spawned],
    [frame, "death_pred", pred_id, generation, age_seconds, prey_eaten]
  ]
}
```

## Event Format Details

### Hunt Success
`[frame, "hunt", predator_id, predator_generation, prey_eaten_count]`
- Logged when predator successfully eats prey
- `prey_eaten_count`: Number of prey consumed in this attack

### Birth Events
`[frame, "birth_prey", child_id, parent_id, generation]`
`[frame, "birth_pred", child_id, parent_id, generation]`
`[frame, "birth_prey", child_id, parent_id, generation, mutations]` (if mutations occurred)

**Mutations Object (optional 6th element):**
- `"s": [old_val, new_val]` - Speed mutation (>10% change)
- `"e": [old_val, new_val]` - Max energy mutation (>5% change) 
- `"r": [old_val, new_val]` - Energy regen mutation (>10% change)
- `"t": [old_val, new_val]` - Turn speed mutation (predators, >10% change)
- `"v": [old_rays, new_rays]` - Vision rays mutation (predators)
- `"n": mutation_strength` - Neural network mutation strength (>0.01)

### Death Events
**Prey:** `[frame, "death_prey", prey_id, generation, age_seconds, energy_at_death, children_spawned]`
**Predator:** `[frame, "death_pred", pred_id, generation, age_seconds, total_prey_eaten]`
- Full lifecycle tracking for fitness analysis

## Entity IDs
- Each entity gets unique incrementing ID starting from 1
- IDs persist across generations for lineage tracking
- Parent-child relationships preserved in birth events

## Analysis Capabilities
- **Individual tracking**: Follow specific entities across their lifetime
- **Family trees**: Trace evolutionary lineages with mutation inheritance
- **Selection pressure**: Compare traits of survivors vs deaths
- **Hunting efficiency**: Correlate predator age/generation with hunting success
- **Trait evolution**: Track min/max/avg changes over time
- **Population dynamics**: Birth/death rates, generation turnover
- **Mutation analysis**: 
  - Which mutations lead to better survival rates?
  - Correlation between mutation types and reproductive success
  - Evolution of mutation effectiveness across generations
  - Neural vs physical trait mutation impact

## File Size
Compact array format reduces file size ~60% compared to verbose JSON objects.