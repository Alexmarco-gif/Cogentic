"""
Document management endpoints.

Handles document CRUD operations with ownership and org scoping.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import (
    AuthContext,
    can_create_resource,
    can_delete_resource,
    can_edit_resource,
    get_current_user,
    require_feature,
    require_org_membership,
)
from backend.database import get_db
from backend.repositories.document import DocumentRepository

router = APIRouter(prefix="/orgs/{org_id}/documents")


# Pydantic schemas
class DocumentResponse(BaseModel):
    """Document response model"""

    id: str
    filename: str
    storage_path: str | None
    size_bytes: int
    content_type: str | None
    processing_status: str
    owner_id: str
    org_id: str
    created_at: str

    class Config:
        from_attributes = True


class DocumentCreate(BaseModel):
    """Document creation request"""

    filename: str = Field(..., min_length=1, max_length=255)
    storage_path: str = Field(..., min_length=1)
    size_bytes: int = Field(..., ge=0)
    content_type: str = Field(..., min_length=1)
    processing_status: str = Field(default="pending")


class DocumentUpdate(BaseModel):
    """Document update request"""

    filename: str | None = Field(None, min_length=1, max_length=255)
    processing_status: str | None = None


@router.get("")
async def list_documents(
    org_id: UUID,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    owner_id: UUID | None = None,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List documents in organization.

    Optional filters:
    - status: Filter by processing status
    - owner_id: Filter by document owner

    All users can list documents in their org.
    """
    require_org_membership(auth, org_id)

    repo = DocumentRepository(db, org_id, user_id=auth.user_id, request_id=None)

    # Apply filters
    if owner_id:
        documents = await repo.get_by_owner(owner_id, skip=skip, limit=limit)
        total = await repo.count(filters={"owner_id": owner_id})
    elif status:
        documents = await repo.get_by_status(status, skip=skip, limit=limit)
        total = await repo.count(filters={"processing_status": status})
    else:
        documents = await repo.get_multi(skip=skip, limit=limit)
        total = await repo.count()

    return {
        "documents": [
            DocumentResponse(
                id=str(doc.id),
                filename=doc.filename,
                storage_path=doc.storage_path,
                size_bytes=doc.size_bytes,
                content_type=doc.content_type,
                processing_status=doc.processing_status,
                owner_id=str(doc.owner_id),
                org_id=str(doc.org_id),
                created_at=doc.created_at.isoformat(),
            )
            for doc in documents
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("")
async def create_document(
    org_id: UUID,
    document: DocumentCreate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Create a new document.

    Requires member role or higher.
    Document is automatically assigned to the creating user.

    Feature flag: bulk_document_operations
    """
    require_org_membership(auth, org_id)

    # Feature gate: require bulk_document_operations feature
    require_feature(auth, "bulk_document_operations")

    # Check if user can create documents
    if not can_create_resource(auth):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create documents",
        )

    repo = DocumentRepository(db, org_id, user_id=auth.user_id, request_id=None)

    # Create document (org_id auto-injected by TenantRepository)
    doc = await repo.create(
        filename=document.filename,
        storage_path=document.storage_path,
        size_bytes=document.size_bytes,
        content_type=document.content_type,
        processing_status=document.processing_status,
        owner_id=auth.user_id,  # Assign to current user
    )

    await db.commit()

    return DocumentResponse(
        id=str(doc.id),
        filename=doc.filename,
        storage_path=doc.storage_path,
        size_bytes=doc.size_bytes,
        content_type=doc.content_type,
        processing_status=doc.processing_status,
        owner_id=str(doc.owner_id),
        org_id=str(doc.org_id),
        created_at=doc.created_at.isoformat(),
    )


@router.get("/storage/usage")
async def get_storage_usage(
    org_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get organization's storage usage.

    Returns total bytes used and number of documents.
    """
    require_org_membership(auth, org_id)

    repo = DocumentRepository(db, org_id, user_id=auth.user_id, request_id=None)
    total_bytes = await repo.get_total_storage_bytes()
    total_documents = await repo.count()

    return {
        "org_id": str(org_id),
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 2),
        "total_documents": total_documents,
    }


@router.get("/{document_id}")
async def get_document(
    org_id: UUID,
    document_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Get a document by ID.

    User must be in the organization.
    """
    require_org_membership(auth, org_id)

    repo = DocumentRepository(db, org_id, user_id=auth.user_id, request_id=None)
    doc = await repo.get(document_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    return DocumentResponse(
        id=str(doc.id),
        filename=doc.filename,
        storage_path=doc.storage_path,
        size_bytes=doc.size_bytes,
        content_type=doc.content_type,
        processing_status=doc.processing_status,
        owner_id=str(doc.owner_id),
        org_id=str(doc.org_id),
        created_at=doc.created_at.isoformat(),
    )


@router.patch("/{document_id}")
async def update_document(
    org_id: UUID,
    document_id: UUID,
    updates: DocumentUpdate,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Update a document.

    Only the document owner or admins can update documents.
    """
    require_org_membership(auth, org_id)

    repo = DocumentRepository(db, org_id, user_id=auth.user_id, request_id=None)
    doc = await repo.get(document_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Check if user can edit this document
    if not can_edit_resource(auth, doc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to edit this document",
        )

    # Build update dict
    update_data = {}
    if updates.filename is not None:
        update_data["filename"] = updates.filename
    if updates.processing_status is not None:
        update_data["processing_status"] = updates.processing_status

    doc = await repo.update(document_id, **update_data)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    await db.commit()

    return DocumentResponse(
        id=str(doc.id),
        filename=doc.filename,
        storage_path=doc.storage_path,
        size_bytes=doc.size_bytes,
        content_type=doc.content_type,
        processing_status=doc.processing_status,
        owner_id=str(doc.owner_id),
        org_id=str(doc.org_id),
        created_at=doc.created_at.isoformat(),
    )


@router.delete("/{document_id}")
async def delete_document(
    org_id: UUID,
    document_id: UUID,
    auth: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Delete a document (soft delete).

    Only the document owner or admins can delete documents.
    """
    require_org_membership(auth, org_id)

    repo = DocumentRepository(db, org_id, user_id=auth.user_id, request_id=None)
    doc = await repo.get(document_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Check if user can delete this document
    if not can_delete_resource(auth, doc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete this document",
        )

    # Soft delete
    await repo.soft_delete(document_id)
    await db.commit()

    return {"message": "Document deleted successfully"}
