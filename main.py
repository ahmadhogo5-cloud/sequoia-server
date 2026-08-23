import os
from facebook_ids_router import router as facebook_ids_router
app.include_router(facebook_ids_router)
import asyncio
from typing import List, Literal, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(
    app.include_router(facebook_ids_router)
    title="Sequoia AI Server",
    version="0.4.2"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ENVIRONMENT
# =========================================================

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
).strip()


GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.7-flash"
).strip()


GEMINI_EMBEDDING_MODEL = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-2"
).strip()


FALLBACK_MODELS = [
    model.strip()
    for model in os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "gemini-3.6-flash,gemini-3.5-flash-lite"
    ).split(",")
    if model.strip()
]


SUPABASE_URL = os.getenv(
    "SUPABASE_URL",
    ""
).strip().rstrip("/")


SUPABASE_KEY = os.getenv(
    "SUPABASE_SERVICE_ROLE_KEY",
    ""
).strip()


OWNER_ID = os.getenv(
    "SEQUOIA_OWNER_ID",
    "Owner"
).strip() or "Owner"


RETRYABLE_STATUS = {
    429,
    500,
    502,
    503,
    504
}


MAX_RETRIES_PER_MODEL = 3


SYSTEM_PROMPT = """
أنت سيكويا، مساعد شخصي ذكي لمستخدم واحد.

قواعد أساسية:

- تحدث بصورة طبيعية ومباشرة.
- استخدم لهجة المستخدم عندما يكون ذلك مناسباً.
- استخدم الذكريات المسترجعة عندما تكون مرتبطة بالسؤال.
- لا تدّع أنك تتذكر شيئاً غير موجود في السياق أو الذاكرة.
- إذا تعارضت معلومة قديمة مع معلومة أحدث من المستخدم، فضّل الأحدث.
- فرّق بين الحقيقة المؤكدة والاستنتاج.
- لا تدّع تنفيذ إجراء خارجي إلا إذا كانت هناك نتيجة تنفيذ حقيقية.
"""


# =========================================================
# REQUEST / RESPONSE MODELS
# =========================================================

class HistoryItem(BaseModel):

    role: Literal[
        "user",
        "assistant"
    ]

    content: str = Field(
        min_length=1,
        max_length=12000
    )


class ChatRequest(BaseModel):

    user_id: str = Field(
        default="Owner",
        max_length=128
    )

    message: str = Field(
        min_length=1,
        max_length=12000
    )

    relationship: str = Field(
        default="رفيق يومي",
        max_length=100
    )

    dialect: str = Field(
        default="لهجة المستخدم",
        max_length=100
    )

    history: List[HistoryItem] = Field(
        default_factory=list
    )


class ChatResponse(BaseModel):

    reply: str

    model: str

    memory_saved: bool

    database_connected: bool

    fallback_used: bool


# =========================================================
# SUPABASE
# =========================================================

def supabase_headers(
    extra: Optional[dict] = None
) -> dict:

    headers = {

        "apikey": SUPABASE_KEY,

        "Content-Type": "application/json"
    }


    if (
        SUPABASE_KEY
        and not SUPABASE_KEY.startswith("sb_secret_")
    ):

        headers["Authorization"] = (
            f"Bearer {SUPABASE_KEY}"
        )


    if extra:

        headers.update(extra)


    return headers


async def db_insert(
    table: str,
    payload: dict
) -> bool:

    if not SUPABASE_URL or not SUPABASE_KEY:

        return False


    try:

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.post(

                f"{SUPABASE_URL}/rest/v1/{table}",

                headers=supabase_headers(
                    {
                        "Prefer": "return=minimal"
                    }
                ),

                json=payload
            )


        if response.status_code not in (
            200,
            201,
            204
        ):

            print(
                f"Supabase insert error "
                f"({table}): "
                f"{response.status_code} "
                f"{response.text[:500]}"
            )

            return False


        return True


    except Exception as error:

        print(
            f"Supabase insert exception "
            f"({table}): "
            f"{type(error).__name__}: "
            f"{error}"
        )

        return False


async def db_recent_messages(
    limit: int = 24
) -> list:

    if not SUPABASE_URL or not SUPABASE_KEY:

        return []


    params = {

        "user_id":
            f"eq.{OWNER_ID}",

        "select":
            "role,content,created_at",

        "order":
            "created_at.desc",

        "limit":
            str(limit)
    }


    try:

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.get(

                f"{SUPABASE_URL}/rest/v1/messages",

                headers=supabase_headers(),

                params=params
            )


        if response.status_code != 200:

            print(
                "Supabase read messages error: "
                f"{response.status_code} "
                f"{response.text[:500]}"
            )

            return []


        rows = response.json()

        rows.reverse()

        return rows


    except Exception as error:

        print(
            "Supabase read messages exception: "
            f"{type(error).__name__}: "
            f"{error}"
        )

        return []


