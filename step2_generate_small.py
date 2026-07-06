"""
Step 2: Small Grid Chronic Generation (Subgrid Extraction).

This script extracts subgrid chronics from the large grid scenarios generated in Step 1
by calculating power flows at the boundaries.
"""
import logging, argparse, shutil, time
import numpy as np
from pathlib import Path
from typing import List, NamedTuple, Dict, Tuple
import pandas as pd
from tqdm import tqdm
import utils

utils.setup_logging()
logger = logging.getLogger(__name__)

class InternalMap(NamedTuple):
    """Maps a component index from small grid to its counterpart in the large grid."""
    small_idx: int
    large_idx: int

class BoundaryMap(NamedTuple):
    """Maps a virtual load in the small grid to a physical line in the large grid."""
    small_load_idx: int
    large_line_idx: int
    is_origin: bool

class GridMapping(NamedTuple):
    """Container for all discovered mappings between the two grids."""
    loads: List[InternalMap]
    generators: List[InternalMap]
    boundaries: List[BoundaryMap]

def get_mapping(env_large, env_small) -> GridMapping:
    """
    Discovers the topological mapping between large and small grids.
    
    This function analyzes substation connectivity and component names to 
    determine how the small grid fits into the large grid. It identifies 
    which components are identical and which lines in the large grid 
    cross the boundary of the small grid (becoming virtual loads).
    
    Args:
        env_large: The source (large) Grid2Op environment.
        env_small: The target (small) Grid2Op environment.
        
    Returns:
        A GridMapping object containing internal and boundary maps.
        
    Raises:
        ValueError: If the mapping is inconsistent or ambiguous.
    """
    # sub_map: maps small substation ID -> large substation ID
    sub_map: Dict[int, int] = {}
    
    # Lookup tables for large grid component names -> indices
    large_load_indices = {name: i for i, name in enumerate(env_large.name_load)}
    large_gen_indices = {name: i for i, name in enumerate(env_large.name_gen)}
    
    # 1. Map substations using load/gen/line names
    for i, name in enumerate(env_small.name_load):
        if not name.startswith("interco_") and name in large_load_indices:
            sub_map[env_small.load_to_subid[i]] = env_large.load_to_subid[large_load_indices[name]]
            
    for i, name in enumerate(env_small.name_gen):
        if name in large_gen_indices:
            sub_map[env_small.gen_to_subid[i]] = env_large.gen_to_subid[large_gen_indices[name]]
            
    for i, name in enumerate(env_small.name_line):
        parts = name.split('_')
        if len(parts) >= 2 and parts[0].isdigit():
            # Lines are often named after the substations they connect (e.g. "1_2_line")
            sub_map[env_small.line_or_to_subid[i]] = int(parts[0])
            sub_map[env_small.line_ex_to_subid[i]] = int(parts[1])

    # 2. Match internal loads, gens and identify boundary interconnections
    # large_lines: (sub_or, sub_ex) -> line_idx
    large_lines = {(o, e): i for i, (o, e) in enumerate(zip(env_large.line_or_to_subid, env_large.line_ex_to_subid))}
    large_lines.update({(e, o): i for i, (o, e) in enumerate(zip(env_large.line_or_to_subid, env_large.line_ex_to_subid))})

    real_loads: List[InternalMap] = []
    boundaries: List[BoundaryMap] = []
    
    for i, name in enumerate(env_small.name_load):
        if not name.startswith('interco_'):
            real_loads.append(InternalMap(i, large_load_indices[name]))
            continue
        
        # Boundary interconnections (virtual loads)
        # Expected format: interco_<sub1>_<sub2>
        parts = name.split('_') 
        sub_id1, sub_id2 = int(parts[1]), int(parts[2])
        large_line_idx = large_lines.get((sub_id1, sub_id2))
        if large_line_idx is None: 
            raise ValueError(f"Boundary line {sub_id1}-{sub_id2} not found for {name}")
        
        # Determine which endpoint of the large line is inside our subgrid
        small_sub_id = env_small.load_to_subid[i]
        large_sub_id = sub_map.get(small_sub_id)
        
        if large_sub_id is None:
            # Try to infer mapping if one of the line ends is known
            large_sub_id = sub_id1 if sub_id1 in sub_map.values() else sub_id2 if sub_id2 in sub_map.values() else None
            if large_sub_id is None: 
                raise ValueError(f"Ambiguous boundary for {name}: neither {sub_id1} nor {sub_id2} known as internal")
            sub_map[small_sub_id] = large_sub_id
        
        if large_sub_id not in (sub_id1, sub_id2): 
            raise ValueError(f"Inconsistent mapping for {name}: {large_sub_id} not in ({sub_id1}, {sub_id2})")
            
        is_origin = (env_large.line_or_to_subid[large_line_idx] == large_sub_id)
        boundaries.append(BoundaryMap(i, large_line_idx, is_origin))
    
    real_gens = [InternalMap(i, large_gen_indices[name]) for i, name in enumerate(env_small.name_gen) if name in large_gen_indices]
    
    return GridMapping(loads=real_loads, generators=real_gens, boundaries=boundaries)

class PowerFlowRunner:
    """
    Encapsulates Power Flow execution logic on the large grid.
    
    This class handles the synchronization between the high-level Observation 
    objects and the low-level Backend buffers.
    """
    def __init__(self, env_large):
        """Initializes the runner with a large environment."""
        self.env = env_large
        self.obs = env_large.reset()

    def compute_step(self, p_load, q_load, p_gen, v_gen=None):
        """
        Updates the grid state with new values and runs a Power Flow.
        
        Args:
            p_load: Active power for loads.
            q_load: Reactive power for loads.
            p_gen: Active power for generators.
            v_gen: Voltage setpoints for generators (optional).
            
        Returns:
            The backend object after a successful Power Flow run.
        """
        self.obs.load_p[:] = p_load
        self.obs.load_q[:] = q_load
        self.obs.prod_p[:] = p_gen
        if v_gen is not None:
            self.obs.prod_v[:] = v_gen
            
        self.env.backend.update_from_obs(self.obs)
        self.env.backend.runpf()
        return self.env.backend

