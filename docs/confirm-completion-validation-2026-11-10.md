# Confirmação de conclusão manual — 2026-11-10

Resultado: implementada para o botão Concluir e a tecla 2.

- Abrir a pergunta não conclui tarefas. Mostra quantidade e pergunta adequada
  para um ou vários itens. 1/Confirmar aplica a conclusão; 2/Cancelar ou Esc
  volta à lista preservando seleção e página, sem fechar o painel.
- IDs/textos são congelados ao abrir e revalidados sob transação ao confirmar.
  Mudança de texto, seleção ou estado invalida o pedido inteiro. Seleções novas
  não são incluídas numa confirmação antiga. Projeto compartilhado usa a
  seleção do usuário/painel correto e propaga a conclusão aos demais painéis.
- Reutilizado o layout modal da fila. Pergunta invisível por tamanho reduzido
  não aceita confirmação; apenas cancelar. Fluxo da fila preservado.
- Sem mudanças nas regras ou chamadas de conclusão automática pela curadoria.

Validação: 114 testes passaram, incluindo curses real em PTY com clique/teclado,
cancelamento por botão/2/Esc, preservação da página, um e vários itens,
redimensionamento pequeno e confirmação explícita antes da mutação no SQLite.
Os testes de curadoria existentes continuam passando. `compileall` e
`git diff --check` sem erros.

Revisão independente sem achados funcionais. Um teste de seleção por letras
na página 2 assumia que as letras não mudariam quando os botões surgissem;
o reflow existente muda esse mapeamento. O teste passou a clicar em IDs
estáveis após o redesenho, sem alterar a paginação do produto.

Prévia rasterizada conferida em 40×24 (3 itens) e 18×12 (1 item):
`docs/evidence/confirm-completion/confirmation.png`, local e ignorada pelo Git.
