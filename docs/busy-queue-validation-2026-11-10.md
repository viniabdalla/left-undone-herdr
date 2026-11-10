# Confirmação de fila com agente ocupado — 2026-11-10

Resultado: implementado para Codex local; fila Claude indisponível nesta versão.
Não incorporada a proteção parcial de UUID do worktree separado.

## Comportamento

Enviar para agente verificado com estado `working` pede confirmação. `1` ou
Colocar na fila usa `codex queue --thread UUID --message TEXT` na conta
verificada. `2`, Cancelar ou Esc volta à lista preservando seleção e página.
Agente livre continua com envio direto; bloqueado/desconhecido ou identidade
inválida não oferece fila. No Claude ocupado, informa indisponibilidade.

Seleção/textos são congelados ao iniciar o envio e revalidados ao confirmar.
Transação SQLite serializa validação e aceite da fila com alterações dos itens.
O CLI tem timeout de 20 s; não há repetição automática nem `--resume`. Isso pode
reter outras gravações da lista enquanto a confirmação externa está em curso.
Recibo do Codex deve conter o UUID exato do vínculo. Falha/recibo incerto não
limpa seleção; sucesso limpa só os itens daquele pedido, sem concluir tarefas.

## Evidências

- CLI Codex real em CODEX_HOME temporário, com rollout sintético e sem modelo:
  exatamente um item gravado em `queue_1.sqlite`, UUID e conteúdo exatos,
  inclusive texto literal com metacaracteres de shell. Nenhuma conversa real
  recebeu mensagens de teste. Isso verifica persistência na fila nativa, não
  uma execução posterior do pedido pelo modelo.
- Curses real em PTY: mouse/teclado para enviar, confirmar e cancelar; Esc
  cancela sem fechar o painel; falha preserva seleção; tarefa permanece na
  lista; cancelamento preserva página; painel muito pequeno não aceita
  confirmação invisível.
- Tests de alterações/conclusões/seleção antes da confirmação e atualização
  concorrente enquanto o pedido é aceito. Sem envio de snapshot alterado.
- Revisão independente encontrou a janela entre validação e submissão e a
  perda de paginação; ambas reproduzidas em testes RED e corrigidas GREEN.
- 107 testes passaram. `compileall` e `git diff --check` sem erros.
- Prévia visual dos layouts 40×24 e 18×12 em
  `docs/evidence/busy-queue/confirmation.png` (local, ignorada pelo Git).

## Limites

O recibo confirma que a fila aceitou o pedido, não que o agente já o executou.
Fila requer suporte a `codex queue` no CLI instalado. A validação de identidade
é a existente nesta branch; a falha de UUID antigo durante /new ou /resume
continua registrada como tarefa separada. O novo caminho de fila usa o UUID
completo do vínculo, em vez de simular teclas no terminal ocupado.
