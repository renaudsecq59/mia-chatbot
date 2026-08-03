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

        # Mettre à jour les métriques d'engagement des posts passés (feedback loop)
        if db:
            try:
                from post_memory import update_post_engagement, update_source_scores
                updated = update_post_engagement(db, max_posts=10)
                if updated:
                    logger.info(f"📊 {updated} posts ont eu leurs métriques mises à jour")
                    # MÉCANISME 3: Mettre à jour les scores des sources RSS
                    update_source_scores(db)
            except Exception as e:
                logger.warning(f"⚠️ Update engagement échoué: {e}")

        edito = generate_weekly_edito(top_articles, trends, db=db)
        post_text = edito.get("post_text", "")
        post_type = edito.get("post_type", "observateur")
        hashtags = edito.get("hashtags", [])

        # Forcer l'URL en FIN de post pour éviter la troncature LinkedIn
        # (LinkedIn tronque le commentary au niveau d'une URL inline quand il y a une image attachée)
        from linkedin_publisher import SITE_URL as _SITE_URL
        if post_text and _SITE_URL in post_text:
            post_text = post_text.replace(_SITE_URL, "").rstrip()
        # Reconstruire : contenu + URL + hashtags toujours en fin
        if post_text:
            url_line = f"\n\n{_SITE_URL}"
            hashtag_line = ("\n\n" + " ".join(hashtags)) if hashtags and not any(h in post_text for h in hashtags) else ""
            post_text = post_text.rstrip() + url_line + hashtag_line
        
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
                logger.info(f"📤 post_text avant publication: {len(post_text)} chars — fin: {repr(post_text[-80:])}")
                image_bytes = generate_visual(post_text, post_type, db=db)
                linkedin_result = publish_to_linkedin(post_text, image_bytes)
                # Compresser l'image en JPEG pour Firestore (< 200KB, limite 1MB)
                image_b64_thumb = None
                if image_bytes:
                    try:
                        from PIL import Image
                        import io
                        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                        img.thumbnail((800, 1067), Image.LANCZOS)  # ratio 3:4 max 800px
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=65, optimize=True)
                        compressed = buf.getvalue()
                        image_b64_thumb = __import__('base64').b64encode(compressed).decode()
                        logger.info(f"🖼️ Image compressée: {len(image_bytes)//1024}KB → {len(compressed)//1024}KB")
                    except Exception as e:
                        logger.warning(f"⚠️ Compression image échouée: {e}")
                linkedin_result["image_b64"] = image_b64_thumb
                linkedin_result["image_size_kb"] = round(len(image_bytes) / 1024) if image_bytes else 0
            logger.info(f"📣 LinkedIn: {linkedin_result.get('status')} — type={post_type} — image={linkedin_result.get('has_image')}")
            
            # Sauvegarder le post dans Firestore
            if db and linkedin_result.get("status") == "published":
                db.collection("linkedin_posts").add({
                    "post_text": post_text,
                    "post_type": post_type,
                    "post_id": linkedin_result.get("post_id"),
                    "has_image": linkedin_result.get("has_image", False),
                    "image_b64": linkedin_result.get("image_b64"),
                    "image_size_kb": linkedin_result.get("image_size_kb", 0),
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "hashtags": hashtags,
                    "hook": edito.get("hook", ""),
                    "quality_gate": edito.get("quality_gate", {}),
                    "dedup": edito.get("dedup", {}),
                    "critic": edito.get("critic", {}),
                    "batch_variety": edito.get("batch_variety", {}),
                    "generation_attempt": edito.get("generation_attempt", 1),
                })
                # Stocker l'embedding pour la déduplication future
                from post_memory import store_post_embedding
                store_post_embedding(db, post_text, linkedin_result.get("post_id", ""))
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
    edito = generate_weekly_edito(top_articles, trends, db=db)

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


