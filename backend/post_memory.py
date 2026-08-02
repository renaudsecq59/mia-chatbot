"""Mémoire des posts LinkedIn : historique, déduplication sémantique, feedback loop.

Stocke les posts publiés dans Firestore, récupère l'historique pour injection
dans le prompt, et fait de la déduplication sémantique via embeddings Gemini.
"""
import logging
import math
from datetime import datetime, timezone
from google import genai
from google.cloud import firestore
from config import GCP_PROJECT, GCP_LOCATION, GEMINI_API_KEY

logger = logging.getLogger(__name__)

# Client Gemini pour les embeddings
try:
    if GEMINI_API_KEY:
        _embed_client = genai.Client(api_key=GEMINI_API_KEY)
    else:
        _embed_client = genai.Client(
            vertexai=True,
            project=GCP_PROJECT,
            location=GCP_LOCATION,
        )
    _EMBED_MODEL = "text-embedding-005"
except Exception:
    _embed_client = None
    _EMBED_MODEL = None

# Seuil de similarité cosinus au-dessus duquel on considère que c'est un duplicate
DEDUP_THRESHOLD = 0.85


def get_recent_posts(db, limit: int = 5) -> list[dict]:
    """Récupère les N derniers posts LinkedIn depuis Firestore."""
    if not db:
        return []
    try:
        docs = (
            db.collection("linkedin_posts")
            .order_by("published_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        posts = []
        for doc in docs:
            data = doc.to_dict()
            posts.append({
                "post_text": data.get("post_text", ""),
                "post_type": data.get("post_type", ""),
                "hook": data.get("hook", ""),
                "hashtags": data.get("hashtags", []),
                "published_at": data.get("published_at", ""),
                "post_id": data.get("post_id", ""),
                "engagement": data.get("engagement", {}),
            })
        logger.info(f"📚 {len(posts)} posts récents récupérés depuis Firestore")
        return posts
    except Exception as e:
        logger.warning(f"⚠️ Erreur récupération posts récents: {e}")
        return []


def get_post_history_summary(db, limit: int = 5) -> str:
    """Retourne un résumé textuel des derniers posts pour injection dans le prompt."""
    posts = get_recent_posts(db, limit)
    if not posts:
        return "Aucun post précédent — c'est le premier post."

    lines = ["POSTS PRÉCÉDENTS (ne PAS répéter ces angles/sujets) :"]
    for i, p in enumerate(posts, 1):
        hook = p.get("hook") or p["post_text"][:120]
        post_type = p.get("post_type", "?")
        date = p.get("published_at", "")[:10]
        lines.append(f"{i}. [{post_type}] ({date}) {hook}")

    return "\n".join(lines)


def get_embedding(text: str) -> list[float] | None:
    """Génère un embedding pour le texte donné via Gemini."""
    if not _embed_client or not text.strip():
        return None
    try:
        from google.genai import types as genai_types
        result = _embed_client.models.embed_content(
            model=_EMBED_MODEL,
            contents=text[:3000],  # Limiter pour la perf
            config=genai_types.EmbedContentConfig(
                task_type="SEMANTIC_SIMILARITY",
            ),
        )
        return result.embeddings[0].values
    except Exception as e:
        logger.warning(f"⚠️ Embedding échoué: {e}")
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calcule la similarité cosinus entre deux vecteurs."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def check_duplicate(db, new_post_text: str, limit: int = 10) -> dict:
    """Vérifie si le nouveau post est trop similaire à un post précédent.

    Returns:
        {"is_duplicate": bool, "max_similarity": float, "similar_post": str|None}
    """
    posts = get_recent_posts(db, limit)
    if not posts:
        return {"is_duplicate": False, "max_similarity": 0.0, "similar_post": None}

    new_embedding = get_embedding(new_post_text)
    if not new_embedding:
        # Fallback: comparaison par mots-clés si embedding échoue
        return _keyword_duplicate_check(new_post_text, posts)

    max_sim = 0.0
    most_similar_hook = None

    for p in posts:
        old_embedding = get_embedding(p["post_text"])
        if not old_embedding:
            continue
        sim = cosine_similarity(new_embedding, old_embedding)
        if sim > max_sim:
            max_sim = sim
            most_similar_hook = p.get("hook") or p["post_text"][:80]

    is_dup = max_sim >= DEDUP_THRESHOLD
    if is_dup:
        logger.warning(f"🔄 Duplicate détecté: similarity={max_sim:.3f} avec '{most_similar_hook}'")
    else:
        logger.info(f"✅ Pas de duplicate: max similarity={max_sim:.3f}")

    return {
        "is_duplicate": is_dup,
        "max_similarity": round(max_sim, 3),
        "similar_post": most_similar_hook,
    }


def _keyword_duplicate_check(new_text: str, posts: list[dict]) -> dict:
    """Fallback: comparaison par mots-clés si embeddings indisponibles."""
    new_words = set(new_text.lower().split())
    max_overlap = 0.0
    most_similar = None

    for p in posts:
        old_words = set(p["post_text"].lower().split())
        if not old_words:
            continue
        overlap = len(new_words & old_words) / len(new_words) if new_words else 0
        if overlap > max_overlap:
            max_overlap = overlap
            most_similar = p.get("hook") or p["post_text"][:80]

    # Seuil plus strict car les mots communs sont fréquents
    is_dup = max_overlap >= 0.70
    return {
        "is_duplicate": is_dup,
        "max_similarity": round(max_overlap, 3),
        "similar_post": most_similar,
    }


def store_post_embedding(db, post_text: str, post_id: str = ""):
    """Stocke l'embedding d'un post dans Firestore pour réutilisation future."""
    if not db:
        return
    embedding = get_embedding(post_text)
    if embedding:
        try:
            # Stocker dans une sous-collection pour éviter de surcharger le doc principal
            db.collection("post_embeddings").add({
                "post_id": post_id,
                "embedding": embedding,
                "text_preview": post_text[:200],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            logger.info(f"💾 Embedding stocké pour post {post_id}")
        except Exception as e:
            logger.warning(f"⚠️ Stockage embedding échoué: {e}")


def get_post_metrics(db, post_id: str) -> dict | None:
    """Récupère les métriques d'engagement d'un post depuis Firestore."""
    if not db:
        return None
    try:
        docs = db.collection("linkedin_posts").where("post_id", "==", post_id).limit(1).stream()
        for doc in docs:
            return doc.to_dict().get("engagement")
    except Exception:
        pass
    return None
