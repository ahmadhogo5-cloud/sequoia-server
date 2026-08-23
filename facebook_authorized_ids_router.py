import os
from typing import Dict, List

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/facebook", tags=["facebook-authorized-ids"])

FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN", "").strip()
FACEBOOK_GRAPH_VERSION = os.getenv("FACEBOOK_GRAPH_VERSION", "").strip().strip("/")


def graph_url(path: str) -> str:
    path = path.lstrip("/")
    if FACEBOOK_GRAPH_VERSION:
        return f"https://graph.facebook.com/{FACEBOOK_GRAPH_VERSION}/{path}"
    return f"https://graph.facebook.com/{path}"


async def graph_get(path: str, params: dict) -> dict:
    if not FACEBOOK_ACCESS_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="FACEBOOK_ACCESS_TOKEN is not configured on Render"
        )

    merged = dict(params)
    merged["access_token"] = FACEBOOK_ACCESS_TOKEN

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(graph_url(path), params=merged)

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={
                "provider": "facebook",
                "status": response.status_code,
                "message": response.text[:1000],
            },
        )

    return response.json()


def normalize_user(item: dict, source: str) -> dict:
    return {
        "id": str(item.get("id", "")).strip(),
        "name": str(item.get("name", "")).strip(),
        "source": source,
        "authorized": True,
    }


@router.get("/authorized-ids")
async def authorized_ids(
    q: str = Query(default="", max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
):
    """
    Returns only Facebook user IDs that the configured Facebook access token
    is permitted to see. It does not enumerate arbitrary/global Facebook IDs.
    """

    users_by_id: Dict[str, dict] = {}

    # The currently authenticated Facebook user.
    me = await graph_get("me", {"fields": "id,name"})
    current = normalize_user(me, "me")
    if current["id"]:
        users_by_id[current["id"]] = current

    # Friends visible to this app/token under Facebook's permissions.
    friends = await graph_get(
        "me/friends",
        {
            "fields": "id,name",
            "limit": str(limit),
        },
    )

    for item in friends.get("data", []):
        user = normalize_user(item, "me/friends")
        if user["id"]:
            users_by_id[user["id"]] = user

    users: List[dict] = list(users_by_id.values())

    query = q.strip().casefold()
    if query:
        users = [
            user
            for user in users
            if query in user["name"].casefold()
            or query in user["id"].casefold()
        ]

    users.sort(key=lambda item: item["name"].casefold())
    users = users[:limit]

    return {
        "ok": True,
        "scope": "facebook-authorized-only",
        "query": q,
        "count": len(users),
        "users": users,
    }
