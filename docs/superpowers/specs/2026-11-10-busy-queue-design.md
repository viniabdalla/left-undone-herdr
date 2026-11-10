# Confirmar fila quando o agente estiver ocupado

Comportamento aprovado por Vini: Enviar com agente ocupado pergunta se deseja
colocar o pedido na fila do próprio agente. Confirmar enfileira; cancelar
preserva a seleção. Agente livre continua recebendo diretamente. Pendências
enviadas ou enfileiradas continuam abertas na lista.

Usar a fila nativa do Codex (`codex queue --thread UUID --message TEXT`),
na conta verificada, sem `--resume` ou mensagem de interrupção. O CLI Claude
instalado não oferece uma API equivalente: informar indisponibilidade e
preservar seleção. Não criar fila interna/polling de envio nem alterar a
proteção de UUID em desenvolvimento no outro worktree.

Congelar IDs/texto selecionados ao pedir envio. Revalidar identidade e itens
ao confirmar. Alteração ou conclusão dos itens cancela o pedido, sem enviar.
Falha/timeout não retenta nem limpa seleção; confirmação de sucesso limpa
somente a seleção enviada. A confirmação aceita mouse e teclas 1/2/Esc.

Abordagens: fila nativa por UUID preserva o destino e o controle do harness;
simular Enter durante trabalho pode interromper o turno; fila própria poderia
reenviar a sessão errada após uma troca e não é o comportamento solicitado.
