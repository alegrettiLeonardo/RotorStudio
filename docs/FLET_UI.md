# RotorStudio — interface Flet

**Distribuição ainda não concluída.** Consulte `FLET_DISTRIBUTION_STATUS.md` para
as evidências desta revisão, os bloqueios de publicação/ambiente e os procedimentos
preparados. Os novos scripts de distribuição não constituem aprovação Windows/web/frozen.

A implementação inicial das quatro áreas foi expandida para todas as telas
inventariadas do Qt na base `fcdac252974aeeded6961dbe3310677e234a6495`.
São **42 classes de apresentação Qt**, **21 contratos AnalysisService** e
os fluxos especializados de campos e mapas de mancais. O inventário
verificável está em `docs/FLET_SCREEN_PARITY.json`; a contagem não significa
42 janelas simultâneas: inclui os painéis/editores embutidos.
As quatro imagens conceituais são a referência de apresentação: editor do rotor,
Campbell, desempenho dos mancais e modos 3D em tema escuro. Os controles são
Flet/Flutter reais, não páginas HTML ou imagens clicáveis da aplicação inteira.

O comando Qt `drm-studio` continua disponível e inalterado. O novo comando é
`drm-studio-flet`. Nenhum arquivo de `drm_core`, `drm_studio` ou `fortran` é
modificado em relação a essa base. A correção A5 e a análise A8 são herdadas integralmente da main, não reimplementadas em Flet.

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

Use **Análises** / **Executar análise** para abrir o catálogo completo. Os
21 contratos têm formulários tipados com unidades explícitas, em vez de um
editor JSON genérico. As grades podem ser uniformes ou explicitamente amostradas.
A árvore abre a configuração do caso; executar, renomear e remover são ações
separadas. Alterar parâmetros não modifica o resultado de uma execução anterior.

| Grupo | Configuração e resultados disponíveis |
|---|---|
| Modal | Modal, Campbell, raízes, modos 3D, órbitas, críticas e diagnóstico iterativo |
| Estática | Deflexão, cortante, momento, reações e pesos |
| Harmônica | Síncrona, apoio auxiliar/spinner, fundação, matriz FRF geral, resposta forçada |
| Transiente | F(t) geral, pulso na fundação, run-up/run-down, órbita e DFFT em grade uniforme |
| Rotores especiais | Coaxial modal/síncrono; assimétrico modal/resposta no referencial girante |
| UCS / estabilidade | Mapa UCS, interseções, dados modais críticos, Level 1 |
| API 617 | Posicionamento de desbalanceamento A7 e resposta/limites de folga A8 |
| Mancais | Matrizes globais, varredura radial, campos físicos e mapas operacionais/cache |

Os editores incluem eixos circulares, cônicos e assimétricos; discos 1–6;
mancais clássicos 1–8 e acoplamentos 20; forças 1–7; pré-curvatura;
definições coaxiais; e as 14 classes de mancal avançado existentes no Core.
Valores de massa, inércia, módulos, carregamentos e coeficientes são armazenados
em SI. A configuração física usa campos por propriedade e vetores/matrizes
explicitamente rotulados; não executa código a partir de texto digitado.

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

## Campos físicos e mapas de mancais

Em **Mancais → Campos físicos**, configure Ω e ω separadamente. As abas apresentam
K/C/M, pressão, temperatura, espessura de filme, deformação, dados por sapata e
convergência, quando tais dados são retornados pelo backend selecionado.
Dados não disponíveis ficam explicitamente desabilitados; não são sintetizados.
A execução é serializada, com progresso nativo e cancelamento em pontos seguros.

Em **Mapa operacional**, escolha eixos Ω/ω, política síncrona ou independente e
interpolação. A tela mostra curvas, superfície, tabela e proveniência/cache L1/L2.
**Aplicar mapa** exige confirmação e verifica o hash do modelo de origem. O
snapshot físico é preservado na proveniência e o comando pode ser desfeito.
Mapas que não satisfazem o contrato do Core, incluindo descarte indevido de M,
não são promovidos silenciosamente. A invalidação atua somente na chave
selecionada e também exige confirmação.

