"""Flag Tracker: compara os red flags / pontos de atencao da nova analise
contra o historico rastreado da empresa - o que ja existia e permanece vira
'confirmado', o que ja existia e nao apareceu mais vira 'revertido', o que e
novo entra 'aberto'.

Casamento e por texto normalizado - uma simplificacao deliberada desta fase
(sem NLP de similaridade); o system prompt do Master instrui a consultar
get_tracked_flags antes de escrever, o que tende a manter a redacao estavel
entre analises sucessivas.

Port de services/flagTracker.ts (Argos legado).
"""

import unicodedata

from sqlalchemy.orm import Session

from app.repositories import credit_repository as repo
from app.schemas.credit_analysis import AnalysisOutput


def _normalize(texto: str) -> str:
    normalized = unicodedata.normalize("NFD", texto)
    without_diacritics = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    return without_diacritics.lower().strip()


def reconcile_tracked_flags(db: Session, company_id: int, analysis_id: int, output: AnalysisOutput) -> None:
    new_flags: list[tuple[str, str]] = [("red_flag", c.texto) for c in output.red_flags] + [
        ("ponto_atencao", c.texto) for c in output.pontos_atencao
    ]

    existing = repo.get_tracked_flags(db, company_id)
    matched_existing_ids: set[int] = set()

    for categoria, descricao in new_flags:
        match = next(
            (
                e
                for e in existing
                if e.status != "resolvido" and e.categoria == categoria and _normalize(e.descricao) == _normalize(descricao)
            ),
            None,
        )
        if match:
            matched_existing_ids.add(match.id)
            repo.update_tracked_flag_status(db, match.id, "confirmado", last_seen_analysis_id=analysis_id)
        else:
            repo.insert_tracked_flag(
                db,
                company_id=company_id,
                categoria=categoria,
                descricao=descricao,
                first_seen_analysis_id=analysis_id,
                last_seen_analysis_id=analysis_id,
                status="aberto",
            )

    for e in existing:
        ainda_ativo = e.status in ("aberto", "confirmado")
        if ainda_ativo and e.id not in matched_existing_ids:
            repo.update_tracked_flag_status(db, e.id, "revertido")
