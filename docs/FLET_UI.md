# RotorStudio — interface Flet

Esta implementação acrescenta `drm_flet` à base `03fef9b0da65c51b7ea3c9a14911cf7f83bcb015`.
As quatro imagens conceituais são a referência de apresentação: editor do rotor,
Campbell, desempenho dos mancais e modos 3D em tema escuro. Os controles são
Flet/Flutter reais, não páginas HTML ou imagens clicáveis da aplicação inteira.

O comando Qt `drm-studio` continua disponível e inalterado. O novo comando é
`drm-studio-flet`. Nenhum arquivo de `drm_core`, `drm_studio` ou `fortran` é
modificado por esta entrega.

## Instalação — Ubuntu 24.04 / WSL com ambiente gráfico

Execute na raiz do repositório que contém esta implementação:

```bash
sudo apt-get update
sudo apt-get install -y gfortran cmake libblas-dev liblapack-dev \
  libgtk-3-0 libsecret-1-0 libgles2 libegl1 libgl1 zenity
python3 -m venv .venv-flet
source .venv-flet/bin/activate
python -m pip install -e './python[flet,test]'
cmake -S fortran -B build-flet -DCMAKE_BUILD_TYPE=Release
cmake --build build-flet -j2
drm-studio-flet --check
drm-studio-flet
```

A versão fixada é Flet **1.0.0**. O cliente desktop oficial pode ser baixado pelo
Flet na primeira execução. Não há cliente Flutter, fonte tipográfica ou DLL
redistribuído no pacote de alterações. No WSL é necessário um ambiente gráfico
funcional (por exemplo WSLg). `zenity` é usado pelos seletores de arquivos no Linux.

A descoberta procura apenas `build-release`, `build-flet`, `build` e suas
subpastas `Release`, na raiz do projeto ou no diretório corrente. Caminhos
explícitos têm prioridade e não são substituídos silenciosamente:

```bash
drm-studio-flet --library /caminho/libdrmrotor.so --project projeto.json
# Alternativamente:
export DRMROTOR_LIB="$PWD/build-flet/libdrmrotor.so"
export DRMBEARINGS_LIB="$PWD/build-flet/libdrmbearings.so"
drm-studio-flet --dark
```

`--check` verifica carregamento da biblioteca, não constitui qualificação
numérica. Sem biblioteca, é possível editar, mas não obter resultados calculados.

## Windows — código-fonte

Use Python 3.12+ e o toolchain UCRT64 já empregado pelo projeto. No terminal
MSYS2 UCRT64, instale `mingw-w64-ucrt-x86_64-gcc-fortran`,
`mingw-w64-ucrt-x86_64-cmake`, `mingw-w64-ucrt-x86_64-ninja` e
`mingw-w64-ucrt-x86_64-openblas`, e compile:

```bash
cmake -S fortran -B build-flet -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_Fortran_COMPILER=/ucrt64/bin/gfortran.exe \
  -DCMAKE_PREFIX_PATH=/ucrt64 -DBLA_VENDOR=OpenBLAS
cmake --build build-flet --parallel 2
```

No PowerShell, na raiz do repositório:

```powershell
py -3.12 -m venv .venv-flet
.\.venv-flet\Scripts\python.exe -m pip install -e './python[flet,test]'
$env:DRMROTOR_LIB = (Get-ChildItem build-flet -Recurse -Filter '*drmrotor*.dll' | Select-Object -First 1).FullName
$env:DRMBEARINGS_LIB = (Get-ChildItem build-flet -Recurse -Filter '*drmbearings*.dll' | Select-Object -First 1).FullName
$env:DRMROTOR_DLL_DIRS = 'C:\msys64\ucrt64\bin'
$env:DRMBEARINGS_DLL_DIRS = $env:DRMROTOR_DLL_DIRS
$env:PATH = "$env:DRMROTOR_DLL_DIRS;$env:PATH"
.\.venv-flet\Scripts\drm-studio-flet.exe --check
.\.venv-flet\Scripts\drm-studio-flet.exe
```

Ajuste apenas o caminho da instalação MSYS2, quando diferente. Esta entrega não
é um instalador Windows nem declara qualificação de executáveis congelados.

## O que está conectado

| Área | Implementação |
|---|---|
| Editor do rotor | Geometria e dimensões obtidas do `RotorModel`, seleção sincronizada entre desenho/árvore/tabela, zoom/deslocamento, propriedades com unidades, inclusão/remoção, validação transacional, desfazer/refazer. |
| Campbell | `AnalysisService` real, pontos calculados selecionáveis, tabela modal, fn e fd separados, linhas 1×/2×, classificação de precessão baseada em kappa, tracking somente quando fornecido pelo Core. |
| Mancais | Escolha do apoio, avaliação nativa K/C/M, tabela e curvas por rotação, importação/edição CSV K/C sem alterar os sinais cruzados. |
| Modos 3D | Autovetor complexo real do resultado, interpolação de visualização já existente no Core, fase, amplitude normalizada, câmera, referência e órbitas; animação visual, não solução transiente. |
| Projetos/resultados | JSON nativo do Core, importação conservadora iRdin, casos nomeados, hashes e estado desatualizado, exportação PNG/CSV/NPZ e relatório ZIP. |
| Execução | Thread de trabalho serializada inclusive entre sessões, progresso informado pelo Core, cancelamento cooperativo e mensagens de falha; nenhuma substituição por resultado fictício. |

As formas gráficas do rotor são SVG gerado da geometria atual, não fotografias dos
mockups. Os gráficos científicos são renderizações Matplotlib de resultados
reais exibidas em controles Flet. A visualização 3D tem câmera por controles;
não é um viewport CAD/OpenGL com seleção de faces.

### Uso

