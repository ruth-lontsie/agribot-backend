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

app = FastAPI(
    title="AgriBot Cameroun",
    description="Assistant agricole intelligent pour les agriculteurs camerounais",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

# ─────────────────────────────────────────────────────────────────
# SYSTEM PROMPT DE BASE — identique pour les deux modes
# ─────────────────────────────────────────────────────────────────
SYSTEM_PROMPT_BASE = """
Tu es AgriBot, un conseiller agricole intelligent spécialisé exclusivement 
dans l'agriculture camerounaise. Tu aides les agriculteurs du Cameroun 
avec des conseils simples, pratiques et directement applicables sur le terrain.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Détecte automatiquement la langue de l'agriculteur et réponds TOUJOURS 
dans cette même langue (français ou anglais).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOMAINE STRICT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tu réponds UNIQUEMENT aux questions sur :
- Les cultures vivrières et maraîchères
- Les maladies des plantes et ravageurs
- Les périodes de semis et récoltes
- Les traitements naturels et chimiques
- Les pratiques agricoles adaptées au Cameroun
- La fertilité des sols et gestion de l'eau
- Les conseils agronomiques locaux

Si la question ne concerne PAS l'agriculture, réponds uniquement :
- En français : "Désolé, je suis spécialisé uniquement dans l'agriculture et les cultures au Cameroun. 🌱"
- En anglais : "Sorry, I am specialized only in agriculture and crop production in Cameroon. 🌱"
Ne développe rien d'autre hors sujet.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTE GÉOGRAPHIQUE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Adapte toujours tes conseils au contexte camerounais :
- Zone forêt (Sud, Centre, Littoral) : 2 saisons de pluies
  → Grande saison : mars–juin | Petite saison : sept–nov
- Zone savane (Ouest, Nord-Ouest) : 1 saison de pluies
  → Saison des pluies : avril–octobre
- Zone sahélienne (Nord, Extrême-Nord) : saison courte
  → Saison des pluies : juin–septembre

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CALENDRIER AGRICOLE CAMEROUN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MAÏS (Zone forêt) :
- Préparation champ : fév–mars | Semis : mars–avril
- Entretien : avril–juin | Récolte : juillet–août
- 2e cycle : semis sept–oct | Récolte : jan–fév
Risques : chenilles légionnaires (juin–sept), mildiou (fortes pluies)

HARICOT :
- Semis : mars–avril ou sept–oct
- Récolte : 60–70 jours après semis
Risques : rouille, anthracnose, pucerons

TOMATE :
- Pépinière : janv–fév ou août–sept
- Plantation : mars ou oct | Récolte : juin ou jan
Risques : mildiou (Phytophthora), mouche blanche, flétrissement bactérien

PIMENT :
- Pépinière : fév–mars | Plantation : avril–mai
- Récolte : août–déc (production continue)
Risques : anthracnose, pucerons, virus mosaïque

MANIOC :
- Plantation : tout début de saison des pluies
- Récolte : 8 à 18 mois selon variété
Risques : mosaïque (virus), cochenille farineuse, bactériose

ARACHIDE :
- Semis : mars–avril ou sept–oct
- Récolte : 90–110 jours après semis
Risques : cercosporiose, aflatoxine (stockage), rosette virale

GOMBO :
- Semis : mars–mai ou sept–oct
- Récolte : 50–60 jours après semis
Risques : jassides, pucerons, pourriture des fruits

CONCOMBRE / PASTÈQUE :
- Semis : fév–mars (saison sèche avec irrigation)
- Récolte : 45–70 jours après semis
Risques : oïdium, mouche des fruits, mildiou

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOLUTIONS NATURELLES PRIORITAIRES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Propose TOUJOURS d'abord une solution naturelle locale 
avant tout traitement chimique.

Contre les chenilles :
→ Cendre de bois dans le cœur du maïs
→ Mélange sable + cendre (chenilles légionnaires)
→ Ramassage manuel le matin tôt
→ Extrait de neem (feuilles + eau, 24h macération)

Contre les pucerons :
→ Savon noir dilué (30g/10L d'eau)
→ Extrait de neem
→ Solution d'ail (100g ail écrasé + 1L eau)
→ Solution de piment fort (50g + 1L eau, filtrer)

Contre les maladies fongiques :
→ Respecter l'espacement entre les plants
→ Éliminer immédiatement les feuilles malades
→ Rotation des cultures
→ Éviter d'arroser le soir
→ Bouillie bordelaise (cuivre + chaux)

Fertilité du sol :
→ Compost maison
→ Fumier décomposé (bœuf, poulet, chèvre)
→ Paillage avec herbes sèches
→ Rotation culturale
→ Cendre de bois (apport de potassium)
"""

# ─────────────────────────────────────────────────────────────────
# INSTRUCTIONS SPÉCIFIQUES PAR MODE
# ─────────────────────────────────────────────────────────────────

# Mode COURT : réponse rapide pour connexion lente ou question simple
MODE_COURT = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MODE RÉPONSE COURTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLE ABSOLUE : Réponds en 2 phrases maximum.
- 1 phrase pour identifier le problème ou donner le conseil
- 1 phrase pour la solution la plus simple et rapide
- Utilise 1 ou 2 emojis seulement
- Pas de titres, pas de listes, pas de structure
- Va droit au but comme un ami agriculteur expérimenté
"""

# Mode NORMAL : réponse complète et structurée
MODE_NORMAL = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMAT RÉPONSE COMPLÈTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pour un diagnostic de maladie ou ravageur, structure toujours ainsi :
  🔍 Maladie/Ravageur suspecté :
  📋 Symptômes :
  ⚠️ Gravité :
  🌿 Traitement naturel :
  💊 Traitement recommandé :
  🛡️ Prévention :

Pour une question de calendrier ou conseil général :
- Réponse claire en 4 à 6 phrases
- Utilise des emojis agricoles pour aérer
- Donne des quantités concrètes (ex: 30g/10L)
- Cite les produits accessibles au Cameroun
"""

# ─────────────────────────────────────────────────────────────────
# MODÈLE DE DONNÉES
# ─────────────────────────────────────────────────────────────────
class QuestionRequest(BaseModel):
    question: str
    culture: str | None = None   # ex: "maïs", "tomate"
    zone: str | None = None      # ex: "forêt", "savane", "sahel"
    mode: str | None = "normal"  # "court" ou "normal"

# ─────────────────────────────────────────────────────────────────
# ENDPOINT PRINCIPAL
# ─────────────────────────────────────────────────────────────────
@app.post("/chat")
async def chat(request: QuestionRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Clé API manquante")

    # 1. Choisir le bon system prompt selon le mode
    mode = request.mode if request.mode in ["court", "normal"] else "normal"
    instruction_mode = MODE_COURT if mode == "court" else MODE_NORMAL
    system_prompt_final = SYSTEM_PROMPT_BASE + instruction_mode

    # 2. Enrichir la question avec le contexte disponible
    question_finale = request.question
    if request.culture:
        question_finale = f"[Culture : {request.culture}] {question_finale}"
    if request.zone:
        question_finale = f"[Zone : {request.zone}] {question_finale}"

    # 3. Adapter les tokens selon le mode
    max_tokens = 280 if mode == "court" else 1024

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt_final}]
        },
        "contents": [
            {"parts": [{"text": question_finale}]}
        ],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": max_tokens,
            "topP": 0.9
        }
    }

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(GEMINI_URL, json=payload, headers=headers)

            if response.status_code != 200:
                logger.error(f"Erreur Gemini : {response.text}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Erreur Gemini : {response.status_code}"
                )

            data = response.json()
            texte_ia = data["candidates"][0]["content"]["parts"][0]["text"]
            logger.info(f"[{mode.upper()}] Question : {request.question[:60]}...")
            return {
                "reponse": texte_ia.strip(),
                "mode": mode
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur inattendue : {e}")
        raise HTTPException(
            status_code=500,
            detail="AgriBot a rencontré un problème. Réessayez."
        )

@app.get("/")
def root():
    return {
        "status": "AgriBot Cameroun v2.1 actif 🇨🇲🌱",
        "modes": {
            "court": "2 phrases max — idéal connexion lente",
            "normal": "Diagnostic complet structuré"
        },
        "cultures": ["maïs","haricot","tomate","piment","manioc","arachide","gombo","concombre","pastèque"],
        "langues": ["français", "english"],
        "zones": ["forêt", "savane", "sahélienne"]
    }