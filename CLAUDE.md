# ARGOS — instruções permanentes para o Claude Code

## Política de desenvolvimento do banco de dados (PostgreSQL real)

O banco real do Argos é `features` (schema `public`), na rede corporativa da EQI.
Este repositório roda em vários ambientes diferentes — sessões na nuvem (sem rota
até esse banco) e o Claude Code na máquina local/corporativa do usuário (com
rota). As regras abaixo valem em qualquer um deles; o que muda é só se a conexão
está ou não alcançável.

### Escopo autorizado

- **Database**: `features` — nenhum outro.
- **Schema**: `public` — nenhum outro.
- **Objetos**: qualquer tabela/índice/sequence cujo nome comece com `argos_`.
  Tudo que não começa com `argos_` (`follow_*`, `aderencia_*`, `martini_*`,
  `ntnb_*`, `solicitacoes_*`, ou qualquer outra tabela existente) está **fora
  de escopo**, sempre, sem exceção.

### Antes de qualquer operação de banco (sem exceção)

1. Validar `SELECT current_database()` = `features`.
2. Validar `SELECT current_schema()` = `public`.
3. Validar que **todos** os objetos que serão criados/alterados/lidos/escritos
   começam com `argos_`.
4. Se qualquer objeto fora desse padrão aparecer no plano (inclusive em JOINs,
   FKs, ou side effects de uma migration), **abortar** sem executar nada.

`backend/run_argos_market_setup.py` já implementa os passos 1–3 antes de
qualquer escrita — usar esse padrão (ou o mesmo helper) em qualquer script novo
que toque no banco.

### Autorizado em `argos_*` (schema `public`, banco `features`)

- `CREATE TABLE public.argos_*`
- `ALTER TABLE` (adicionar coluna, criar índice, ajustar constraint/default)
- `CREATE INDEX`
- `INSERT` / `UPDATE` / `DELETE`
- Rodar migrations (Alembic) e/ou SQL direto quando fizer sentido no momento

### Nunca, em nenhuma tabela, mesmo `argos_*`

- `DROP TABLE`
- `DROP DATABASE`

### Nunca, em qualquer tabela fora de `argos_*`

- Qualquer DDL ou DML (nem `SELECT` é necessário fora de investigação pontual
  e justificada — este projeto não deve depender de dados de outras tabelas
  além de `argos_assets` no futuro, e mesmo essa dependência ainda não existe).

### Migrations sempre documentadas no repositório

Toda mudança de schema aplicada diretamente no banco (via Claude Code
conectado, ou via SQL manual) precisa ser refletida no repositório antes de
considerar a tarefa concluída:

- Alembic (`backend/alembic/versions/`) é a fonte de verdade para o histórico
  de schema.
- `docs/argos_market_migration.sql` deve continuar espelhando o estado atual
  esperado das tabelas `argos_market_history`/`argos_metrics` (é o fallback
  para quem preferir rodar via DBeaver).
- Os modelos SQLAlchemy (`backend/app/models/`) devem sempre corresponder à
  estrutura real após qualquer alteração.

Nunca alterar o banco "no braço" sem atualizar esses três em seguida.

### Credenciais

- Vivem exclusivamente em `backend/.env` (nunca commitado — está no
  `.gitignore`; sempre confirmar com `git check-ignore` antes de escrever nele).
- Nunca imprimir senha, connection string completa ou `BRAPI_API_TOKEN` em
  output, log, ou nas respostas do chat.
- Nunca é necessário o usuário reenviar credenciais pelo chat — se não
  estiverem em `backend/.env`, perguntar como proceder em vez de assumir.

### Quando a rede não alcança o Postgres real

Isso é o comportamento padrão em sessões na nuvem (sandbox sem rota até a RDS
da EQI) — não é um bug e não deve ser contornado (nada de pedir para abrir o
security group, nada de proxy alternativo). Testar conectividade honestamente
(ex.: TCP na porta 5432) e, se falhar, reportar isso claramente e seguir
apenas com o que não depende do banco real (testes com Postgres local
descartável/SQLite, revisão de código, etc.).

Quando rodando no Claude Code da máquina corporativa do usuário e a conexão
estiver disponível, pode conectar e trabalhar diretamente no banco seguindo
todas as regras acima — sem precisar de autorização adicional para cada
operação individual, desde que dentro do escopo `argos_*`/`features`/`public`.
