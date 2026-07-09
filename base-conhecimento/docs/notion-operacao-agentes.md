# Operação do Notion por agentes

Este guia orienta agentes IA trabalhando a partir de um checkout local deste repositório quando a tarefa envolver a base Notion operacional da Gestão de Cursos do IFPR.

## Regra principal

Para dados operacionais de gestão, o Notion é a fonte da verdade, inclusive para propriedades, tipos e opções vigentes das bases.

Os JSONs em `institucional/ifpr/campi/`, `institucional/ifpr/processos-seletivos/` e outros artefatos derivados não são espelho operacional nem fonte de curadoria: são saída publicável/cache gerado a partir do Notion e de fontes documentais locais. Não consulte nem edite esses JSONs para decidir o estado atual de Campi, Cursos, Movimentações de Cursos, Processos Seletivos, Editais ou Ofertas quando a base Notion estiver acessível.

Use este guia quando a solicitação envolver:

- Campi;
- Cursos;
- metadados de PPC em Cursos;
- Movimentações de Cursos;
- Pareceres de Curso;
- Tarefas;
- horários dos campi;
- Processos Seletivos;
- Editais de Ingresso;
- Ofertas de Ingresso.
- Conselhos institucionais, reuniões, documentos e itens de pauta, inicialmente do Consepe;
- Servidores e conselheiros vinculados a conselhos institucionais.

## Autenticação padrão

Por padrão, não presuma que o Notion MCP local do usuário tem acesso a esta base.

Em geral, o MCP local do usuário estará conectado ao Notion pessoal dele, enquanto esta base Notion fica em um workspace organizacional. Portanto, o fluxo padrão para agentes é usar a API do Notion com `NOTION_TOKEN` deste projeto.

Antes de operar no Notion:

1. Verifique se existe `.env.local` na raiz do repositório.
2. Verifique se `.env.local` contém `NOTION_TOKEN=...`.
3. Se não houver token, peça ao usuário o token da integração Notion organizacional desta base.
4. Grave o token em `.env.local` no formato:

```bash
NOTION_TOKEN=secret_...
```

Nunca commite `.env.local` nem escreva o token em documentação, logs ou exemplos.

Os scripts Notion deste repositório carregam `.env.local` automaticamente quando usam `scripts/notion_client.py`.

## MCP, API e scripts locais

Ordem preferida de operação:

1. Use os scripts locais quando a tarefa já estiver coberta por eles, como atualizar movimentações SEI no Notion, exportar JSON público, regenerar índices ou validar a base.
2. Use a API do Notion com `scripts/notion_client.py` para operações repetíveis, migrações, consultas estruturadas ou alterações em lote.
3. Use Notion MCP apenas quando estiver claro que o MCP disponível está conectado ao workspace organizacional correto e consegue acessar a página raiz desta base.

Se MCP e API divergirem, confie na API com `NOTION_TOKEN` do projeto.

## Como localizar as bases

Use `config/notion.json` como mapa operacional. Ele contém:

- `parent_page_id`: página raiz Notion da Gestão de Cursos;
- `databases.<chave>.id`: ID da database/página Notion;
- `databases.<chave>.data_source_id`: ID do data source usado para consultas e escrita;
- `databases.<chave>.title`: nome humano da base.

Não dependa apenas do nome visual da base no Notion. Use as chaves e IDs de `config/notion.json`.

Antes de criar ou alterar registros, consulte o data source no Notion para confirmar as propriedades, tipos e opções atuais. A documentação local descreve fluxos e propriedades recorrentes, mas não substitui o schema vivo do Notion.

Chaves atuais:

- `campi`;
- `cursos`;
- `movimentacoes_cursos`;
- `pareceres_curso`;
- `tarefas`;
- `processos_seletivos`;
- `editais_ingresso`;
- `ofertas_ingresso`.
- `conselhos`;
- `reunioes_conselho`;
- `documentos`;
- `itens_pauta`;
- `servidores`;
- `conselheiros`.