def process_scenario(scen_path: Path, out_dir: Path, env_large, env_small, mapping: GridMapping):
    """
    Generates small grid chronics for a single scenario.
    
    This function:
    1. Loads large grid data for a scenario.
    2. Performs a fast vectorized copy for internal components.
    3. Runs a simulation loop to calculate boundary flows.
    4. Saves the resulting CSV files for the small grid.
    
    Args:
        scen_path: Path to the source scenario directory.
        out_dir: Directory where the small grid scenario will be saved.
        env_large: Large grid environment.
        env_small: Small grid environment.
        mapping: Pre-calculated mapping between the two grids.
    """
    logger.info(f"Processing scenario: {scen_path.name}")
    start_t = time.time()
    scen_out = out_dir / scen_path.name
    utils.clean_path(scen_out)
    scen_out.mkdir(parents=True)
    
    for suffix in ["", "_forecasted"]:
        load_p_file = scen_path / f"load_p{suffix}.csv.bz2"
        if not load_p_file.exists(): 
            continue
        
        # Load large grid data
        large_lp = pd.read_csv(load_p_file, sep=';')
        large_lq = pd.read_csv(scen_path / f"load_q{suffix}.csv.bz2", sep=';')
        large_pp = pd.read_csv(scen_path / f"prod_p{suffix}.csv.bz2", sep=';')
        
        prod_v_file = scen_path / f"prod_v{suffix}.csv.bz2"
        large_pv = pd.read_csv(prod_v_file, sep=';') if prod_v_file.exists() else None

        # Initialize small grid dataframes
        small_lp = pd.DataFrame(0.0, index=large_lp.index, columns=env_small.name_load)
        small_lq = pd.DataFrame(0.0, index=large_lp.index, columns=env_small.name_load)
        small_pp = pd.DataFrame(0.0, index=large_lp.index, columns=env_small.name_gen)
        
        # 1. Vectorized copy for internal components (Fast)
        small_lp.iloc[:, [m.small_idx for m in mapping.loads]] = large_lp.iloc[:, [m.large_idx for m in mapping.loads]].values
        small_lq.iloc[:, [m.small_idx for m in mapping.loads]] = large_lq.iloc[:, [m.large_idx for m in mapping.loads]].values
        small_pp.iloc[:, [m.small_idx for m in mapping.generators]] = large_pp.iloc[:, [m.large_idx for m in mapping.generators]].values
        
        # 2. Power Flow loop for boundary virtual loads (Slow, but necessary)
        pf_runner = PowerFlowRunner(env_large)
        for t in tqdm(range(len(large_lp)), desc=f"Steps{suffix}", leave=False):
            # Run power flow on large grid for this timestamp
            backend = pf_runner.compute_step(
                p_load=large_lp.iloc[t].values,
                q_load=large_lq.iloc[t].values,
                p_gen=large_pp.iloc[t].values,
                v_gen=large_pv.iloc[t].values if large_pv is not None else None
            )
            
            # Map flows to virtual loads in small grid
            for b in mapping.boundaries:
                small_lp.iloc[t, b.small_load_idx] = backend.p_or[b.large_line_idx] if b.is_origin else backend.p_ex[b.large_line_idx]
                small_lq.iloc[t, b.small_load_idx] = backend.q_or[b.large_line_idx] if b.is_origin else backend.q_ex[b.large_line_idx]
        
        # Save results
        for df, name in [(small_lp, "load_p"), (small_lq, "load_q"), (small_pp, "prod_p")]:
            df.to_csv(scen_out / f"{name}{suffix}.csv.bz2", sep=';', index=False, compression='bz2')

    # 3. Copy scenario-specific metadata (non-CSV files)
    for f in scen_path.glob("*"):
        if f.is_file() and not f.name.endswith((".csv", ".csv.bz2")):
            shutil.copy(f, scen_out / f.name)
    
    # 4. Ensure episode_meta.json exists
    utils.add_episode_meta(scen_out)
    
    end_t = time.time()
    logger.info(f"Scenario {scen_path.name} processed in {end_t - start_t:.2f}s")

def main():
    """
    Main entry point for subgrid extraction.
    
    Loads both environments, calculates the topological mapping, and processes 
    all scenarios discovered in the large grid's chronics folder.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--large_env", type=str, default="ai4realnet_large")
    parser.add_argument("--small_env", type=str, default="ai4realnet_small")
    args = parser.parse_args()

    env_large = utils.make_env(args.large_env)
    env_small = utils.make_env(args.small_env)
    
    # Sync environment-level metadata files (*params*.json)
    for pattern in ["*params*.json"]:
        for f in Path(args.large_env).glob(pattern):
            dest = Path(args.small_env) / f.name
            shutil.copy(f, dest)

    mapping = get_mapping(env_large, env_small)
    out_dir = Path(args.small_env) / "chronics"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    start_total = time.time()
    scenarios = utils.get_scenario_dirs(Path(args.large_env))
    for scen in scenarios:
        process_scenario(scen, out_dir, env_large, env_small, mapping)
    
    end_total = time.time()
    logger.info("Generation complete in %.2fs.", end_total - start_total)

if __name__ == "__main__":
    main()
