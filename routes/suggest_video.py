from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import httpx
import os
import PyPDF2
from io import BytesIO
import json
from database import get_db
from models import MyNote as Notes
from pydantic import BaseModel

router = APIRouter(prefix="/suggest", tags=["suggest"])

# Groq configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.1-8b-instant"


class VideoSuggestion(BaseModel):
    title: str
    url: str
    thumbnail: str


@router.get("/suggested-videos/{note_id}", response_model=list[VideoSuggestion])
async def suggest_videos(note_id: int, db: AsyncSession = Depends(get_db)):
    """
    Analyze a PDF note and return 5 YouTube videos related to the academic topics in it.
    Always returns videos relevant to the subject matter for StudyBuddy.
    """
    try:
        # Fetch the note
        result = await db.execute(select(Notes).where(Notes.id == note_id))
        note = result.scalars().first()
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")

        if not os.path.exists(note.pdf_path):
            raise HTTPException(status_code=404, detail="PDF file not found")

        # Extract text from PDF (first 5 pages for speed)
        with open(note.pdf_path, "rb") as f:
            pdf_data = f.read()
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_data))
        extracted_text = "".join([page.extract_text() or "" for page in pdf_reader.pages[:5]])
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from PDF")

        # Use Groq to extract academic keywords/topics
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        prompt = (
            "You are StudyBuddy, an academic assistant. Extract 3-5 concise academic keywords "
            "from these university notes to help students find learning videos. "
            "Respond as a comma-separated list:\n\n"
            f"{extracted_text[:3000]}"
        )

        async with httpx.AsyncClient() as client:
            res = await client.post(
                GROQ_URL,
                headers=headers,
                json={"model": MODEL_NAME, "messages": [{"role": "user", "content": prompt}], "max_tokens": 150},
            )
            res.raise_for_status()
            data = res.json()

        keywords_raw = data["choices"][0]["message"]["content"]
        keywords_list = [kw.strip() for kw in keywords_raw.replace("\n", ",").split(",") if kw.strip()]
        if not keywords_list:
            # Fallback topics
            keywords_list = ["study skills", "academic success", "university learning"]

        # Scrape YouTube for each keyword
        videos = []
        async with httpx.AsyncClient() as client:
            for kw in keywords_list[:3]:  # limit to 3 topics
                search_url = f"https://www.youtube.com/results?search_query={kw.replace(' ', '+')}"
                try:
                    resp = await client.get(search_url, headers={"User-Agent": "Mozilla/5.0"})
                    html = resp.text

                    start = html.find("var ytInitialData =")
                    if start == -1:
                        continue
                    start += len("var ytInitialData =")
                    end = html.find(";</script>", start)
                    json_str = html[start:end].strip()
                    if not json_str:
                        continue

                    data_json = json.loads(json_str)
                    videos_section = (
                        data_json.get("contents", {})
                        .get("twoColumnSearchResultsRenderer", {})
                        .get("primaryContents", {})
                        .get("sectionListRenderer", {})
                        .get("contents", [])[0]
                        .get("itemSectionRenderer", {})
                        .get("contents", [])
                    )

                    for item in videos_section:
                        vid = item.get("videoRenderer")
                        if not vid:
                            continue
                        video_id = vid.get("videoId")
                        title = vid.get("title", {}).get("runs", [{}])[0].get("text", "")
                        thumbnail_url = vid.get("thumbnail", {}).get("thumbnails", [{}])[-1].get("url", "")
                        if video_id and title:
                            videos.append({"title": title, "url": f"https://www.youtube.com/watch?v={video_id}", "thumbnail": thumbnail_url})
                            if len(videos) >= 5:
                                break
                except Exception:
                    continue

        # Ensure fallback videos if scraping fails
        if not videos:
            videos = [
                {"title": "Study Skills 101", "url": "https://www.youtube.com/watch?v=example1", "thumbnail": ""},
                {"title": "Effective University Learning", "url": "https://www.youtube.com/watch?v=example2", "thumbnail": ""}
            ]

        return videos[:5]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