@app.post("/api/linkedin/preview")
async def preview_linkedin_post():
    """Génère un post LinkedIn avec image SANS publier. Pour valider le style."""
    import base64
    raw_articles = await scrape_all_sources()
    top_articles = sorted(
        raw_articles,
        key=lambda x: (x.get("is_trending", False), x.get("source_weight", 1.0)),
        reverse=True
    )[:15]
    trending_keywords = set()
    for a in raw_articles:
        if a.get("is_trending"):
            trending_keywords.update(a.get("trending_keywords", []))
    edito = generate_weekly_edito(top_articles, list(trending_keywords)[:10])
    post_text = edito.get("post_text", "")
    post_type = edito.get("post_type", "signal_faible")
    image_bytes = generate_visual(post_text, post_type, db=db)
    return {
        "post_text": post_text,
        "post_type": post_type,
        "hashtags": edito.get("hashtags", []),
        "word_count": edito.get("word_count", 0),
        "image_b64": base64.b64encode(image_bytes).decode() if image_bytes else None,
    }


@app.get("/api/linkedin/check/{post_id:path}")
async def check_linkedin_post(post_id: str):
    """Vérifie le commentary réel d'un post LinkedIn via l'API (diagnostic troncature)."""
    import httpx
    from linkedin_publisher import LINKEDIN_ACCESS_TOKEN
    if not LINKEDIN_ACCESS_TOKEN:
        return {"error": "Token non configuré"}
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "LinkedIn-Version": "202607",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    encoded_id = __import__('urllib.parse', fromlist=['quote']).quote(post_id, safe='')
    r = httpx.get(f"https://api.linkedin.com/rest/posts/{encoded_id}", headers=headers, timeout=10)
    if r.status_code == 200:
        d = r.json()
        commentary = d.get("commentary", "")
        return {"post_id": post_id, "commentary_chars": len(commentary), "commentary_end": commentary[-100:], "full": commentary}
    return {"error": f"HTTP {r.status_code}", "body": r.text[:300]}


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
                "post_text": d.get("post_text", ""),
            })
        return {"posts": posts, "count": len(posts)}
    except Exception as e:
        return {"posts": [], "message": str(e)}


@app.get("/api/linkedin/posts/{post_id:path}")
async def get_linkedin_post_by_id(post_id: str):
    """Récupère un post LinkedIn par son post_id (depuis Firestore)."""
    if not db:
        return {"post_text": None, "message": "Firestore non disponible"}
    try:
        docs = (
            db.collection("linkedin_posts")
            .where("post_id", "==", post_id)
            .limit(1)
            .stream()
        )
        for doc in docs:
            return doc.to_dict()
        return {"post_text": None, "message": "Post non trouvé"}
    except Exception as e:
        return {"post_text": None, "message": str(e)}


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
        "LinkedIn-Version": "202607",
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


@app.post("/api/linkedin/update-engagement")
async def update_linkedin_engagement():
    """Met à jour les métriques d'engagement des derniers posts dans Firestore."""
    if not db:
        raise HTTPException(status_code=503, detail="Firestore non disponible")
    from post_memory import update_post_engagement, update_source_scores
    updated = update_post_engagement(db, max_posts=20)
    if updated:
        update_source_scores(db)
    return {"status": "ok", "updated": updated}