## Quando usar Notion

Use Notion quando o usuário pedir para:

- consultar ou alterar cadastro atual de campus ou curso;
- registrar ou revisar processo SEI de curso;
- criar, corrigir ou consultar movimentação de curso;
- revisar dados de horários dos campi;
- revisar dados SUAP em cursos;
- criar ou revisar processo seletivo, edital ou oferta de ingresso;
- consultar ou registrar dados do Consepe, como reuniões, pautas, atas, pareceres, processos SEI, relatores e conselheiros;
- consultar ou registrar servidores quando forem usados como diretório central para conselheiros, relatores ou outras funções institucionais;
- executar curadoria operacional que depois será publicada nos JSONs.

Quando a consulta ou alteração depender de evidência do Sistema Eletrônico de Informações, leia também `docs/sei-cli-operacao-agentes.md` e use `../sei-cli` para localizar, extrair ou inspecionar o processo antes de registrar dados no Notion.

## Quando não usar Notion primeiro

Não comece pelo Notion quando a tarefa for:

- responder pergunta normativa geral: consulte primeiro os manifestos e arquivos locais deste repositório;
- consultar legislação, resoluções, portarias, CNCT ou PPCs publicados;
- alterar scripts, schemas ou documentação do repositório;
- debugar geração ou validação de JSON público.

Nesses casos, use os arquivos locais. Comece por `manifest.json`, `institucional_manifest.json`, `catalogos_manifest.json` ou `institucional/ifpr/ppcs/index.json`, conforme o tipo de consulta, e abra os arquivos indicados no campo `path`.

## Regras de escrita

Ao alterar dados no Notion:

- preserve identificadores estáveis, como `campus_id`, `curso_slug`, `notion_page_id`, `SEI Processo`, `SUAP ID`, `SUAP Código` e IDs de processo seletivo;
- não crie campos técnicos de sincronização, migração ou controle interno sem necessidade operacional atual;
- não crie propriedades novas no Notion sem verificar o schema atual, a necessidade operacional e os scripts que leem ou exportam a base;
- se o Notion contiver um valor ou propriedade operacional legítima que a validação local rejeite, ajuste o exportador, schemas públicos ou validadores locais. Não altere o Notion apenas para caber em enumerações locais desatualizadas;
- registre fontes, datas de coleta e notas de curadoria quando a informação vier de site externo, planilha, SEI ou SUAP;
- prefira relações entre bases, não duplicação textual, quando a relação já existir no modelo;
- não edite manualmente os JSONs públicos para refletir curadoria operacional.

## Fluxos típicos

### Consultar uma base

1. Leia `config/notion.json`.
2. Obtenha o `data_source_id` da base.
3. Consulte o data source com a API do Notion ou com script local, incluindo o schema/propriedades quando isso afetar escrita, filtros ou validação.
4. Se precisar cruzar relações, busque os registros relacionados pelos IDs de página. Em `Cursos`, use `Página oficial` como URL pública do curso; scripts antigos ainda aceitam `URL oficial` como fallback.

### Alterar dados operacionais

1. Confirme que `NOTION_TOKEN` está disponível em `.env.local`.
2. Localize a base e o registro Notion correto.
3. Aplique a alteração via API ou MCP conectado ao workspace correto.
4. Quando a alteração afetar artefatos publicados, exporte os JSONs públicos. A exportação audita o Notion antes de escrever arquivos e falha quando encontra campos obrigatórios ausentes, IDs locais duplicados ou relações que impediriam reconstrução confiável dos JSONs.
5. Regenere índices quando necessário.
6. Valide a base.

Comandos:

```bash
python3 scripts/notion_exportar_base_publica.py
python3 scripts/gerar_indice_ppcs.py
python3 scripts/validar_base.py
```

Para conferir a reconstrução sem alterar arquivos, use:

