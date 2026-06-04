import os
import httpx
import logging
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv


load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgriBot")


app = FastAPI(title="Agri Cameroun", version="2.4.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# On utilise l'URL v1 (la plus stable)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# --- Ton SYSTEM_PROMPT_BASE reste le même ---


class QuestionRequest(BaseModel):
    question: str
    culture: str | None = None

@app.post("/chat")
async def chat(request: QuestionRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Clé API manquante")

    # On simplifie le message pour éviter les erreurs de filtrage
    contexte = f"Culture : {request.culture}. " if request.culture else ""
    full_prompt = f"OBLIGATION : Réponds comme AgriBot expert au Cameroun.\n\n{SYSTEM_PROMPT_BASE}\n\n{contexte}QUESTION : {request.question}"

    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 600}
    }

    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            response = await client.post(GEMINI_URL, json=payload)
            
            if response.status_code != 200:
                # On renvoie l'erreur réelle de Google pour débugger
                logger.error(f"Google Error: {response.text}")
                return {"reponse": f"⚠️ (Erreur Google {response.status_code}) L'IA est saturée. Réessayez."}

            data = response.json()
            texte = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"reponse": texte.strip()}

    except Exception as e:
        logger.error(f"Crash Backend: {str(e)}")
        return {"reponse": "⚠️ Erreur de connexion au cerveau de l'IA. Mode local activé."}

@app.get("/")
def root(): return {"status": "ok"}