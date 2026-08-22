import os
import json
from typing import List, Literal, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Sequoia AI Server", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
OWNER_ID = os.getenv("SEQUOIA_OWNER_ID", "owner").strip() or "owner"

SYSTEM_PROMPT = """
أنت سيكويا، مساعد شخصي ذكي لمستخدم واحد.
تحدث بصورة طبيعية ومباشرة، وتعلّم أسلوب المستخدم ولهجته من السياق.

قواعد الذاكرة:
- استخدم الذكريات والمحادثات السابقة المرسلة لك عندما تكون ذات صلة.
- لا تتظاهر بأنك تتذكر شيئاً غير موجود في السياق أو الذاكرة.
- إذا تعارضت معلومة قديمة مع معلومة أحدث من المستخدم، فضّل الأحدث.
- فرّق بين الحقيقة المؤكدة والاستنتاج.
- لا تدّع تنفيذ أمر على الهاتف أو في حساب خارجي إلا إذا أعاد التطبيق نتيجة تنفيذ حقيقية.
"""

class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)

class ChatRequest(BaseModel):
    user_id: str = Field(default="owner", max_length=128)
    message: str = Field(min_length=1, max_length=12000)
    relationship: str = Field(default="رفيق يومي", max_length=100)
    dialect: str = Field(default="لهجة المستخدم", max_length=100)
    history: List[HistoryItem] = Field(default_factory=list)

class ChatResponse(BaseModel):
    reply: str
    model: str
    memory_saved: bool = False
    database_connected: bool = False

def supabase_headers(extra: Optional[dict] = None):
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    if SUPABASE_KEY and not SUPABASE_KEY.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {SUPABASE_KEY}"
    if extra:
        headers.update(extra)
    return headers

async def db_insert(table: str, payload: dict) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=supabase_headers({"Prefer": "return=minimal"}), json=payload)
    if r.status_code not in (200, 201, 204):
        print(f"Supabase insert error ({table}): {r.status_code} {r.text[:500]}")
        return False
    return True

async def db_recent_messages(limit: int = 30) -> list:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    url = f"{SUPABASE_URL}/rest/v1/messages"
    params = {
        "user_id": f"eq.{OWNER_ID}",
        "select": "role,content,created_at",
        "order": "created_at.desc",
        "limit": str(limit),
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=supabase_headers(), params=params)
    if r.status_code != 200:
        print(f"Supabase read messages error: {r.status_code} {r.text[:500]}")
        return []
    rows = r.json()
    rows.reverse()
    return rows

async def db_memories(limit: int = 30) -> list:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    url = f"{SUPABASE_URL}/rest/v1/memories"
    params = {
        "user_id": f"eq.{OWNER_ID}",
        "select": "category,content,importance,confidence,created_at",
        "order": "importance.desc,created_at.desc",
        "limit": str(limit),
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=supabase_headers(), params=params)
    if r.status_code != 200:
        print(f"Supabase read memories error: {r.status_code} {r.text[:500]}")
        return []
    return r.json()

async def gemini_generate(contents: list, system_text: str, max_tokens: int = 1400, temperature: float = 0.85):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured")
    payload = {
        "systemInstruction": {"parts": [{"text": system_text}]},
        "contents": contents,
        "generationConfig": {"temperature": temperature, "topP": 0.95, "maxOutputTokens": max_tokens},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(url, json=payload)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Gemini request failed ({r.status_code}): {r.text[:1000]}")
    data = r.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        raise HTTPException(status_code=502, detail="Gemini returned an unexpected response")

async def extract_and_save_memory(user_message: str) -> bool:
    prompt = f"""
حلل رسالة المستخدم التالية وحدها:
{user_message}

استخرج فقط معلومة طويلة الأمد تستحق أن يتذكرها مساعد شخصي مستقبلاً:
- تفضيل ثابت
- معلومة شخصية صريحة
- قرار مشروع
- هدف مستمر
- اسم/علاقة مهمة
- قاعدة عمل يكرر المستخدم الاعتماد عليها

لا تحفظ الأسئلة العابرة أو الكلام المؤقت.
أعد JSON فقط بهذا الشكل:
{{"save":true,"category":"general","content":"...","importance":5,"confidence":1.0}}
أو:
{{"save":false}}
"""
    try:
        raw = await gemini_generate(
            [{"role": "user", "parts": [{"text": prompt}]}],
            "أنت وحدة استخراج ذاكرة. أعد JSON صالح فقط دون شرح.",
            max_tokens=300,
            temperature=0.15,
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        obj = json.loads(raw)
        if not obj.get("save"):
            return False
        content = str(obj.get("content", "")).strip()
        if not content:
            return False
        importance = max(1, min(10, int(obj.get("importance", 5))))
        confidence = max(0.0, min(1.0, float(obj.get("confidence", 1.0))))
        return await db_insert("memories", {
            "user_id": OWNER_ID,
            "category": str(obj.get("category", "general"))[:80],
            "content": content[:5000],
            "importance": importance,
            "confidence": confidence,
            "metadata": {"source": "auto_memory_v0.3"},
        })
    except Exception as e:
        print(f"Memory extraction skipped: {e}")
        return False

@app.get("/")
async def root():
    return {"name": "Sequoia", "status": "online", "version": "0.3.0", "memory": "supabase"}

@app.get("/health")
async def health():
    db_ok = False
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            await db_recent_messages(limit=1)
            db_ok = True
        except Exception:
            db_ok = False
    return {
        "ok": True,
        "version": "0.3.0",
        "model": GEMINI_MODEL,
        "gemini_configured": bool(GEMINI_API_KEY),
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_KEY),
        "database_connected": db_ok,
    }

@app.get("/memory/status")
async def memory_status():
    messages = await db_recent_messages(limit=5)
    memories = await db_memories(limit=10)
    return {
        "owner": OWNER_ID,
        "recent_messages_count": len(messages),
        "memory_count_returned": len(memories),
        "recent_memories": memories,
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    user_saved = await db_insert("messages", {
        "user_id": OWNER_ID,
        "role": "user",
        "content": req.message,
    })

    stored_messages = await db_recent_messages(limit=30)
    stored_memories = await db_memories(limit=30)

    memory_text = "لا توجد ذكريات طويلة الأمد محفوظة بعد."
    if stored_memories:
        memory_text = "\n".join(
            f"- [{m.get('category','general')}] {m.get('content','')}"
            for m in stored_memories
        )

    system_text = (
        SYSTEM_PROMPT
        + f"\nنوع العلاقة: {req.relationship}"
        + f"\nاللهجة: {req.dialect}"
        + "\n\nالذكريات طويلة الأمد المتاحة:\n"
        + memory_text
    )

    contents = []
    for item in stored_messages[-24:]:
        role = "model" if item.get("role") == "assistant" else "user"
        text = str(item.get("content", "")).strip()
        if text:
            contents.append({"role": role, "parts": [{"text": text}]})

    if not contents:
        for item in req.history[-20:]:
            contents.append({
                "role": "model" if item.role == "assistant" else "user",
                "parts": [{"text": item.content}],
            })
        contents.append({"role": "user", "parts": [{"text": req.message}]})

    reply = await gemini_generate(contents, system_text)

    await db_insert("messages", {
        "user_id": OWNER_ID,
        "role": "assistant",
        "content": reply,
    })

    memory_saved = await extract_and_save_memory(req.message)

    return ChatResponse(
        reply=reply,
        model=GEMINI_MODEL,
        memory_saved=memory_saved,
        database_connected=bool(user_saved),
    )
