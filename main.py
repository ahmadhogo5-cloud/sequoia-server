import os
import json
import asyncio
from typing import List, Literal, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Sequoia AI Server", version="0.4.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash").strip()
GEMINI_EMBEDDING_MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-2"
).strip()
# Optional comma-separated fallback chain.
# Example:
# gemini-3.6-flash,gemini-3.5-flash-lite
FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "gemini-3.6-flash,gemini-3.5-flash-lite"
    ).split(",")
    if m.strip()
]

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
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

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES_PER_MODEL = 3


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
    fallback_used: bool = False


def supabase_headers(extra: Optional[dict] = None):
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
    }
    # Legacy JWT service_role keys can also be sent as Bearer.
    # New sb_secret_* keys should be sent only as apikey.
    if SUPABASE_KEY and not SUPABASE_KEY.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {SUPABASE_KEY}"
    if extra:
        headers.update(extra)
    return headers


async def db_insert(table: str, payload: dict) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False

    url = f"{SUPABASE_URL}/rest/v1/{table}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                url,
                headers=supabase_headers({"Prefer": "return=minimal"}),
                json=payload,
            )
        if r.status_code not in (200, 201, 204):
            print(f"Supabase insert error ({table}): {r.status_code} {r.text[:500]}")
            return False
        return True
    except Exception as e:
        print(f"Supabase insert exception ({table}): {type(e).__name__}: {e}")
        return False


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

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=supabase_headers(), params=params)

        if r.status_code != 200:
            print(f"Supabase read messages error: {r.status_code} {r.text[:500]}")
            return []

        rows = r.json()
        rows.reverse()
        return rows
    except Exception as e:
        print(f"Supabase read messages exception: {type(e).__name__}: {e}")
        return []


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

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=supabase_headers(), params=params)

        if r.status_code != 200:
            print(f"Supabase read memories error: {r.status_code} {r.text[:500]}")
            return []

        return r.json()
    except Exception as e:
        print(f"Supabase read memories exception: {type(e).__name__}: {e}")
        return []

async def gemini_embedding(
    text: str,
    task_type: str = "RETRIEVAL_DOCUMENT"
):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_EMBEDDING_MODEL}:embedContent"
    )

    payload = {
        "content": {
            "parts": [
                {"text": text}
            ]
        },
        "embedContentConfig": {
            "taskType": task_type,
            "outputDimensionality": 768
        }
    }

    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            url,
            headers=headers,
            json=payload
        )

    if r.status_code != 200:
        raise RuntimeError(
            f"Embedding failed: {r.status_code} {r.text[:500]}"
        )

    data = r.json()
    return data["embedding"]["values"]
    
    
def model_chain():
    result = []
    for model in [GEMINI_MODEL] + FALLBACK_MODELS:
        if model and model not in result:
            result.append(model)
    return result


async def call_gemini_model(model: str, contents: list, system_text: str, max_tokens: int):
    payload = {
        "systemInstruction": {"parts": [{"text": system_text}]},
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens
        },
    }

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={GEMINI_API_KEY}"
    )

    async with httpx.AsyncClient(timeout=90) as client:
        return await client.post(url, json=payload)


async def gemini_generate(contents: list, system_text: str, max_tokens: int = 1400):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured")

    errors = []
    chain = model_chain()

    for model_index, model in enumerate(chain):
        for attempt in range(MAX_RETRIES_PER_MODEL):
            try:
                r = await call_gemini_model(model, contents, system_text, max_tokens)

                if r.status_code == 200:
                    data = r.json()
                    try:
                        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                        return text, model, (model_index > 0)
                    except Exception:
                        errors.append(f"{model}: unexpected response")
                        break

                body = r.text[:800]
                errors.append(f"{model}: HTTP {r.status_code}: {body}")

                # Retry temporary overload/rate/server errors.
                if r.status_code in RETRYABLE_STATUS:
                    if attempt < MAX_RETRIES_PER_MODEL - 1:
                        # 1.5s, 3s, ...
                        await asyncio.sleep(1.5 * (2 ** attempt))
                        continue
                    # Exhausted retries -> next fallback model.
                    break

                # Non-temporary error (for example bad model name).
                # Move to the next fallback immediately.
                break

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                errors.append(f"{model}: {type(e).__name__}: {e}")
                if attempt < MAX_RETRIES_PER_MODEL - 1:
                    await asyncio.sleep(1.5 * (2 ** attempt))
                    continue
                break
            except Exception as e:
                errors.append(f"{model}: {type(e).__name__}: {e}")
                break

    raise HTTPException(
        status_code=503,
        detail={
            "message": "All Gemini models are temporarily unavailable.",
            "attempted_models": chain,
            "errors": errors[-6:],
        },
    )


