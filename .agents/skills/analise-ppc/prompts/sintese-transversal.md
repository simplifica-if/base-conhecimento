# Síntese Transversal da Análise de PPC

Você fará uma revisão transversal depois que todos os sub-agentes concluírem seus grupos de fichas.

## Entrada que você receberá

1. O `PPC.md` completo.
2. O `resultados-subagents.json` coletado dos grupos.
3. O `cnct_contexto`, quando disponível.
4. O `contexto_estrutural`, quando disponível.
5. Os achados `fundamentacao_normativa` registrados nas respostas das fichas, quando existirem.
6. O bloco `validacoes_cruzadas`, com as validações transversais canônicas e seus IDs.

## Tarefa

Avalie as validações de `validacoes_cruzadas.validacoes` que forem aplicáveis ao PPC e aos resultados das fichas. Procure inconsistências que só aparecem ao comparar respostas de fichas diferentes, como divergências entre identificação, perfil do egresso, matriz, ementário, carga horária, AEE, estágio, infraestrutura, CNCT e base normativa. Em cursos técnicos integrados, verifique especialmente se fundamentos legais, concepção do curso e referências finais tratam de modo coerente a DCNEM vigente e as Diretrizes Curriculares Nacionais Gerais da Educação Profissional e Tecnológica.

Use os achados `fundamentacao_normativa` para detectar padrões transversais: norma citada sem suporte, norma antiga usada como fundamento vigente principal, afirmação normativa sem fonte consultada, conflito entre CNCT e texto do PPC ou generalização indevida de regra restrita.

Para estágio, use também `cnct_contexto.correspondencia.estagio`, `cnct_contexto.estagio_ppc` e `cnct_contexto.comparacoes.estagio_cnct` quando disponíveis, conferindo se CT-CURR-20, CT-CURR-21, CT-CURR-24 e CT-CURR-25 são coerentes entre si e com a matriz.

Para convênios de estágio, procure contradições entre a seção narrativa, convênios, campos de estágio e responsabilidades do campus, especialmente quando o PPC tratar convênio como exigência indistinta sem separar TCE/Plano de Estágio das hipóteses específicas de convênio prévio.

Quando uma validação cruzada exigir conferência aritmética, registre a memória de cálculo no próprio alerta. Use a `descricao` para resumir a inconsistência encontrada e inclua em `evidencias` as etapas numéricas essenciais, como conversão de janelas de horário em minutos, quantidade estimada de aulas, semanas equivalentes, conversão de hora-aula para hora-relógio e comparação com a carga horária declarada. Se os dados forem insuficientes para fechar a conta, indique exatamente quais dados faltam ou quais unidades estão ambíguas.

Preencha `evidencias` preferencialmente como objetos estruturados com `trecho`, `secao`, `localizador`, `papel`, `fonte` e, quando houver âncoras do PPC disponíveis, `anchor`. Use uma evidência por ponto relevante do PPC. O campo `papel` deve indicar a função daquele ponto no problema transversal, por exemplo `ponto_de_conflito`, `dado_matriz`, `dado_texto_narrativo`, `memoria_de_calculo` ou `fundamento_normativo`. Se não houver âncora, ainda assim informe `secao` e `trecho` para permitir localização posterior.

Não reescreva as respostas das fichas. Registre apenas alertas transversais úteis para a revisão humana. Todo alerta deve informar `validacao_id` com o ID da validação cruzada canônica que fundamenta o alerta.

## Convenções de matriz do modelo IFPR

Não gere alerta transversal apenas porque Atividades Complementares (AC) ou Estágio Supervisionado (ES) aparecem na matriz com carga horária zero. Essa presença pode ser uma linha-padrão do modelo.

Considere consistente quando:

- a carga horária de AC/ES for 0;
- o texto declarar que AC/ES são opcionais, não obrigatórios ou não exigidos;
- AC/ES não forem somados à carga horária obrigatória de integralização.

Gere alerta somente se houver:

- carga horária obrigatória diferente de zero;
- texto dizendo que é obrigatório, mas matriz com zero;
- matriz ou totais computando AC/ES como carga obrigatória;
- exigência de AC/ES para aprovação, certificação ou diploma.
- estágio obrigatório sem componente curricular nem justificativa para outra forma de organização;
- estágio não obrigatório tratado em algum ponto como requisito de aprovação, certificação ou integralização.
- contradição entre decisão macro, organização/orientação, convênios ou campos de estágio nas fichas CT-CURR-20, CT-CURR-21, CT-CURR-24 e CT-CURR-25.

## Saída obrigatória

Retorne somente JSON válido:

```json
{
  "alertas_transversais": [
    {
      "id": "ALERTA-001",
      "validacao_id": "VC-01-03-11-NORMAS",
      "titulo": "Título curto",
      "criticidade": "BLOQ | OBRIG | REC",
      "descricao": "Descrição objetiva do problema transversal.",
      "fichas_relacionadas": ["CT-IDENT-01"],
      "evidencias": [
        {
          "secao": "5.6 Matriz curricular",
          "trecho": "Trecho ou referência textual",
          "localizador": "Título, item ou página, quando identificável",
          "papel": "ponto_de_conflito",
          "fonte": "PPC.md",
          "anchor": {
            "block_id": "ppc-b00042",
            "quote": "Trecho exato dentro do bloco, quando disponível"
          }
        }
      ],
      "revisao_humana_obrigatoria": true
    }
  ]
}
```

Se não houver alerta transversal relevante, retorne `{"alertas_transversais": []}`.
