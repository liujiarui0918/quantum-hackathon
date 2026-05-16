# MIQP Block Selector Ablation

| instance | selector | objective | gap_percent | runtime_ms | candidate_evaluations |
| --- | --- | ---: | ---: | ---: | ---: |
| miqp_sample_A | default_greedy | 106.094636 | 0.0 | 11428.217 | 49 |
| miqp_sample_A | q_heavy_greedy | 106.094636 | 0.0 | 10932.327 | 49 |
| miqp_sample_A | constraint_heavy_greedy | 106.094636 | 0.0 | 10974.129 | 49 |
| miqp_sample_A | balanced_greedy | 106.094636 | 0.0 | 11199.841 | 49 |
| miqp_sample_A | default_cluster | 106.094636 | 0.0 | 11123.072 | 49 |
| miqp_sample_A | q_heavy_cluster | 106.094636 | 0.0 | 11101.428 | 49 |
| miqp_sample_B | default_greedy | 514.568884 | 15.681302 | 3201.724 | 83 |
| miqp_sample_B | q_heavy_greedy | 493.650779 | 19.109001 | 3184.534 | 75 |
| miqp_sample_B | constraint_heavy_greedy | 517.323331 | 15.229951 | 3110.261 | 83 |
| miqp_sample_B | balanced_greedy | 536.780652 | 12.04162 | 3075.046 | 83 |
| miqp_sample_B | default_cluster | 513.144711 | 15.914671 | 3140.089 | 79 |
| miqp_sample_B | q_heavy_cluster | 519.289895 | 14.907704 | 3163.295 | 84 |
