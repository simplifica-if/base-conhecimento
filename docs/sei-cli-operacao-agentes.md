# Uso do sei-cli por agentes

Este guia orienta agentes IA que trabalham nesta base quando a tarefa exigir dados do Sistema Eletrônico de Informações do IFPR, como processos administrativos de abertura, ajuste, atualização, suspensão, reversão de suspensão ou extinção de cursos.

## Regra principal

Quando houver pergunta, dúvida de curadoria ou necessidade de evidência sobre processo SEI, verifique se o repositório irmão `../sei-cli` está disponível e use essa ferramenta para obter ou inspecionar uma fotografia local do processo.

O `sei-cli` é a ferramenta operacional preferencial para coletar dados do SEI. Esta base registra o resultado curado no Notion e publica JSONs derivados; ela não substitui o SEI como fonte primária do andamento processual.

## Onde fica

O repositório esperado é:

```bash
../sei-cli
```

Antes de usar, confira a documentação da própria ferramenta:

```bash
cd ../sei-cli
sed -n '1,220p' README.md
```

Se `../sei-cli` não existir, diga ao usuário que a ferramenta não está disponível neste ambiente e peça o caminho correto do checkout.

## Quando usar

Use `sei-cli` quando a tarefa envolver:

- localizar ou revisar um processo SEI;
- confirmar `Data de abertura` ou `Última movimentação`;
- identificar documentos relevantes, como pareceres, despachos, PPCs, portarias, resoluções, atas ou documentos externos;
- verificar se houve ato definitivo, arquivamento, cancelamento ou encaminhamento recente;
- extrair evidências para preencher `Processos SEI`, `Movimentações de Cursos` ou `Documentos de Curso` no Notion;
- responder a dúvidas operacionais quando os JSONs publicados não tiverem evidência suficiente.

Não use `sei-cli` para substituir a consulta normativa da base pública. Para normas, legislação, resoluções, portarias publicadas, catálogos e PPCs já convertidos, siga primeiro `llms.txt`.

## Autenticação

O comando `extrair` acessa o SEI e depende de credenciais:

- `SEI_USUARIO`;
- `SEI_SENHA`;
- `SEI_BASE_URL`, opcional, padrão `https://sei.ifpr.edu.br`;
- `SEI_HEADLESS`, opcional, padrão `true`.

Essas variáveis devem estar no ambiente ou em `../sei-cli/.env.local`. Nunca registre usuário, senha ou conteúdo de `.env.local` em documentação, logs de resposta, commits ou exemplos.

Se as credenciais não estiverem disponíveis, peça ao usuário as credenciais ou um snapshot já extraído. Não invente dados do processo.

## Comandos essenciais

Para extrair uma fotografia atual do SEI:

```bash
cd ../sei-cli
bun run sei extrair processo 23411.018179/2025-81
```

Para ler um ZIP de processo já baixado:

```bash
cd ../sei-cli
bun run sei ler processo 23411.018179/2025-81 --zip processo.zip
```

Para ler um diretório local de documentos:

```bash
cd ../sei-cli
bun run sei ler processo 23411.018179/2025-81 --diretorio documentos/
```

Para inspecionar uma execução já extraída:

```bash
cd ../sei-cli
bun run sei inspecionar ultima-atualizacao dados/sei/23411.018179_2025-81/<execucao>
bun run sei inspecionar documentos dados/sei/23411.018179_2025-81/<execucao> --ultimos 20
bun run sei inspecionar historico dados/sei/23411.018179_2025-81/<execucao> --ultimos 50
```

Use `--json` quando precisar processar a saída por script, `jq` ou outro programa:

```bash
bun run sei inspecionar documentos dados/sei/23411.018179_2025-81/<execucao> --ultimos 20 --json
```

## Estrutura do snapshot

Cada execução cria uma pasta semelhante a:

```text
dados/sei/<numero-processo>/<execucao>/
  AGENTS.md
  processo.json
  processo.zip
  documentos/
  logs/execucao.log
```

Dentro do snapshot, leia primeiro o `AGENTS.md` gerado para aquela execução. Ele contém instruções específicas de pesquisa e citação.

Use `processo.json` como índice canônico da extração. Campos importantes:

