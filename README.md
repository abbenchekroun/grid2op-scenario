# grid2op-scenario

This repo contains scenario data corresponding to the different grid2op environments used in the project.

## ai4realnet_small

Corresponds to the basic environment (**36 substations**) from open sourced RTE interactiveAI use case will be reused (see predefined "l2rpn_icaps_2021" environment). 

More details about this environment can be found in [Grid2Op documentation](https://grid2op.readthedocs.io/en/latest/available_envs.html#l2rpn-idf-2023).

## ai4realnet_small_sim2real

This environment will use the same data as for the ai4realnet_small environment but will alter observations as seen by the agent: default approach is to use *NoisyObservation* class from Grid2op.

Other approaches will be tested during the project through dedicated agent developed by Task 4.2: Random perturbation agent, Gradient estimation perturbation agent, RL-based perturbation agent. It is also possible to consider that different backends can be used:

+ a “light” backend, such as LightSim2Grid, can be used for training,
+ a more “precise” backend (thus more representative of reality), such as PyPowsybl, can be used for evaluation. 

## ai4realnet_large

This more advanced environment (**118 substations**) corresponds to L2RPN competition organized by RTE in 2023 ("l2rpn_idf_2023"). 

More details about this environment can be found in [Grid2Op documentation](https://grid2op.readthedocs.io/en/latest/available_envs.html#l2rpn-idf-2023). 

## ai4realnet_large_sim2real

This environment will use the same data as for the ai4realnet_large environment but will alter observations as seen by the agent. Default approach is to use NoisyObservation class.
