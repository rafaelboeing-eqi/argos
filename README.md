# ARGOS

Sistema interno de monitoramento e inteligência sobre ativos distribuídos.

Estado atual: infraestrutura inicial + módulo **Mercado** (curvas de futuros B3 e macro via brapi.dev). Regras de risco/concentração, motor de eventos e IA ainda não implementados.

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
│   └── tests/
├── frontend/                     # Next.js + TypeScript + Tailwind - apenas apresentação
│   └── src/
│       ├── app/mercado/           # página /mercado
│       ├── components/market/     # cards, gráficos (Recharts), estado vazio
│       ├── lib/                    # fetch helper + formatação (sem regra de negócio)
│       └── types/                  # tipos TS espelhando os schemas do backend
└── docs/                          # documentação do projeto
```

O frontend não contém regra de negócio: apenas consome a API do backend.
O banco PostgreSQL existente é tratado como **somente leitura** para as tabelas legadas — o Argos nunca faz `DROP`/`DELETE`/`UPDATE`/`ALTER` nelas. Tabelas novas (ou colunas adicionadas de forma aditiva) usam o prefixo `argos_` e só elas são versionadas pelo Alembic.

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
- `GET /api/market/futures/{asset}/curve` → curva atual de `DI1`, `DAP`, `BGI`, `CCM`, `ICF` ou `SJC`
- `GET /api/market/futures/{symbol}/history` → série histórica de um contrato específico (ex.: `DI1F27`)
- `GET /api/market/macro?slugs=selic,ipca` → séries macro (padrão: as configuradas em `MACRO_SERIES`)
- `GET /api/market/metrics?category=&asset=&symbol=` → indicadores calculados (variações, vértices da curva)

Todos os endpoints `/api/market/*` leem apenas do PostgreSQL — o backend nunca chama a brapi durante uma requisição do frontend.

### Aplicar a migration do módulo Mercado

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

Isso adiciona colunas (todas `ADD COLUMN IF NOT EXISTS`, nunca `DROP`/`ALTER TYPE`) e índices em `argos_market_history` e `argos_metrics`. **Antes de rodar em produção**, confira o schema atual dessas duas tabelas (comandos SQL na seção de migrations pendentes, abaixo) — se alguma coluna legada for `NOT NULL` sem default, os inserts do coletor vão falhar até essa constraint ser relaxada.

### Popular dados (coleta manual / backfill)

```bash
# snapshot do dia (curvas atuais + macro mais recente) - é isto que rodaria via cron:
python -c "from app.core.database import SessionLocal; from app.services.market_data.scheduler import collect_daily_market_data; \
db = SessionLocal(); collect_daily_market_data(db)"

# backfill de histórico - NUNCA roda sozinho, sempre manual e explícito:
python -m app.scripts.backfill_market --macro --start-date 2024-01-01
python -m app.scripts.backfill_market --futures-asset DI1 --start-date 2025-01-01
```

`collect_daily_market_data()` não tem cron/scheduler embutido de propósito — é só a função de entrada para ser chamada pela infraestrutura de agendamento da empresa.

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
