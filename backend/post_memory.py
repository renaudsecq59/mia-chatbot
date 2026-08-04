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


def fetch_linkedin_engagement(access_token: str, post_urn: str) -> dict | None:
    """Récupère les métriques d'engagement d'un post via l'API LinkedIn.

    Args:
        access_token: Token LinkedIn valide
        post_urn: URN du post (urn:li:share:xxx ou urn:li:ugcPost:xxx)

    Returns:
        {"likes": int, "comments": int, "impressions": int, "engagement_rate": float}
    """
    import httpx
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202607",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        # 1. Social Metadata API (remplace socialActions — fonctionne pour les posts personnels)
        likes_count = 0
        comments_count = 0

        social_resp = httpx.get(
            f"https://api.linkedin.com/rest/socialMetadata/{post_urn}",
            headers=headers, timeout=15,
        )
        if social_resp.status_code == 200:
            data = social_resp.json()
            # reactionSummaries: dict of reactionType -> {count}
            for rtype, rdata in data.get("reactionSummaries", {}).items():
                likes_count += rdata.get("count", 0)
            comments_count = data.get("commentSummary", {}).get("topLevelCount", 0)
        else:
            logger.debug(f"socialMetadata {post_urn}: {social_resp.status_code} — {social_resp.text[:200]}")

        # 2. Impressions via individualShareStatistics (profil personnel)
        impressions = 0
        try:
            analytics_resp = httpx.get(
                f"https://api.linkedin.com/rest/individualShareStatistics",
                params={"q": "share", "share": post_urn},
                headers=headers, timeout=15,
            )
            if analytics_resp.status_code == 200:
                elements = analytics_resp.json().get("elements", [])
                if elements:
                    stats = elements[0].get("totalShareStatistics", {})
                    impressions = stats.get("impressionCount", 0)
            else:
                logger.debug(f"individualShareStatistics {post_urn}: {analytics_resp.status_code}")
        except Exception:
            pass

        engagement_rate = round((likes_count + comments_count) / impressions * 100, 2) if impressions > 0 else 0.0

        return {
            "likes": likes_count,
            "comments": comments_count,
            "impressions": impressions,
            "engagement_rate": engagement_rate,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.warning(f"⚠️ Fetch engagement LinkedIn échoué pour {post_urn}: {e}")
        return None


def update_post_engagement(db, max_posts: int = 10) -> int:
    """Met à jour les métriques d'engagement des N derniers posts publiés.

    Returns: nombre de posts mis à jour.
    """
    if not db:
        return 0

    import os
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    if not access_token:
        logger.warning("⚠️ Pas de LINKEDIN_ACCESS_TOKEN — skip engagement update")
        return 0

    try:
        docs = (
            db.collection("linkedin_posts")
            .order_by("published_at", direction=firestore.Query.DESCENDING)
            .limit(max_posts)
            .stream()
        )

        updated = 0
        for doc in docs:
            data = doc.to_dict()
            post_id = data.get("post_id", "")
            if not post_id:
                continue

            # Skip si déjà fetché il y a moins de 24h
            existing_eng = data.get("engagement", {})
            if existing_eng and existing_eng.get("fetched_at", "")[:10] == datetime.now(timezone.utc).isoformat()[:10]:
                continue

            engagement = fetch_linkedin_engagement(access_token, post_id)
            if engagement:
                doc.reference.update({"engagement": engagement})
                updated += 1
                logger.info(f"📊 Engagement mis à jour pour {post_id}: {engagement['likes']} likes, {engagement['comments']} comments")

        logger.info(f"📊 Engagement mis à jour pour {updated}/{max_posts} posts")
        return updated
    except Exception as e:
        logger.error(f"❌ Erreur update engagement: {e}")
        return 0


def get_performance_insights(db, limit: int = 15) -> str:
    """Analyse les posts passés et retourne des insights pour le prompt.

    Identifie quels piliers, formats et styles performent le mieux.
    """
    if not db:
        return "Aucune donnée de performance disponible."

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
            eng = data.get("engagement", {})
            posts.append({
                "post_type": data.get("post_type", ""),
                "hook": data.get("hook", data.get("post_text", "")[:100]),
                "hashtags": data.get("hashtags", []),
                "likes": eng.get("likes", 0),
                "comments": eng.get("comments", 0),
                "engagement_rate": eng.get("engagement_rate", 0),
                "has_engagement": bool(eng),
            })

        if not posts:
            return "Aucun post précédent avec métriques."

        posts_with_eng = [p for p in posts if p["has_engagement"]]
        if not posts_with_eng:
            return f"{len(posts)} posts publiés mais aucune métrique d'engagement récupérée encore."

        # Trier par engagement
        posts_with_eng.sort(key=lambda p: p["likes"] + p["comments"], reverse=True)

        top_posts = posts_with_eng[:3]
        bottom_posts = posts_with_eng[-2:] if len(posts_with_eng) > 4 else []

        # Analyser quels formats performent
        format_scores = {}
        for p in posts_with_eng:
            fmt = p["post_type"]
            if fmt not in format_scores:
                format_scores[fmt] = {"total_eng": 0, "count": 0}
            format_scores[fmt]["total_eng"] += p["likes"] + p["comments"]
            format_scores[fmt]["count"] += 1

        best_format = max(format_scores.items(), key=lambda x: x[1]["total_eng"] / x[1]["count"]) if format_scores else None

        lines = ["PERFORMANCE DES POSTS PRÉCÉDENTS :"]

        if top_posts:
            lines.append("TOP POSTS (plus d'engagement) :")
            for p in top_posts:
                lines.append(f"  → [{p['post_type']}] {p['likes']} likes, {p['comments']} comments — {p['hook'][:80]}")

        if bottom_posts:
            lines.append("POSTS FAIBLES (moins d'engagement) :")
            for p in bottom_posts:
                lines.append(f"  → [{p['post_type']}] {p['likes']} likes, {p['comments']} comments — {p['hook'][:80]}")

        if best_format:
            avg = best_format[1]["total_eng"] / best_format[1]["count"]
            lines.append(f"FORMAT QUI PERFORME LE MIEUX: {best_format[0]} (avg {avg:.1f} interactions)")

        lines.append("CONCLUSION: Inspire-toi des top posts (angle, ton, structure) et évite les patterns des posts faibles.")

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"⚠️ Erreur performance insights: {e}")
        return "Erreur lors de l'analyse de performance."


