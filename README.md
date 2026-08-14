# ARGOS

Sistema interno de monitoramento e inteligência sobre ativos distribuídos.

Estado atual: estrutura inicial do projeto (backend FastAPI + frontend Next.js), sem integrações externas, regras de risco, motor de eventos ou IA ainda implementados.

## Arquitetura

```
argos/
├── backend/            # FastAPI - API, regras de negócio, acesso ao PostgreSQL
│   ├── app/
│   │   ├── core/        # configuração (.env) e conexão com o banco
│   │   ├── repositories/# acesso às tabelas existentes (somente leitura)
│   │   ├── models/       # modelos SQLAlchemy (a criar após mapear o schema)
│   │   ├── schemas/      # schemas Pydantic (contratos da API)
│   │   ├── services/
│   │   │   ├── market_data/  # integrações futuras (spreads, brapi, etc.)
│   │   │   └── rules/        # motor de regras (futuro)
│   │   ├── events/       # motor de estado dos eventos (futuro)
│   │   └── api/routers/  # endpoints HTTP
│   └── tests/
├── frontend/            # Next.js + TypeScript + Tailwind - apenas apresentação
└── docs/                # documentação do projeto
```

O frontend não contém regra de negócio: apenas consome a API do backend.
O banco PostgreSQL existente é tratado como **somente leitura** — nenhuma tabela legada é alterada ou migrada pelo Argos. Tabelas novas do Argos usam o prefixo `argos_`.

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

O arquivo `.env` real nunca é commitado (está no `.gitignore`). Nenhuma credencial é exposta ao frontend, e a senha/connection string nunca é impressa em log.

## Configuração do `.env.local` (frontend)

Copie `frontend/.env.local.example` para `frontend/.env.local` e ajuste, se necessário:

| Variável              | Descrição                          |
|-----------------------|-------------------------------------|
| `NEXT_PUBLIC_API_URL` | URL do backend (padrão `http://localhost:8000`) |