async def db_memories(
    limit: int = 12
) -> list:

    if not SUPABASE_URL or not SUPABASE_KEY:

        return []


    params = {

        "user_id":
            f"eq.{OWNER_ID}",

        "select":
            "id,category,content,"
            "importance,confidence,created_at",

        "order":
            "created_at.desc",

        "limit":
            str(limit)
    }


    try:

        async with httpx.AsyncClient(
            timeout=30
        ) as client:

            response = await client.get(

                f"{SUPABASE_URL}/rest/v1/memories",

                headers=supabase_headers(),

                params=params
            )


        if response.status_code != 200:

            print(
                "Supabase read memories error: "
                f"{response.status_code} "
                f"{response.text[:500]}"
            )

            return []


        return response.json()


    except Exception as error:

        print(
            "Supabase read memories exception: "
            f"{type(error).__name__}: "
            f"{error}"
        )

        return []


# =========================================================
# GEMINI EMBEDDINGS
# =========================================================

async def gemini_embedding(
    text: str,
    task_type: str = "RETRIEVAL_DOCUMENT"
) -> list:

    if not GEMINI_API_KEY:

        raise RuntimeError(
            "GEMINI_API_KEY is not configured"
        )


    url = (

        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"

        f"{GEMINI_EMBEDDING_MODEL}:embedContent"
    )


    payload = {

        "content": {

            "parts": [

                {
                    "text": text
                }
            ]
        },

        "embedContentConfig": {

            "taskType":
                task_type,

            "outputDimensionality":
                768
        }
    }


    headers = {

        "x-goog-api-key":
            GEMINI_API_KEY,

        "Content-Type":
            "application/json"
    }


    async with httpx.AsyncClient(
        timeout=60
    ) as client:

        response = await client.post(

            url,

            headers=headers,

            json=payload
        )


    if response.status_code != 200:

        raise RuntimeError(

            "Embedding failed: "
            f"{response.status_code} "
            f"{response.text[:500]}"
        )


    data = response.json()


    return data[
        "embedding"
    ][
        "values"
    ]


# =========================================================
# SEMANTIC MEMORY SEARCH
# =========================================================

async def db_semantic_memories(
    query_text: str,
    limit: int = 12
) -> list:

    if not SUPABASE_URL or not SUPABASE_KEY:

        return []


    try:

        query_embedding = await gemini_embedding(

            query_text,

            task_type="RETRIEVAL_QUERY"
        )


        async with httpx.AsyncClient(
            timeout=60
        ) as client:

            response = await client.post(

                (
                    f"{SUPABASE_URL}"
                    "/rest/v1/rpc/match_memories"
                ),

                headers=supabase_headers(),

                json={

                    "query_embedding":
                        query_embedding,

                    "match_owner":
                        OWNER_ID,

                    "match_count":
                        limit
                }
            )


        if response.status_code != 200:

            print(

                "Semantic memory search error: "

                f"{response.status_code} "

                f"{response.text[:500]}"
            )

            return []


        return response.json()


    except Exception as error:

        print(

            "Semantic memory search exception: "

            f"{type(error).__name__}: "

            f"{error}"
        )

        return []


# =========================================================
# SAVE EVERYTHING
# =========================================================

async def save_user_memory(
    text: str
) -> bool:

    memory_embedding = None


    try:

        memory_embedding = await gemini_embedding(

            text,

            task_type="RETRIEVAL_DOCUMENT"
        )


    except Exception as error:

        print(

            "Memory embedding skipped: "

            f"{type(error).__name__}: "

            f"{error}"
        )


    return await db_insert(

        "memories",

        {

            "user_id":
                OWNER_ID,

            "category":
                "conversation",

            "content":
                text[:5000],

            "importance":
                5,

            "confidence":
                1.0,

            "embedding":
                memory_embedding,

            "metadata": {

                "source":
                    "all_memory_v0.4.2",

                "kind":
                    "raw_user_message"
            }
        }
    )


# =========================================================
# GEMINI CHAT
# =========================================================

def model_chain() -> list:

    result = []


    for model in (
        [GEMINI_MODEL]
        + FALLBACK_MODELS
    ):

        if (
            model
            and model not in result
        ):

            result.append(model)


    return result


async def call_gemini_model(
    model: str,
    contents: list,
    system_text: str,
    max_tokens: int
):

    url = (

        "https://generativelanguage.googleapis.com/"
        "v1beta/models/"

        f"{model}:generateContent"

        f"?key={GEMINI_API_KEY}"
    )


    payload = {

        "systemInstruction": {

            "parts": [

                {
                    "text":
                        system_text
                }
            ]
        },

        "contents":
            contents,

        "generationConfig": {

            "maxOutputTokens":
                max_tokens
        }
    }


    async with httpx.AsyncClient(
        timeout=90
    ) as client:

        return await client.post(

            url,

            json=payload
        )


