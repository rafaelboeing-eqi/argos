# ARGOS

Sistema interno de monitoramento e inteligência sobre ativos distribuídos.

Estado atual: infraestrutura inicial + módulo **Mercado** (curvas de futuros B3, Tesouro Direto e macro via brapi.dev). Regras de risco/concentração, motor de eventos e IA ainda não implementados.

## Arquitetura

```
argos/
├── backend/                     # FastAPI - API, regras de negócio, acesso ao PostgreSQL
│   ├── alembic/                 # migrations - SOMENTE para tabelas argos_*
│   ├── app/
│   │   ├── core/                 # configuração (.env) e conexão com o banco
│   │   ├── repositories/         # toda query SQL vive aqui (market_repository.py)
│   │   ├── models/                # modelos SQLAlchemy das tabelas argos_* (base.py, market_history.py, metric.py)
│   │   ├── schemas/               # schemas Pydantic (contratos da API)
│   │   ├── services/
│   │   │   ├── market_data/       # brapi_provider, normalizers, collector, metrics, overview, scheduler
│   │   │   └── rules/             # motor de regras (futuro)
│   │   ├── events/                # motor de estado dos eventos (futuro)
│   │   ├── scripts/                # comandos manuais (backfill_market.py)
│   │   └── api/routers/            # endpoints HTTP (system.py, market.py)
│   ├── run_argos_market_setup.py  # setup único contra o Postgres real (ver abaixo)
│   └── tests/
├── frontend/                     # Next.js + TypeScript + Tailwind - apenas apresentação
│   └── src/
│       ├── app/mercado/           # página /mercado
│       ├── components/market/     # cards, gráficos (Recharts), estado vazio
│       ├── lib/                    # fetch helper + formatação (sem regra de negócio)
│       └── types/                  # tipos TS espelhando os schemas do backend
└── docs/
    └── argos_market_migration.sql # migration em SQL puro, pronta pro DBeaver
```

O frontend não contém regra de negócio: apenas consome a API do backend.
O banco PostgreSQL existente é tratado como **somente leitura** para as tabelas legadas — o Argos nunca faz `DROP`/`DELETE`/`UPDATE`/`ALTER` nelas. Tabelas novas (ou colunas adicionadas de forma aditiva) usam o prefixo `argos_` e só elas são versionadas pelo Alembic.

### Regra central: a brapi é fonte de ingestão, não de consulta

```
brapi (fonte externa) → coleta/normalização → PostgreSQL → métricas/regras → API interna → frontend
```

- A brapi **só** é chamada por `MarketCollectorService`, pelo script de backfill e por `collect_daily_market_data()` — nunca pelos endpoints `GET /api/market/*` nem pelo frontend.
- Toda consulta do usuário (página Mercado, gráficos, métricas) lê exclusivamente `argos_market_history`/`argos_metrics` no Postgres.
- Se a brapi cair, a página Mercado continua funcionando normalmente com os últimos dados persistidos — o card "Dados atualizados até `<data>`" (endpoint `overview`) mostra a data mais recente realmente disponível no banco, para deixar isso transparente ao usuário.
- A coleta diária é **incremental e autocurativa**: ela sempre busca o snapshot atual (1 chamada barata) e, se detectar que o último dado salvo está a mais de 1 dia de distância (job que não rodou por alguns dias, feriado, instabilidade), busca automaticamente só a janela que falta via `futures/historical`/`macro` — nunca refaz o histórico completo. Ver `MarketCollectorService.collect_futures_curve_incremental()` / `collect_macro_incremental()`.