```bash
python3 scripts/notion_exportar_base_publica.py --dry-run
```

### Criar movimentação de curso

1. Localize o curso em `Cursos`.
2. Crie uma entrada em `Movimentações de Cursos`.
3. Preencha tipo, situação e anotações quando houver evidências, pendências ou nuances de curadoria.
4. Quando houver processo SEI, preencha na própria movimentação `SEI Processo`, `Data de abertura SEI`, `Data Última mov. SEI`, `Última movimentação SEI` e `Observações SEI`.
5. O mesmo `SEI Processo` pode aparecer em mais de uma movimentação quando um único processo fundamentar mudanças em cursos diferentes.

### Registrar dados SEI em movimentação

1. Use `SEI Processo` como identificador operacional no formato `00000.000000/0000-00`.
2. Quando o `id_procedimento` for confirmado no SEI, faça do próprio valor de `SEI Processo` um hyperlink para a URL interna limpa do processo, no formato `https://sei.ifpr.edu.br/sei/controlador.php?acao=procedimento_trabalhar&id_procedimento=<id>`. Não grave URLs com `infra_hash`, pois esse parâmetro é volátil, e não crie propriedade separada para o link.
3. Em atualizações rotineiras de movimentações do SEI, considere implícito que o escopo são todas as entradas de `Movimentações de Cursos` que tenham `SEI Processo` preenchido e estejam em qualquer situação de andamento ou a fazer: `Não iniciada`/`A fazer`, `Em instrução no campus`, `Em análise Proens`, `CONSEP`, `CONSUP` ou `Aguardando ato/publicação`. Não inclua `Concluído` ou `Arquivado`, salvo pedido explícito.
4. Mantenha `Data de abertura SEI`, `Data Última mov. SEI` e `Última movimentação SEI` preenchidas sempre que o processo for localizado ou revisado. `Data de abertura SEI` é a autuação/criação do processo; `Data Última mov. SEI` é a data mais recente encontrada no andamento ou nos documentos, não a conclusão administrativa. `Última movimentação SEI` é um resumo textual curto das quatro movimentações mais recentes encontradas pela SEI CLI.
5. Para atualização rotineira desses campos, prefira o script local:

```bash
python3 scripts/notion_atualizar_movimentacoes_sei.py --apply
```

Sem `--apply`, o script roda em modo dry-run. Ele consulta o histórico remoto pelo `sei-cli`, atualiza incrementalmente o Notion e nunca apaga `Data Última mov. SEI` quando a CLI não retorna data.

6. Para consultas avulsas, use `bun run sei extrair ultimas-movimentacoes <processo> --ultimos 4 --json --quiet` ou o lote `bun run sei extrair ultimas-movimentacoes lote processos.txt --ultimos 4 --jsonl --quiet`, conforme `docs/sei-cli-operacao-agentes.md`.
7. Se a autuação exata não estiver disponível e você usar a primeira data documentada como aproximação, registre isso em `Observações SEI`.
8. Escreva `Observações SEI` em blocos curtos, com quebras de linha e marcadores, para facilitar leitura humana e reuso por agentes. Em campos textuais do Notion, use datas no formato brasileiro curto `DD/MM/AA`. Comece com uma frase simples no formato `Revisado em DD/MM/AA via <ferramenta ou fonte>.` Em seguida, use, quando aplicável, os blocos `Contexto`, `Evidências`, `Datas de controle` e `Observação técnica`. Não inclua caminho local de snapshot.
9. Se a informação vier de coleta automatizada, preserve origem, linhas, observações ou notas relevantes em `Observações SEI` ou `Anotações`.

Quando usar `sei-cli`, registre `Revisado em DD/MM/AA via sei-cli.` e cite nas evidências os documentos ou eventos usados, como `SEI 1234567 (DD/MM/AA): Parecer ...`. Não grave caminhos locais do snapshot em `Observações`.

### Registrar parecer de curso