async def gemini_generate(
    contents: list,
    system_text: str,
    max_tokens: int = 1400
):

    if not GEMINI_API_KEY:

        raise HTTPException(

            status_code=500,

            detail=(
                "GEMINI_API_KEY "
                "is not configured"
            )
        )


    errors = []

    chain = model_chain()


    for model_index, model in enumerate(chain):

        for attempt in range(
            MAX_RETRIES_PER_MODEL
        ):

            try:

                response = await call_gemini_model(

                    model,

                    contents,

                    system_text,

                    max_tokens
                )


                if response.status_code == 200:

                    data = response.json()


                    try:

                        text = (

                            data[
                                "candidates"
                            ][0][
                                "content"
                            ][
                                "parts"
                            ][0][
                                "text"
                            ].strip()
                        )


                        return (

                            text,

                            model,

                            model_index > 0
                        )


                    except Exception:

                        errors.append(

                            f"{model}: "
                            "unexpected response"
                        )

                        break


                errors.append(

                    f"{model}: HTTP "

                    f"{response.status_code}: "

                    f"{response.text[:800]}"
                )


                if (
                    response.status_code
                    in RETRYABLE_STATUS
                ):

                    if (
                        attempt
                        < MAX_RETRIES_PER_MODEL - 1
                    ):

                        await asyncio.sleep(

                            1.5
                            * (2 ** attempt)
                        )

                        continue


                    break


                break


            except (
                httpx.TimeoutException,
                httpx.NetworkError
            ) as error:

                errors.append(

                    f"{model}: "

                    f"{type(error).__name__}: "

                    f"{error}"
                )


                if (
                    attempt
                    < MAX_RETRIES_PER_MODEL - 1
                ):

                    await asyncio.sleep(

                        1.5
                        * (2 ** attempt)
                    )

                    continue


                break


            except Exception as error:

                errors.append(

                    f"{model}: "

                    f"{type(error).__name__}: "

                    f"{error}"
                )

                break


    raise HTTPException(

        status_code=503,

        detail={

            "message":
                (
                    "All Gemini models "
                    "are temporarily unavailable."
                ),

            "attempted_models":
                chain,

            "errors":
                errors[-6:]
        }
    )


# =========================================================
# ROOT
# =========================================================

