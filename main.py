import os
from typing import List, Literal
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Sequoia AI Server", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash").strip()

class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)

class ChatRequest(BaseModel):
    user_id: str = Field(default="guest", max_length=128)
    message: str = Field(min_length=1, max_length=12000)
    relationship: str = Field(default="رفيق يومي", max_length=100)
    dialect: str = Field(default="لهجة المستخدم", max_length=100)
    history: List[HistoryItem] = Field(default_factory=list)

class ChatResponse(BaseModel):
    reply: str
    model: str

SYSTEM_PROMPT = """
أنت سيكويا، مساعد شخصي ذكي شديد الطبيعية والدفء في الحوار.
- تحدث بالعربية أو بلغة المستخدم، وتعلّم لهجته ومفرداته من السياق وقلّدها بصورة طبيعية من دون سخرية.
- اجعل الردود إنسانية، مباشرة، غير متكلفة، وقريبة عاطفياً حسب نوع العلاقة الذي اختاره المستخدم.
- تذكّر سياق المحادثة المرسل إليك ولا تتصرف كأن كل رسالة محادثة جديدة.
- لا تكرر أنك ذكاء اصطناعي من دون سبب، لكن إذا سُئلت عن حقيقتك فأجب بوضوح أنك مساعد ذكاء اصطناعي.
- لا تدّع تنفيذ إجراء على الهاتف أو الحسابات إلا إذا أعاد التطبيق لك نتيجة تنفيذ حقيقية.
- الأوامر التي ستغيّر شيئاً فعلياً على الهاتف أو الحسابات يجب أن ينفذها تطبيق أندرويد بعد تأكيد المستخدم، وليس هذا الخادم.
- كن مفيداً ومتعاطفاً وتكيّف مع أسلوب المستخدم.
"""

@app.get("/")
async def root():
    return {"name": "Sequoia", "status": "online", "version": "0.1.0"}

@app.get("/health")
async def health():
    return {"ok": True, "model": GEMINI_MODEL, "key_configured": bool(GEMINI_API_KEY)}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured")

    recent = req.history[-20:]
    contents = []
    for item in recent:
        contents.append({
            "role": "user" if item.role == "user" else "model",
            "parts": [{"text": item.content}]
        })
    contents.append({"role": "user", "parts": [{"text": req.message}]})

    relationship_note = (
        f"\nنوع العلاقة الذي اختاره المستخدم: {req.relationship}."
        f"\nاللهجة المفضلة/المتعلمة: {req.dialect}."
        f"\nمعرف المستخدم الداخلي: {req.user_id}."
    )

    payload = {
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT + relationship_note}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.9,
            "topP": 0.95,
            "maxOutputTokens": 1200
        }
    }

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )

    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(url, json=payload)

    if response.status_code != 200:
        detail = response.text[:1200]
        raise HTTPException(
            status_code=502,
            detail=f"Gemini request failed ({response.status_code}): {detail}"
        )

    data = response.json()
    try:
        reply = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        raise HTTPException(status_code=502, detail="Gemini returned an unexpected response")

    return ChatResponse(reply=reply, model=GEMINI_MODEL)
