from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import os
import httpx

from database import get_db
from models import ChatMessage
from schemas import ChatInput, ChatResponse, ChatHistoryResponse

router = APIRouter(prefix="/studybuddy", tags=["StudyBuddy Chat Bot"])

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.1-8b-instant"

@router.post("/", response_model=ChatResponse)
async def ask_chat(input_data: ChatInput,
                   background_tasks: BackgroundTasks,
                   db: AsyncSession = Depends(get_db)) -> ChatResponse:
    """
    Handles a student's academic question.
    StudyBuddy will provide concise answers using reliable academic references only.
    """
    try:
        # Save student's question
        student_msg = ChatMessage(
            student_email=input_data.email,
            message=input_data.question,
            sender="student"
        )
        db.add(student_msg)
        await db.commit()
        await db.refresh(student_msg)

        # Construct prompt for StudyBuddy
        system_prompt = (
            "You are StudyBuddy, an AI tutor that answers academic questions only. "
            "Use reliable academic references and maintain a concise, student-friendly style. "
            "Do NOT provide non-academic advice or web search content. "
            "Cite references if possible."
        )
        user_prompt = (
            f"{system_prompt}\n\n"
            f"Student Email: {input_data.email}\n"
            f"Question: {input_data.question}\n\n"
            "Provide a clear answer in 1-2 sentences. Include references if applicable."
        )

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 200,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(GROQ_URL, headers=headers, json=payload)
            response.raise_for_status()
            rdata = response.json()

        answer = rdata["choices"][0]["message"]["content"].strip()

        # Save StudyBuddy's answer
        bot_msg = ChatMessage(
            student_email=input_data.email,
            message=answer,
            sender="bot"
        )
        db.add(bot_msg)
        await db.commit()

        return {"success": True, "answer": answer}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{student_email}", response_model=ChatHistoryResponse)
async def chat_history(student_email: str, db: AsyncSession = Depends(get_db)) -> ChatHistoryResponse:
    """
    Retrieves the chat history for a given student.
    """
    try:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.student_email == student_email)
            .order_by(ChatMessage.created_at.asc())
        )
        rows = result.scalars().all()
        return {"messages": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
