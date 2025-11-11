from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
import shutil
import os

from models import MyNote
from schemas import NoteCreate, NoteUpdate, NoteResponse
from database import get_db as get_async_session

router = APIRouter(prefix="/notes", tags=["My Notes"])

UPLOAD_DIR = "uploaded_notes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- CREATE NOTE ----------------
@router.post("/", response_model=NoteResponse)
async def create_note(
    user_id: int = Form(...),
    note_name: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
):
    # Save the uploaded file
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Insert into database
    query = text(
        "INSERT INTO my_notes (user_id, note_name, pdf_path) "
        "VALUES (:user_id, :note_name, :pdf_path) RETURNING id"
    )
    result = await session.execute(
        query, {"user_id": user_id, "note_name": note_name, "pdf_path": file_path}
    )
    await session.commit()
    note_id = result.scalar_one()

    return NoteResponse(id=note_id, user_id=user_id, note_name=note_name, pdf_path=file_path)


# ---------------- GET USER NOTES ----------------
@router.get("/{user_id}", response_model=List[NoteResponse])
async def get_notes(user_id: int, session: AsyncSession = Depends(get_async_session)):
    query = text("SELECT * FROM my_notes WHERE user_id = :user_id")
    result = await session.execute(query, {"user_id": user_id})
    notes = result.fetchall()
    return [
        NoteResponse(
            id=row.id,
            user_id=row.user_id,
            note_name=row.note_name,
            pdf_path=row.pdf_path
        )
        for row in notes
    ]


# ---------------- UPDATE NOTE ----------------
@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: int,
    note_update: NoteUpdate,
    user_id: int = Form(...),
    session: AsyncSession = Depends(get_async_session),
):
    query = text(
        "UPDATE my_notes SET note_name = :note_name "
        "WHERE id = :id AND user_id = :user_id "
        "RETURNING id, note_name, pdf_path, user_id"
    )
    result = await session.execute(
        query,
        {"note_name": note_update.note_name, "id": note_id, "user_id": user_id}
    )
    updated_note = result.fetchone()
    if not updated_note:
        raise HTTPException(status_code=404, detail="Note not found")
    await session.commit()
    return NoteResponse(**updated_note._mapping)


# ---------------- DELETE NOTE ----------------
@router.delete("/{note_id}")
async def delete_note(
    note_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    # Get the note first to delete the file
    query = text("SELECT pdf_path FROM my_notes WHERE id = :id")
    result = await session.execute(query, {"id": note_id})
    note = result.fetchone()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Delete file
    file_path = note._mapping["pdf_path"]
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete from database
    del_query = text("DELETE FROM my_notes WHERE id = :id")
    await session.execute(del_query, {"id": note_id})
    await session.commit()
    return {"detail": "Note deleted successfully"}


# ---------------- DOWNLOAD NOTE ----------------
@router.get("/download/{note_id}")
async def download_note(
    note_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    query = text("SELECT pdf_path FROM my_notes WHERE id = :id")
    result = await session.execute(query, {"id": note_id})
    note = result.fetchone()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    file_path = note._mapping["pdf_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    from fastapi.responses import FileResponse
    return FileResponse(file_path, filename=os.path.basename(file_path))
