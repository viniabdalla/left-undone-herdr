# Validação — seletor global e data de criação

2026-11-16. Implementado em worktree `left-undone-herdr-picker-dates`, branch
`feat/picker-created-order`, a partir da main `0ae0c31`. Preservado o worktree
`left-undone-herdr-codex-title` e seu commit exclusivo de identidade Codex.

## Verificações

- Base: 117 testes passaram antes de alterar código.
- Reproduzidas as falhas do comando curto e do foco ao reutilizar painel.
- Testes de criação falharam antes da implementação; validam timestamp da fonte,
  edição, replay, registros antigos, importação, tombstones e múltiplas conexões.
- Teste PTY validou tecla 6, clique no botão e preservação da seleção durante
  inversões, envio, fila e confirmação. Desconectar a inversão faz o teste falhar.
- Suíte final: `python3 -m unittest discover -s tests -q` — 128 testes OK no
  worktree e no checkout instalado. `compileall` e `git diff --check` OK.
- Revisão independente: nenhum problema no código; pedido de preservar duas
  entradas antigas do TODO foi avaliado contra a regra de manter só dez em Feito.
- Painel descartável no Herdr, com estado em `/tmp`: ordem recente e antiga,
  datas no horário local e desconhecidos ao final. Snapshots locais ignorados:
  `docs/evidence/2026-11-16-creation-order-newest.txt` e `...-oldest.txt`.
- Comando instalado sem argumentos executado de `/tmp` e com estado temporário:
  abriu seletor global incluindo as duas conversas pedidas. Snapshot local:
  `docs/evidence/2026-11-16-global-picker.txt`. Nenhuma conversa escolhida no teste.
- Painel e seletor de teste fechados; estado descartável removido.

## Aplicação local

Arquivos revisados aplicados ao checkout main sem commit, reset, merge ou push.
Backup SQLite consistente e local em `docs/evidence/` antes de carregar a nova
versão nos painéis. Recarregados apenas os dois painéis abertos nesta conversa;
confirmados botão de ordem e datas na renderização. Herdr permaneceu ativo.
Testes não usaram a base nem sessões reais; a recarga final foi uso da instalação.

## Limites

Registros anteriores sem data comprovável continuam desconhecidos; nenhum ID
ou timestamp mutável foi convertido em data de criação. Exportação Markdown
mantém seu formato: importar em outro estado representa nova entrada local.
A preferência de ordem dura até fechar o painel. Outros painéis já abertos
carregam a nova interface quando forem fechados e reabertos. As quatro melhorias
de confiabilidade da curadoria continuam fora desta entrega.
