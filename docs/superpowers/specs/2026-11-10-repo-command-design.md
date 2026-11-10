# Abertura por repositório

Comportamento aprovado pelo usuário em 2026-11-10: comando curto `left-undone`
na pasta do repo abre a única sessão ativa, ou seleciona entre várias do repo.
Reutiliza o painel existente. Sessões encerradas conservam dados, mas precisam
ser retomadas para abrir um painel vinculado. Não agrega listas entre sessões.

## Abordagens
- Escolhida: filtrar sessões por repo, preservando identidade e listas individuais.
- Alternativa: painel agregado por repo; exigiria indicar e rotear a origem de cada tarefa.

## Implementação
Python stdlib; sem dependências. Sem argumentos equivale a `open --repo .`.
`open` explícito preserva o seletor global; `--pane` + `--session` preservam abertura exata.
Raiz Git física identifica o checkout (worktrees separados); sem Git usa pasta exata.
O cwd vem do histórico com UUID correspondente; nunca serve como autorização de envio.
Correção aprovada durante implementação: opções no próprio terminal, nunca popup.
Com TTY, curses roda no terminal chamador; sem TTY, abre seletor em split Herdr.
Split recebe caminho absoluto por variável própria, pois seu cwd pode ser o do plugin.
Seletor mostra agente, pane, UUID, conta e contagem de itens abertos.
Instalador cria link em ~/.local/bin/left-undone, recusando conflito com outro executável.
Listas, coleta, validação de identidade e ações de mouse/teclado permanecem iguais.
