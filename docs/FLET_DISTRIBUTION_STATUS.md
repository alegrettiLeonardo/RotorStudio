# RotorStudio Flet — distribuição e publicação: fechamento parcial

## Estado desta revisão

Esta revisão local continua a expansão de 42 classes de apresentação Qt e 21
contratos AnalysisService da base `fcdac252974aeeded6961dbe3310677e234a6495`.
Não é uma versão publicada, instalador ou executável qualificado.

A ferramenta GitHub aceitou a criação de um objeto de árvore intermediário,
`62a4d5183f513be49906b5918a86ef618a41dc47`, contendo apenas um arquivo novo.
A chamada seguinte de criação de árvore, que acrescentaria o catálogo de análises,
foi bloqueada: “não foi possível determinar o status de segurança da solicitação”.
A publicação foi interrompida. O objeto intermediário NÃO é um commit, não contém
a expansão completa e NÃO deve ser usado como revisão de entrega.
Não houve atualização de referência, commit novo nem merge pelo assistente.

A consulta final do PR #32 ainda retornou o HEAD
`842a8013b6ddc99956641f55420a80c2b504e15e`, aberto, em rascunho e sem merge.
A autorização do usuário para publicar não deve ser confundida com a conclusão
da operação nem com uma aprovação independente da interface.

## Separação de estados

| Item | Estado e evidência |
|---|---|
| Core + testes Flet | 269 testes aprovados; 248 existentes + 21 testes novos dos contratos de distribuição. |
| Compilação Fortran | 14/14 CTests aprovados. |
| Interface Linux por código-fonte | 131 verificações e 199 capturas em sessão real; não é teste de executável congelado. |
| Publicação no GitHub | Bloqueada pela ferramenta; nenhuma branch atualizada. |
| GitHub Actions desta expansão | Não executado. Workflows no pacote são procedimentos preparados, não evidência remota. |
| Desktop Windows | Não executado nesta revisão. Não herda a qualificação de versões anteriores. |
| Browser | Tentativa bloqueada por `net::ERR_BLOCKED_BY_ADMINISTRATOR`; nenhum teste da interface web foi concluído. |
| Executáveis congelados | Não produzidos nesta sessão: PyInstaller indisponível e instalação bloqueada por falha de resolução DNS do índice de dependências. |
| Diálogos nativos de arquivo | Driver preparado, não executado localmente. O teste desktop aprovado não habilitou `--file-dialogs`. |

O processo Python/Flet respondeu HTTP 200 à verificação local, mas isso não é
renderização web. A restrição do navegador não foi contornada. Os testes de
contratos Python não substituem as execuções Windows, web ou frozen.

## Alterações implementadas para a campanha de distribuição

- Descoberta de bibliotecas nativas dentro do bundle congelado, sem fallback
  silencioso para um build de desenvolvimento quando o bundle estiver incompleto.
- Retenção dos handles de diretório de DLL no Windows.
- Entrada explícita de qualificação do mesmo aplicativo (`--qualification-all-screens`).
  O relatório identifica o processo real, plataforma, modo web/desktop e `sys.frozen`.
- Driver externo para cliente desktop/navegador, upload/download e diálogos do
  sistema operacional. Política administrativa bloqueante encerra a tentativa;
  não há retry destinado a superar essa política.
- Empacotamento onedir por plataforma, runtime Flet oficial e bibliotecas nativas,
  com manifesto de hashes; extração em diretório novo e verificação dos arquivos.
- Gate que rejeita coleções de testes vazias, falhas, skips, ausência de diálogos,
  hashes divergentes, screenshots faltantes, sessões repetidas e identidades
  fonte/frozen incompatíveis.
- Workflow separado `.github/workflows/flet-distribution-qualification.yml`, com
  permissões somente de leitura e jobs Linux/Windows. Não publica nem faz merge.

Os scripts de empacotamento, os caminhos Windows e a automação de diálogos ainda
exigem execução no ambiente de destino. Podem precisar de ajustes após uma falha
concreta; a presença desses scripts não é “qualificação concluída”.

## Reproduzir depois da publicação/revisão do código

A forma mais direta é executar o workflow de distribuição no commit exato da
expansão. Ele compila as bibliotecas e executa os seguintes percursos:

1. Fonte → desktop Linux/Windows → 21 análises → resultados → persistência →
   diálogos nativos de arquivos.
2. Fonte → navegador com backend Linux → renderização → upload/download reais.
3. Pacote extraído → ambiente de processo isolado → desktop Linux/Windows →
   mesmos testes, sem `PYTHONPATH` e sem overrides externos dos solvers.
4. Pacote Linux extraído → servidor nativo → navegador → mesmos contratos.

As sessões web deste workflow usam backend Linux; não são Pyodide nem um site
estático, e não qualificam backend Windows em modo web.
O isolamento do ambiente de processo em CI não demonstra, por si só, execução
em uma máquina física sem ferramentas de desenvolvimento instaladas.

### Comandos por código-fonte

Na raiz da revisão completa, após instalar as dependências do guia Flet:

```bash
python -m pip install -e './python[flet,test,package]' 'pyautogui==0.9.54' 'playwright==1.55.0'
cmake -S fortran -B build-flet -DCMAKE_BUILD_TYPE=Release
cmake --build build-flet -j2
export PYTHONPATH="$PWD/python/src:$PWD"
export DRMROTOR_LIB="$PWD/build-flet/libdrmrotor.so"
export DRMBEARINGS_LIB="$PWD/build-flet/libdrmbearings.so"
python -m pytest python/tests python/tests_flet -q
ctest --test-dir build-flet --output-on-failure
```

Para o driver desktop Linux são necessários Xvfb, Openbox, Zenity, xdotool e uma
ferramenta de captura de tela compatível. Cada execução exige um diretório novo:

```bash
xvfb-run -a -s '-screen 0 1800x1120x24' bash -c \
  'openbox >/tmp/flet-wm.log 2>&1 & python scripts/flet_distribution_driver.py --out validation/reports/flet_distribution/source_desktop --file-dialogs --source-head "$(git rev-parse HEAD)" -- python -m drm_flet'
```

Não remova a exigência de diálogos ou de modo congelado para transformar um gate
vermelho em aprovação. Investigue a falha ou registre o bloqueio de ambiente.

## Limitações funcionais separadas de cobertura de telas

| Limitação | Classificação |
|---|---|
| 3D científico com controles de câmera, sem seleção de faces CAD/OpenGL | Limitação de interação; não é ausência da tela de modos. |
| Reabrir projeto exige recalcular as vistas | Limitação de persistência de resultados; o contrato JSON do Core não foi alterado. |
| Inventário mapeado não prova cada botão/gesto do Qt | Limitação da evidência de paridade funcional; revisão de fluxos completos continua necessária. |
| Passar testes de interface não certifica adequação física ou normativa | Limite da qualificação, não recurso gráfico faltante. |

Nenhum arquivo Fortran, `drm_core` ou `drm_studio` foi alterado em relação ao
pacote-base verificado. Não foram acrescentadas físicas, tolerâncias numéricas
mais permissivas ou resultados fictícios para obter aprovação.
