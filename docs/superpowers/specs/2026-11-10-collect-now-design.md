# Coletar agora

Comportamento aprovado: botão no painel solicita coleta imediata da conversa
vinculada, com andamento/erro visível; coleta automática permanece ativa.

## Abordagem

Reutilizar o coletor único e seu bloqueio, solicitando uma rodada via arquivo
local por vínculo. Evita iniciar um segundo processo ou usar sinais antes da
inicialização. O atalho 5 compartilha a ação do clique. Pedidos repetidos são
agrupados; pedidos durante análise aguardam a rodada atual. O pedido interrompe
a espera normal ou de erro, sem ignorar a validação da identidade. A leitura
permanece incremental, sem reanalisar respostas processadas ou alterar modelos.

Não muda envio, seleção, conclusão, associação de projetos ou UUID.
