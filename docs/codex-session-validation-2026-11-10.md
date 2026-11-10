# Validação ao vivo: troca e retomada Codex

Resultado: **reprovada na transição de sessão; persistência aprovada**.
Codex CLI/app-server 0.167.0, integração Herdr Codex v8. Nenhum registro manual
de UUID foi usado neste teste. Sessões descartáveis, tarefas sintéticas e estado
SQLite separado; nenhuma conversa real foi trocada/encerrada pelo teste.

## Passou
- Sessão A recebeu UUID nativo após primeira resposta.
- Depois de B receber UUID nativo, verify(A) recusou o vínculo e o coletor A
  exibiu erro sem apagar os itens.
- /resume A seguido de primeira resposta recuperou UUID A e reutilizou o painel.
- Encerrado o processo Codex de teste, o vínculo antigo foi recusado.
- `codex resume <A>` em novo processo, seguido de primeira resposta: novo PID,
  vínculo antigo recusado, painel substituído, itens/seleção/baixa manual preservados.
- Recuperação de contexto a partir de CODEX_THREAD_ID sem HERDR_* encontrou o
  pane correto no novo processo, usando os dados reais do Herdr.

## Falhou — UUID nativo desatualizado
1. Sessão A: 01a1c597-3399-7851-9d20-f51931456fe1.
2. /new deixou a interface vazia, mas agent get continuou retornando A.
3. verify(A, ready=True) aceitou, mesmo após tempo suficiente para a UI mudar.
4. send(A, mensagem sintética LU-STALE-ROUTE-6e42) foi aceito e a mensagem
   chegou à nova sessão B, 01a1c598-4d14-7b23-9182-b4812944a500.
5. Somente após interação B o Herdr passou a informar B.
6. /resume A também exibiu o histórico A enquanto a API ainda informava B;
   após mensagem direta ao Codex, voltou a informar A.

Não é apenas a corrida curta entre verificar e enviar: a API já oferece uma
identidade antiga antes da chamada de verificação. A causa observada é atraso
na atualização da identidade nativa. A correção exata no evento/integrador ainda
precisa ser investigada; não foi alterado código de runtime nesta validação.

## Evidências
`docs/evidence/codex-session-lifecycle/`: before/after da API e conteúdo terminal,
resultado de envio, mensagens reais separadas por role user/assistant (não simples
busca de substring, pois memória injetada pode conter referências a outras sessões),
e verificação da persistência após novo PID.

53 testes automatizados passaram; eles não detectaram o UUID nativo desatualizado.
Os painéis/coletores de teste foram encerrados. As novas solicitações do usuário
(falha UUID ausente, botão Coletar agora, commit/push e distribuição SSH) foram
adicionadas ao painel real e ao TODO, sem implementar essas mudanças neste teste.
