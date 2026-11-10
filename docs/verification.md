# Verificação — 2026-11-10, omarchy2

## Automatizada

`python3 -m unittest discover -s tests -v`: 21 testes, todos passaram.
Inclui importação/exportação, isolamento por sessão, validação de JSON,
linha parcial, turno repetido, retomada de cursor, falha/retry do analisador,
planos Codex, tarefas Claude, baixa de promessas, conta com log compartilhado,
verificação de troca de sessão/terminal/foreground PID, seleção e envio,
paginação, reabertura após processo substituído e startup lento.

O teste de encerramento usa um PTY real e subprocessos: SIGTERM na UI deve
encerrar o coletor. Quatro regressões da revisão independente foram vistas
falhar antes da correção e passaram depois. Nenhum teste depende de chamar
modelos pagos.

## Execução real

- Herdr cliente/servidor 0.9.1, protocol 22; plugin link aceito sem warnings.
- A ação `open` aparece em `herdr plugin action list`.
- Skill instalada para ambos os agentes e wrapper executável.
- Codex gpt-6-luna/low, CLI autenticado: prompt sintético contendo trabalho
  concluído, promessa abandonada, nova promessa, pergunta e obrigação do
  usuário retornou `done: [1,2]`, `add: ["Add retry tests."]`.
- Conversa descartável Codex, pane w1P:p3, UUID
  01a1c3d1-4222-7640-9a8f-1ffd68ecdd5e: agente prometeu poema; coletor detectou
  uma promessa; painel aberto à direita, foco original preservado.
- Teclas `a`, `1` no painel enviaram a pendência para essa conversa. O agente
  respondeu com poema de duas linhas. Analisador encerrou promessa: zero
  pendências. Abrir novamente com painel vivo retornou `reused: true`.
- Esc fechou o painel; reabertura recuperou o estado sem repetir a análise.
- Fechamento externo via plugin pane close encerrou o coletor real.
- Duas aberturas simultâneas retornaram o mesmo pane (uma criação e um reused).
- Panes descartáveis foram encerrados após o teste; foco e panes originais preservados.

## Tentativa inicial bloqueada por cota (resolvida abaixo)

Claude Haiku autenticado retornou `429 usage_limit_reached`, limite de cinco
horas da conta. Não foi possível demonstrar o ciclo completo **ao vivo** no
Claude. O formato do histórico real foi conferido (assistant/end_turn e
assistant/tool_use) e o adaptador está coberto por testes, mas isso não
substitui uma demonstração completa após a cota voltar.

## Limitação da API

O Herdr não aceita precondição de sessão no `agent prompt`; existe janela
TOCTOU entre a checagem de identidade e o envio. Documentado no README e na
skill. O plugin recusa inconsistências conhecidas e nunca repete envios.


## Tropico-2 — recuperação do contexto em 2026-11-10

Codex TUI tinha contexto Herdr; ferramentas executadas pelo app-server não.
Integração nativa Codex estava ausente. Instalada sem reiniciar servidores.
Conversa atual confirmada por marca aleatória em commentary, histórico real,
conteúdo visível do pane e PID foreground. Hook nativo registrou o UUID real.

Wrapper agora recupera ambiente por UUID nativo exato, consultando o socket
de cada processo Codex interativo e checando o foreground no mesmo servidor.
Ausência, divergência e duplicidade recusam a recuperação. A revisão independente
identificou troca de socket sem revalidação; teste de regressão e correção incluídos.
25 testes passaram. Skill validada com quick_validate. Plugin/skill instalados,
checklist importado e deduplicado; reabertura retornou reused:true.
Renderização conferida via herdr pane read: docs/evidence/checklist-tropico-2.txt.
A tela gráfica local pertence a outro desktop; não foi usada como evidência do painel remoto.

A troca/retomada automática de conversas através do app-server ainda requer
validação ao vivo; não foi simulada nesta conversa em andamento. O teste Claude foi concluído na seção abaixo; o limite de envio atômico da API permanece.


## Claude ao vivo — concluído em 2026-11-10, tropico-2

Claude Code 2.1.319, Haiku 5.5/low, conta autenticada. Integração nativa
Claude v10 instalada sem reiniciar o servidor. Sessão descartável
8831ff18-2100-40c6-8bfe-2a9d9b2bd98e, agente em w3:p5, painel em w3:p6.

1. Claude prometeu escrever um poema de duas linhas quando lembrado.
2. Coletor real e analisador Haiku criaram uma promessa no painel.
3. Teclas a e 1 selecionaram e enviaram a promessa exclusivamente ao Claude.
4. Claude recebeu "You left this undone" e escreveu o poema.
5. Analisador concluiu automaticamente: zero itens abertos, status=done,
   dismissed=0 (não houve baixa manual na sessão de teste).
6. Painel e agente descartáveis fechados; foco devolvido ao checklist original.
   Pendência de validação Claude retirada manualmente do checklist principal.

Evidências em docs/evidence/claude-live-before.txt,
claude-live-conversation.txt, claude-live-after.txt e claude-live-state.json.


## Mouse e quebra de texto — 2026-11-10

UI em curses com layout por células, hit areas por linha e eventos SGR.
Tarefas longas quebram na largura e continuam em páginas quando excedem a altura.
Botões de seleção/envio/conclusão/exportação/importação/páginas/fechamento,
roda para páginas e seletor de conversas com Abrir. Teclado preservado.

40 testes passaram em tropico-2 e omarchy2. Teste com PTY/ncurses real cobriu
clique em continuação, envio uma única vez, resize e conclusão por teclado.
Revisão independente encontrou casos de painel pequeno, seleção escondida após
resize do picker e ZWJ: todos reproduzidos por testes antes das correções.
Revisão final limpa. Skill passou quick_validate.

No Herdr real, eventos SGR enviados ao painel descartável confirmaram seleção
em linha continuada, botão Concluir e roda nas duas direções. O painel de teste
foi fechado. O painel original foi reaberto com a mesma lista e seleção e a
largura anterior restaurada (48 colunas). A própria pendência de mouse foi
selecionada e concluída usando os novos controles. Evidências textuais reais:
docs/evidence/mouse-herdr-*.txt e mouse-installed-*.txt. Não se trata de captura
gráfica de clique físico no cliente remoto: a validação usou eventos de terminal
reais através do Herdr, além de PTY.
# Atalho por repo e seletor no terminal — 2026-11-10

- Suíte completa: 53 testes passaram (`python3 -m unittest discover -s tests -v`).
- Casos novos: repo/subpasta/symlink; worktrees distintos e overrides Git herdados;
  UUID/cwd ausente; uma/várias/zero sessões; dados salvos inválidos; contagens isoladas;
  seletor inline com TTY e split sem TTY; instalador idempotente e conflito preservado.
- `left-undone` instalado em ~/.local/bin; executado em git-todo retornou
  `{"reused": true, "pane": "w3:p8"}`. Executado no projeto left-undone-herdr
  informou corretamente que não havia sessão ativa verificável daquela pasta.
- Seletor com filtro de repo conferido no Herdr em split temporário, removido
  ao fim: `docs/evidence/repo-picker-live.txt`.
- Após correção solicitada pelo usuário, `TERM=xterm-256color left-undone open`
  executado em PTY real exibiu o seletor no próprio terminal, agente/UUID/3 pendências;
  Enter reutilizou o painel e saiu com código 0, restaurando o terminal.
- Manifesto atualizado para seletor split (sem dimensões exclusivas de popup);
  `python3 install.py` validado com sucesso pelo Herdr instalado.
- Validação visual por conteúdo terminal renderizado; não foi captura gráfica do cliente remoto.