@app.get("/auth/linkedin/callback")
async def linkedin_oauth_callback(code: str = None, state: str = None, error: str = None):
    """Échange le code OAuth LinkedIn contre un access token et le stocke dans Secret Manager."""
    if error:
        raise HTTPException(status_code=400, detail=f"LinkedIn OAuth error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Paramètre 'code' manquant")

    import httpx
    from google.cloud import secretmanager

    client_id = "78050rhmzifhz2"
    sm = secretmanager.SecretManagerServiceClient()
    secret_name = f"projects/{GCP_PROJECT}/secrets/LINKEDIN_CLIENT_SECRET/versions/latest"
    client_secret = sm.access_secret_version(name=secret_name).payload.data.decode()

    redirect_uri = "https://renaudsecq59.github.io/mia-chatbot/callback.html"
    r = httpx.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"LinkedIn token exchange failed: {r.text[:200]}")

    token_data = r.json()
    access_token = token_data.get("access_token", "")
    expires_in = token_data.get("expires_in", 0)

    if not access_token:
        raise HTTPException(status_code=502, detail="Pas d'access_token dans la réponse LinkedIn")

    # Stocker dans Secret Manager
    sm_client = secretmanager.SecretManagerServiceClient()
    secret_path = f"projects/{GCP_PROJECT}/secrets/LINKEDIN_ACCESS_TOKEN"
    payload = access_token.encode("UTF-8")
    sm_client.add_secret_version(
        request={"parent": secret_path, "payload": {"data": payload}}
    )

    # Mettre à jour la variable d'env Cloud Run pour pointer sur latest
    expires_days = round(expires_in / 86400)
    logger.info(f"✅ Token LinkedIn renouvelé via OAuth — expire dans {expires_days} jours")

    return {
        "status": "ok",
        "message": f"Token LinkedIn stocké dans Secret Manager. Expire dans {expires_days} jours.",
        "expires_in_days": expires_days,
    }


@app.get("/auth/linkedin/authorize")
async def linkedin_authorize():
    """Retourne l'URL d'autorisation LinkedIn OAuth."""
    import urllib.parse
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": "78050rhmzifhz2",
        "redirect_uri": "https://renaudsecq59.github.io/mia-chatbot/callback.html",
        "state": "auto",
        "scope": "openid profile w_member_social",
    })
    url = f"https://www.linkedin.com/oauth/v2/authorization?{params}"
    return {"auth_url": url}


@app.get("/llms.txt")
async def llms_txt():
    """llms.txt — carte machine-readable du site pour les agents IA.

    Format proposé par Jeremy Howard (Answer.AI) pour rendre le site
    consommable par les LLMs et agents sans parser le HTML.
    """
    from fastapi.responses import PlainTextResponse
    content = """# MIA Veille — Data & AI Governance

> Veille automatisée sur l'AI Governance, la Data Governance et le Vibe Coding.
> Curatée par Renaud Secq, Consultant Freelance IA & Data.

## API Endpoints
- /api/articles: Liste des articles scorés par pertinence (JSON, paramètres: category, limit)
- /api/linkedin/posts: Historique des posts LinkedIn publiés (JSON)
- /api/linkedin/stats: Métriques d'engagement des posts (JSON)
- /api/linkedin/edito: Génération d'édito LinkedIn (POST, JSON)
- /api/linkedin/update-engagement: Mise à jour des métriques d'engagement (POST)
- /api/scrape: Déclenche le scraping complet + génération + publication (POST)

## JSON Feed
- /api/feed.json: Flux JSON des derniers articles au format JSON Feed 1.1

## Topics
- AI Governance: EU AI Act, model governance, AI safety, compliance, risk management
- Data Governance: data quality, catalog, lineage, Collibra, data mesh, data contracts
- Vibe Coding: cursor, claude code, copilot, windsurf, agent coding, dev assisté IA

## Sources
- 50+ feeds RSS (Medium, Substack, ArXiv, blogs d'experts, HN, Dev.to)
- Scoring automatique par pertinence thématique (0-10)
- Déduplication sémantique via embeddings Gemini

## Auteur
- Renaud Secq — Consultant Freelance IA & Data
- LinkedIn: https://www.linkedin.com/in/renaud-secq-5593832a/
- Site: https://renaudsecq59.github.io/mia-chatbot/veille.html
"""
    return PlainTextResponse(content=content, media_type="text/plain")


