# Investigação da identificação antiga — 2026-11-10

Resultado: **falha reproduzida novamente em /new e /resume; correção pendente**.
Nenhum código de comportamento ou integração foi alterado nesta investigação.

## Comparação com a tentativa do usuário

O usuário retomou a conversa original e abriu o Left Undone com o identificador
correto. A saída prova que a identificação estava correta naquele momento.
Ela não registra o identificador da etapa intermediária; por isso, não permite
concluir que houve uma troca A → B confirmada antes de voltar a A. Retomar A
quando o Herdr ainda informa A pode funcionar mesmo com a falha presente.

## Reprodução controlada

Codex 0.167.0, integração Herdr v8, conta existente, um painel descartável em
`/tmp`. Modelo gpt-6-luna / low como na reprodução anterior. Apenas três
respostas curtas e sintéticas, sem ferramentas. Nenhuma conversa do usuário
foi trocada; nenhum vínculo nativo foi registrado manualmente.

1. Primeira resposta de A: Herdr informou A (`01a1c6bd-90f3-7fa3-be44-d06527f3e421`).
2. `/new`: Codex exibiu conversa vazia, mas Herdr continuou informando A.
3. `/status`, sem mensagem ao modelo: Codex informou B
   (`01a1c6be-3395-7121-91ed-3ae2c8ca10ba`); Herdr ainda informou A.
4. Primeira mensagem de B: Herdr passou a informar B.
5. `/resume`, selecionando A pelo histórico sintético: Codex exibiu A;
   consultas da API após aproximadamente 0,3, 2 e 5 segundos ainda informaram B.
6. `/status`, sem mensagem ao modelo: confirmou A, enquanto Herdr informou B.
7. `candidates()` e `verify(binding_B, ready=True)` aceitaram o vínculo de B
   mesmo com A ativa. **Nenhum envio foi feito por esse vínculo.**
8. Mensagem direta na A retomada: Herdr passou a informar A novamente.
9. Encerrado somente o painel descartável; o painel real foi preservado.

## O que foi localizado

O hook instalado `~/.codex/herdr-agent-state.sh` publica o identificador recebido
no evento SessionStart. Não observa a troca da conversa visível por conta própria.
Nos testes, a atualização desse registro só se tornou visível na API depois de
uma interação com o modelo, embora `/status` já identificasse a nova conversa.
Isso localiza a divergência entre seleção da conversa no Codex e registro nativo
no Herdr. Ainda não distingue o atraso de execução do hook de um atraso na entrega
ou aplicação do evento; não foi instrumentado o stdin do hook.

O Left Undone verifica esse registro, PID, terminal, conta e histórico. Como
essas informações antigas continuam coerentes entre si no mesmo processo,
aceita o vínculo. Mais tempo de espera e reabrir o painel não resolveram a
divergência. O problema é diferente da janela curta entre verificar e enviar.

Próxima correção deve obter um sinal verificável da troca da conversa antes de
usar o vínculo, bloquear coleta/envio enquanto houver dúvida e atualizar o
destinatário apenas após confirmação. Foco, título, pasta, histórico mais recente
ou simples presença do arquivo de uma sessão não demonstram a conversa ativa.

## Evidências e limites

Saídas da API, telas `/status`, verificação aceita e identidades em
`docs/evidence/uuid-investigation-2026-11-10/` (local, ignorado pelo Git).
As telas completas contêm dados de conta e não devem ser publicadas.
Houve uma abertura transitória da tela de uso durante automação dos comandos;
ela foi fechada e a seleção A foi confirmada explicitamente no seletor e em
`/status`. As conclusões usam esses estados confirmados.

Esta investigação não valida uma correção nem encerra a pendência. A origem
exata do atraso de SessionStart ainda precisa ser localizada antes de escolher
entre corrigir a integração e adicionar uma fonte adicional de identificação.