# ============================================================
# MÉCANISME 1: LEARNING LOOP — Leçons du critic persistées
# ============================================================

def store_critic_lesson(db, critic_result: dict, post_text: str):
    """Stocke une leçon du critic en Firestore pour accumulation."""
    if not db or not critic_result:
        return
    try:
        db.collection("critic_lessons").add({
            "scores": critic_result.get("scores", {}),
            "average": critic_result.get("average", 0),
            "worst_dimension": critic_result.get("worst_dimension", ""),
            "suggestion": critic_result.get("suggestion", ""),
            "verdict": critic_result.get("verdict", ""),
            "post_preview": post_text[:200],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"📝 Leçon critic stockée (avg={critic_result.get('average', 0)})")
    except Exception as e:
        logger.warning(f"⚠️ Stockage leçon critic échoué: {e}")


def get_critic_lessons(db, limit: int = 20) -> str:
    """Récupère les leçons accumulées du critic pour injection dans le prompt.

    Synthétise les feedbacks récurrents en instructions actionnables.
    """
    if not db:
        return ""
    try:
        docs = (
            db.collection("critic_lessons")
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        lessons = [doc.to_dict() for doc in docs]
        if not lessons:
            return ""

        # Analyser les dimensions les plus faibles
        dim_counts = {}
        dim_scores = {}
        for l in lessons:
            scores = l.get("scores", {})
            for dim, score in scores.items():
                dim_counts[dim] = dim_counts.get(dim, 0) + 1
                dim_scores.setdefault(dim, []).append(score)

        # Dimensions systématiquement faibles (avg < 7)
        weak_dims = []
        for dim, scores_list in dim_scores.items():
            avg = sum(scores_list) / len(scores_list)
            if avg < 7:
                weak_dims.append((dim, round(avg, 1)))

        # Suggestions récurrentes
        suggestions = [l.get("suggestion", "") for l in lessons if l.get("suggestion")]
        unique_suggestions = list(dict.fromkeys(suggestions))[:5]

        lines = ["LEÇONS ACCUMULÉES PAR LE CRITIC (applique-les absolument) :"]

        if weak_dims:
            lines.append("DIMENSIONS SYSTÉMATIQUEMENT FAIBLES (à corriger en priorité) :")
            for dim, avg in sorted(weak_dims, key=lambda x: x[1]):
                lines.append(f"  → {dim}: moyenne {avg}/10")

        if unique_suggestions:
            lines.append("SUGGESTIONS RÉCURRENTES DU CRITIC :")
            for s in unique_suggestions:
                lines.append(f"  → {s}")

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"⚠️ Erreur récupération leçons critic: {e}")
        return ""


# ============================================================
# MÉCANISME 2: AUTO-TUNING — Analyse des patterns gagnants
# ============================================================

def get_style_guidelines(db, limit: int = 20) -> str:
    """Analyse les top posts et génère des guidelines de style injectées dans le prompt.

    Détecte les patterns structurels, de longueur, de ton et de hashtags
    qui corrèlent avec le plus d'engagement.
    """
    if not db:
        return ""
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
            eng = data.get("engagement", {})
            if not eng:
                continue
            posts.append({
                "post_text": data.get("post_text", ""),
                "post_type": data.get("post_type", ""),
                "hook": data.get("hook", ""),
                "hashtags": data.get("hashtags", []),
                "word_count": data.get("word_count", 0),
                "likes": eng.get("likes", 0),
                "comments": eng.get("comments", 0),
                "engagement_rate": eng.get("engagement_rate", 0),
            })

        if len(posts) < 3:
            return ""

        # Trier par engagement
        posts.sort(key=lambda p: p["likes"] + p["comments"], reverse=True)
        top = posts[:max(3, len(posts) // 3)]
        bottom = posts[-max(2, len(posts) // 3):]

        # Analyser les patterns des top posts
        top_avg_words = sum(p["word_count"] for p in top) / len(top)
        bottom_avg_words = sum(p["word_count"] for p in bottom) / len(bottom) if bottom else 0

        top_hashtags = {}
        for p in top:
            for h in p.get("hashtags", []):
                top_hashtags[h] = top_hashtags.get(h, 0) + 1
        popular_hashtags = sorted(top_hashtags.items(), key=lambda x: x[1], reverse=True)[:5]

        top_formats = {}
        for p in top:
            fmt = p["post_type"]
            top_formats[fmt] = top_formats.get(fmt, 0) + 1
        best_formats = sorted(top_formats.items(), key=lambda x: x[1], reverse=True)[:3]

        # Analyser la structure des hooks gagnants
        top_hooks = [p["hook"] for p in top if p.get("hook")]
        hook_patterns = []
        for h in top_hooks:
            if h.startswith(("Le ", "La ", "Les ", "Un ", "Une ", "En ")):
                hook_patterns.append("assertion directe")
            elif "?" in h:
                hook_patterns.append("question")
            elif any(w in h.lower() for w in ["chiffre", "x", "%", "fois"]):
                hook_patterns.append("choc chiffré")
            elif h.startswith(("Si ", "Quand ", "Pourquoi")):
                hook_patterns.append("conditionnel")
        best_hook = max(set(hook_patterns), key=hook_patterns.count) if hook_patterns else None

        lines = ["GUIDELINES DE STYLE (basées sur les posts qui performent le mieux) :"]

        if top_avg_words > 0:
            lines.append(f"  → Longueur idéale: ~{int(top_avg_words)} mots (top posts) vs ~{int(bottom_avg_words)} mots (posts faibles)")

        if best_formats:
            fmt_str = ", ".join(f"{f} ({c}x)" for f, c in best_formats)
            lines.append(f"  → Formats qui performent: {fmt_str}")

        if best_hook:
            lines.append(f"  → Pattern de hook gagnant: {best_hook}")

        if popular_hashtags:
            ht_str = ", ".join(f"#{h}" for h, _ in popular_hashtags)
            lines.append(f"  → Hashtags populaires dans les top posts: {ht_str}")

        lines.append("CONCLUSION: Reproduis ces patterns gagnants et évite les structures des posts faibles.")

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"⚠️ Erreur style guidelines: {e}")
        return ""


# ============================================================
# MÉCANISME 3: SCORING DES SOURCES RSS
# ============================================================

def update_source_scores(db):
    """Calcule un score par source RSS basé sur l'engagement des posts publiés.

    Associe chaque post à sa source d'origine et calcule un score moyen.
    """
    if not db:
        return {}
    try:
        docs = (
            db.collection("linkedin_posts")
            .order_by("published_at", direction=firestore.Query.DESCENDING)
            .limit(50)
            .stream()
        )
        source_stats = {}
        for doc in docs:
            data = doc.to_dict()
            eng = data.get("engagement", {})
            source = data.get("source_name", "unknown")
            if not eng:
                continue
            score = eng.get("likes", 0) + eng.get("comments", 0) * 3
            source_stats.setdefault(source, []).append(score)

        scores = {}
        for source, score_list in source_stats.items():
            avg = sum(score_list) / len(score_list)
            scores[source] = {
                "avg_engagement": round(avg, 1),
                "post_count": len(score_list),
                "total_engagement": sum(score_list),
            }

        # Stocker en Firestore pour réutilisation
        if scores:
            db.collection("source_scores").document("latest").set({
                "scores": scores,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            logger.info(f"📊 Scores de {len(scores)} sources mis à jour")

        return scores
    except Exception as e:
        logger.warning(f"⚠️ Erreur scoring sources: {e}")
        return {}


def get_top_sources(db, limit: int = 10) -> str:
    """Retourne les sources qui génèrent le plus d'engagement pour injection dans le prompt."""
    if not db:
        return ""
    try:
        doc = db.collection("source_scores").document("latest").get()
        if not doc.exists:
            return ""
        scores = doc.to_dict().get("scores", {})
        if not scores:
            return ""

        sorted_sources = sorted(scores.items(), key=lambda x: x[1]["avg_engagement"], reverse=True)
        top = sorted_sources[:limit]
        bottom = sorted_sources[-3:]

        lines = ["SOURCES QUI GÉNÈTENT LE PLUS D'ENGAGEMENT :"]
        for source, stats in top:
            lines.append(f"  → {source}: {stats['avg_engagement']} avg engagement ({stats['post_count']} posts)")

        if bottom:
            lines.append("SOURCES FAIBLES (à éviter) :")
            for source, stats in bottom:
                lines.append(f"  → {source}: {stats['avg_engagement']} avg engagement")

        lines.append("CONCLUSION: Priorise les articles des sources qui performent.")

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"⚠️ Erreur top sources: {e}")
        return ""


# ============================================================
# MÉCANISME 4: A/B TESTING DES HOOKS
# ============================================================

def store_hook_experiment(db, hooks: list[str], winner_idx: int, critic_scores: list[dict], post_id: str = ""):
    """Stocke une expérience A/B de hooks pour analyse future."""
    if not db or len(hooks) < 2:
        return
    try:
        db.collection("hook_experiments").add({
            "hooks": hooks,
            "winner_idx": winner_idx,
            "winner_hook": hooks[winner_idx],
            "critic_scores": critic_scores,
            "post_id": post_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"🧪 Expérience A/B hooks stockée — gagnant: hook #{winner_idx + 1}")
    except Exception as e:
        logger.warning(f"⚠️ Stockage A/B hooks échoué: {e}")


def get_hook_patterns(db, limit: int = 15) -> str:
    """Analyse les hooks gagnants des expériences A/B passées pour injection dans le prompt."""
    if not db:
        return ""
    try:
        docs = (
            db.collection("hook_experiments")
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        experiments = [doc.to_dict() for doc in docs]
        if not experiments:
            return ""

        winners = [e.get("winner_hook", "") for e in experiments if e.get("winner_hook")]
        if not winners:
            return ""

        lines = ["PATTERNS DE HOOKS GAGNANTS (A/B testing) :"]
        for i, h in enumerate(winners[:5]):
            lines.append(f"  → {h[:100]}")

        lines.append("CONCLUSION: Ces hooks ont gagné en A/B testing. Inspire-t'en pour le hook de ce post.")

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"⚠️ Erreur hook patterns: {e}")
        return ""


# ============================================================
# MÉCANISME 5: LEÇONS VISUELLES — Feedback du visual critic
# ============================================================

def get_visual_lessons(db, limit: int = 15) -> str:
    """Récupère les leçons du visual critic pour améliorer les futurs infographics.

    Identifie les problèmes récurrents (spelling, readability, layout) et
    génère des instructions correctives injectées dans le prompt image.
    """
    if not db:
        return ""
    try:
        docs = (
            db.collection("visual_lessons")
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        lessons = [doc.to_dict() for doc in docs]
        if not lessons:
            return ""

        # Analyser les dimensions récurrentes faibles
        dim_scores = {}
        all_issues = []
        for l in lessons:
            scores = l.get("scores", {})
            for dim, score in scores.items():
                dim_scores.setdefault(dim, []).append(score)
            for issue in l.get("issues", []):
                all_issues.append(issue)

        weak_dims = []
        for dim, scores_list in dim_scores.items():
            avg = sum(scores_list) / len(scores_list)
            if avg < 7:
                weak_dims.append((dim, round(avg, 1)))

        # Issues les plus fréquentes
        from collections import Counter
        issue_words = []
        for issue in all_issues:
            issue_lower = issue.lower()
            for keyword in ["spelling", "orthographe", "readability", "lisible", "overlap", "chevauchement", "layout", "alignement", "text", "truncated", "coupé"]:
                if keyword in issue_lower:
                    issue_words.append(keyword)
        frequent_issues = Counter(issue_words).most_common(3)

        lines = []
        if weak_dims:
            lines.append("PROBLÈMES VISUELS RÉCURRENTS (corrige-les dans l'infographic) :")
            for dim, avg in sorted(weak_dims, key=lambda x: x[1]):
                lines.append(f"  → {dim}: moyenne {avg}/10")

        if frequent_issues:
            lines.append("ISSUES FRÉQUENTES :")
            for issue, count in frequent_issues:
                lines.append(f"  → {issue} ({count}x)")

        if not lines:
            return ""

        lines.append("CONCLUSION: Applique ces corrections dans le design de l'infographic.")

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"⚠️ Erreur visual lessons: {e}")
        return ""
