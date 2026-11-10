# Conversa ativa do Codex após /new e /resume — 2026-11-10

Resultado: **correção PARCIAL validada ao vivo**. O vínculo antigo é recusado
nos dois casos; /resume para conversa já confirmada no mesmo processo é
reconhecido antes da primeira mensagem; /new continua exigindo a primeira
mensagem direta para a conversa nova ficar disponível.

## Causa e fontes descartadas
- Codex 0.167.0 dispara SessionStart (e SessionEnd) só na volta seguinte; o hook
  Herdr v8 depende de SessionStart. Registros do ai-memory confirmam o atraso.
- Logs `logs_2.sqlite` só têm `thread_id` por processo quando o TUI usa app-server
  in-process; TUIs ligados ao daemon (a maioria) não têm. Descartado.
- A thread nova só grava rollout na primeira volta; antes disso não há histórico.

## Mecanismo
`left_undone/codex_identity.py`, usado por `candidates()` e `verify()` só para Codex:
1. Prova de origem do título: `/proc/PID/cmdline` do processo verificado tem
   `-c tui.terminal_title=["thread-id"]` (último override vence). Bloqueia se
   faltar, se outro valor, se override ambíguo (`tui={...}`, chave com aspas,
   índice), se `/etc/codex/managed_config.toml` define título, ou se
   `config.toml` da conta foi gravado depois do início do processo, qualquer
   que seja o conteúdo (a tela de título do TUI salva lá e aplica na hora; uma
   regravação posterior pode remover o campo sem mudar o título em execução).
   Arquivo atual de config nunca é usado como prova.
2. Título inteiro = um prefixo 8-4-4-4-5 (truncamento do Codex) com `...`
   opcional; texto extra ou dois UUIDs bloqueiam.
3. Herdr e título concordam → UUID completo confirmado; registrado em
   `codex-confirmed.json` (estado local, lock) por conta+pane+terminal+PID+início.
4. Herdr diverge do título → aceita só UUID completo já confirmado nessa mesma
   chave cujo prefixo seja o exibido; zero → bloqueia. Em qualquer ramo, inclusive
   quando o Herdr concorda, mais de um UUID confirmado com o prefixo → ambíguo.
   Entradas de processos encerrados são descartadas.
O prefixo nunca escolhe histórico e nunca é reportado ao Herdr.

## Validação ao vivo
Sessão Herdr isolada `lu-test` (tmux 140x45; servidor real intocado), Codex
0.167.0 descartável em `/tmp/lu-title-test`, gpt-6-luna low, read-only, estado
Left Undone separado. A=01a1c6d9-7870-78a2-a755-e75580bcd10b,
B=01a1c6da-1640-7cf0-9a94-b1071e5efa9b. Evidência local (ignorada):
`docs/evidence/codex-active-thread/`.

| Passo | Herdr | Título | Resultado |
|---|---|---|---|
| A após 1ª volta | A | A | candidates=A; verify(A) aceito |
| /new, antes de qualquer mensagem | A | B | verify(A) **recusado**; candidates vazio com motivo |
| send(A) nesse estado | A | B | **recusado**; texto não apareceu no pane |
| 1ª mensagem direta em B | B | B | B aceito; A recusado |
| /resume A, antes de mensagem | B | A | **A aceito**, B recusado |
| send(A) sintético `LU-T-SEND-A-7f3c` | B | A | chegou só ao histórico de A (user+assistant); nada em B |
| novo PID, `["thread-title"]`, A renomeada para o prefixo de B | — | igual ao prefixo de B | **recusado** (origem não nativa) |
| novo PID, `["thread-id","thread-title"]` | — | A … \| B … | **recusado** |
| novo PID `["thread-id"]`, `codex resume A` | nenhum | A | recusado (não confirmado neste processo) |
| 1ª mensagem direta | A | A | A aceito |

Título fica igual durante `working` (sem spinner). /new em sequência rápida
gerou prefixos com os mesmos 8 primeiros caracteres (`01a1c6d5-…`) mas
diferentes nos 25; colisão de 25 não foi reproduzível e é tratada como ambígua.

Servidor real, somente leitura: todos os Codex atuais aparecem como
"Codex iniciado sem -c ...", ou seja, ficariam bloqueados com esta versão.

## Testes
`python3 -m unittest discover -s tests` → 114 OK após a 3ª passada (18 novos em
`tests/test_codex_identity.py`: nome/projeto com prefixo, config atual sem
override, `--ignore-user-config`, vários UUIDs, prefixos curtos, config salva
após início (inclusive campo removido), managed/overrides ambíguos, /new, /resume, escopo por
processo/pane/terminal, processo morto, prefixo duplicado nos dois ramos, histórico não
confirmado, verify/send seguindo a conversa ativa, Claude inalterado, fallback Python 3.10).

## Revisão (2ª passada)
Duas lacunas apontadas pelo Codex revisor, reproduzidas e corrigidas:
1. Config regravada sem `terminal_title` depois de `/title` reabilitava a prova.
   Agora qualquer gravação do `config.toml` após o início bloqueia até reabrir o
   Codex. Conferido: iniciar Codex em pasta confiável não grava a config.
2. Colisão de prefixo era ignorada quando o UUID nativo também casava. Agora a
   ambiguidade é verificada nos dois ramos.
Sequências exatas da revisão: `docs/evidence/codex-active-thread/16-review-sequences.txt`.
A validação ao vivo da tabela acima foi feita antes dessa passada; as duas
mudanças só acrescentam bloqueios em casos que não ocorreram no roteiro
(config não foi gravada; nenhum prefixo repetido), mas o roteiro não foi refeito.

## Limites e pendências
- /new antes da primeira mensagem: só proteção. Falta UUID completo verificável.
- /resume para conversa nunca confirmada no mesmo processo: espera 1ª mensagem.
- Pré-visualização transitória na tela de configuração do título, ou mudança
  aplicada ao vivo cujo salvamento falhe, não é detectável; exigiria escolher
  `thread-title` com nome igual a prefixo — risco residual documentado.
- QUALQUER alteração do `config.toml` após o início bloqueia, não só um
  `terminal_title` diferente: inclusive `/model` persistido, confiar numa pasta
  ou outro Codex gravando a config. Todos os Codex já abertos ficam bloqueados
  até serem reabertos. Conservador por decisão da revisão.
- Python: mínimo continua 3.10. Sem `tomllib` (3.10), overrides só valem se
  forem JSON-compatíveis (`["thread-id"]`) e qualquer menção a `terminal_title`
  na config gerenciada bloqueia. Testado simulando ausência de `tomllib`; não
  havia Python 3.10 real nesta máquina.
- Requer lançar Codex com o override; sem isso Codex fica bloqueado. Alterar
  config global/atalhos de lançamento ainda não foi feito (coordenar com Vini).
- Janela entre verificação e `agent prompt` continua (outra pendência, API Herdr).
