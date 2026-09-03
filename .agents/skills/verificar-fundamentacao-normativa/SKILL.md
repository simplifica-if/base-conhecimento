---
name: verificar-fundamentacao-normativa
description: Verificar fundamentação normativa de documentos, PPCs, pareceres, minutas, relatórios e respostas que citam ou afirmam obrigações baseadas em leis, resoluções, portarias, notas técnicas, CNCT ou regulamentos institucionais. Use quando o usuário pedir checagem de citações normativas, validação de afirmações sobre normas, conferência de base legal, identificação de norma ausente, correção de fundamentação ou análise de risco de uma redação normativa.
---

# Verificar Fundamentação Normativa

Verifique se cada afirmação normativa de um documento está apoiada por fonte válida, vigente e pertinente. A regra central é simples: não aceite uma afirmação sobre lei, resolução, portaria, regulamento ou CNCT sem consultar a própria fonte.

## Fontes

Use primeiro a base local do projeto:

- `base-conhecimento/manifest.json` para normas, leis, resoluções, portarias e notas técnicas.
- `base-conhecimento/institucional_manifest.json` para coleções institucionais.
- `base-conhecimento/catalogos_manifest.json` para catálogos.
- `base-conhecimento/catalogos/cnct/manifest.json`, `index.json` e `cursos/*.json` para afirmações sobre cursos técnicos no CNCT.
- `base-conhecimento/institucional/ifpr/ppcs/` apenas como exemplos institucionais observados, não como fonte normativa obrigatória.

Se a skill estiver instalada fora do repositório unificado, localize a base nesta ordem:

1. `base-conhecimento/` no diretório atual ou em algum diretório pai.
2. Raiz do repositório que contém a skill em `.agents/skills/verificar-fundamentacao-normativa`.
3. `SIMPLIFICA_IF_BASE`, se existir no ambiente.
4. Fonte oficial online ou URL pública da base, somente se a base local não estiver disponível ou se a atualização externa for indispensável.

Declare explicitamente quando usar fonte externa. Se a norma necessária não estiver na base nem puder ser consultada com segurança, classifique como `FONTE AUSENTE OU NÃO CONSULTADA`.

## Fluxo

1. Identifique o escopo do pedido: documento inteiro, seção específica, trecho colado, resposta gerada por IA ou conjunto de alegações.
2. Extraia alegações normativas explícitas e implícitas:
   - citações diretas a leis, resoluções, portarias, notas técnicas, regulamentos, CNCT, RGE, PPC, artigos, incisos, parágrafos e anexos;
   - frases com força normativa, como `deve`, `é obrigatório`, `é vedado`, `conforme`, `nos termos`, `previsto`, `regulamentado`, `exigido`;
   - afirmações de vigência, revogação, competência, carga horária, pré-requisito, certificação, matriz curricular, estágio, avaliação, assistência estudantil, acessibilidade ou fluxo processual.
3. Para cada alegação, localize a fonte normativa exata por manifesto, aliases, keywords, título, número, ano e órgão.
4. Abra a fonte e leia o trecho aplicável antes de concluir.
5. Confira:
   - se a norma citada existe e corresponde ao número, ano, órgão e tema indicados;
   - se o dispositivo citado sustenta exatamente a afirmação;
   - se a afirmação omite condicionantes, exceções, escopo, sujeito obrigado, modalidade, nível de ensino ou data de vigência;
   - se há conflito com outra norma da base ou com catálogo aplicável;
   - se a afirmação usa PPCs ou práticas institucionais como se fossem obrigação normativa.
6. Classifique cada alegação e proponha redação corrigida quando houver problema objetivo.

## Classificação

Use uma destas conclusões por alegação:

- `CONFIRMADA`: a fonte consultada sustenta a afirmação sem ressalva relevante.
- `CONFIRMADA COM RESSALVA`: a fonte sustenta a ideia geral, mas a redação precisa limitar escopo, condição, prazo, sujeito ou dispositivo.
- `IMPRECISA`: a afirmação aponta norma correta, mas erra artigo, nomenclatura, alcance, terminologia ou grau de obrigação.
- `SEM SUPORTE NA FONTE`: a norma foi consultada e não sustenta a afirmação.
- `CONTRADITÓRIA`: a afirmação contraria o texto da fonte consultada ou outra fonte normativa aplicável.
- `FONTE AUSENTE OU NÃO CONSULTADA`: a fonte necessária não está disponível ou não pôde ser verificada.
- `NÃO NORMATIVA`: o trecho é contextual, opinativo, histórico, pedagógico ou exemplo institucional, sem pretensão normativa verificável.

## Relatório

Para revisões substantivas, leia `references/relatorio.md` antes de redigir. Entregue relatório em Markdown com:

1. síntese executiva;
2. escopo e limitações;
3. fontes consultadas;
4. achados por alegação, com status, trecho analisado, fonte, evidência e recomendação;
5. lacunas da base, quando houver normas citadas mas ausentes;
6. redações sugeridas, quando útil.

Sempre cite o caminho local da fonte usada e o artigo, inciso, parágrafo, seção ou item analisado. Não substitua leitura da fonte por conhecimento interno.