## Análise A8 de folgas

A configuração recebe nós/ângulos/nomes de sondas radiais, nós/nomes/folgas
**radiais** de operação, faixa de rotação, Nma/Nmc, modo direto e quantidade
par de autovalores. A UI usa rpm, graus e µm; a API recebe rad/s, rad e m.
O limite opcional do fator de escala é vazio por padrão e não assume 6
silenciosamente. O desbalanceamento explícito é opcional; sem essa seleção,
o Core usa o posicionamento nativo A7.

O resultado separa resposta escalada nas folgas e resposta **não escalada** nas
sondas, ambas pico a pico. A faixa de operação, Avl, Amax, Scc, cap, máximo e
status são apresentados a partir do resultado nativo. A condição é estrita:
resposta < 75% da folga diametral; igualdade não é aprovada. As telas não
transformam a paridade numérica do Core em certificação normativa da máquina.

## Resultados, relatórios e diagnóstico

O centro de resultados permite abrir, reconfigurar, repetir e remover registros.
O centro de relatórios exporta um resultado ou um conjunto; o pacote conserva
seleções de visualização, casos, hashes e dados completos. PNG/SVG/PDF são
figuras; CSV é a tabela longa integral, preservando partes real e imaginária;
NPZ preserva arrays complexos sem objetos/pickle. Nenhum arquivo existente é
apagado por exportação implícita.

A resposta assimétrica é identificada como pertencente ao referencial girante;
não se desenha uma órbita harmônica fictícia para uma solução estática nesse
referencial. A DFFT exige amostras temporais uniformes: resultados adaptativos
não são interpolados/resampleados silenciosamente. Os limites de memória e
de graus de liberdade seguem os contratos nativos.

## Limites e rastreabilidade

- A cobertura é a das **42 classes de apresentação e 21 contratos** inventariados
  na revisão de comparação indicada acima. Não é uma afirmação de igualdade de
  pixels com o Qt, nem de qualificação de executáveis congelados ou desktop
  Windows. As disposições foram adaptadas ao Flet, mantendo controles reais.
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
python scripts/flet_screen_inventory.py --out validation/reports/flet/inventory.json
xvfb-run -a -s '-screen 0 1800x1120x24' bash -c \
  'openbox >/tmp/rotorstudio-openbox.log 2>&1 & python scripts/flet_desktop_smoke.py --outdir validation/reports/flet/desktop'
xvfb-run -a -s '-screen 0 1800x1120x24' bash -c \
  'openbox >/tmp/rotorstudio-openbox-all.log 2>&1 & python scripts/flet_all_screens_smoke.py --outdir validation/reports/flet/all_screens'
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

`flet_all_screens_smoke.py` percorre os 21 formulários, executa cada contrato
no solver nativo e compara seus arrays com chamadas diretas ao Core. Também
exibe todas as abas de resultados, os 42 formulários de entidades exercitados,
os campos/mapas físicos e os centros de projeto/resultados/relatórios. Reabrir
cada projeto deve recuperar o mesmo hash de análise após recalcular.
Cada imagem é capturada do cliente real e registrada com tamanho e SHA-256.
Uma imagem não comprova interação manual de mouse/teclado: esta campanha usa
handlers reais com o cliente renderizando, não automação integral por cliques.

O workflow `Flet workbench - source qualification` verifica preservação das
fontes numéricas/Qt, regressão e integração. O job Linux inclui o desktop real;
o job Windows declara apenas Core/handlers, sem alegação de desktop/frozen.
Os resultados efetivos ficam nos artefatos da execução do HEAD correspondente.

Documentação Flet consultada: https://flet.dev/blog/flet-1-0/ e
https://flet.dev/docs/controls/listview/ (API 1.0.0).
