import pytest
from sqlalchemy.orm import Session

from app.core.database import engine
from app.repositories import credit_repository as repo
from app.services.ai_provider.fake_provider import FakeAIProvider
from app.services.credit.sector_agent import (
    build_sector_agent_prompt,
    list_available_sectors,
    run_sector_specialist,
    slugify_sector,
)


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


def test_slugify_sector_strips_diacritics_and_spaces():
    assert slugify_sector("Proteína Animal") == "sector-proteina-animal"
    assert slugify_sector("Óleo e Gás") == "sector-oleo-e-gas"


def test_build_sector_agent_prompt_without_knowledge_is_explicit_about_gap():
    prompt = build_sector_agent_prompt("Agro", None)
    assert "Nenhum conhecimento setorial estruturado" in prompt
    assert "Agro" in prompt


def test_list_available_sectors_union_of_knowledge_and_active_framework(db):
    repo.upsert_sector_knowledge(db, "SetorComConhecimento", {"placeholder": True})
    repo.propose_sector_metric(
        db,
        setor="SetorComFrameworkAtivo",
        company_id=None,
        metric_key="x",
        relevancia_credito="x",
        como_interpretar="x",
        sinal_melhora="x",
        sinal_deterioracao="x",
        fonte_ideal="x",
        frequencia_atualizacao="x",
        prioridade="Relevante",
    )
    # promove manualmente para 'active' (simulando revisao humana)
    proposed = repo.get_proposed_sector_framework(db, "SetorComFrameworkAtivo")
    proposed[0].status = "active"
    db.flush()

    sectors = list_available_sectors(db)
    assert "SetorComConhecimento" in sectors
    assert "SetorComFrameworkAtivo" in sectors


def test_run_sector_specialist_dispatches_tools_and_validates_output(db):
    company = repo.create_company(db, nome="Sector Agent Co", setor="Agro")
    db.flush()
    repo.insert_financial_indicator(db, company_id=company.id, period="2025-Q1", metric_key="liquidez_corrente", value=1.4)
    db.flush()

    fake = FakeAIProvider(
        planned_tool_calls=[
            ("get_company_profile", {"company_id": company.id}),
            ("get_financial_indicators", {"company_id": company.id}),
        ],
        final_result={"texto": "Leitura setorial: liquidez corrente estavel em 1.4x no 2025-Q1 (fato)."},
    )

    texto = run_sector_specialist(db, fake, "Agro", company.id)

    assert texto.startswith("Leitura setorial:")
    assert len(fake.executed_tool_calls) == 2
    assert fake.executed_tool_calls[0][2]["nome"] == "Sector Agent Co"
    assert "Agro" in fake.received_system_prompt
    assert str(company.id) in fake.received_user_prompt