## Como iniciar o backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # preencha com os dados reais do banco
uvicorn app.main:app --reload --port 8000
```

Endpoints disponíveis:
- `GET /` → `{"system": "ARGOS", "status": "online"}`
- `GET /health` → `{"api": "ok", "database": "connected"|"disconnected"}`
- `GET /api/market/overview` → cards de Selic, IPCA, DI curto/médio/longo e commodities
- `GET /api/market/futures/{asset}/curve` → curva atual completa de `DI1`, `DAP`, `BGI`, `CCM`, `ICF` ou `SJC`
- `GET /api/market/futures/{asset}/rate-curve` → curva de DI/DAP reduzida a 1 contrato/ano (preferência janeiro), comparando hoje/7d/30d/90d
- `GET /api/market/futures/{symbol}/history` → série histórica de um contrato específico (ex.: `DI1F27`)
- `GET /api/market/macro?slugs=selic,ipca` → séries macro (padrão: as configuradas em `MACRO_SERIES`)
- `GET /api/market/treasury/{asset}/curve?coupon_type=` → curva do Tesouro Direto (`treasury_ipca`/`treasury_prefixado`/`treasury_selic`) por vencimento, hoje/7d/30d/90d, com filtro opcional de modalidade (`zero`/`semestral`)
- `GET /api/market/commodities/{asset}/history?period=30d|90d|6m|1a` → histórico do contrato representativo (front) de uma commodity
- `GET /api/market/metrics?category=&asset=&symbol=` → indicadores calculados (variações, vértices da curva)

Todos os endpoints `/api/market/*` leem apenas do PostgreSQL — o backend nunca chama a brapi durante uma requisição do frontend.

### Colocar o módulo Mercado para funcionar no banco real (`features`)

Um passo só, na máquina que tiver acesso à rede do Postgres real (este ambiente de desenvolvimento não alcança a RDS da EQI — ver `CLAUDE.md` para a política completa de banco):

Com `backend/.env` preenchido (host/porta/banco/usuário/senha reais + `BRAPI_API_TOKEN`):
```bash
cd backend
python run_argos_market_setup.py
```

Esse script sozinho: valida banco/schema/tabelas (aborta sem alterar nada se algo não bater com `features`/`public`/`argos_*`), aplica as migrations pendentes (Alembic — só em `argos_market_history`/`argos_metrics`), faz o backfill inicial de ~180 dias só onde ainda não houver histórico, roda a coleta incremental e recalcula `argos_metrics`, terminando com um relatório (contagens, intervalo de datas, duplicidades, última atualização). **É idempotente**: rodar de novo não duplica nada, não reaplica migration já rodada, só preenche o que estiver faltando.

Nunca imprime credenciais. `docs/argos_market_migration.sql` documenta o mesmo schema em SQL puro, para quem preferir revisar/rodar manualmente no DBeaver — mantenha os dois em sync se as migrations mudarem.

<details>
<summary>Comandos individuais (equivalentes ao que o script acima já faz)</summary>

```bash
cd backend
source .venv/bin/activate
alembic upgrade head

# snapshot do dia (curvas atuais + macro mais recente) - é isto que rodaria via cron:
python -c "from app.core.database import SessionLocal; from app.services.market_data.scheduler import collect_daily_market_data; \
db = SessionLocal(); collect_daily_market_data(db)"

# backfill de histórico - NUNCA roda sozinho, sempre manual e explícito:
python -m app.scripts.backfill_market --macro --start-date 2024-01-01
python -m app.scripts.backfill_market --futures-asset DI1 --start-date 2025-01-01
```

`collect_daily_market_data()` não tem cron/scheduler embutido de propósito — é só a função de entrada para ser chamada pela infraestrutura de agendamento da empresa.
</details>

### Rodar os testes

```bash
cd backend
source .venv/bin/activate
pytest -v
```

## Como iniciar o frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local  # ajuste a URL do backend se necessário
npm run dev
```

Acesse `http://localhost:3000` — a página mostra o status do backend e do banco, obtidos via `GET /health`.

> Use sempre `localhost` (não `127.0.0.1`) ao acessar o frontend em desenvolvimento: o servidor de desenvolvimento do Next.js valida a origem das requisições e bloqueia por padrão origens que não sejam `localhost`.

## Configuração do `.env` (backend)

Copie `backend/.env.example` para `backend/.env` e preencha:

| Variável             | Descrição                                              |
|----------------------|---------------------------------------------------------|
| `DATABASE_HOST`      | Host do PostgreSQL existente                             |
| `DATABASE_PORT`      | Porta do PostgreSQL (padrão `5432`)                       |
| `DATABASE_NAME`      | Nome do banco                                             |
| `DATABASE_USER`      | Usuário (recomendado: usuário dedicado, somente leitura)  |
| `DATABASE_PASSWORD`  | Senha do usuário                                          |
| `CORS_ORIGINS`       | Origem(ns) do frontend permitidas, separadas por vírgula (padrão `http://localhost:3000`) |
| `BRAPI_API_TOKEN`    | Token da [brapi.dev](https://brapi.dev) — usado só no backend, nunca enviado ao frontend nem colocado em URL (vai sempre em `Authorization: Bearer`) |

O arquivo `.env` real nunca é commitado (está no `.gitignore`). Nenhuma credencial é exposta ao frontend, e a senha/connection string/token nunca são impressos em log.

## Configuração do `.env.local` (frontend)

Copie `frontend/.env.local.example` para `frontend/.env.local` e ajuste, se necessário:

| Variável              | Descrição                          |
|-----------------------|-------------------------------------|
| `NEXT_PUBLIC_API_URL` | URL do backend (padrão `http://localhost:8000`) |
