# Seletor global e ordem por criação

Aprovado por Vini na conversa de 2026-11-16: `left-undone` sem argumentos sempre apresenta as conversas verificáveis do Herdr, independentemente da pasta. Escolher uma conversa abre seu painel; se já existir, mostra o painel existente. `--repo` continua sendo um filtro explícito.

O painel começa com as mais recentes primeiro. Um botão no topo, também pela tecla 6, alterna entre mais recentes e mais antigas. Cada item mostra data/hora local de criação; alterações de texto não mudam essa data. Datas desconhecidas ficam ao final em ambas as ordens, com desempate por ID; a ordenação não agrupa por origem. A escolha de ordem vale durante a abertura atual. Seleções continuam ligadas ao ID.

## Abordagens

Implementar no painel a ordenação da lista existente evita alterar a ordem interna usada pelos consumidores atuais. Uma tabela independente com timestamp imutável mantém a migração compatível com processos antigos e separada do relógio de proteção da curadoria. Usar IDs como datas ou reaproveitar o timestamp mutável da curadoria inventaria informação: não será feito. Registros legados sem fonte comprovável mostram “data desconhecida”. Novas importações usam a data de entrada local; coletas usam o timestamp da transcrição quando válido.

## Limites

Python stdlib, sem trocar modelos. Preservar proteção de identidade, concorrência, histórico, tombstones e formatos Markdown existentes. Não implementar as quatro melhorias de curadoria neste trabalho. Não alterar o worktree fix/codex-active-thread, não fazer commit/push ou reiniciar o Herdr. Validar usando somente estado temporário e sessões de teste; instalar arquivos somente após testes.
