# Distribuição por SSH — 2026-11-10

Repositório privado: https://github.com/viniabdalla/left-undone-herdr

| Máquina | Resultado |
|---|---|
| tropico-2 | Origem de desenvolvimento, Git main publicado |
| omarchy2 | Instalação antiga convertida em checkout Git, preservando cópia anterior e evidências locais |
| Omarchy novo | Clone novo, plugin/skills/comando instalados |

Tropico-1 excluída do escopo a pedido do usuário; nenhuma instalação pendente ali.

Nas duas máquinas remotas: projeto em `~/Projects/left-undone-herdr`, comando em
`~/.local/bin/left-undone`, skills ligadas para Codex e Claude. Herdr 0.9.1,
integração Codex v8, integração Claude atualizada para v10. 53 testes passaram
em cada máquina. GitHub privado acessível diretamente via Git em ambas.

Código validado no commit `1378776`; atualização posterior do TODO e deste
relatório não altera runtime. As três máquinas acompanham `origin/main`.
Registros locais de instalação/testes em `~/.local/state/left-undone-deploy/`.
Backup da instalação antiga do omarchy2:
`~/Projects/left-undone-herdr.backup-20261110-111638`.

`left-undone --help` e resolução do comando em shell interativo conferidos.
Codex 0.167.0 disponível nas duas máquinas. Claude 2.1.322 disponível; no
Omarchy novo, launcher sem conta explícita excedeu 15 segundos, enquanto shim
direto e launcher com CLAUDE_CONFIG_DIR responderam normalmente. O analisador
do Left Undone já fixa a conta verificada por essa variável.

Não foi refeito ciclo completo com LLM nas máquinas remotas nesta distribuição.
A falha conhecida de UUID antigo na troca Codex continua documentada e pendente.
Servidores e conversas existentes não foram reiniciados.

## Atualizações seguintes

Com checkout limpo:

```sh
cd ~/Projects/left-undone-herdr
git pull --ff-only
python3 install.py
```

Feche e reabra painéis existentes para carregar a nova implementação. As listas
são locais e ficam fora do checkout; atualizar código não sincroniza listas.

### 2026-11-11

tropico-2, omarchy2 e Omarchy novo atualizados para `70b61a3` com
`git pull --ff-only` e `python3 install.py`. Suíte passou nas três (no Omarchy
novo, 1 teste pulado pelo ambiente). Painéis abertos precisam ser fechados e
reabertos para carregar a nova versão. A correção do Codex após /new e /resume
segue só no branch `fix/codex-active-thread`, fora das instalações.
