from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import os
import httpx

from database import get_db
from models import ChatMessage
from schemas import ChatInput, ChatResponse, ChatHistoryResponse
from fastapi import UploadFile, File
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import io

router = APIRouter(prefix="/studybuddy", tags=["StudyBuddy Chat Bot"])

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.1-8b-instant"

@router.post("/", response_model=ChatResponse)
async def ask_chat(
    input_data: ChatInput,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    try:
        user_input = input_data.question.strip()

        # Save student message
        student_msg = ChatMessage(
            student_email=input_data.email,
            message=user_input,
            sender="student"
        )
        db.add(student_msg)
        await db.commit()

        # 1️⃣ FIRST MESSAGE → SHOW MENU
        if user_input.lower() in ["hi", "hello", "start", "menu"]:
            return {
                "success": True,
                "answer": MENU_TEXT
            }

        # 2️⃣ MENU OPTIONS
        if user_input == "1":
            return {
                "success": True,
                "answer": (
                    "📘 You chose: Explain a concept\n\n"
                    "Please tell me:\n"
                    "- Subject\n"
                    "- Topic / Concept\n"
                    "- Grade (e.g. Grade 9)\n\n"
                    "Example: Mathematics, Algebraic expressions, Grade 9"
                )
            }

        if user_input == "2":
            return {
                "success": True,
                "answer": (
                    "✏️ You chose: Examples & practice\n\n"
                    "Please provide:\n"
                    "- Subject\n"
                    "- Topic\n"
                    "- Grade\n\n"
                    "Example: Natural Sciences, Photosynthesis, Grade 8"
                )
            }

        if user_input == "3":
            return {
                "success": True,
                "answer": (
                    "📝 You chose: Summarise a topic\n\n"
                    "Please provide:\n"
                    "- Subject\n"
                    "- Topic\n"
                    "- Grade\n\n"
                    "Example: History, French Revolution, Grade 10"
                )
            }

        # 3️⃣ OPTION 4 → CUSTOM ACADEMIC QUESTION
        if user_input == "4":
            return {
                "success": True,
                "answer": (
                    "❓ You chose: Other\n\n"
                    "Please ask your academic question.\n"
                    "Make sure it includes:\n"
                    "- Subject\n"
                    "- Topic\n"
                    "- Grade"
                )
            }

        # 4️⃣ ACTUAL AI QUESTION (ONLY AFTER MENU)
        system_prompt = (
            "You are StudyBuddy, an academic tutor for school learners (Grades 7–12). "
            "Answer strictly within the subject, topic, and grade provided. "
            "No non-academic content. Keep answers concise and clear."
        )

        user_prompt = (
            f"Student Question:\n{user_input}\n\n"
            "Answer in a learner-friendly way (2–4 sentences)."
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
            "max_tokens": 250,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(GROQ_URL, headers=headers, json=payload)
            response.raise_for_status()
            rdata = response.json()

        answer = rdata["choices"][0]["message"]["content"].strip()

        # Save bot response
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

from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import io
import re

router = APIRouter()

@router.post("/extract-student-card")
async def extract_student_card_details(
    image: UploadFile = File(...)
):
    """
    Upload a student card image and extract:
    - Full Name
    - Student Number
    """

    try:
        # =========================
        # 1️⃣ Load Image
        # =========================
        image_bytes = await image.read()
        img = Image.open(io.BytesIO(image_bytes))

        # =========================
        # 2️⃣ IMAGE PREPROCESSING (ID CARD OPTIMIZED)
        # =========================
        img = img.convert("L")  # grayscale

        contrast = ImageEnhance.Contrast(img)
        img = contrast.enhance(2.2)

        sharpness = ImageEnhance.Sharpness(img)
        img = sharpness.enhance(2.0)

        img = img.filter(ImageFilter.MedianFilter(size=3))

        # Slight thresholding (ID cards prefer softer binarization)
        img = img.point(lambda x: 0 if x < 160 else 255, "1")

        # =========================
        # 3️⃣ OCR
        # =========================
        ocr_config = r"--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789/"
        extracted_text = pytesseract.image_to_string(img, config=ocr_config)

        if not extracted_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No readable text detected. Please upload a clearer student card image."
            )

        # Normalize text
        clean_text = extracted_text.upper()

        # =========================
        # 4️⃣ STUDENT NUMBER EXTRACTION
        # =========================
        student_number = None

        student_patterns = [
            r"\b\d{6,12}\b",                  # 123456 / 202012345
            r"\b[A-Z]{1,3}\d{5,10}\b"         # ST123456 / UJ20201234
        ]

        for pattern in student_patterns:
            match = re.search(pattern, clean_text)
            if match:
                student_number = match.group()
                break

        # =========================
        # 5️⃣ NAME EXTRACTION
        # =========================
        name = None

        # Look for FULL NAME patterns (capital letters)
        name_candidates = re.findall(
            r"\b[A-Z]{2,}\s+[A-Z]{2,}(?:\s+[A-Z]{2,})?\b",
            clean_text
        )

        if name_candidates:
            # Pick the longest match (usually full name)
            name = max(name_candidates, key=len)

        # =========================
        # 6️⃣ RESPONSE
        # =========================
        return {
            "success": True,
            "data": {
                "name": name,
                "student_number": student_number,
                "raw_text": extracted_text.strip()
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
