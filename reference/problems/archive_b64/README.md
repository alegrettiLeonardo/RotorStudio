# DRM problem-script authority archive

The exact user-supplied `DRM_problem_scripts.zip` is stored losslessly as Base64 fragments because the repository connector accepts text files.

- SHA256: `8b5db23fa57bc5e41f68ed9e25ab8f1f1a72e4a24b9e11af38dccdd4098501d1`
- payload: 84 MATLAB files under `rb_prob_solns/`
- book problems: 83 `Problem_*.m`
- helper: `bnpr.m`

Reconstruction is performed by `validation/book_problems/materialize_archive.py`. The script validates the archive SHA256 before extracting and refuses a count other than 83 problem scripts.
