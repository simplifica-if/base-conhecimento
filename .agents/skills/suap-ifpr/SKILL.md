---
name: suap-ifpr
description: Consultar e navegar no SUAP do IFPR com base nos tutoriais oficiais, especialmente em fluxos de Ensino, Cursos, Coordenação de Curso, Registro Acadêmico, docentes e estudantes. Use quando a tarefa exigir localizar um procedimento do SUAP, acessar dados no sistema ou executar uma alteração explicitamente solicitada.
---

# SUAP IFPR

Use o portal de tutoriais do IFPR para descobrir o procedimento e o SUAP como fonte do dado operacional. A cobertura mais detalhada desta versão é Ensino e Cursos; os demais módulos usam o mesmo roteamento pelo catálogo.

Para instruções de configuração e manutenção, leia [README.md](README.md). Para tarefas de Ensino, leia [references/ensino-cursos.md](references/ensino-cursos.md).

## Fluxo

1. Identifique a intenção, o módulo e se a tarefa é consulta ou alteração.
2. Pesquise o índice local antes de navegar:

   ```bash
   python3 .agents/skills/suap-ifpr/scripts/tutoriais.py buscar TERMOS
   ```

3. Abra o artigo oficial retornado e confirme no conteúdo vivo o caminho de menu, os campos e as condições atuais. O índice serve para descoberta, não substitui o tutorial.
4. Reutilize uma sessão autenticada existente. Se o SUAP redirecionar para `/accounts/login/`, use `SUAP_USUARIO` e `SUAP_SENHA` somente em `https://suap.ifpr.edu.br/`.
5. Navegue pelo caminho confirmado no tutorial e colete apenas os dados necessários para a solicitação.
6. Informe o tutorial consultado, o caminho de menu efetivamente observado e o resultado. Diferencie dado ausente de recurso indisponível para o perfil atual.

Se não houver correspondência adequada no índice, consulte a [categoria SUAP do portal oficial](https://ifpr.edu.br/tutoriais/base-conhecimento/categoria/suap/) ou sua busca. Não altere o índice durante uma tarefa operacional comum.

## Limites de segurança

- Opere em leitura por padrão. Um pedido de consulta, navegação ou explicação não autoriza alterações.
- Antes do envio final de uma alteração explicitamente solicitada, apresente o registro-alvo, o valor anterior e o novo valor e obtenha a confirmação exigida pela ferramenta de navegação.
- Nunca mostre, registre, persista ou inclua credenciais em comandos, relatórios, imagens ou mensagens. Não salve cookies ou estado autenticado no repositório.
- Se houver CAPTCHA, autenticação em duas etapas, Gov.br, troca obrigatória de senha ou falha de autenticação, pare e solicite intervenção do usuário.
- Não conclua que um recurso inexiste apenas porque o menu não aparece: o perfil pode não ter permissão.
- Não persista dados pessoais ou acadêmicos obtidos no SUAP, salvo quando o usuário solicitar explicitamente um artefato que os exija.

## Manutenção

Use `atualizar` somente em trabalho de manutenção da skill. Depois, execute `validar` e os testes descritos no README.
