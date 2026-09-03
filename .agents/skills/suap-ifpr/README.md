# SUAP IFPR

Esta skill localiza procedimentos na documentação oficial do IFPR e orienta a navegação autenticada no SUAP. A primeira versão prioriza Ensino, Cursos, Coordenação de Curso, Registro Acadêmico, docentes e estudantes.

## Configuração

Defina na raiz do projeto, em `.env.local`:

```dotenv
SUAP_USUARIO=seu_usuario
SUAP_SENHA=sua_senha
```

Variáveis já presentes no processo têm precedência sobre `.env.local`. A skill nunca deve imprimir os valores. Confira apenas a presença da configuração com:

```bash
python3 .agents/skills/suap-ifpr/scripts/tutoriais.py config
```

O login automatizado cobre apenas usuário e senha. CAPTCHA, autenticação em duas etapas, Gov.br e troca obrigatória de senha exigem intervenção humana.

## Uso

Exemplos de solicitação:

```text
Use $suap-ifpr para localizar no SUAP os dados gerais deste curso.
Use $suap-ifpr para descobrir como matricular um aluno avulso em um diário.
Use $suap-ifpr para consultar as vagas cadastradas para este curso, sem alterar dados.
```

A skill consulta por padrão. Operações que escrevem no SUAP dependem de pedido explícito e de confirmação antes do envio final.

## Catálogo de tutoriais

`references/tutoriais.json` é um índice de descoberta. Ele guarda somente metadados da categoria SUAP e aponta para o conteúdo vivo no portal oficial.

Pesquisar:

```bash
python3 .agents/skills/suap-ifpr/scripts/tutoriais.py buscar matriz curricular
python3 .agents/skills/suap-ifpr/scripts/tutoriais.py buscar --json diploma digital
```

Atualizar explicitamente o índice:

```bash
python3 .agents/skills/suap-ifpr/scripts/tutoriais.py atualizar
```

A atualização usa a API REST pública do WordPress, percorre a categoria raiz `SUAP` e todas as suas subcategorias e grava uma saída determinística. Ela não copia o corpo dos artigos, imagens ou anexos.

## Validação

```bash
python3 .agents/skills/suap-ifpr/scripts/tutoriais.py validar
python3 -m unittest discover -s .agents/skills/suap-ifpr/tests -v
codex_skills_dir="${CODEX_HOME:-$HOME/.codex}/skills"
uv run --no-project --with pyyaml python "$codex_skills_dir/.system/skill-creator/scripts/quick_validate.py" .agents/skills/suap-ifpr
```

O smoke test faz login, mantém os cookies apenas em memória e consulta uma página de curso sem enviar formulários de alteração. A saída mostra somente o título e o caminho da página:

```bash
python3 .agents/skills/suap-ifpr/scripts/tutoriais.py auth-check
```

## Segurança

- `.env.local` deve permanecer fora do Git.
- Credenciais não devem aparecer em argumentos de linha de comando nem em logs.
- Não salve cookies, HTML autenticado ou exportações com dados pessoais dentro da skill.
- Quando o perfil não puder acessar uma tela, registre a limitação de permissão; não trate a tela como inexistente.
