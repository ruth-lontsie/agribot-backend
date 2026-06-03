import os
import httpx
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgriBot")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# L'URL EXACTE fournie par ton guide de démarrage
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

class QuestionRequest(BaseModel):
    question: str

@app.post("/chat")
async def chat(request: QuestionRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Clé API manquante")

    # On utilise exactement la structure du cURL
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"Réponds comme un expert agronome camerounais en 3 phrases maximum : {request.question}"
                    }
                ]
            }
        ]
    }

    # On utilise l'en-tête recommandé : X-goog-api-key
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(GEMINI_URL, json=payload, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Erreur Google : {response.text}")
                return {"erreur": response.json()}

            data = response.json()
            texte_ia = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"reponse": texte_ia.strip()}

    except Exception as e:
        logger.error(f"Erreur : {e}")
        raise HTTPException(status_code=500, detail="Le serveur AgriBot a rencontré un problème.")

@app.get("/")
def root():
    return {"status": "AgriBot prêt avec gemini-flash-latest ! 🇨🇲"}