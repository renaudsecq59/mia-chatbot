"""Module IA pour scorer, résumer et générer du contenu à partir des articles."""
import json
import logging
from google import genai
from config import GCP_PROJECT, GCP_LOCATION, EXPERT_PROFILE, MIN_SCORE, MIN_SCORE_LINKEDIN

logger = logging.getLogger(__name__)

try:
    from config import GEMINI_API_KEY
    if GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
    else:
        client = genai.Client(
            vertexai=True,
            project=GCP_PROJECT,
            location=GCP_LOCATION,
        )
    MODEL_ID = "gemini-2.0-flash"
    logger.info("✅ Google GenAI initialisé")
except Exception as e:
    client = None
    MODEL_ID = None
    logger.warning(f"⚠️ GenAI non disponible: {e}")


SCORING_PROMPT = """Tu es un curateur de contenu expert pour {name}, {title}.

EXPERTISE DE RENAUD :
{expertise}

TON : {tone}

AUDIENCE CIBLE (décideurs tech/data en entreprise) :
- CDOs, VP Data, CTOs qui recrutent des freelances
- Product Managers IA qui cherchent des insights terrain
- Data Engineers/Scientists qui veulent monter en compétence
- Recruteurs tech qui sourcent des profils IA/Data

ARTICLE À ÉVALUER :
Titre : {title}
Source : {source}
Catégorie : {category}
Contenu : {summary}

CRITÈRES DE SCORING (0-10 chacun) :

1. PERTINENCE MÉTIER
   - 9-10 : Directement lié à build IA, gouvernance data, ou management tech
   - 5-8 : Lié à l'écosystème (cloud, outils, régulation)
   - 0-4 : Trop théorique, trop niche, ou hors sujet
   
2. QUALITÉ & CRÉDIBILITÉ
   - 9-10 : Source officielle (GCP, AWS, Databricks) ou média reconnu, contenu substantiel
   - 5-8 : Blog d'expert, retour d'expérience concret
   - 0-4 : Clickbait, contenu superficiel, source douteuse
   
3. NOUVEAUTÉ & TIMING
   - 9-10 : Annonce produit, nouvelle régulation, tendance émergente
   - 5-8 : Best practice récente, cas d'usage intéressant
   - 0-4 : Contenu recyclé, évident, ou dépassé
   
4. ACTIONNABLE BUSINESS
   - 9-10 : Insights qu'un décideur peut appliquer cette semaine (ex: nouvelle feature Vertex AI, checklist AI Act)
   - 5-8 : Utile pour la stratégie moyen terme
   - 0-4 : Trop théorique, pas d'application concrète
   
5. POTENTIEL LINKEDIN
   - 9-10 : Sujet qui génère du débat, chiffres marquants, opinion tranchée possible
   - 5-8 : Intéressant mais consensuel
   - 0-4 : Ennuyeux, trop technique, ou trop corporate

GÉNÈRE ENSUITE :

RÉSUMÉ (2-3 phrases max) :
- Accessible pour un non-tech
- Focus sur le "pourquoi c'est important" pas le "comment ça marche"
- Évite le jargon (ou explique-le)

AVIS EXPERT (1-2 phrases, ton Renaud) :
- Opinion tranchée, pas neutre
- Basé sur l'expérience terrain ("J'ai vu...", "En pratique...")
- Peut être critique si pertinent
- Exemples de bon ton :
  ✅ "En pratique, 80% des projets IA échouent sur la qualité des données, pas sur le choix du modèle."
  ✅ "Cette feature va sauver 2 semaines de dev par projet. Game changer."
  ❌ "C'est une évolution intéressante dans le domaine." (trop mou)

TAGS (3-4 max) :
- Business-friendly (pas de jargon tech)
- Exemples : "Agents IA", "Gouvernance", "Cloud", "Conformité", "ROI IA"

RÉPONDS EN JSON STRICT :
{{
  "scores": {{
    "pertinence": X,
    "qualite": X,
    "nouveaute": X,
    "impact_business": X,
    "partageabilite": X
  }},
  "score_final": X.X,
  "summary": "Résumé accessible en 2-3 phrases...",
  "expert_opinion": "Avis tranché de Renaud en 1-2 phrases...",
  "tags": ["tag1", "tag2", "tag3"],
  "reject_reason": null
}}

Si score_final < 5, mets une reject_reason courte (ex: "Trop théorique", "Hors expertise", "Contenu superficiel")."""