- `numero_processo`: número do processo;
- `tipo_processo` e `especificacao`: metadados coletados no SEI, quando disponíveis;
- `ultima_movimentacao`: movimentação mais recente identificada;
- `historico[]`: lista de eventos de andamento;
- `documentos[]`: documentos localizados;
- `documentos[].numero_sei`: número SEI do documento;
- `documentos[].titulo`: título do documento;
- `documentos[].tipo_documento`: formato ou tipo inferido;
- `documentos[].criado_em` e `documentos[].modificado_em`: datas disponíveis;
- `documentos[].criado_por`: autor ou unidade quando disponível;
- `documentos[].assinantes_html`: assinantes extraídos de documentos HTML, quando disponíveis;
- `documentos[].unidade_sei` e `documentos[].caminho_hierarquico`: posição na árvore do processo, quando disponível;
- `documentos[].caminho_relativo`: caminho do arquivo dentro do snapshot.

## Procedimento de pesquisa

1. Identifique o número do processo no formato `00000.000000/0000-00`.
2. Veja se já existe snapshot em `../sei-cli/dados/sei/<numero-processo>/`.
3. Se houver múltiplas execuções, prefira a mais recente, salvo se o usuário pedir outra data.
4. Se não houver snapshot ou se for necessário dado atual, rode `bun run sei extrair processo <numero>`.
5. Leia o `AGENTS.md` do snapshot.
6. Consulte `processo.json`, começando por `ultima_movimentacao`, `historico[]` e `documentos[]`.
7. Use os comandos `inspecionar` para uma visão rápida dos documentos e eventos recentes.
8. Abra apenas os documentos relevantes para a pergunta ou curadoria.
9. Para HTML e texto, use `rg` dentro de `documentos/`.
10. Para PDF, use uma ferramenta própria de leitura de PDF; o snapshot preserva o arquivo, mas não garante OCR.

Comandos úteis dentro do snapshot:

```bash
jq '.ultima_movimentacao' processo.json
jq '.historico[] | select(.descricao | test("Gerado documento|Registro de documento|arquiv|conclu|parecer|portaria|resolu"; "i"))' processo.json
jq '.documentos[] | {numero_sei, titulo, unidade_sei, caminho_hierarquico, assinantes_html, criado_em, modificado_em, caminho_relativo}' processo.json
rg -n "termo de busca" documentos/
```

## Como registrar evidências

Ao usar o SEI para curadoria, registre no Notion somente informações sustentadas por evidências do snapshot.

Em `Processos SEI`:

- use `Número SEI` como identificador operacional;
- preencha `Data de abertura` com a autuação/criação do processo quando encontrada;
- preencha `Última movimentação` com a data mais recente localizada em `historico[]` ou nos documentos;
- use `Status` apenas para o estado geral do processo: `Não iniciada`, `Em andamento`, `Concluído`, `Cancelado` ou `Arquivado`;
- escreva `Observações` em blocos curtos.

Modelo recomendado de `Observações`:

```text
Revisado em AAAA-MM-DD via sei-cli.

Contexto
- Curso/campus e finalidade do processo.

Evidências
- SEI 1234567 (AAAA-MM-DD): título do documento e síntese da evidência.
- Histórico em AAAA-MM-DD: descrição relevante do andamento.

Datas de controle
- Data de abertura: AAAA-MM-DD, conforme ...
- Última movimentação: AAAA-MM-DD, conforme ...

Observação técnica
- Limitação da extração, pendência ou ressalva, quando houver.
```

Não inclua caminho local de snapshot no Notion. Caminhos como `../sei-cli/dados/sei/...` são úteis para trabalho local, mas não são fonte estável para a base operacional.

Em `Movimentações de Cursos`, use o processo SEI como eixo da linha do tempo e registre a etapa fina em `Situação`, como `Em instrução no campus`, `Em análise Proens`, `Em colegiados/conselhos`, `Aguardando ato/publicação`, `Concluído` ou `Arquivado`.

## Como citar em respostas

Quando responder ao usuário com base em snapshot do SEI, informe:

- número do processo;
- número SEI, título e data do documento usado;
- data e descrição do item de `historico[]`, quando a conclusão depender do andamento;
- se a informação veio de snapshot local extraído pelo `sei-cli`.

Não trate snapshot local como publicação oficial para fins normativos gerais. Para decisões administrativas, jurídicas ou acadêmicas, recomende conferência no próprio SEI e nas publicações oficiais indicadas.

## Depois de alterar o Notion

Depois de alterar dados institucionais no Notion com base em evidências do SEI, volte para este repositório e rode:

```bash
python3 scripts/notion_exportar_base_publica.py
python3 scripts/gerar_indice_ppcs.py
python3 scripts/validar_base.py
```

Esses comandos atualizam os artefatos públicos e validam a base gerada.