async def save_everything_memory(user_message: str) -> bool:
    """
    Save every user message as long-term memory automatically.
    The user never needs to say "remember this".
    """

    # First: guaranteed raw memory copy.
      memory_embedding = None

    try:
        memory_embedding = await gemini_embedding(
            user_message,
            task_type="RETRIEVAL_DOCUMENT"
        )
    except Exception as e:
        print(
            f"Memory embedding skipped: "
            f"{type(e).__name__}: {e}"
        )
    raw_saved = await db_insert(
        "memories",
        {
            "user_id": OWNER_ID,
            "category": "conversation",
            "content": user_message[:5000],
            "importance": 5,
            "confidence": 1.0,
                        "embedding": memory_embedding,
            "metadata": {
                "source": "all_memory_v0.4.1",
                "kind": "raw_user_message",
            },
        },
    )

    # Second: try to create a cleaner structured memory as an extra layer.
    # If this fails, the raw message is still safely stored.
    prompt = f"""
حوّل رسالة المستخدم التالية إلى ذاكرة قصيرة ومنظمة للمساعد الشخصي:
{user_message}

أعد JSON صالح فقط بهذا الشكل:
{{
  "category":"general",
  "content":"ملخص دقيق للمعلومة أو الحدث أو الطلب أو الفكرة",
  "importance":5,
  "confidence":1.0
}}

لا تُرجع save:false. يجب دائماً إنتاج ذاكرة.
لا تضف معلومات غير موجودة في الرسالة.
"""

    try:
        raw, _, _ = await gemini_generate(
            [{"role": "user", "parts": [{"text": prompt}]}],
            "أنت وحدة تنظيم ذاكرة. أعد JSON صالح فقط دون شرح.",
            max_tokens=300,
        )

        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        obj = json.loads(raw)
        content = str(obj.get("content", "")).strip()

        if content and content != user_message.strip():
            importance = max(1, min(10, int(obj.get("importance", 5))))
            confidence = max(0.0, min(1.0, float(obj.get("confidence", 1.0))))

            await db_insert(
                "memories",
                {
                    "user_id": OWNER_ID,
                    "category": str(obj.get("category", "general"))[:80],
                    "content": content[:5000],
                    "importance": importance,
                    "confidence": confidence,
                    "metadata": {
                        "source": "all_memory_v0.4.1",
                        "kind": "organized_memory",
                    },
                },
            )

    except Exception as e:
        print(f"Memory organization skipped: {type(e).__name__}: {e}")

    return raw_saved

@app.get("/")
async def root():
    return {
        "name": "Sequoia",
        "status": "online",
        "version": "0.4.1",
        "memory": "supabase",
        "primary_model": GEMINI_MODEL,
        "fallback_models": FALLBACK_MODELS,
    }


@app.get("/health")
async def health():
    db_connected = False
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            url = f"{SUPABASE_URL}/rest/v1/messages"
            params = {
                "user_id": f"eq.{OWNER_ID}",
                "select": "id",
                "limit": "1",
            }
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(url, headers=supabase_headers(), params=params)
            db_connected = (r.status_code == 200)
            if not db_connected:
                print(f"Supabase health error: {r.status_code} {r.text[:500]}")
        except Exception as e:
            print(f"Supabase health exception: {type(e).__name__}: {e}")

    return {
        "ok": True,
        "version": "0.4.1",
        "model": GEMINI_MODEL,
        "fallback_models": FALLBACK_MODELS,
        "gemini_configured": bool(GEMINI_API_KEY),
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_KEY),
        "database_connected": db_connected,
    }


@app.post("/memory/reindex")
async def memory_reindex():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(
            status_code=500,
            detail="Supabase is not configured"
        )

    url = f"{SUPABASE_URL}/rest/v1/memories"

    params = {
        "user_id": f"eq.{OWNER_ID}",
        "embedding": "is.null",
        "select": "id,content",
        "limit": "100"
    }

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(
            url,
            headers=supabase_headers(),
            params=params
        )

    if r.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail=r.text
        )

    memories = r.json()
    updated = 0
    failed = 0

    for memory in memories:
        try:
            embedding = await gemini_embedding(
                memory["content"],
                task_type="RETRIEVAL_DOCUMENT"
            )

            update_url = (
                f"{SUPABASE_URL}/rest/v1/memories"
                f"?id=eq.{memory['id']}"
            )

            async with httpx.AsyncClient(timeout=60) as client:
                update_response = await client.patch(
                    update_url,
                    headers=supabase_headers(),
                    json={"embedding": embedding}
                )

            if update_response.status_code in (200, 204):
                updated += 1
            else:
                failed += 1

        except Exception as e:
            print(
                f"Reindex failed for {memory['id']}: "
                f"{type(e).__name__}: {e}"
            )
            failed += 1

    return {
        "found": len(memories),
        "updated": updated,
        "failed": failed
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
    db_connected = bool(SUPABASE_URL and SUPABASE_KEY)

    user_saved = await db_insert(
        "messages",
        {
            "user_id": OWNER_ID,
            "role": "user",
            "content": req.message,
        },
    )

    stored_messages = await db_recent_messages(limit=30)
    stored_memories = await db_semantic_memories(
    req.message,
    limit=12
)

if not stored_memories:
    stored_memories = await db_memories(limit=12)

    memory_text = "لا توجد ذكريات طويلة الأمد محفوظة بعد."
    if stored_memories:
        memory_text = "\n".join(
            f"- [{m.get('category', 'general')}] {m.get('content', '')}"
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
            contents.append(
                {
                    "role": "model" if item.role == "assistant" else "user",
                    "parts": [{"text": item.content}],
                }
            )
        contents.append({"role": "user", "parts": [{"text": req.message}]})

    reply, used_model, fallback_used = await gemini_generate(contents, system_text)

    await db_insert(
        "messages",
        {
            "user_id": OWNER_ID,
            "role": "assistant",
            "content": reply,
        },
    )

    # Every user message is saved automatically as long-term memory.
    memory_saved = await save_everything_memory(req.message)

    return ChatResponse(
        reply=reply,
        model=used_model,
        memory_saved=memory_saved,
        database_connected=db_connected and user_saved,
        fallback_used=fallback_used,
    )