@app.get("/")
async def root():

    return {

        "name":
            "Sequoia",

        "status":
            "online",

        "version":
            "0.4.2",

        "memory":
            "supabase+semantic",

        "primary_model":
            GEMINI_MODEL,

        "embedding_model":
            GEMINI_EMBEDDING_MODEL,

        "fallback_models":
            FALLBACK_MODELS
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
async def health():

    database_connected = False


    if (
        SUPABASE_URL
        and SUPABASE_KEY
    ):

        try:

            async with httpx.AsyncClient(
                timeout=15
            ) as client:

                response = await client.get(

                    (
                        f"{SUPABASE_URL}"
                        "/rest/v1/messages"
                    ),

                    headers=supabase_headers(),

                    params={

                        "user_id":
                            f"eq.{OWNER_ID}",

                        "select":
                            "id",

                        "limit":
                            "1"
                    }
                )


            database_connected = (
                response.status_code == 200
            )


        except Exception as error:

            print(

                "Supabase health exception: "

                f"{type(error).__name__}: "

                f"{error}"
            )


    return {

        "ok":
            True,

        "version":
            "0.4.2",

        "model":
            GEMINI_MODEL,

        "embedding_model":
            GEMINI_EMBEDDING_MODEL,

        "fallback_models":
            FALLBACK_MODELS,

        "gemini_configured":
            bool(GEMINI_API_KEY),

        "supabase_configured":
            bool(
                SUPABASE_URL
                and SUPABASE_KEY
            ),

        "database_connected":
            database_connected
    }


# =========================================================
# MEMORY STATUS
# =========================================================

@app.get("/memory/status")
async def memory_status():

    messages = await db_recent_messages(
        limit=5
    )

    memories = await db_memories(
        limit=10
    )


    return {

        "owner":
            OWNER_ID,

        "recent_messages_count":
            len(messages),

        "memory_count_returned":
            len(memories),

        "recent_memories":
            memories
    }


# =========================================================
# MEMORY SEARCH
# =========================================================

@app.get("/memory/search")
async def memory_search(

    q: str = Query(
        min_length=1,
        max_length=5000
    )
):

    memories = await db_semantic_memories(

        q,

        limit=12
    )


    return {

        "query":
            q,

        "count":
            len(memories),

        "memories":
            memories
    }


# =========================================================
# MEMORY REINDEX
# =========================================================

@app.post("/memory/reindex")
async def memory_reindex():

    if (
        not SUPABASE_URL
        or not SUPABASE_KEY
    ):

        raise HTTPException(

            status_code=500,

            detail=(
                "Supabase is not configured"
            )
        )


    async with httpx.AsyncClient(
        timeout=60
    ) as client:

        response = await client.get(

            (
                f"{SUPABASE_URL}"
                "/rest/v1/memories"
            ),

            headers=supabase_headers(),

            params={

                "user_id":
                    f"eq.{OWNER_ID}",

                "embedding":
                    "is.null",

                "select":
                    "id,content",

                "limit":
                    "100"
            }
        )


    if response.status_code != 200:

        raise HTTPException(

            status_code=500,

            detail=response.text
        )


    memories = response.json()

    updated = 0

    failed = 0


    async with httpx.AsyncClient(
        timeout=60
    ) as client:

        for memory in memories:

            try:

                embedding = await gemini_embedding(

                    memory["content"],

                    task_type="RETRIEVAL_DOCUMENT"
                )


                update_response = await client.patch(

                    (
                        f"{SUPABASE_URL}"
                        "/rest/v1/memories"
                        f"?id=eq.{memory['id']}"
                    ),

                    headers=supabase_headers(

                        {
                            "Prefer":
                                "return=minimal"
                        }
                    ),

                    json={

                        "embedding":
                            embedding
                    }
                )


                if (
                    update_response.status_code
                    in (200, 204)
                ):

                    updated += 1


                else:

                    failed += 1

                    print(

                        "Reindex update failed: "

                        f"{update_response.status_code} "

                        f"{update_response.text[:500]}"
                    )


            except Exception as error:

                failed += 1


                print(

                    "Reindex failed for "

                    f"{memory.get('id')}: "

                    f"{type(error).__name__}: "

                    f"{error}"
                )


    return {

        "found":
            len(memories),

        "updated":
            updated,

        "failed":
            failed
    }


# =========================================================
# CHAT
# =========================================================

@app.post(
    "/chat",
    response_model=ChatResponse
)
async def chat(
    req: ChatRequest
):

    previous_messages = (
        await db_recent_messages(
            limit=24
        )
    )


    user_saved = await db_insert(

        "messages",

        {

            "user_id":
                OWNER_ID,

            "role":
                "user",

            "content":
                req.message
        }
    )


    memory_saved = await save_user_memory(

        req.message
    )


    relevant_memories = (
        await db_semantic_memories(

            req.message,

            limit=12
        )
    )


    if not relevant_memories:

        relevant_memories = (
            await db_memories(
                limit=12
            )
        )


    memory_text = (
        "لا توجد ذكريات مسترجعة."
    )


    if relevant_memories:

        memory_text = "\n".join(

            (
                f"- ["
                f"{memory.get('category', 'general')}"
                f"] "
                f"{memory.get('content', '')}"
            )

            for memory
            in relevant_memories
        )


    system_text = (

        SYSTEM_PROMPT

        + (
            f"\nنوع العلاقة: "
            f"{req.relationship}"
        )

        + (
            f"\nاللهجة: "
            f"{req.dialect}"
        )

        + (
            "\n\nذكريات مرتبطة "
            "بالسؤال الحالي:\n"
        )

        + memory_text
    )


    contents = []


    if previous_messages:

        for item in previous_messages:

            text = str(
                item.get(
                    "content",
                    ""
                )
            ).strip()


            if not text:

                continue


            contents.append(

                {

                    "role": (
                        "model"
                        if item.get("role")
                        == "assistant"
                        else "user"
                    ),

                    "parts": [

                        {
                            "text":
                                text
                        }
                    ]
                }
            )


    else:

        for item in req.history[-20:]:

            contents.append(

                {

                    "role": (
                        "model"
                        if item.role
                        == "assistant"
                        else "user"
                    ),

                    "parts": [

                        {
                            "text":
                                item.content
                        }
                    ]
                }
            )


    contents.append(

        {

            "role":
                "user",

            "parts": [

                {
                    "text":
                        req.message
                }
            ]
        }
    )


    (
        reply,
        used_model,
        fallback_used

    ) = await gemini_generate(

        contents,

        system_text
    )


    await db_insert(

        "messages",

        {

            "user_id":
                OWNER_ID,

            "role":
                "assistant",

            "content":
                reply
        }
    )


    return ChatResponse(

        reply=
            reply,

        model=
            used_model,

        memory_saved=
            memory_saved,

        database_connected=
            bool(
                SUPABASE_URL
                and SUPABASE_KEY
                and user_saved
            ),

        fallback_used=
            fallback_used
        )
