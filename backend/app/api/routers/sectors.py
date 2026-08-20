from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import credit_repository as repo
from app.schemas.sector_knowledge import SectorKnowledgeContent
from app.services.credit.serialization import row_to_dict

router = APIRouter(prefix="/api/sectors", tags=["credit"])


@router.get("/{setor}/framework")
def read_sector_framework(setor: str, company_id: int | None = Query(default=None), db: Session = Depends(get_db)) -> dict:
    """Framework ativo (+ propostas pendentes) de um setor - permite revisar
    o que o especialista esta usando, e o que ele propos e ainda nao foi
    aprovado."""
    active = repo.get_active_sector_framework(db, setor, company_id=company_id)
    proposed = repo.get_proposed_sector_framework(db, setor)
    return {
        "setor": setor,
        "active": [row_to_dict(r) for r in active],
        "proposed": [row_to_dict(r) for r in proposed],
    }


@router.get("/{setor}/knowledge")
def read_sector_knowledge(setor: str, db: Session = Depends(get_db)) -> dict:
    row = repo.get_sector_knowledge(db, setor)
    if row is None:
        raise HTTPException(status_code=404, detail="conhecimento setorial nao cadastrado para este setor")
    return {"setor": row.setor, "version": row.version, "updated_at": row.updated_at, **row.content}


@router.put("/{setor}/knowledge")
def upsert_sector_knowledge(
    setor: str, payload: SectorKnowledgeContent, response: Response, db: Session = Depends(get_db)
) -> dict:
    """Upsert do conhecimento setorial - permite atualizar o conhecimento de
    um setor (ou cadastrar um novo especialista) sem alterar codigo: a
    proxima analise ja usa a versao nova."""
    existing = repo.get_sector_knowledge(db, setor)
    row = repo.upsert_sector_knowledge(db, setor, payload.model_dump())
    db.commit()

    if existing:
        response.status_code = 200
        return {"mensagem": "conhecimento setorial atualizado", "setor": setor, "version": row.version}
    response.status_code = 201
    return {"mensagem": "conhecimento setorial cadastrado", "setor": setor, "version": row.version}
