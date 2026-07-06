"""
Utility functions for the Grid2Op scenario generation pipeline.

This module provides shared helpers for environment creation, logging setup, 
file system management, and scenario discovery.
"""
import logging
import shutil
import sys
import json
from pathlib import Path
from enum import Enum
import functools

import grid2op
import pandas as pd
import numpy as np
from lightsim2grid import LightSimBackend

def setup_logging(level=logging.INFO):
    """
    Configures standard logging for all scripts in the pipeline.
    
    Args:
        level: The logging level (default: logging.INFO).
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def clean_path(path: Path):
    """
    Safely removes a file or directory if it exists.
    
    If the path is a directory, it is removed recursively.
    
    Args:
        path: Pathlib object to be removed.
    """
    if path.exists():
        logging.info(f"Removing existing: {path}")
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

def make_env(env_path, backend_class=LightSimBackend):
    """
    Creates a Grid2Op environment with a specific backend.
    
    By default, it uses LightSimBackend for fast power flow calculations.
    
    Args:
        env_path: Path to the environment directory.
        backend_class: The Grid2Op Backend class to use.
        
    Returns:
        The initialized Grid2Op environment.
    """
    return grid2op.make(str(env_path), backend=backend_class())

def get_scenario_dirs(env_path: Path):
    """
    Lists scenario directories within an environment's chronics folder.
    
    Args:
        env_path: Path to the root directory of the environment.
        
    Returns:
        Sorted list of Path objects pointing to scenario directories.
    """
    chronics_path = Path(env_path) / "chronics"
    if not chronics_path.exists():
        return []
    
    all_dirs = sorted([d for d in chronics_path.iterdir() if d.is_dir()])
    scenarios = [d for d in all_dirs if d.name != "chronic_example"]
    
    if not scenarios and any(d.name == "chronic_example" for d in all_dirs):
        scenarios = [d for d in all_dirs if d.name == "chronic_example"]
    
    return scenarios

def add_episode_meta(scen_dir: Path):
    """
    Adds an episode_meta.json file to the scenario directory.
    This is required by some Grid2Op utilities (like scoring).
    
    Args:
        scen_dir: Path to the scenario directory.
    """
    load_p_path = scen_dir / "load_p.csv.bz2"
    if not load_p_path.exists():
        # Fallback to .csv if .csv.bz2 is missing
        load_p_path = scen_dir / "load_p.csv"
        
    if load_p_path.exists():
        # We only need the length. Reading the whole file is fine for these small chronics.
        df = pd.read_csv(load_p_path, sep=';')
        length = len(df)
        meta_path = scen_dir / "episode_meta.json"
        with open(meta_path, "w") as f:
            json.dump({"length": int(length)}, f)
        logging.info(f"Created {meta_path} (length: {length})")
    else:
        logging.warning(f"Could not find load_p.csv.bz2 or load_p.csv in {scen_dir}. episode_meta.json not created.")
