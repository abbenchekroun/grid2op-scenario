# AI4RealNet Chronics Generation Workflow

This project provides a workflow to generate chronics for both the `ai4realnet_large` and `ai4realnet_small` environments.

## 🚀 Quick Start

The process is divided into two main steps:

### Step 1: Generate Large Grid Chronics
Generate realistic power grid scenarios for the large environment (118 substations) using `chronix2grid`.
```bash
python3 step1_generate_large.py --weeks 1 --scenarios 1 --start_date 2035-01-01
```
*This will create scenarios in `ai4realnet_large/chronics/`.*

### Step 2: Derive Small Grid Chronics
Extract the subgrid data for the small environment (36 substations). This script simulates the large grid and calculates boundary flows to populate interconnection loads setpoints.
```bash
python3 step2_generate_small.py
```
*This automatically populates `ai4realnet_small/chronics/`.*

---

## 📦 Requirements

To ensure you have exactly the right versions and a clean environment, use the provided `pyproject.toml` and `uv` (a fast Python package manager).

### Installation with `uv`
```bash
# 1. Install uv if you don't have it (see https://github.com/astral-sh/uv)
# 2. Sync the environment (creates .venv and installs dependencies)
uv sync

# 3. Activate the environment
source .venv/bin/activate
```

---

## 📖 Documentation

### Technical Mapping
The derivation from large to small grid uses a mapping methodology where boundary lines are converted into "virtual loads".

👉 **Read [METHODOLOGY.md](METHODOLOGY.md) for full technical details.**

### Environment Descriptions
- **ai4realnet_large**: 118 substations (based on L2RPN IDF 2023).
- **ai4realnet_small**: 36 substations (subgrid of **ai4realnet_large**).

*Note that the **ai4realnet_small** environment was previously based on **l2rpn_icaps_2021**. Both environments are now based on **l2rpn_idf_2023** (see https://grid2op.readthedocs.io/en/latest/available_envs.html for more details).*
