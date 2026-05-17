"""Module IA pour scorer, résumer et générer du contenu à partir des articles."""
import json
import logging
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, EXPERT_PROFILE, MIN_SCORE, MIN_SCORE_LINKEDIN

logger = logging.getLogger(__name__)

client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


SCORING_PROMPT = """Tu es un curateur de contenu expert pour {name}, {title}.

Ses domaines d'expertise :
{expertise}

Son ton : {tone}

OBJECTIF : Évaluer cet article pour sa page de veille publique. Son audience cible :
- CDOs, VP Data, CTOs (prospects potentiels)
- Recruteurs freelance tech/data
- Product Managers IA
- Data Engineers & Scientists

ARTICLE À ÉVALUER :
- Titre : {title}
- Source : {source}
- Catégorie : {category}
- Résumé brut : {summary}

ÉVALUE sur ces critères (0-10 chacun) :
1. PERTINENCE : Est-ce lié aux domaines d'expertise de Renaud ? Utile pour son audience ?
2. QUALITÉ : Contenu substantiel vs clickbait ? Source fiable ?
3. NOUVEAUTÉ : Info récente, pas du réchauffé ?
4. IMPACT BUSINESS : Insights actionnables pour des décideurs ?
5. PARTAGEABILITÉ : Est-ce que ça mérite un partage LinkedIn ?

Puis génère :
- Un résumé de 2-3 phrases accessibles (pas jargon technique)
- L'avis d'expert de Renaud (1-2 phrases, ton direct et pragmatique)
- 3-4 tags business-friendly

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
  "summary": "Résumé accessible...",
  "expert_opinion": "L'avis de Renaud...",
  "tags": ["tag1", "tag2", "tag3"],
  "reject_reason": null
}}

Si l'article n'est PAS pertinent (score < 5), mets une reject_reason explicative."""


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
        return _mock_score(article)
    
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
        "summary": f"Résumé de l'article '{article['title'][:50]}...' — contenu pertinent pour les professionnels data et IA.",
        "expert_opinion": "Un article à garder sous le coude pour les équipes qui structurent leur gouvernance IA.",
        "tags": ["IA", "Data Governance", "Tendances"],
        "reject_reason": None,
    }


def _mock_linkedin(article: dict) -> dict:
    """Post LinkedIn simulé pour les tests."""
    return {
        "linkedin_post": f"""🔥 {article['title']}

{article.get('summary', 'Un article qui mérite votre attention.')}

{article.get('expert_opinion', 'Mon avis : à lire absolument.')}

Et vous, qu'en pensez-vous ?

#DataGovernance #IA #Freelance""",
        "linkedin_hook": article["title"],
        "linkedin_suggested_day": "mercredi",
        "visual_type": "article_resume",
        "visual_data": {
            "main_text": article["title"],
            "subtitle": article.get("source_name", ""),
            "stat": ""
        },
    }
