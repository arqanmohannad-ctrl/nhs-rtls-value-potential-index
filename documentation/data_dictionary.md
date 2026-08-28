# RVPI analytical data dictionary

| Field | Construction | Direction |
|---|---|---|
| `bed_occupancy_pressure` | occupied beds / available beds | higher pressure |
| `ae_delay_burden` | 1 − attendances within four hours / attendances | higher burden |
| `emergency_admissions_intensity` | emergency admissions / available beds | higher intensity |
| `waiting_list_burden` | incomplete RTT pathways over 18 weeks / total incomplete pathways | higher burden |
| `estates_burden` | backlog maintenance cost / occupied floor area (m²) | higher burden |
| `resource_capacity_strain` | A&E attendances / available beds | higher strain |
| `rvpi_z` | unweighted mean of available component z-scores; minimum 4 of 6 | higher potential value |
| `rvpi_percentile` | empirical percentile rank of `rvpi_z` | 100 = highest |
| `provider_type_source` | exact ERIC `Trust Type` | classification source |
| `provider_group` | deterministic mapping of ERIC type; literal name fallback only if type absent | sample stratification |
| `is_acute_general` | ERIC acute large/medium/multi-service/small/teaching | primary type criterion |
| `primary_acute_eligible` | acute general, beds > 0, A&E > 0, and ≥4 components | primary inclusion |
| `raw_components_available` | count of non-missing raw components before standardisation | 0–6 |
| `rvpi_standardisation_sample` | `primary_acute_trusts` or `full_provider_sensitivity` | identifies score reference population |

Denominators must be positive. Infinite ratios are converted to missing. Z-scores use the population standard deviation (`ddof=0`) within the named analysis sample. Equal weights are the baseline because evidence does not justify differential weights. Primary and full-provider scores are not numerically interchangeable because their reference populations differ. Sensitivity analysis should also vary weights, inclusion thresholds, time windows, winsorisation, and standardisation method.

RVPI is a descriptive prioritisation index. It does not identify causal RTLS effects, implementation feasibility, achievable savings, or return on investment.