LINKEDIN_PROMPT = """Tu es le ghostwriter LinkedIn de {name}, {title}.

Son style LinkedIn :
- Hook percutant en 1ère ligne (visible avant "voir plus")
- Paragraphes courts (2-3 lignes max)
- Chiffres et faits concrets
- Avis personnel tranché
- Question d'engagement à la fin
- 3-5 hashtags pertinents
- Pas de emojis excessifs (max 3-4)
- Ton : expert pragmatique, pas corporate

ARTICLE :
- Titre : {title}
- Source : {source}
- Résumé : {summary}
- Avis expert : {expert_opinion}
- Tags : {tags}

GÉNÈRE un post LinkedIn prêt à publier (max 1300 caractères).
Le post doit positionner Renaud comme expert, pas juste relayer l'info.

RÉPONDS EN JSON STRICT :
{{
  "hook": "La première ligne percutante",
  "full_post": "Le post complet prêt à copier-coller",
  "suggested_day": "lundi|mercredi|vendredi",
  "visual_type": "stat_choc|citation_expert|article_resume",
  "visual_data": {{
    "main_text": "Le texte principal du visuel",
    "subtitle": "Le sous-titre",
    "stat": "Le chiffre clé (si stat_choc)"
  }}
}}"""


async def score_article(article: dict) -> dict:
    """Score et enrichit un article avec Gemini."""
    if not client:
        article.update(_mock_score(article))
        return article
    
    try:
        prompt = SCORING_PROMPT.format(
            name=EXPERT_PROFILE["name"],
            title=EXPERT_PROFILE["title"],
            expertise="\n".join(f"- {e}" for e in EXPERT_PROFILE["expertise"]),
            tone=EXPERT_PROFILE["tone"],
            title_article=article["title"],
            source=article["source_name"],
            category=article["category_label"],
            summary=article["summary_raw"],
        ).replace("{title}", article["title"]).replace("{source}", article["source_name"]).replace("{category}", article["category_label"]).replace("{summary}", article["summary_raw"])
        
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
        )
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        
        result = json.loads(raw_text)
        
        # Appliquer le poids de la source
        result["score_final"] = round(
            result["score_final"] * article.get("source_weight", 1.0), 1
        )
        
        article.update({
            "scores": result["scores"],
            "score": result["score_final"],
            "summary": result["summary"],
            "expert_opinion": result["expert_opinion"],
            "tags": result["tags"],
            "reject_reason": result.get("reject_reason"),
        })
        
        logger.info(f"  📝 Score {result['score_final']}/10 - {article['title'][:60]}")
        
    except Exception as e:
        logger.error(f"  ❌ Erreur scoring: {e}")
        article.update(_mock_score(article))
    
    return article


async def generate_linkedin_post(article: dict) -> dict:
    """Génère un post LinkedIn pour un article bien scoré."""
    if not client:
        logger.warning("⚠️ GenAI non disponible, post LinkedIn simulé")
        return _mock_linkedin(article)
    
    try:
        prompt = LINKEDIN_PROMPT.format(
            name=EXPERT_PROFILE["name"],
            title=EXPERT_PROFILE["title"],
            title_article=article["title"],
            source=article["source_name"],
            summary=article.get("summary", article["summary_raw"]),
            expert_opinion=article.get("expert_opinion", ""),
            tags=", ".join(article.get("tags", [])),
        ).replace("{title}", article["title"]).replace("{source}", article["source_name"]).replace("{summary}", article.get("summary", "")).replace("{expert_opinion}", article.get("expert_opinion", "")).replace("{tags}", ", ".join(article.get("tags", [])))
        
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
        )
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        
        result = json.loads(raw_text)
        
        article.update({
            "linkedin_post": result["full_post"],
            "linkedin_hook": result["hook"],
            "linkedin_suggested_day": result["suggested_day"],
            "visual_type": result["visual_type"],
            "visual_data": result["visual_data"],
        })
        
        logger.info(f"  📣 Post LinkedIn généré ({len(result['full_post'])} chars)")
        
    except Exception as e:
        logger.error(f"  ❌ Erreur LinkedIn: {e}")
        article.update(_mock_linkedin(article))
    
    return article


async def process_articles(articles: list[dict]) -> list[dict]:
    """Pipeline complet : scoring → filtrage → génération LinkedIn."""
    logger.info(f"\n🧠 Scoring de {len(articles)} articles avec Claude...")
    
    scored = []
    for article in articles:
        scored_article = await score_article(article)
        scored.append(scored_article)
    
    # Filtrer par score minimum
    good_articles = [a for a in scored if a.get("score", 0) >= MIN_SCORE]
    good_articles.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    logger.info(f"✅ {len(good_articles)} articles retenus (score >= {MIN_SCORE})")
    
    # Générer posts LinkedIn pour les meilleurs
    linkedin_count = 0
    for article in good_articles:
        if article.get("score", 0) >= MIN_SCORE_LINKEDIN:
            await generate_linkedin_post(article)
            linkedin_count += 1
    
    logger.info(f"📣 {linkedin_count} posts LinkedIn générés (score >= {MIN_SCORE_LINKEDIN})")
    
    return good_articles


