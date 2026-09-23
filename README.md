# RotorStudio — Stage 1 M2

Continuação do baseline M1 da migração do Rotor Software MATLAB para **Fortran 2018 + Python Core**, sem reiniciar a implementação e sem UI desktop.

## Escopo implementado neste incremento

- `taper.m` → eixo cônico, tipos 21–28;
- `shftasym.m` → elemento de eixo assimétrico, tipos 11–18, preservando/gateando defeitos legados em vez de corrigi-los silenciosamente;
- `bearmtx.m` → tipos 1–8 e comportamento legado do tipo 20 no assembly estacionário;
- assembly estacionário M/C/G/K;
- `freq_rsp.m` → resposta harmônica síncrona;
- `crit_spd.m` → método direto e dois caminhos iterativos;
- ABI `ctypes -> ISO_C_BINDING -> Fortran -> BLAS/LAPACK`;
- Python Core tipado, validation, result objects, AnalysisService, CLI e pós-processamento headless;
- 3 exemplos traduzidos/executados como smoke: 05.08.01, 06.03.01 e 06.08.01.

## Estado de qualificação

A implementação interna foi compilada e testada em Linux:

- Fortran Release: 6/6 CTest PASS;
- Fortran Debug: 6/6 CTest PASS;
- Python: 11 pytest PASS;
- clean package test: PASS;
- Linux execution: PASS;
- Python↔Fortran ABI: PASS.

**MATLAB/Octave não está disponível no ambiente de execução. Por isso, toda equivalência MATLAB↔Fortran permanece BLOCKED.** Nenhum teste interno foi promovido para equivalência MATLAB.

Consulte `STAGE1_M2_STATUS.md`.

## Fonte exata do incremento

Por limitação do conector de upload binário, o snapshot de fontes foi preservado em partes binárias Git. Reconstrua com:

```bash
chmod +x artifacts/reconstruct_stage1_m2_source.sh
./artifacts/reconstruct_stage1_m2_source.sh
tar -xzf artifacts/RotorStudio_Stage1_M2_source.tar.gz
```

SHA256 esperado:

```text
03b68d3cea9555665ab26eb6f3b2c895d3df7970a3a350419ee3aa12ced34c1d  RotorStudio_Stage1_M2_source.tar.gz
```

O ZIP de qualificação completo (com referências locais não publicadas neste repositório) possui SHA256:

```text
8f7454e0dc8ce01366abfcf7014f96d1cf6d1d945492b9c9c666d57f1113c2b7  DRM_Fortran_Python_Stage1_20260923_M2.zip
```
