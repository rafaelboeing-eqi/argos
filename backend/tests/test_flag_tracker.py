import pytest
from sqlalchemy.orm import Session

from app.core.database import engine
from app.repositories import credit_repository as repo
from app.schemas.credit_analysis import AnalysisOutput, Claim, RiscoCredito
from app.services.credit.flag_tracker import reconcile_tracked_flags


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


def _output(red_flags: list[str], pontos_atencao: list[str]) -> AnalysisOutput:
    return AnalysisOutput(
        resumo_executivo="x",
        o_que_mudou=[],
        financeiro=[],
        caixa=[],
        endividamento_liquidez=[],
        visao_setorial=[],
        pontos_positivos=[],
        pontos_atencao=[Claim(texto=t, tipo="fato") for t in pontos_atencao],
        red_flags=[Claim(texto=t, tipo="fato") for t in red_flags],
        tendencia="estavel",
        risco_credito=RiscoCredito(nivel="moderado", justificativa="x"),
        o_que_monitorar=[],
        dados_faltantes=[],
        conclusao="x",
    )


def test_flag_lifecycle_aberto_confirmado_revertido(db):
    company = repo.create_company(db, nome="Flag Lifecycle Co", setor="Agro")
    db.flush()
    analysis_1 = repo.insert_analysis(
        db, company_id=company.id, period="2025-Q1", output={}, tendencia="estavel", risco_credito="moderado"
    )
    db.flush()

    # Rodada 1: red flag nova -> aberto
    reconcile_tracked_flags(db, company.id, analysis_1.id, _output(["Alavancagem subindo"], []))
    db.flush()
    flags = repo.get_tracked_flags(db, company.id)
    assert len(flags) == 1
    assert flags[0].status == "aberto"
    assert flags[0].descricao == "Alavancagem subindo"

    # Rodada 2: mesma red flag (variando so acentuacao/caixa) -> confirmado
    analysis_2 = repo.insert_analysis(
        db, company_id=company.id, period="2025-Q2", output={}, tendencia="estavel", risco_credito="moderado"
    )
    db.flush()
    reconcile_tracked_flags(db, company.id, analysis_2.id, _output(["ALAVANCAGEM SUBINDO"], []))
    db.flush()
    flags = repo.get_tracked_flags(db, company.id)
    assert len(flags) == 1
    assert flags[0].status == "confirmado"
    assert flags[0].last_seen_analysis_id == analysis_2.id

    # Rodada 3: red flag nao aparece mais -> revertido
    analysis_3 = repo.insert_analysis(
        db, company_id=company.id, period="2025-Q3", output={}, tendencia="melhora", risco_credito="baixo"
    )
    db.flush()
    reconcile_tracked_flags(db, company.id, analysis_3.id, _output([], []))
    db.flush()
    flags = repo.get_tracked_flags(db, company.id)
    assert len(flags) == 1
    assert flags[0].status == "revertido"


def test_new_ponto_de_atencao_and_resolvido_flags_are_never_rematched(db):
    company = repo.create_company(db, nome="Flag Resolvido Co", setor="Agro")
    db.flush()
    analysis_1 = repo.insert_analysis(
        db, company_id=company.id, period="2025-Q1", output={}, tendencia="estavel", risco_credito="moderado"
    )
    db.flush()
    resolved_flag = repo.insert_tracked_flag(
        db,
        company_id=company.id,
        categoria="ponto_atencao",
        descricao="Concentracao de clientes",
        first_seen_analysis_id=analysis_1.id,
        last_seen_analysis_id=analysis_1.id,
        status="resolvido",
    )
    db.flush()

    analysis_2 = repo.insert_analysis(
        db, company_id=company.id, period="2025-Q2", output={}, tendencia="estavel", risco_credito="moderado"
    )
    db.flush()
    reconcile_tracked_flags(db, company.id, analysis_2.id, _output([], ["Concentracao de clientes"]))
    db.flush()

    flags = repo.get_tracked_flags(db, company.id)
    # a flag resolvida antiga NAO deve ser reaberta; deve existir uma nova linha 'aberto'
    statuses = sorted(f.status for f in flags)
    assert statuses == ["aberto", "resolvido"]
    assert resolved_flag.status == "resolvido"
