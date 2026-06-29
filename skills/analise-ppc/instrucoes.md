# Instruções da Skill Análise de PPC

## Resumo

Esta skill executa análise de PPC por sub-agentes dentro da conversa. Os scripts Python são deliberadamente pequenos: convertem o documento para `PPC.md`, montam grupos de fichas e renderizam o PPC HTML anotado a partir do JSON coletado dos sub-agentes.

O output padrão fica em `analise-ppc/output/<rodada>/`. O relatório final fica em `relatorio-analise.html`; os assets do leitor ficam em `assets/`; os artefatos de suporte ficam em `arquivos-suporte/`.

## Dependências

Instale as dependências Python a partir da raiz do projeto onde a skill está instalada:

```bash
python3 -m pip install -r .agents/skills/analise-ppc/requirements.txt
```

Se a instalação estiver em `.claude/skills`, substitua o prefixo do caminho.

## Fluxo recomendado

Use `.agents/skills/analise-ppc` nos exemplos abaixo. Se a skill estiver instalada em `.claude/skills`, troque apenas o prefixo.

```bash
python3 -B .agents/skills/analise-ppc/scripts/analise_ppc.py preparar-documento caminho/PPC.docx
python3 -B .agents/skills/analise-ppc/scripts/analise_ppc.py montar-grupos-subagents --rodada-dir .agents/skills/analise-ppc/output/<rodada>
python3 -B .agents/skills/analise-ppc/scripts/analise_ppc.py preparar-prompts-subagents --rodada-dir .agents/skills/analise-ppc/output/<rodada>
```

Depois disso, o agente principal deve:

1. Ler `arquivos-suporte/PPC.md`.
2. Ler `arquivos-suporte/grupos-subagents.json`.
3. Ler `prompts/subagent-lote-fichas.md`.
4. Preferencialmente ler os pacotes prontos em `arquivos-suporte/prompts-subagents/*.md`.
5. Spawnar um sub-agente por grupo.
6. Passar a cada sub-agente o pacote do grupo ou, de forma equivalente, o PPC completo, o prompt de trabalho, as fichas do grupo e os blocos de `contextos` do grupo, incluindo `contextos.fundamentacao_normativa` quando presente.
7. Coletar as respostas em `arquivos-suporte/resultados-subagents.json`.
8. Fazer a etapa de validações cruzadas usando `prompts/sintese-transversal.md`, o PPC completo, todos os resultados, `cnct_contexto`, `contexto_estrutural` e `validacoes_cruzadas`; salvar o retorno em `alertas_transversais` dentro de `resultados-subagents.json`.
9. Gerar o relatório:

```bash
python3 -B .agents/skills/analise-ppc/scripts/analise_ppc.py gerar-relatorio-html --rodada-dir .agents/skills/analise-ppc/output/<rodada> --resultados resultados-subagents.json
```

## Contrato de resultados

`resultados-subagents.json` deve conter:

```json
{
  "metadata": {
    "observacao": "opcional"
  },
  "grupos": [
    {
      "grupo_id": "grupo-001",
      "resultados": [
        {
          "ficha_id": "CT-IDENT-01",
          "estado": "ATENDE",
          "confianca": 0.9,
          "justificativa": "Decisão fundamentada no PPC.",
          "evidencias": [
            {
              "trecho": "Trecho ou referência textual do PPC.",
              "secao": "Seção do PPC, quando identificável.",
              "localizador": "Página, item, título ou outro ponto de localização.",
              "fonte": "PPC.md",
              "artefato": "Caminho de artefato estruturado ou visual, quando usado.",
              "anchor": {
                "block_id": "ppc-b00042",
                "quote": "Trecho exato dentro do bloco, quando disponível."
              }
            }
          ],
          "lacunas": [],
          "revisao_humana_obrigatoria": false,
          "fundamentacao_normativa": [
            {
              "status": "CONFIRMADA",
              "trecho_ppc": "Trecho do PPC que afirma algo sobre uma norma.",
              "norma": "Norma consultada.",
              "fonte": "base-conhecimento/normas/...",
              "dispositivo": "Artigo, inciso, parágrafo, seção ou campo do CNCT.",
              "evidencia": "Resumo fiel do dispositivo consultado.",
              "analise": "Relação entre a fonte e a afirmação do PPC.",
              "recomendacao": "Ajuste sugerido, quando aplicável."
            }
          ],
          "feedback_autores": "Campo opcional para fichas que solicitam texto de feedback aos autores do PPC."
        }
      ]
    }
  ]
}
```

