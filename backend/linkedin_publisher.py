"""Module de publication LinkedIn automatique.

Génère un édito hebdomadaire à partir des meilleurs articles de la veille,
puis le publie sur LinkedIn via l'API REST v2.

Setup requis :
1. Créer une app sur https://www.linkedin.com/developers/
2. Activer le product "Share on LinkedIn" (scope w_member_social)
3. Obtenir un access token via OAuth2
4. Stocker le token dans LINKEDIN_ACCESS_TOKEN (env var)
"""
import json
import logging
import os
import httpx
from datetime import datetime, timezone
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, EXPERT_PROFILE

logger = logging.getLogger(__name__)

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN", "")  # Format: urn:li:person:XXXXXX

SITE_URL = "https://renaudsecq59.github.io/mia-chatbot/veille.html"

claude = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


EDITO_PROMPT = """Tu es le ghostwriter LinkedIn de {name}, {title}.

CONTEXTE : C'est l'édito hebdomadaire de sa veille IA & Data. Tu dois rédiger UN SEUL post LinkedIn 
qui synthétise les tendances de la semaine et donne envie de lire la veille complète.

ARTICLES DE LA SEMAINE (top {count}) :
{articles_summary}

TENDANCES DÉTECTÉES : {trends}

RÈGLES DU POST :
- Hook percutant en 1ère ligne (visible avant "voir plus") — pose une question ou une affirmation forte
- 3-4 paragraphes courts : tendances clés, ce que ça change, son avis d'expert
- Terminer par un CTA vers le site de veille : {site_url}
- 4-6 hashtags pertinents en fin de post
- Max 2-3 emojis, pas plus
- Ton : expert terrain qui partage ses découvertes, pas corporate
- Max 1500 caractères
- NE PAS lister les articles un par un, faire une SYNTHÈSE éditoriale

RÉPONDS EN JSON STRICT :
{{
  "post_text": "Le post LinkedIn complet prêt à publier",
  "hook": "La première ligne seule",
  "hashtags": ["#tag1", "#tag2"]
}}"""


def generate_weekly_edito(articles: list[dict], trends: list[str] = None) -> dict:
    """Génère l'édito LinkedIn hebdomadaire à partir des meilleurs articles."""
    if not articles:
        return {"error": "Aucun article pour générer l'édito"}

    # Préparer le résumé des articles pour Claude
    articles_summary = ""
    for i, a in enumerate(articles[:10], 1):
        articles_summary += f"{i}. [{a.get('category_label', 'IA')}] {a['title']} ({a.get('source_name', 'Source')})\n"
        if a.get('summary'):
            articles_summary += f"   → {a['summary'][:150]}\n"
        if a.get('expert_opinion'):
            articles_summary += f"   💬 {a['expert_opinion'][:120]}\n"

    trends_str = ", ".join(trends[:8]) if trends else "IA agentique, data governance, LLM en production"

    if not claude:
        logger.warning("⚠️ ANTHROPIC_API_KEY non configurée, édito simulé")
        return _mock_edito(articles, trends_str)

    try:
        prompt = EDITO_PROMPT.format(
            name=EXPERT_PROFILE["name"],
            title=EXPERT_PROFILE["title"],
            count=len(articles[:10]),
            articles_summary=articles_summary,
            trends=trends_str,
            site_url=SITE_URL,
        )

        response = claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        result = json.loads(response.content[0].text)
        result["generated_at"] = datetime.now(timezone.utc).isoformat()
        result["article_count"] = len(articles)
        result["status"] = "generated"

        logger.info(f"📝 Édito LinkedIn généré ({len(result['post_text'])} chars)")
        return result

    except Exception as e:
        logger.error(f"❌ Erreur génération édito: {e}")
        return _mock_edito(articles, trends_str)


def publish_to_linkedin(post_text: str) -> dict:
    """Publie un post sur LinkedIn via l'API REST v2."""
    if not LINKEDIN_ACCESS_TOKEN:
        logger.warning("⚠️ LINKEDIN_ACCESS_TOKEN non configuré")
        return {
            "status": "draft",
            "message": "Token LinkedIn non configuré — post prêt à copier-coller",
            "post_text": post_text,
        }

    if not LINKEDIN_PERSON_URN:
        logger.warning("⚠️ LINKEDIN_PERSON_URN non configuré")
        return {
            "status": "draft",
            "message": "Person URN non configuré — post prêt à copier-coller",
            "post_text": post_text,
        }

    try:
        headers = {
            "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202405",
        }

        # API LinkedIn Posts (v2)
        payload = {
            "author": LINKEDIN_PERSON_URN,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post_text
                    },
                    "shareMediaCategory": "ARTICLE",
                    "media": [
                        {
                            "status": "READY",
                            "originalUrl": SITE_URL,
                            "title": {
                                "text": "Veille IA & Data — Renaud Secq"
                            },
                            "description": {
                                "text": "Ma sélection hebdomadaire sur l'IA en entreprise et la data governance"
                            }
                        }
                    ]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        response = httpx.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.status_code == 201:
            post_id = response.headers.get("X-RestLi-Id", "unknown")
            logger.info(f"✅ Post LinkedIn publié ! ID: {post_id}")
            return {
                "status": "published",
                "post_id": post_id,
                "post_text": post_text,
                "published_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            logger.error(f"❌ LinkedIn API error {response.status_code}: {response.text}")
            return {
                "status": "error",
                "error": f"HTTP {response.status_code}: {response.text[:300]}",
                "post_text": post_text,
            }

    except Exception as e:
        logger.error(f"❌ Erreur publication LinkedIn: {e}")
        return {
            "status": "error",
            "error": str(e),
            "post_text": post_text,
        }


def _mock_edito(articles: list[dict], trends: str) -> dict:
    """Édito simulé pour tests sans API key."""
    top_titles = [a["title"][:60] for a in articles[:5]]
    sources = list(set(a.get("source_name", "") for a in articles[:10]))

    post_text = f"""Cette semaine dans ma veille IA & Data, 3 signaux forts à retenir.

Les plateformes cloud accélèrent sur l'IA agentique. Google Cloud, AWS et Databricks ont tous annoncé des avancées majeures sur leurs outils d'IA en entreprise.

Côté gouvernance, la question de la souveraineté des données revient en force — et ce n'est pas qu'un sujet réglementaire, c'est un enjeu business concret.

Mon take : les entreprises qui ne structurent pas leur data governance AVANT de déployer leurs agents IA vont perdre 6 à 12 mois.

Ma sélection complète ({len(articles)} articles, {len(sources)} sources) 👇
{SITE_URL}

#IA #DataGovernance #AIAgents #EntrepriseIA #VeilleIA"""

    return {
        "post_text": post_text,
        "hook": "Cette semaine dans ma veille IA & Data, 3 signaux forts à retenir.",
        "hashtags": ["#IA", "#DataGovernance", "#AIAgents", "#EntrepriseIA", "#VeilleIA"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(articles),
        "status": "mock",
    }
