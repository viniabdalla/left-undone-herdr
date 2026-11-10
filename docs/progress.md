# Left Undone — implementação do plano aprovado

Plano: plugin Herdr + skill; Python/curses/SQLite; tarefas e promessas por sessão;
Claude Haiku e Codex gpt-6-luna low; painel direito; letras/1/2/3/4;
coleta incremental, envio com vínculo validado, importação aditiva, testes reais.

1. Estado e adaptadores; 2. Analisadores; 3. Vínculo/Herdr e painel;
4. Empacotamento/skill; 5. Testes e revisão.

Decisão: projeto novo e vazio, implementação diretamente na nova pasta
left-undone-herdr, com symlink no nome antigo para preservar a sessão ativa.
Não existe repositório base ou worktree a isolar.
Decisão: sem sessão identificada pelo Herdr, envio será recusado; contexto
herdado/foco não é suficiente. Processo Linux confirma conta, não destinatário.
Tarefa operacional: 9a097abf-870c-465a-b6ab-97f406c1b100.

Implementados: estado/adaptadores; analisadores; vínculo; curses; manifesto;
skill compartilhada Codex/Claude; instalador local sem sobrescrever conflitos.
14 testes passaram inicialmente. Codex Luna real retornou done=[1,2],
add=[Add retry tests.]; Claude real retornou API 429 usage_limit_reached.
Decisão: históricos Claude podem ser compartilhados por symlink entre contas;
a conta é sempre a do processo verificado, não é inferida do caminho do log.

Revisão independente (gpt-6-astra) identificou quatro falhas importantes:
coletor órfão após SIGTERM/SIGHUP, vínculo antigo após retomar mesmo UUID,
PID persistido frágil na deduplicação e baixa nativa impedindo reabertura.
Os quatro testes de regressão falharam antes das correções; suíte posterior:
20 testes passaram, inclusive encerramento real por sinal com PTY.
Correções: cleanup por sinal, comparação integral do vínculo, dedup pelo
processo foreground/ambiente do painel com janela de startup, e tombstone
manual distinto de conclusão nativa.

Codex ao vivo: sessão descartável detectou promessa de poema; letra a e 1
no painel enviaram exclusivamente ao agente lu-demo. Agente respondeu poema;
analisador removeu promessa ao cumprir (0 pendências). Reabertura testada.
Foco continuou no pane original. Nenhum servidor reiniciado.
Decisão: API Herdr 0.9.1 não oferece compare-and-send atômico por UUID;
implementada verificação imediata de sessão, terminal, PID foreground,
starttime, conta e histórico. Resta janela TOCTOU nativa documentada.

Verificação final ampliada: 21 testes passaram; proteção adicional evita
herdar credenciais API de outra conta do processo chamador. A skill passou
quick_validate e os módulos compilaram. Fechamento externo real encerrou
coletor; duas aberturas concorrentes criaram um único painel. Panes de demo
encerrados. Validação Claude ao vivo continua parcial por cota da conta.

2026-11-10 tropico-2: ciclo Claude ao vivo concluído com Haiku; promessa detectada, enviada pela UI, cumprida e removida automaticamente (dismissed=0). Evidências em docs/verification.md.
