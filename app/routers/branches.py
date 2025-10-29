"""Branch management router."""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.models.user import User, UserRole
from app.core.deps import get_current_user
from app.core.decorators import csrf_protect
from app.core.deps import require_role
from app.core.validators import validate_uuid
from app.core.operations import branch as branch_ops
from app.schemas.location.branch_schemas import (
    BranchCreate,
    BranchUpdate,
    BranchResponse,
    BranchDetailResponse,
    BranchListResponse
)
from math import ceil
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/branches",
    tags=["branches"]
)


@router.post("/", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
@csrf_protect
async def create_branch(
    branch_data: BranchCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Create a new branch. Requires STAFF role or higher."""
    try:
        branch = await branch_ops.create_branch(
            db=db,
            name=branch_data.name,
            address=branch_data.address,
            contact_info=branch_data.contact_info
        )
        
        return BranchResponse(
            id=branch.id,
            name=branch.name,
            address=branch.address,
            contact_info=branch.contact_info
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating branch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create branch"
        )


@router.get("/", response_model=BranchListResponse)
async def list_branches(
    search: Optional[str] = Query(None, description="Search by name or address"),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    """List all branches. Available to all authenticated users."""
    branches, total = await branch_ops.list_branches(
        db=db,
        search=search
    )
    
    branch_responses = [
        BranchResponse(
            id=branch.id,
            name=branch.name,
            address=branch.address,
            contact_info=branch.contact_info
        )
        for branch in branches
    ]
    
    return BranchListResponse(
        items=branch_responses,
        total=total
    )


@router.get("/{branch_id}", response_model=BranchDetailResponse)
async def get_branch(
    branch_id: str = Path(..., description="Branch ID"),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    """Get branch details by ID. Available to all authenticated users."""
    branch_uuid = validate_uuid(branch_id)
    branch = await branch_ops.get_branch_by_id(db, branch_uuid)
    
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found"
        )
    
    # Get statistics
    stats = await branch_ops.get_branch_statistics(db, branch_uuid)
    
    return BranchDetailResponse(
        id=branch.id,
        name=branch.name,
        address=branch.address,
        contact_info=branch.contact_info,
        room_count=stats["room_count"],
        course_count=stats["course_count"]
    )


@router.put("/{branch_id}", response_model=BranchResponse)
@csrf_protect
async def update_branch(
    branch_update: BranchUpdate,
    branch_id: str = Path(..., description="Branch ID"),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Update branch details. Requires STAFF role or higher."""
    branch_uuid = validate_uuid(branch_id)
    
    try:
        branch = await branch_ops.update_branch(
            db=db,
            branch_id=branch_uuid,
            name=branch_update.name,
            address=branch_update.address,
            contact_info=branch_update.contact_info
        )
        
        if not branch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found"
            )
        
        return BranchResponse(
            id=branch.id,
            name=branch.name,
            address=branch.address,
            contact_info=branch.contact_info
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating branch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update branch"
        )


@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
@csrf_protect
async def delete_branch(
    branch_id: str = Path(..., description="Branch ID"),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Delete a branch. Requires ADMIN role. Cannot delete if branch has rooms or courses."""
    branch_uuid = validate_uuid(branch_id)
    
    try:
        success = await branch_ops.delete_branch(db, branch_uuid)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting branch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete branch"
        )