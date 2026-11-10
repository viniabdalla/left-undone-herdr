# Listas por projeto e recuperação de identidade

O usuário aprovou tarefas compartilhadas por projeto e promessas privadas por
conversa, priorizando isso antes da troca automática do destinatário visível.

## Verificado

- Suite completa: 69 testes aprovados; compileall e git diff --check sem falhas.

- `recover --marker` identificou corretamente a conversa real por histórico,
  commentary recente, pane visível e foreground PID, e confirmou o hook nativo.
- Dois painéis Codex reais, em sessões distintas, mostraram as mesmas seis
  tarefas existentes. Selecionar uma tarefa no segundo painel não selecionou
  essa tarefa no primeiro. Nenhum prompt foi enviado por esse teste.
- Dados antigos preservados; cópia consistente do SQLite antes da ativação.
- Testes automatizados cobrem sessões Codex/Claude, projeto diferente,
  promessas privadas, baixa compartilhada, importação repetida, seleção privada,
  reabertura, snapshots independentes e associação explícita persistente.
- Revisão independente encontrou e ajudou a reproduzir três condições corrigidas:
  descoberta atrasada sobrescrevendo projeto explícito, promessa privada impedindo
  importação compartilhada e seleção concorrente ressurgindo após conclusão.
- Teste de consumo da skill: agente passou a usar recover --marker e recusou
  declarar /new seguro automaticamente; associação explícita de projeto correta.

## Limites preservados

As listas são locais a cada máquina. A integração Herdr ainda pode manter UUID
antigo antes da primeira interação após /new ou /resume. Compartilhar tarefas
e recuperar pontualmente o registro não resolvem essa detecção automaticamente.
O envio permanece pela API Herdr, sem precondição atômica por UUID.

Capturas textuais reais dos dois panes, backup e resultado estruturado ficam em
`docs/evidence/` (ignorado pelo Git). Uma captura do desktop não mostrava Herdr e
foi descartada; a validação visual usou a renderização terminal dos panes e testes PTY.
