from fastapi import APIRouter, HTTPException, Depends
from app.models.document import IngestRequest, Document, DocumentSummary, SearchRequest, SearchResult
from app.models.user import UserInDB
from app.services import rag_service
from app.services.auth_service import get_current_user
from typing import List

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/", response_model=Document, status_code=201)
async def ingest_document(
    request: IngestRequest,
    _: UserInDB = Depends(get_current_user),
):
    try:
        return await rag_service.ingest_document(
            filename=request.filename,
            content=request.content,
            chunk_size=request.chunk_size,
            metadata=request.metadata or {},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[DocumentSummary])
async def list_documents(_: UserInDB = Depends(get_current_user)):
    return await rag_service.list_documents()


@router.post("/search", response_model=List[SearchResult])
async def search_documents(
    request: SearchRequest,
    _: UserInDB = Depends(get_current_user),
):
    return await rag_service.retrieve(query=request.query, top_k=request.top_k)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: str,
    _: UserInDB = Depends(get_current_user),
):
    try:
        await rag_service.delete_document(doc_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