Use `Pareceres de Curso` para arquivar metadados de pareceres localizados em processos SEI associados a movimentações de curso. Cada registro representa um documento SEI específico, pois uma única movimentação pode ter mais de um parecer ao longo das revisões do PPC.

Campos centrais:

- relacione `Movimentação de Curso` à entrada correspondente em `Movimentações de Cursos`;
- preencha `SEI Documento`;
- use `SEI Processo` como roll-up da relação com `Movimentação de Curso`, não como cópia textual manual;
- use `Data do parecer` para a data de criação/emissão identificada no SEI;
- use `Autor` e `SIAPE/Autor SEI` quando autoria ou assinatura estiverem confirmadas;
- registre `Tipo de parecer` e `Conclusão` conforme a curadoria avançar;
- use `Substitui parecer` para encadear versões ou revisões do mesmo parecer.

Quando a fonte for snapshot do `sei-cli`, preserve a evidência em termos estáveis, como número SEI, data, autoria/assinatura e processo. Não grave caminhos locais do snapshot em campos do Notion.

### Registrar dados do Consepe

Use o conjunto de bases de conselhos para dados institucionais do Conselho de Ensino, Pesquisa e Extensão:

- `Conselhos`: cadastro do órgão colegiado. O Consepe é o primeiro registro.
- `Reuniões de Conselho`: uma entrada por reunião, relacionada a `Conselhos`.
- `Documentos`: pautas, atas, pareceres, legislação e anexos, relacionados à reunião quando aplicável.
- `Itens de Pauta`: assuntos deliberados ou pautados, relacionados à reunião e ao documento de origem.
- `Servidores`: diretório central de pessoas servidoras, com `Campus` como relação para `Campi`.
- `Conselheiros`: participação de um servidor em um conselho, com segmento, função, mandato, fonte e status.

Fluxo recomendado:

1. Localize ou crie o registro do conselho em `Conselhos`.
2. Registre cada reunião em `Reuniões de Conselho`, com data, tipo, fonte oficial e link de transmissão quando existir.
3. Registre pautas, atas, pareceres e demais documentos em `Documentos`, preservando URL oficial, número do documento, texto ou resumo extraído e data de coleta.
4. Registre cada assunto em `Itens de Pauta`, preenchendo `Processo SEI`, `Documento SEI`, `Tipo de demanda`, `Resultado`, `Relator(a)`, `Trecho da pauta`, `Trecho da ata` e `Resumo` sempre que a fonte permitir.
5. Quando um relator, conselheiro ou participante for identificado, crie ou reutilize o registro em `Servidores`; depois crie ou reutilize a participação em `Conselheiros` e relacione em `Itens de Pauta.Conselheiros relacionados`.
6. Marque `Conselheiros.Status` como `Não confirmado` quando a fonte for provisória, incompleta ou apenas inferida de relatoria; use `Ativo` somente quando houver fonte de composição, posse, mandato ou homologação final.

Para processos SEI do Consepe, prefira registrar o número diretamente no item de pauta, pois o processo normalmente se refere ao assunto deliberado, não à reunião inteira. Use `Documentos` para o link ao parecer ou publicação SEI quando o documento for público.

Em `Servidores`, não duplique o campus em texto quando houver registro em `Campi`; use a relação `Campus`. O campo textual `Campus/Unidade`, quando existir, serve como trilha de origem para valores ainda não normalizados ou unidades que não sejam campus.

## Documentos relacionados

- `docs/notion-gestao-cursos.md`: modelo operacional das bases.
- `docs/curadoria-metadados-institucionais.md`: regras de curadoria institucional.
- `docs/sei-cli-operacao-agentes.md`: uso do `../sei-cli` para extrair e inspecionar processos SEI.
- `config/notion.json`: IDs das bases Notion.
- `scripts/notion_client.py`: cliente mínimo da API Notion.
- `scripts/notion_exportar_base_publica.py`: exportação Notion para JSON público.