@app.get("/api/feed.json")
async def json_feed(limit: int = 20):
    """JSON Feed 1.1 — flux agent-readable des derniers articles.

    Format standardisé https://www.jsonfeed.org/version/1.1/
    Consommable par les agents IA, les lecteurs RSS modernes, et les pipelines RAG.
    """
    if not db:
        raise HTTPException(status_code=503, detail="Firestore non disponible")

    try:
        docs = (
            db.collection("articles")
            .order_by("score", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )

        items = []
        for doc in docs:
            d = doc.to_dict()
            items.append({
                "id": d.get("id", doc.id),
                "url": d.get("url", ""),
                "title": d.get("title", ""),
                "content_text": d.get("summary", "")[:500],
                "date_published": d.get("created_at", ""),
                "authors": [{"name": d.get("source_name", "Unknown")}],
                "tags": [d.get("category_label", ""), d.get("pillar", "")],
                "_meta": {
                    "score": d.get("score", 0),
                    "pillar": d.get("pillar", ""),
                    "pillar_score": d.get("pillar_score", 0),
                    "expert_opinion": d.get("expert_opinion", ""),
                },
            })

        return {
            "version": "https://www.jsonfeed.org/version/1.1",
            "title": "MIA Veille — Data & AI Governance",
            "description": "Veille automatisée sur l'AI Governance, Data Governance et Vibe Coding",
            "home_page_url": "https://renaudsecq59.github.io/mia-chatbot/veille.html",
            "feed_url": "https://veille-backend-791183172510.europe-west1.run.app/api/feed.json",
            "author": {
                "name": "Renaud Secq",
                "url": "https://www.linkedin.com/in/renaud-secq-5593832a/",
            },
            "items": items,
        }
    except Exception as e:
        return {"version": "https://www.jsonfeed.org/version/1.1", "items": [], "error": str(e)}


# ─── Newsletter ───────────────────────────────────────────────────────────────
from pydantic import BaseModel


class NewsletterSubscribe(BaseModel):
    email: str


@app.post("/api/newsletter/subscribe")
async def newsletter_subscribe(data: NewsletterSubscribe):
    """Inscription à la newsletter (stockage dans Firestore)."""
    import re
    email = data.email.strip().lower()
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return {"ok": False, "message": "Email invalide"}

    if not db:
        return {"ok": False, "message": "Service non disponible"}

    try:
        doc_id = hashlib.sha256(email.encode()).hexdigest()[:16]
        doc_ref = db.collection("newsletter_subscribers").document(doc_id)
        doc = doc_ref.get()

        if doc.exists:
            return {"ok": True, "message": "Vous êtes déjà inscrit !", "already_subscribed": True}

        doc_ref.set({
            "email": email,
            "subscribed_at": datetime.now(timezone.utc).isoformat(),
            "source": "website",
            "active": True,
        })
        logger.info(f"📧 Nouvel inscrit newsletter: {email}")
        return {"ok": True, "message": "Inscription confirmée ! Vous recevrez la veille IA & Data chaque semaine."}
    except Exception as e:
        logger.error(f"Erreur newsletter subscribe: {e}")
        return {"ok": False, "message": "Erreur lors de l'inscription"}


@app.delete("/api/newsletter/unsubscribe")
async def newsletter_unsubscribe(data: NewsletterSubscribe):
    """Désinscription de la newsletter."""
    email = data.email.strip().lower()
    if not db:
        return {"ok": False, "message": "Service non disponible"}

    try:
        doc_id = hashlib.sha256(email.encode()).hexdigest()[:16]
        doc_ref = db.collection("newsletter_subscribers").document(doc_id)
        doc_ref.set({"active": False}, merge=True)
        logger.info(f"📧 Désinscription newsletter: {email}")
        return {"ok": True, "message": "Vous avez été désinscrit avec succès."}
    except Exception as e:
        logger.error(f"Erreur newsletter unsubscribe: {e}")
        return {"ok": False, "message": "Erreur lors de la désinscription"}


@app.get("/api/newsletter/count")
async def newsletter_count():
    """Nombre d'inscrits actifs (publique)."""
    if not db:
        return {"count": 0}
    try:
        docs = db.collection("newsletter_subscribers").where("active", "==", True).stream()
        return {"count": sum(1 for _ in docs)}
    except Exception:
        return {"count": 0}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
