"""API FastAPI pour la veille Data & AI Governance."""
import hashlib
import logging
import os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import firestore

from scraper import scrape_all_sources
from ai_curator import process_articles
from visual_generator import save_visual_html
from linkedin_publisher import generate_weekly_edito, generate_visual, publish_to_linkedin
from config import GCP_PROJECT, MAX_ARTICLES_PER_WEEK

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MIA Veille - Data & AI Governance",
    description="API de veille automatisée sur la Data Governance et l'IA",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Firestore client
db = None
try:
    db = firestore.Client(project=GCP_PROJECT)
    logger.info(f"✅ Firestore connecté (projet: {GCP_PROJECT})")
except Exception as e:
    logger.warning(f"⚠️ Firestore non disponible: {e} — mode local activé")


@app.get("/")
async def root():
    """Health check."""
    return {
        "status": "ok",
        "service": "MIA Veille - Data & AI Governance",
        "version": "1.0.0",
        "firestore": "connected" if db else "offline"
    }


@app.post("/api/scrape")
async def run_scrape():
    """Déclenche le scraping complet : RSS → scoring → Firestore."""
    logger.info("🚀 Démarrage du scraping...")
    
    # 1. Scrape toutes les sources RSS
    raw_articles = await scrape_all_sources()
    
    if not raw_articles:
        return {"status": "warning", "message": "Aucun article récupéré"}
    
    # 2. Scoring et enrichissement avec Claude
    scored_articles = await process_articles(raw_articles)
    
    # 3. Limiter le nombre d'articles par jour
    top_articles = scored_articles[:MAX_ARTICLES_PER_WEEK]
    
    # 4. Générer les visuels HTML
    for article in top_articles:
        if article.get("visual_type"):
            save_visual_html(article)
    
    # 5. Sauvegarder dans Firestore
    saved_count = 0
    for article in top_articles:
        if "id" not in article:
            article["id"] = hashlib.md5(article.get("title", "").encode()).hexdigest()[:12]
    if db:
        batch = db.batch()
        for article in top_articles:
            doc_ref = db.collection("articles").document(article["id"])
            article_data = {
                **article,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            batch.set(doc_ref, article_data, merge=True)
            saved_count += 1
        batch.commit()
        logger.info(f"💾 {saved_count} articles sauvegardés dans Firestore")
    else:
        logger.warning("⚠️ Firestore offline — articles non sauvegardés")
    
    # 6. Générer et publier le post LinkedIn automatiquement
    linkedin_result = None
    try:
        trending = [a for a in raw_articles if a.get("is_trending")]
        trend_keywords = set()
        for a in trending:
            trend_keywords.update(a.get("trending_keywords", []))
        trends = list(trend_keywords)[:10]
        
        edito = generate_weekly_edito(top_articles, trends)
        post_text = edito.get("post_text", "")
        post_type = edito.get("post_type", "observateur")
        hashtags = edito.get("hashtags", [])
        
        # S'assurer que les hashtags sont dans le post
        if post_text and hashtags and not any(h in post_text for h in hashtags):
            post_text = post_text.rstrip() + "\n\n" + " ".join(hashtags)
        
        if post_text:
            # Garde-fou anti-shadowban : max 1 post LinkedIn par jour
            already_published_today = False
            if db:
                from zoneinfo import ZoneInfo
                today_paris = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d")
                recent = (
                    db.collection("linkedin_posts")
                    .order_by("published_at", direction=firestore.Query.DESCENDING)
                    .limit(1)
                    .stream()
                )
                for doc in recent:
                    last_date = doc.to_dict().get("published_at", "")[:10]
                    if last_date == today_paris:
                        already_published_today = True
                        logger.warning(f"⛔ Post déjà publié aujourd'hui ({last_date}) — publication bloquée pour éviter le shadowban")
                        break

            if already_published_today:
                linkedin_result = {"status": "skipped", "reason": "Un post a déjà été publié aujourd'hui (limite 1/jour)"}
            else:
                # Générer un visuel IA pour accompagner le post
                image_bytes = generate_visual(post_text, post_type)
                linkedin_result = publish_to_linkedin(post_text, image_bytes)
            logger.info(f"📣 LinkedIn: {linkedin_result.get('status')} — type={post_type} — image={linkedin_result.get('has_image')}")
            
            # Sauvegarder le post dans Firestore
            if db and linkedin_result.get("status") == "published":
                db.collection("linkedin_posts").add({
                    "post_text": post_text,
                    "post_type": post_type,
                    "post_id": linkedin_result.get("post_id"),
                    "has_image": linkedin_result.get("has_image", False),
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "hashtags": hashtags,
                })
        else:
            logger.warning("⚠️ Édito vide, publication LinkedIn ignorée")
    except Exception as e:
        logger.error(f"❌ Erreur LinkedIn auto-publish: {e}")
        linkedin_result = {"status": "error", "error": str(e)}
    
    return {
        "status": "ok",
        "raw_articles": len(raw_articles),
        "scored_articles": len(scored_articles),
        "saved_articles": saved_count,
        "linkedin": linkedin_result,
        "top_articles": [
            {
                "title": a.get("title", "Sans titre"),
                "source": a.get("source_name", ""),
                "score": a.get("score", 0),
                "category": a.get("category_label", ""),
            }
            for a in top_articles[:5]
        ]
    }


@app.get("/api/articles")
async def get_articles(category: str = None, limit: int = 20):
    """Récupère les articles depuis Firestore."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore non disponible")
    
    query = db.collection("articles").order_by("score", direction=firestore.Query.DESCENDING)
    
    if category:
        query = query.where("category", "==", category)
    
    query = query.limit(limit)
    docs = query.stream()
    
    articles = []
    for doc in docs:
        data = doc.to_dict()
        articles.append(data)
    
    return {"articles": articles, "count": len(articles)}


@app.get("/api/articles/{article_id}")
async def get_article(article_id: str):
    """Récupère un article spécifique."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore non disponible")
    
    doc = db.collection("articles").document(article_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Article non trouvé")
    
    return doc.to_dict()


@app.get("/api/linkedin")
async def get_linkedin_posts(limit: int = 10):
    """Récupère les posts LinkedIn prêts à publier."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore non disponible")
    
    query = (
        db.collection("articles")
        .where("linkedin_post", "!=", "")
        .order_by("linkedin_post")
        .order_by("score", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )
    
    docs = query.stream()
    
    posts = []
    for doc in docs:
        data = doc.to_dict()
        posts.append({
            "id": data.get("id"),
            "title": data.get("title"),
            "source": data.get("source_name"),
            "score": data.get("score"),
            "linkedin_post": data.get("linkedin_post"),
            "linkedin_hook": data.get("linkedin_hook"),
            "linkedin_suggested_day": data.get("linkedin_suggested_day"),
            "visual_type": data.get("visual_type"),
        })
    
    return {"posts": posts, "count": len(posts)}


@app.post("/api/linkedin/edito")
async def generate_edito():
    """Génère l'édito LinkedIn hebdomadaire à partir des articles scrapés."""
    logger.info("📝 Génération de l'édito LinkedIn...")

    # 1. Scrape les articles frais
    raw_articles = await scrape_all_sources()
    if not raw_articles:
        raise HTTPException(status_code=404, detail="Aucun article trouvé")

    # 2. Extraire les tendances
    trending = [a for a in raw_articles if a.get("is_trending")]
    trend_keywords = set()
    for a in trending:
        trend_keywords.update(a.get("trending_keywords", []))
    trends = list(trend_keywords)[:10]

    # 3. Prendre les meilleurs articles (trending + récents)
    top_articles = sorted(
        raw_articles,
        key=lambda x: (x.get("is_trending", False), x.get("source_weight", 1.0)),
        reverse=True
    )[:15]

    # 4. Générer l'édito
    edito = generate_weekly_edito(top_articles, trends)

    return edito


@app.post("/api/linkedin/publish")
async def publish_edito(post_text: str = None):
    """Publie l'édito sur LinkedIn. Si pas de texte fourni, en génère un."""
    if not post_text:
        # Générer d'abord
        edito_response = await generate_edito()
        post_text = edito_response.get("post_text", "")

    if not post_text:
        raise HTTPException(status_code=400, detail="Aucun texte à publier")

    result = publish_to_linkedin(post_text)
    return result


@app.get("/api/linkedin/latest")
async def get_latest_linkedin_post():
    """Retourne le dernier post LinkedIn publié (depuis Firestore)."""
    if not db:
        return {"post_text": None, "message": "Firestore non disponible"}

    try:
        docs = (
            db.collection("linkedin_posts")
            .order_by("published_at", direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        for doc in docs:
            return doc.to_dict()
        return {"post_text": None, "message": "Aucun post trouvé"}
    except Exception as e:
        return {"post_text": None, "message": str(e)}


@app.get("/api/linkedin/posts")
async def get_all_linkedin_posts():
    """Retourne tous les posts LinkedIn publiés (depuis Firestore)."""
    if not db:
        return {"posts": [], "message": "Firestore non disponible"}
    try:
        docs = (
            db.collection("linkedin_posts")
            .order_by("published_at", direction=firestore.Query.DESCENDING)
            .limit(50)
            .stream()
        )
        posts = []
        for doc in docs:
            d = doc.to_dict()
            posts.append({
                "post_id": d.get("post_id"),
                "post_type": d.get("post_type"),
                "published_at": d.get("published_at"),
                "has_image": d.get("has_image", False),
                "hashtags": d.get("hashtags", []),
                "post_text": d.get("post_text", "")[:200],
            })
        return {"posts": posts, "count": len(posts)}
    except Exception as e:
        return {"posts": [], "message": str(e)}


@app.get("/api/linkedin/stats")
async def get_linkedin_stats():
    """Récupère les stats de tous les posts LinkedIn via l'API LinkedIn."""
    import httpx
    from linkedin_publisher import LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_URN

    if not LINKEDIN_ACCESS_TOKEN:
        raise HTTPException(status_code=400, detail="Token LinkedIn non configuré")

    # Récupérer les post_ids depuis Firestore
    post_ids = []
    if db:
        docs = (
            db.collection("linkedin_posts")
            .order_by("published_at", direction=firestore.Query.DESCENDING)
            .limit(20)
            .stream()
        )
        for doc in docs:
            d = doc.to_dict()
            if d.get("post_id") and d["post_id"] != "unknown":
                post_ids.append({
                    "post_id": d["post_id"],
                    "post_type": d.get("post_type", "?"),
                    "published_at": d.get("published_at", ""),
                    "has_image": d.get("has_image", False),
                })

    if not post_ids:
        return {"stats": [], "message": "Aucun post avec ID valide trouvé"}

    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "LinkedIn-Version": "202506",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    stats = []
    async with httpx.AsyncClient(timeout=30) as client:
        for post in post_ids:
            share_id = post["post_id"]
            try:
                # Stats sociales (likes, comments, shares)
                social_url = f"https://api.linkedin.com/rest/socialActions/{share_id}"
                social_resp = await client.get(social_url, headers=headers)

                likes = 0
                comments = 0
                shares = 0
                if social_resp.status_code == 200:
                    data = social_resp.json()
                    likes = data.get("likesSummary", {}).get("totalLikes", 0)
                    comments = data.get("commentsSummary", {}).get("totalFirstLevelComments", 0)
                    shares = data.get("shareStatistics", {}).get("shareCount", 0)

                stats.append({
                    **post,
                    "likes": likes,
                    "comments": comments,
                    "shares": shares,
                    "engagement": likes + comments + shares,
                })
            except Exception as e:
                stats.append({**post, "likes": 0, "comments": 0, "shares": 0, "engagement": 0, "error": str(e)})

    # Trier par engagement
    stats.sort(key=lambda x: x["engagement"], reverse=True)
    return {"stats": stats, "total_posts": len(stats)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
