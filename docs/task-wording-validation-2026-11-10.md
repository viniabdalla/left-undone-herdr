# Validação da linguagem das pendências — 2026-11-10

Alterados apenas os prompts de promessas e curadoria, usados por Codex e Claude.
Formato aprovado: termo técnico junto de uma tarefa curta em linguagem simples.

Teste com o consumidor real `Analyzer`, Codex gpt-6-luna / low e conta vinculada
à conversa. Nenhuma resposta de teste foi importada para o estado do projeto.
A primeira instrução genérica ainda produziu “corrigir UUID obsoleto” e “enviar
de forma atômica”; foi reforçada para separar rótulo técnico e ação simples.

Respostas após o ajuste, validadas pelos esquemas existentes:

- Promessas: “Codex /resume / UUID: reconhecer a conversa certa ao retomar.”
- Curadoria: “API Herdr / envio atômico por UUID: garantir o envio à conversa
  certa mesmo se ela mudar durante o envio.”
- Termos não presentes nos exemplos do prompt: “Debounce do botão: impedir que
  cliques repetidos iniciem várias coletas.” e “Cache por sessão: evitar analisar
  o mesmo texto mais de uma vez.”
- Pergunta/explicação sobre API, sem trabalho solicitado: nenhuma ação de curadoria.

96 testes existentes passaram. `compileall` e `git diff --check` sem erros.
Revisão independente dos prompts sem achados. Não foram criados testes que
apenas verificam strings das instruções. Claude não foi chamado neste teste;
usa os mesmos prompts, mas sua qualidade de redação não foi avaliada ao vivo.

Painel desta conversa recarregado para aplicar os novos prompts. Pendência
correspondente concluída pelo ID exato, preservando os três itens anteriores.
Nenhuma migração de estilo foi feita em itens antigos ou tarefas nativas.
