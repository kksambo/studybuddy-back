from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from database import get_db
from models import TimetableEvent as TimetableEventModel
from schemas import TimetableEventCreate, TimetableEvent

router = APIRouter(prefix="/timetable", tags=["timetable"])

# Create a new event
@router.post("/", response_model=TimetableEvent)
async def create_event(
    event: TimetableEventCreate, 
    db: AsyncSession = Depends(get_db), 
    user_id: int = 1
):
    db_event = TimetableEventModel(user_id=user_id, **event.dict())
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event

# Get all events for a user
@router.get("/", response_model=List[TimetableEvent])
async def get_events(db: AsyncSession = Depends(get_db), user_id: int = 1):
    result = await db.execute(select(TimetableEventModel).where(TimetableEventModel.user_id == user_id))
    events = result.scalars().all()
    return events

# Get a single event
@router.get("/{event_id}", response_model=TimetableEvent)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db), user_id: int = 1):
    result = await db.execute(
        select(TimetableEventModel).where(
            TimetableEventModel.id == event_id,
            TimetableEventModel.user_id == user_id
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

# Update an event
@router.put("/{event_id}", response_model=TimetableEvent)
async def update_event(event_id: int, updated: TimetableEventCreate, db: AsyncSession = Depends(get_db), user_id: int = 1):
    result = await db.execute(
        select(TimetableEventModel).where(
            TimetableEventModel.id == event_id,
            TimetableEventModel.user_id == user_id
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    for key, value in updated.dict().items():
        setattr(event, key, value)

    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event

# Delete an event
@router.delete("/{event_id}")
async def delete_event(event_id: int, db: AsyncSession = Depends(get_db), user_id: int = 1):
    result = await db.execute(
        select(TimetableEventModel).where(
            TimetableEventModel.id == event_id,
            TimetableEventModel.user_id == user_id
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    await db.delete(event)
    await db.commit()
    return {"message": "Event deleted successfully"}