def _mock_score(article: dict) -> dict:
    """Score intelligent basé sur des mots-clés (fallback sans API key)."""
    title = (article.get("title", "") + " " + article.get("summary_raw", "")).lower()
    source = article.get("source_name", "").lower()

    # Mots-clés haute valeur (directement lié à l'expertise Renaud)
    high_kw = ["agent", "governance", "govern", "vertex", "bigquery", "databricks",
               "snowflake", "cloud run", "mlops", "deploy", "production", "enterprise",
               "compliance", "ai act", "regulation", "catalog", "quality", "pipeline",
               "rag", "llm", "genai", "generative", "platform", "multi-agent",
               "orchestrat", "framework", "bedrock", "sagemaker", "cortex"]
    # Mots-clés moyens (écosystème)
    mid_kw = ["openai", "anthropic", "google", "aws", "azure", "startup", "strategy",
              "cto", "cdo", "leadership", "team", "roi", "adoption", "scale",
              "fine-tun", "embedding", "vector", "retrieval", "benchmark"]
    # Mots-clés négatifs (bruit)
    neg_kw = ["tutorial", "beginner", "introduction to", "getting started",
              "earth observation", "climate", "biology", "medical imaging",
              "game", "music", "art generation", "musk vs", "drama", "lawsuit"]

    high_hits = sum(1 for kw in high_kw if kw in title)
    mid_hits = sum(1 for kw in mid_kw if kw in title)
    neg_hits = sum(1 for kw in neg_kw if kw in title)

    # Score de base selon source
    source_bonus = 0
    if any(s in source for s in ["databricks", "snowflake", "aws", "google cloud", "gcp"]):
        source_bonus = 1.5
    elif any(s in source for s in ["infoq", "venturebeat", "mit tech"]):
        source_bonus = 1.0
    elif any(s in source for s in ["hugging face", "towards data"]):
        source_bonus = 0.3  # Souvent trop académique

    base_score = 4.5 + (high_hits * 0.9) + (mid_hits * 0.5) + source_bonus - (neg_hits * 2.5)
    score = round(min(max(base_score, 2.0), 9.5), 1)

    # Avis expert contextualisé
    if high_hits >= 2:
        opinion = f"Directement applicable en mission. À surveiller pour les équipes qui déploient de l'IA en prod."
    elif "agent" in title:
        opinion = "Les agents IA sont le sujet chaud de 2026. Ce type d'article aide à cadrer les projets clients."
    elif any(kw in title for kw in ["governance", "govern", "catalog", "quality"]):
        opinion = "Gouvernance et qualité des données : le socle indispensable avant tout projet IA sérieux."
    elif any(kw in title for kw in ["cloud", "vertex", "bedrock", "sagemaker", "databricks", "snowflake"]):
        opinion = "Les plateformes cloud se différencient sur l'IA. Important de suivre pour le conseil client."
    elif neg_hits > 0:
        opinion = "Hors périmètre de mon expertise. Pas prioritaire pour l'audience cible."
    else:
        opinion = "Article intéressant pour la culture tech générale, mais pas directement actionnable."

    # Tags contextualisés
    tags = []
    if any(kw in title for kw in ["agent", "multi-agent", "orchestrat"]):
        tags.append("Agents IA")
    if any(kw in title for kw in ["governance", "govern", "catalog", "quality"]):
        tags.append("Gouvernance")
    if any(kw in title for kw in ["cloud", "vertex", "bedrock", "aws", "gcp", "azure"]):
        tags.append("Cloud")
    if any(kw in title for kw in ["deploy", "production", "mlops", "pipeline"]):
        tags.append("MLOps")
    if any(kw in title for kw in ["regulation", "ai act", "compliance"]):
        tags.append("Conformité")
    if not tags:
        tags = ["IA", "Tendances"]

    return {
        "scores": {
            "pertinence": min(10, 5 + high_hits * 2),
            "qualite": min(10, 6 + int(source_bonus)),
            "nouveaute": 7 if article.get("is_trending") else 5,
            "impact_business": min(10, 5 + high_hits + mid_hits),
            "partageabilite": min(10, 5 + high_hits),
        },
        "score": score,
        "summary": f"{article.get('title', 'Article')}: contenu pertinent pour les professionnels data et IA en entreprise.",
        "expert_opinion": opinion,
        "tags": tags,
        "reject_reason": "Hors expertise" if score < 5.0 else None,
    }


def _mock_linkedin(article: dict) -> dict:
    """Post LinkedIn simulé pour les tests."""
    return {
        "linkedin_post": f"""🔥 {article.get('title', 'Article IA & Data')}

{article.get('summary', 'Un article qui mérite votre attention.')}

{article.get('expert_opinion', 'Mon avis : à lire absolument.')}

Et vous, qu'en pensez-vous ?

#DataGovernance #IA #Freelance""",
        "linkedin_hook": article.get("title", "Article IA & Data"),
        "linkedin_suggested_day": "mercredi",
        "visual_type": "article_resume",
        "visual_data": {
            "main_text": article.get("title", "Article IA & Data"),
            "subtitle": article.get("source_name", ""),
            "stat": ""
        },
    }
