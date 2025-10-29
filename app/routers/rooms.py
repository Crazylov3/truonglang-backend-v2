"""Room management router."""

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
from app.core.operations import room as room_ops
from app.schemas.location.room_schemas import (
    RoomCreate,
    RoomUpdate,
    RoomResponse,
    RoomDetailResponse,
    RoomListResponse,
    CreateRoomResponse,
    UpdateRoomResponse
)
from math import ceil
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/rooms",
    tags=["rooms"]
)


@router.post("/", response_model=CreateRoomResponse, status_code=status.HTTP_201_CREATED)
@csrf_protect
async def create_room(
    room_data: RoomCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Create a new room. Requires STAFF role or higher."""
    try:
        room = await room_ops.create_room(
            db=db,
            branch_id=room_data.branch_id,
            room_number=room_data.room_number,
            capacity=room_data.capacity
        )
        
        return CreateRoomResponse(
            message=f"Room {room.room_number} created successfully in {room.branch.name}",
            room_id=room.id
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating room: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create room"
        )


@router.get("/", response_model=RoomListResponse)
async def list_rooms(
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    search: Optional[str] = Query(None, description="Search by room number"),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    """List all rooms with optional filtering. Available to all authenticated users."""
    branch_uuid = None
    if branch_id:
        branch_uuid = validate_uuid(branch_id)
    
    rooms, total = await room_ops.list_rooms(
        db=db,
        branch_id=branch_uuid,
        search=search
    )
    
    room_responses = [
        RoomResponse(
            id=room.id,
            branch_id=room.branch_id,
            room_number=room.room_number,
            capacity=room.capacity
        )
        for room in rooms
    ]
    
    return RoomListResponse(
        items=room_responses,
        total=total
    )


@router.get("/{room_id}", response_model=RoomDetailResponse)
async def get_room(
    room_id: str = Path(..., description="Room ID"),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: AsyncSession = Depends(get_db)
):
    """Get room details by ID. Available to all authenticated users."""
    room_uuid = validate_uuid(room_id)
    room = await room_ops.get_room_by_id(db, room_uuid)
    
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # Get statistics
    stats = await room_ops.get_room_statistics(db, room_uuid)
    
    return RoomDetailResponse(
        id=room.id,
        branch_id=room.branch_id,
        room_number=room.room_number,
        capacity=room.capacity,
        branch_name=room.branch.name,
        schedule_count=stats["schedule_count"]
    )


@router.put("/{room_id}", response_model=UpdateRoomResponse)
@csrf_protect
async def update_room(
    room_update: RoomUpdate,
    room_id: str = Path(..., description="Room ID"),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Update room details. Requires STAFF role or higher."""
    room_uuid = validate_uuid(room_id)
    
    try:
        room = await room_ops.update_room(
            db=db,
            room_id=room_uuid,
            room_number=room_update.room_number,
            capacity=room_update.capacity
        )
        
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        
        return UpdateRoomResponse(
            message=f"Room {room.room_number} updated successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating room: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update room"
        )


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
@csrf_protect
async def delete_room(
    room_id: str = Path(..., description="Room ID"),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Delete a room. Requires ADMIN role. Cannot delete if room has scheduled courses."""
    room_uuid = validate_uuid(room_id)
    
    try:
        success = await room_ops.delete_room(db, room_uuid)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting room: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete room"
        )