Abra o rotor de exemplo ou um projeto existente. O exemplo contém **entradas
sintéticas explicitamente identificadas**, não medições de uma máquina e não os
resultados ilustrativos dos mockups. Só aparecem resultados após execução real.

Clique em um elemento, altere as propriedades e use **Aplicar**. A coluna de
comprimento vem dos nós; sua edição é feita nas posições dos nós. Entradas
inválidas mantêm o modelo anterior. As tabelas têm cabeçalho fixo e paginação,
com a seleção trazida à página correspondente, sem chamadas de rolagem tardias
a controles já fechados. `Ctrl+Z` e `Ctrl+Y` restauram os snapshots.

Use **Executar análise** para configurar modal, Campbell, velocidades críticas,
resposta síncrona ou estática. Cada caso é persistido; os itens de casos na árvore
permitem executar novamente. Outros casos existentes podem ser chamados pelo
editor de parâmetros JSON com os nomes e unidades da API do Core.

Em **Mancais**, selecione o apoio e use **Calcular**. As curvas percorrem 25
pontos do intervalo da tabela, ou 300–6000 rpm para apoios sem intervalo tabulado.
O ponto selecionado mostra K/C/M radial. O símbolo do apoio é esquemático: não
representa folga ou filme calculado. A edição CSV aceita:

```text
rpm;kxx;kxy;kyx;kyy;cxx;cxy;cyx;cyy
0;10000000;0;0;9000000;1500;0;0;1800
6000;14800000;0;0;13000000;1740;0;0;2040
```

K em N/m e C em N·s/m; separador `;`; decimal com ponto ou vírgula. Massas
adicionadas existentes são preservadas; a mudança de eixo é rejeitada quando
invalidaria uma massa dependente da rotação. Tabelas 2D rotação/frequência e outras
famílias usam o editor tipado, não são convertidas silenciosamente para 1D.

## Limites e rastreabilidade

- Esta é a implementação das quatro áreas dos mockups, **não a migração integral
  de todas as telas especializadas Qt**. Editores avançados estruturais preservam
  os campos Core, mas não replicam todos os formulários especializados Qt.
- Não são acrescentadas físicas, critérios normativos, dados de pressão ou
  temperatura artificiais. Recursos incompatíveis são bloqueados pelo Core ou
  pelo preflight explícito. A análise estática, por exemplo, conserva as
  restrições atuais do Core e não aproxima mancais avançados como apoios clássicos.
- A ABI nativa baseada em posições exige nós consecutivos `1..N` na ordem da
  lista. Outros IDs podem ser preservados na edição/importação, mas são
  bloqueados antes da execução. Não há renumeração silenciosa de referências.
- Casos importados `BLOCKED_FOR_NUMERICAL_ANALYSIS` continuam bloqueados. Abrir
  a geometria iRdin não significa que todas as suas entidades foram qualificadas.
- Resultados pertencem ao snapshot original. Uma edição marca-os como
  desatualizados; desfazer pode restaurar sua atualidade. A geometria modal é a
  geometria do resultado, não uma mistura com a edição posterior.
- O JSON de projeto mantém o contrato Core: modelo, metadados e casos. Resultados
  não são inseridos nesse JSON; permanecem na sessão e nos arquivos exportados.
  Após reabrir o projeto, é necessário recalcular para preencher as vistas.
- A varredura selecionada de mancais é orquestração Flet de chamadas nativas. Sua
  opção `flet_scope=bearing_sweep` não promete a mesma apresentação em Qt.
- A tabela modal usa `fn = |lambda|/(2*pi)` do Core. O gráfico pode exibir `fd`,
  devidamente rotulado. Ramos legados sem tracking recebem aviso explícito.
  Resultados de velocidades críticas conservam diagnósticos/estimativas repetidas;
  a interface não inventa convergência nem remove raízes por uma nova heurística.
- `--web` inicia um servidor local Python em `127.0.0.1`. Fortran continua no
  servidor: não é uma aplicação estática/Pyodide. O modo web e seus diálogos de
  arquivos não têm qualificação visual nesta entrega.

## Verificação reproduzível

```bash
export PYTHONPATH="$PWD/python/src:$PWD"
export DRMROTOR_LIB="$PWD/build-flet/libdrmrotor.so"
export DRMBEARINGS_LIB="$PWD/build-flet/libdrmbearings.so"
ctest --test-dir build-flet --output-on-failure
python -m pytest python/tests python/tests_flet -q
# Linux com Xvfb instalado; em desktop também pode executar sem xvfb-run:
xvfb-run -a -s '-screen 0 1920x1200x24' \
  python scripts/flet_desktop_smoke.py --outdir validation/reports/flet/desktop
```

`test_flet_core_adapter.py` inclui comparação com chamadas diretas ao Core,
valores sentinela, rollback, serialização e conservação de valores complexos.
Os testes `PageStub` verificam controles/handlers Python, não renderização.

`flet_desktop_smoke.py` abre o **cliente Flutter real**, captura as quatro telas,
executa handlers e análises, salva/reabre/recalcula e exige um arquivo PASS novo
para cada execução, uma única sessão e 26 verificações distintas. Uma reconexão
ou falha anterior não pode ser convertida em PASS por uma tentativa automática.
Não automatiza cliques nos diálogos nativos do sistema
operacional e não testa um executável congelado.

O workflow `Flet workbench - source qualification` verifica preservação das
fontes numéricas/Qt, regressão e integração. O job Linux inclui o desktop real;
o job Windows declara apenas Core/handlers, sem alegação de desktop/frozen.
Os resultados efetivos ficam nos artefatos da execução do HEAD correspondente.

Documentação Flet consultada: https://flet.dev/blog/flet-1-0/ e
https://flet.dev/docs/controls/listview/ (API 1.0.0).
