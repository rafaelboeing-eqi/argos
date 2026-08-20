"""Testes do repositorio de credito contra o Postgres real (features/public).

Diferente dos testes de mercado (tests/conftest.py::db_session), que usam
Base.metadata.drop_all/create_all contra um Postgres de teste DESCARTAVEL,
aqui isso seria destrutivo demais para arriscar (dropp_all/create_all na base
real, mesmo restrito as tabelas argos_*, e desnecessario e fora do escopo
autorizado em CLAUDE.md). Em vez disso, cada teste abre uma transacao na base
real e SEMPRE faz rollback no final - nada e persistido, nenhuma tabela
existente e tocada.
"""

import pytest
from sqlalchemy.orm import Session

from app.core.database import engine
from app.repositories import credit_repository as repo


@pytest.fixture()
def db():
    if engine is None:
        pytest.skip("Postgres real nao configurado neste ambiente")
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def test_company_crud_roundtrip(db):
    company = repo.create_company(db, nome="Fazenda Teste Agro S.A.", ticker="FTAG", setor="Agro")
    db.flush()
    assert company.id is not None

    fetched = repo.get_company(db, company.id)
    assert fetched is not None
    assert fetched.nome == "Fazenda Teste Agro S.A."
    assert fetched.setor == "Agro"

    all_companies = repo.list_companies(db)
    assert any(c.id == company.id for c in all_companies)


def test_financial_statement_and_metric_value_lookup(db):
    company = repo.create_company(db, nome="Energia Teste S.A.", ticker="ENTS", setor="Energia")
    db.flush()

    repo.insert_financial_statement(
        db,
        company_id=company.id,
        period="2025-Q1",
        period_type="trimestral",
        statement_type="DRE",
        receita_liquida=100_000_000,
        ebitda=20_000_000,
    )
    repo.insert_financial_indicator(
        db, company_id=company.id, period="2025-Q1", metric_key="divida_liquida_ebitda", value=2.5
    )
    db.flush()

    statements = repo.get_financial_statements(db, company.id)
    assert len(statements) == 1
    assert float(statements[0].ebitda) == 20_000_000

    # campo normalizado (financial_statements)
    ebitda_value = repo.get_metric_value_in_period(db, company.id, "ebitda", "2025-Q1")
    assert ebitda_value == 20_000_000

    # metrica EAV (financial_indicators)
    indicator_value = repo.get_metric_value_in_period(db, company.id, "divida_liquida_ebitda", "2025-Q1")
    assert indicator_value == 2.5

    # metrica inexistente
    assert repo.get_metric_value_in_period(db, company.id, "nao_existe", "2025-Q1") is None


def test_sector_knowledge_upsert_versioning(db):
    content = {"modelo_de_negocio": "teste", "setor_marker": "v1"}
    row = repo.upsert_sector_knowledge(db, "SetorTeste", content)
    db.flush()
    assert row.version == 1

    updated = repo.upsert_sector_knowledge(db, "SetorTeste", {**content, "setor_marker": "v2"})
    db.flush()
    assert updated.version == 2
    assert updated.content["setor_marker"] == "v2"


def test_sector_framework_active_scope_and_propose(db):
    company = repo.create_company(db, nome="Empresa Framework", setor="Agro")
    db.flush()

    repo.propose_sector_metric(
        db,
        setor="Agro",
        company_id=None,
        metric_key="liquidez_corrente",
        relevancia_credito="x",
        como_interpretar="x",
        sinal_melhora="x",
        sinal_deterioracao="x",
        fonte_ideal="x",
        frequencia_atualizacao="Trimestral",
        prioridade="Relevante",
    )
    db.flush()

    proposed = repo.get_proposed_sector_framework(db, "Agro")
    assert any(m.metric_key == "liquidez_corrente" for m in proposed)

    # ainda nao ha nenhuma metrica 'active' para este setor de teste
    active = repo.get_active_sector_framework(db, "Agro", company_id=company.id)
    assert active == []


def test_flag_tracker_insert_and_status_update(db):
    company = repo.create_company(db, nome="Empresa Flags", setor="Agro")
    db.flush()
    analysis = repo.insert_analysis(
        db,
        company_id=company.id,
        period="2025-Q1",
        output={"conclusao": "teste"},
        tendencia="estavel",
        risco_credito="baixo",
    )
    db.flush()

    flag = repo.insert_tracked_flag(
        db,
        company_id=company.id,
        categoria="red_flag",
        descricao="Alavancagem subindo",
        first_seen_analysis_id=analysis.id,
        last_seen_analysis_id=analysis.id,
    )
    db.flush()
    assert flag.status == "aberto"

    repo.update_tracked_flag_status(db, flag.id, "confirmado", last_seen_analysis_id=analysis.id)
    db.flush()

    flags = repo.get_tracked_flags(db, company.id)
    assert flags[0].status == "confirmado"
