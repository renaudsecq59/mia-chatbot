"""Module IA pour scorer, résumer et générer du contenu à partir des articles."""
import json
import logging
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, EXPERT_PROFILE, MIN_SCORE, MIN_SCORE_LINKEDIN

logger = logging.getLogger(__name__)

client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


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
    """Score et enrichit un article avec Claude."""
    if not client:
        logger.warning("⚠️ ANTHROPIC_API_KEY non configurée, scoring simulé")
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
            # Fix template vars
        ).replace("{title}", article["title"]).replace("{source}", article["source_name"]).replace("{category}", article["category_label"]).replace("{summary}", article["summary_raw"])
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = json.loads(response.content[0].text)
        
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
        logger.warning("⚠️ ANTHROPIC_API_KEY non configurée, post LinkedIn simulé")
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
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = json.loads(response.content[0].text)
        
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
    """Score simulé pour les tests sans API key."""
    import random
    score = round(random.uniform(5.0, 9.5), 1)
    return {
        "scores": {
            "pertinence": random.randint(5, 10),
            "qualite": random.randint(5, 10),
            "nouveaute": random.randint(5, 10),
            "impact_business": random.randint(5, 10),
            "partageabilite": random.randint(5, 10),
        },
        "score": score,
        "summary": f"Résumé de l'article '{article.get('title', 'IA & Data')[:50]}...' — contenu pertinent pour les professionnels data et IA.",
        "expert_opinion": "Un article à garder sous le coude pour les équipes qui structurent leur gouvernance IA.",
        "tags": ["IA", "Data Governance", "Tendances"],
        "reject_reason": None,
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
