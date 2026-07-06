"""
Step 1: Large Grid Chronic Generation.

This script uses `chronix2grid` to generate realistic load and production chronics 
for the large Grid2Op environment.
"""
import datetime
import logging
import warnings
import argparse
import time
from pathlib import Path
from numpy.random import default_rng

import utils

# Configure logging
utils.setup_logging()
logger = logging.getLogger(__name__)

def apply_solver_patch():
    """
    Patches chronix2grid to ensure it respects the 'solver_name' from params_opf.json.
    By default, chronix2grid may ignore this setting and try to use 'glpk', 
    which might not be installed.
    """
    try:
        from chronix2grid.generation._dispatch._PypsaDispatchBackend.PypsaEconomicDispatch import PypsaDispatcher
        original_run = PypsaDispatcher.run

        def patched_run(self, load, total_solar, total_wind, params, **kwargs):
            # Force the solver specified in the opf_params if not already set in kwargs
            if "solver_name" in params and "solver_name" not in kwargs:
                kwargs["solver_name"] = params["solver_name"]
            return original_run(self, load, total_solar, total_wind, params, **kwargs)

        PypsaDispatcher.run = patched_run
        logger.info("Applied chronix2grid solver compatibility patch (using solver from params).")
    except ImportError:
        logger.warning("Could not import chronix2grid to apply solver patch.")

# -----------------------------------

warnings.filterwarnings("ignore", category=FutureWarning)


def run_chronix2grid(
    env_path: Path,
    chronics_path: Path,
    nb_weeks: int,
    nb_scenarios: int,
    start_date_str: str,
    weeks_per_chunk: int = 1,
    dt: int = 5,
) -> None:
    """
    Generate chronics using chronix2grid.
    
    Args:
        env_path: Path to the Grid2Op environment.
        chronics_path: Directory where chronics will be saved.
        nb_weeks: Total number of weeks to generate.
        nb_scenarios: Number of scenarios per week chunk.
        start_date_str: Initial date in YYYY-MM-DD format.
        weeks_per_chunk: Number of weeks per generated chunk.
        dt: Time step in minutes.
    """
    logger.info("Loading environment from %s", env_path)
    env = utils.make_env(env_path)

    nb_steps = int(weeks_per_chunk * 7 * 24 * 60 / dt)
    master_seed = 42
    prng = default_rng(master_seed)

    # Late import of chronix2grid
    from chronix2grid.grid2op_utils.utils import generate_a_scenario

    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
    
    num_chunks = int(nb_weeks / weeks_per_chunk)
    for chunk in range(num_chunks):
        current_start = start_date + datetime.timedelta(weeks=chunk * weeks_per_chunk)
        start_str = current_start.strftime("%Y-%m-%d")

        for scenario_idx in range(nb_scenarios):
            scen_name = f"{start_str}_{scenario_idx}"
            logger.info("Generating scenario %s", scen_name)
            
            # Ensure a clean start by removing existing scenario directory
            utils.clean_path(chronics_path / scen_name)

            load_seed, renew_seed, gen_p_forecast_seed = prng.integers(2**32 - 1, size=3)

            start_t = time.time()
            error_, quality_, _, _, _, _, _, _ = generate_a_scenario(
                path_env=str(env_path),
                name_gen=env.name_gen,
                gen_type=env.gen_type,
                output_dir=str(chronics_path),
                start_date=start_str,
                dt=dt,
                scen_id=str(scenario_idx),
                load_seed=int(load_seed),
                renew_seed=int(renew_seed),
                gen_p_forecast_seed=int(gen_p_forecast_seed),
                handle_loss=True,
                nb_steps=nb_steps,
            )
            end_t = time.time()

            if error_ is not None:
                logger.error("Scenario %s_%d failed in %.2fs: %s", start_str, scenario_idx, end_t - start_t, error_)
            else:
                logger.info("Scenario %s_%d completed in %.2fs. Quality: %s", start_str, scenario_idx, end_t - start_t, quality_)
                utils.add_episode_meta(chronics_path / scen_name)


def main():
    """
    Main entry point for large grid chronic generation.
    
    Parses CLI arguments and initiates the `chronix2grid` generation process.
    """
    parser = argparse.ArgumentParser(description="Generate large grid chronics using chronix2grid.")
    parser.add_argument("--env", type=str, default="ai4realnet_large", help="Path to the large environment.")
    parser.add_argument("--start_date", type=str, default="2035-01-01", help="Start date (YYYY-MM-DD).")
    parser.add_argument("--weeks", type=int, default=1, help="Number of weeks to generate.")
    parser.add_argument("--scenarios", type=int, default=1, help="Number of scenarios.")
    args = parser.parse_args()

    apply_solver_patch()

    env_path = Path(args.env)
    chronics_path = env_path / "chronics"
    chronics_path.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("Starting chronix2grid generation on %s", env_path)
    logger.info("=" * 60)
    
    start_total = time.time()
    run_chronix2grid(
        env_path=env_path,
        chronics_path=chronics_path,
        nb_weeks=args.weeks,
        nb_scenarios=args.scenarios,
        start_date_str=args.start_date,
    )
    end_total = time.time()
    logger.info("Generation process finished in %.2fs.", end_total - start_total)


if __name__ == "__main__":
    main()