O renderizador valida campos obrigatórios, fichas duplicadas, fichas ausentes, fichas desconhecidas e quantidade mínima de evidências por ficha antes de gerar o HTML. `evidencias` aceita strings legadas, mas o formato preferido é objeto estruturado com `trecho`, `secao`, `localizador`, `fonte`, `artefato` e `anchor`.
O campo opcional `anchor` deve conter `block_id` e `quote`; quando ausente, o renderizador tenta localizar a anotação por trecho, localizador ou seção.
Quando uma ficha declarar `feedback_autores.obrigatorio_quando_estado`, o renderizador também valida a presença de `feedback_autores` para os estados indicados.
O campo `fundamentacao_normativa` é opcional, mas deve ser usado quando a ficha avaliar afirmação do PPC sobre lei, resolução, portaria, nota técnica, regulamento, CNCT ou outro documento normativo. Quando informado, ele aparece no relatório HTML dentro da ficha correspondente.

## Contexto CNCT

`montar-grupos-subagents` identifica a entrada provável do CNCT para o curso usando a base unificada em `base-conhecimento/catalogos/cnct/index.json` e os arquivos `base-conhecimento/catalogos/cnct/cursos/*.json`. O contexto é salvo em:

```text
arquivos-suporte/cnct-contexto.json
```

O mesmo contexto aparece no topo de `grupos-subagents.json` como `cnct_contexto`. Grupos com fichas que mencionam CNCT ou `contexto_estrutural.cnct` recebem também `requer_contexto_cnct: true` e `contextos.cnct`. Passe esse bloco ao sub-agente junto com o PPC e as fichas do grupo.

## Validações cruzadas

`montar-grupos-subagents` também salva:

```text
arquivos-suporte/validacoes-cruzadas-contexto.json
```

Esse bloco contém as validações transversais canônicas de `base-analise/validacoes-cruzadas/`. Na etapa de síntese transversal, todo alerta deve informar `validacao_id`, apontando para a validação cruzada que fundamenta o alerta.

## Contexto estrutural e anexos visuais

`montar-grupos-subagents` também salva:

```text
arquivos-suporte/contexto-estrutural-subagents.json
```

Esse bloco resume artefatos extraídos do DOCX, como identificação, matriz curricular, ementário e caminhos dos JSONs estruturados. Ele é incluído como `contextos.estrutura` em todos os grupos. Quando a representação gráfica do processo formativo é extraída e o grupo contém `CT-CURR-10`, o grupo recebe `contextos.anexos_visuais` com o caminho absoluto da imagem.

## Fundamentação normativa

`montar-grupos-subagents` também inclui `contextos.fundamentacao_normativa` nos grupos com fichas que citam ou dependem de base legal. Esse contexto aponta para `base-conhecimento/` e para a skill `verificar-fundamentacao-normativa`.

Quando um PPC afirmar algo sobre lei, resolução, portaria, nota técnica, CNCT ou regulamento, o sub-agente deve consultar a fonte antes de validar a alegação. A saída da ficha deve registrar os achados no campo `fundamentacao_normativa` usando os status:

```text
CONFIRMADA
CONFIRMADA_COM_RESSALVA
IMPRECISA
SEM_SUPORTE_NA_FONTE
CONTRADITORIA
FONTE_AUSENTE_OU_NAO_CONSULTADA
NAO_NORMATIVA
```

## Reavaliação avulsa

Para reavaliar fichas específicas sem refazer todos os grupos:

```bash
python3 -B .agents/skills/analise-ppc/scripts/analise_ppc.py montar-grupo-avulso --rodada-dir .agents/skills/analise-ppc/output/<rodada> --ficha-id CT-IDENT-01
```

Spawnar um sub-agente com o grupo avulso retornado, salvar a resposta em `arquivos-suporte/resultado-avulso.json` e mesclar:

```bash
python3 -B .agents/skills/analise-ppc/scripts/analise_ppc.py mesclar-resultados-avulsos --rodada-dir .agents/skills/analise-ppc/output/<rodada> --resultados-avulsos resultado-avulso.json
```

Depois, rode novamente `gerar-relatorio-html`.

## Manutenção da base de análise

Ao alterar fichas, validações cruzadas, contratos ou schemas, valide a base e regenere o índice:

```bash
python3 -B .agents/skills/analise-ppc/scripts/validar_base_analise.py
python3 -B .agents/skills/analise-ppc/scripts/gerar_indice_base_analise.py
```

## Entrega do relatório

Ao concluir `gerar-relatorio-html`, use preferencialmente a URL `surge_url` ou `publicacao_url` retornada pelo comando para avisar a pessoa. O comando publica o HTML interativo no Surge por padrão e também mantém o arquivo local em `relatorio_html`. Se a publicação externa não for desejada, rode com `--sem-surge`.

```text
Relatório pronto: [abrir relatório](https://analise-ppc-<rodada>.surge.sh)
```

Não peça para a pessoa procurar o arquivo dentro dos artefatos.
