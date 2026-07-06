# Technical Mapping Methodology: From Large to Small Grid

This document explains how the chronics for `ai4realnet_small` are derived from the `ai4realnet_large` environment.

## 1. Overview
The `ai4realnet_small` grid (36 substations) is a physical subgrid of the `ai4realnet_large` grid (118 substations). To ensure that the scenarios in the small grid are physically realistic, they are extracted from full-grid simulations of the large grid.

| Feature | ai4realnet_large | ai4realnet_small |
| :--- | :--- | :--- |
| **Substations** | 118 | 36 |
| **Total Loads** | 99 | 37 (29 Real + 8 Virtual) |
| **Generators** | 62 | 22 |
| **Lines/Trafos** | 186 | 59 |

## 2. Methodology

The generation process follows these steps for every timestamp (real and forecasted):

1.  **Full Grid Simulation**: We load the `ai4realnet_large` environment and set its loads and generation to the values specified in the original large chronics.
2.  **Power Flow (PF)**: We run a Power Flow using `lightsim2grid` to calculate all branch flows and bus voltages in the large grid.
3.  **Data Extraction**:
    -   **Real Loads**: Values for the 29 loads internal to the subgrid are copied directly.
    -   **Generators**: Values for the 22 generators internal to the subgrid are copied directly.
    -   **Boundary Flows**: For lines that cross the subgrid boundary, we extract the power flow at the "internal" end of the line.
4.  **Aggregation (Virtual Loads)**: These boundary flows are converted into virtual loads in the small grid, named `interco_<sub_A>_<sub_B>`.

### Sign Convention for Boundaries
In `grid2op`, a **Load** is positive when power is **consumed** (leaves the bus).
-   If power flows **OUT** of the small subgrid into the large grid: `interco` load is **positive**.
-   If power flows **INTO** the small subgrid from the large grid: `interco` load is **negative**.

## 3. Detailed Mapping Tables

### 3.1 Boundary Aggregation (Virtual Loads)
These 8 connections represent the physical "cut" made to isolate the small subgrid.

| Small Virtual Load | Large Connection (Line/Trafo) | Connection Point (Small Sub) | Direction for Positive Load |
| :--- | :--- | :--- | :--- |
| `interco_14_32` | Line 14_32_108 | Sub 32 | From 32 to 14 |
| `interco_18_33` | Line 18_33_109 | Sub 33 | From 33 to 18 |
| `interco_29_37` | Line 29_37_117 | Sub 37 | From 37 to 29 |
| `interco_64_67` | Line 64_67_183 | Sub 64 | From 64 to 67 |
| `interco_68_74` | Line 68_74_9 | Sub 68 | From 68 to 74 |
| `interco_68_76` | Line 68_76_12 | Sub 68 | From 68 to 76 |
| `interco_68_69` | Line 68_69_171 | Sub 68 | From 68 to 69 |
| `interco_67_68` | Line 67_68_184 | Sub 68 | From 68 to 67 |

### 3.2 Real Loads Mapping (Direct)
The following 29 loads are mapped 1-to-1 by name between the environments:
`load_32_26`, `load_33_27`, `load_34_28`, `load_35_29`, `load_38_30`, `load_39_31`, `load_40_32`, `load_41_33`, `load_42_34`, `load_43_35`, `load_44_36`, `load_45_37`, `load_46_38`, `load_47_39`, `load_48_40`, `load_49_41`, `load_50_42`, `load_51_43`, `load_52_44`, `load_53_45`, `load_54_46`, `load_55_47`, `load_56_48`, `load_57_49`, `load_58_50`, `load_59_51`, `load_61_52`, `load_65_53`, `load_66_54`.

### 3.3 Generators Mapping (Direct)
The following 22 generators are mapped 1-to-1 by name:
`gen_33_16`, `gen_39_17`, `gen_41_18`, `gen_41_19`, `gen_45_20`, `gen_48_21`, `gen_48_22`, `gen_48_23`, `gen_48_24`, `gen_53_25`, `gen_54_26`, `gen_55_27`, `gen_55_28`, `gen_55_29`, `gen_58_30`, `gen_59_31`, `gen_60_32`, `gen_61_33`, `gen_61_34`, `gen_64_35`, `gen_65_36`, `gen_68_37`.

## 4. Examples

The following examples use real values extracted from the `2035-01-15_0` scenario to demonstrate how boundary flows are converted into virtual loads.

### Example A: Power Entering the Subgrid (`interco_14_32`)
1.  **Topology**: Substation **32** is in the small grid; Substation **14** is outside. They are connected by Line `14_32_108`.
2.  **Simulation Result**: In the full-grid simulation, the Power Flow shows **7.11 MW** flowing from Sub 14 to Sub 32.
3.  **Aggregation**:
    -   Since power is entering the small subgrid, it acts as a "negative consumption".
    -   In `ai4realnet_small` chronics, `interco_14_32` is set to **-7.11 MW**.

### Example B: Power Leaving the Subgrid (`interco_64_67`)
1.  **Topology**: Substation **64** is in the small grid; Substation **67** is outside. They are connected by Line `64_67_183`.
2.  **Simulation Result**: The Power Flow shows **344.69 MW** flowing from Sub 64 to Sub 67.
3.  **Aggregation**:
    -   Since power is leaving the small subgrid, it acts as a "positive consumption".
    -   In `ai4realnet_small` chronics, `interco_64_67` is set to **+344.69 MW**.

## 5. Workflow Implementation

The main generation workflow is implemented in three main scripts:
- **`step1_generate_large.py`**: Handles the generation of full-grid scenarios for `ai4realnet_large`.
- **`step2_generate_small.py`**: Implements the mapping logic to derive `ai4realnet_small` chronics. It uses `lightsim2grid` for power flow simulations to ensure boundary consistency.
