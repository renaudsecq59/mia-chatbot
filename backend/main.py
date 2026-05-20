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
from linkedin_publisher import generate_weekly_edito, publish_to_linkedin
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
    
    return {
        "status": "ok",
        "raw_articles": len(raw_articles),
        "scored_articles": len(scored_articles),
        "saved_articles": saved_count,
        "top_articles": [
            {
                "title": a.get("title", "Sans titre"),
                "source": a.get("source_name", ""),
                "score": a.get("score", 0),
                "category": a.get("category_label", ""),
                "has_linkedin": bool(a.get("linkedin_post")),
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


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
