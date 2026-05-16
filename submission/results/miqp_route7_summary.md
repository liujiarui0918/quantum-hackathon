# MIQP Route 7 Result Summary

| Instance | Size | Objective | Official | Gap | Feasible | Best seed | Runtime ms | Mode | Evaluations |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| miqp_sample_A | n=15, p=5, m1=5, m2=1 | 106.094636 | 106.094636 | 0.00% | True | 7 | 2087.065 | exact_binary_plus_continuous_lp | 1152 |
| miqp_sample_B | n=80, p=20, m1=20, m2=4 | 610.266639 | 610.266639 | 0.00% | True | 11 | 83644.468 | miqp_aware_block_heuristic | 768 |

The gap is computed as `(official - objective) / abs(official)` for this maximization problem.
