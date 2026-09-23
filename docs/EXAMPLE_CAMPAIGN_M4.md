# Example campaign M4

| MATLAB example | Python entry point | Main exercised path | M4 status |
|---|---|---|---|
| 05_08_01 | `examples/chapter05/example_05_08_01.py` | stationary modal / discretisation | PASS_IMPLEMENTED_SCOPE |
| 05_08_03 | `examples/chapter05/example_05_08_03.py` | disk-shaft interface alternatives | PASS_IMPLEMENTED_SCOPE |
| 05_09_01 | `examples/chapter05/example_05_09_01.py` | isotropic modal | PASS_IMPLEMENTED_SCOPE |
| 05_09_02 | `examples/chapter05/example_05_09_02.py` | anisotropic bearing modal | PASS_IMPLEMENTED_SCOPE |
| 05_09_03 | `examples/chapter05/example_05_09_03.py` | strongly anisotropic / mixed whirl | PASS_IMPLEMENTED_SCOPE |
| 05_09_04 | `examples/chapter05/example_05_09_04.py` | cross-coupled bearing | PASS_IMPLEMENTED_SCOPE |
| 05_09_05 | `examples/chapter05/example_05_09_05.py` | bearing damping | PASS_IMPLEMENTED_SCOPE |
| 05_09_06 | `examples/chapter05/example_05_09_06.py` | fluid-film bearing / eccentricity | PASS_IMPLEMENTED_SCOPE |
| 05_09_07 | `examples/chapter05/example_05_09_07.py` | axial load / follower torque | PASS_IMPLEMENTED_SCOPE |
| 05_09_09 | `examples/chapter05/example_05_09_09.py` | overhung rotor | PASS_IMPLEMENTED_SCOPE |
| 05_09_10 | `examples/chapter05/example_05_09_10.py` | stepped vs tapered shaft | PASS_IMPLEMENTED_SCOPE |
| 06_03_01 | `examples/chapter06/example_06_03_01.py` | synchronous unbalance response | PASS_IMPLEMENTED_SCOPE |
| 06_03_02 | `examples/chapter06/example_06_03_02.py` | bent rotor / equivalent unbalance | PASS_IMPLEMENTED_SCOPE |
| 06_03_03 | `examples/chapter06/example_06_03_03.py` | `freq_aux` spinner/vibrator | PASS_IMPLEMENTED_SCOPE |
| 06_05_01 | `examples/chapter06/example_06_05_01.py` | `freq_fdn`; transient branch | PARTIAL — frequency PASS, transient BLOCKED_PHASE8 |
| 06_06_01 | `examples/chapter06/example_06_06_01.py` | coaxial modal + response | PASS_IMPLEMENTED_SCOPE |
| 06_08_01 | `examples/chapter06/example_06_08_01.py` | direct/iterative critical speeds | PASS_IMPLEMENTED_SCOPE |
| 06_10_01 | `examples/chapter06/example_06_10_01.py` | critical-speed map / mode shapes | PASS_IMPLEMENTED_SCOPE |
| 06_11_01 | `examples/chapter06/example_06_11_01.py` | stationary precheck + runup | PARTIAL — modal PASS, runup BLOCKED_PHASE8 |
| 07_06_01 | `examples/chapter07/example_07_06_01.py` | asymmetric modal + response | PASS_IMPLEMENTED_SCOPE |
| 07_07_01 | `examples/chapter07/example_07_07_01.py` | internal shaft damping stability | PASS_IMPLEMENTED_SCOPE |
| 07_09_01 | `examples/chapter07/example_07_09_01.py` | bearing cross coupling / stability | PASS_IMPLEMENTED_SCOPE |

The deterministic campaign entry point is `scripts/run_example_campaign.py`. It removes MATLAB menu dependence and records `campaign_status.csv` plus `campaign_summary.json`.

Campaign totals: **32 runs, 30 pass, 2 Phase-8 blocks, 0 fail, 22 unique examples**.
