# MIQP Baseline Study

| instance | method | family | objective | official | gap_percent | feasible | runtime_ms | search_bits | qaoa_qubits | candidates_evaluated |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| miqp_sample_A | zero_x_lp | classical_baseline | 7.275696 | 106.094636 | 93.142258 | True | 1437.001 | 0 | 0 | 1 |
| miqp_sample_A | marginal_greedy_lp | classical_baseline | 97.720843 | 106.094636 | 7.892758 | True | 22.603 | 15 | 0 | 15 |
| miqp_sample_A | structural_warm_start_lp | learning_guided_baseline | 97.720843 | 106.094636 | 7.892758 | True | 15.312 | 15 | 0 | 1 |
| miqp_sample_A | random_repair_lp | classical_stochastic | 105.090577 | 106.094636 | 0.946381 | True | 241.071 | 15 | 0 | 96 |
| miqp_sample_A | genetic_repair_lp | classical_metaheuristic | 106.094636 | 106.094636 | 0.0 | True | 201.509 | 15 | 0 | 61 |
| miqp_sample_A | binary_pso_repair_lp | classical_metaheuristic | 106.094636 | 106.094636 | 0.0 | True | 449.57 | 15 | 0 | 148 |
| miqp_sample_A | exact_binary_lp | classical_exact | 106.094636 | 106.094636 | 0.0 | True | 3580.598 | 15 | 0 | 1152 |
| miqp_sample_A | global_binary_sa_lp | classical_annealing | 105.090577 | 106.094636 | 0.946381 | True | 3155.469 | 16 | 0 | 9 |
| miqp_sample_A | global_learning_guided_lp | learning_guided_baseline | 98.547928 | 106.094636 | 7.113185 | True | 44.835 | 16 | 0 | 3 |
| miqp_sample_A | block_sa_lp | classical_annealing | 105.090577 | 106.094636 | 0.946381 | True | 1202.661 | 11 | 0 | 8 |
| miqp_sample_A | block_learning_guided_lp | learning_guided_baseline | 98.547928 | 106.094636 | 7.113185 | True | 26.718 | 11 | 0 | 3 |
| miqp_sample_A | block_qaoa_lp | quantum_model | 105.090577 | 106.094636 | 0.946381 | True | 4796.089 | 10 | 10 | 137 |
| miqp_sample_A | miqp_aware_route7 | proposed_hybrid_quantum | 106.094636 | 106.094636 | 0.0 | True | 2087.065 | 12 | 0 | 1152 |
| miqp_sample_A | official_reference | reference | 106.094636 | 106.094636 | 0.0 | True | 0.0 | 0 | 0 | 0 |
| miqp_sample_B | zero_x_lp | classical_baseline | 1.30021 | 610.266639 | 99.786944 | True | 5.715 | 0 | 0 | 1 |
| miqp_sample_B | marginal_greedy_lp | classical_baseline | 544.475466 | 610.266639 | 10.780726 | True | 184.183 | 80 | 0 | 80 |
| miqp_sample_B | structural_warm_start_lp | learning_guided_baseline | 472.797422 | 610.266639 | 22.526091 | True | 302.724 | 80 | 0 | 1 |
| miqp_sample_B | random_repair_lp | classical_stochastic | 381.824684 | 610.266639 | 37.433138 | True | 481.908 | 80 | 0 | 96 |
| miqp_sample_B | genetic_repair_lp | classical_metaheuristic | 565.761894 | 610.266639 | 7.292672 | True | 1126.462 | 80 | 0 | 146 |
| miqp_sample_B | binary_pso_repair_lp | classical_metaheuristic | 544.475466 | 610.266639 | 10.780726 | True | 1479.704 | 80 | 0 | 192 |
| miqp_sample_B | exact_binary_lp | classical_exact | None | 610.266639 | None | False | 0.0 | 80 | 0 | 0 |
| miqp_sample_B | global_binary_sa_lp | classical_annealing | None | 610.266639 | None | False | 0.0 | 80 | 0 | 0 |
| miqp_sample_B | global_learning_guided_lp | learning_guided_baseline | None | 610.266639 | None | False | 0.0 | 80 | 0 | 0 |
| miqp_sample_B | block_sa_lp | classical_annealing | 492.115433 | 610.266639 | 19.360587 | True | 7955.0 | 26 | 0 | 44 |
| miqp_sample_B | block_learning_guided_lp | learning_guided_baseline | 454.884678 | 610.266639 | 25.461323 | True | 169.3 | 26 | 0 | 6 |
| miqp_sample_B | block_qaoa_lp | quantum_model | 488.070768 | 610.266639 | 20.023357 | True | 5109.62 | 10 | 10 | 146 |
| miqp_sample_B | miqp_aware_route7 | proposed_hybrid_quantum | 577.780995 | 610.266639 | 5.323189 | True | 118030.386 | 20 | 0 | 436 |
| miqp_sample_B | official_reference | reference | 610.266639 | 610.266639 | 0.0 | True | 0.0 | 0 | 0 | 0 |

Gap is `(official - objective) / abs(official) * 100` because the task is maximization.
Peak memory is Python heap measured by `tracemalloc`, so native LP/BLAS memory is not fully counted.
