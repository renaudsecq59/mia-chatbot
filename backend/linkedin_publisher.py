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

CONTEXTE : Chaque semaine, Renaud publie un post LinkedIn basé sur sa veille IA & Data.
L'objectif : le positionner comme EXPERT reconnu, PAS comme curateur de contenu.

ARTICLES LUS CETTE SEMAINE (contexte, ne pas citer directement) :
{articles_summary}

TENDANCES DÉTECTÉES : {trends}

TYPE DE POST CETTE SEMAINE : {post_type}

=== SI TYPE = OBSERVATEUR (génère des partages) ===
Structure :
- Hook = observation terrain contre-intuitive que personne n'ose dire
- 2-3 paragraphes : développement avec exemples concrets
- Question ouverte finale pour créer le débat

=== SI TYPE = VULGARISATEUR (génère des saves) ===
Structure :
- Hook = concept complexe promis en version simple
- Analogie du quotidien
- Application concrète
- Une phrase à retenir

=== SI TYPE = QUESTIONNEUR (génère des commentaires) ===
Structure :
- Hook = question polarisante qui divise
- Point de vue nuancé de Renaud
- Invitation explicite à donner son avis

RÈGLES ABSOLUES :
- Max 150 mots. Phrases de max 15 mots.
- Un paragraphe = une idée. Sauts de ligne entre chaque.
- Opinion TRANCHÉE. Quelqu'un doit pouvoir être en désaccord.
- Ton direct : "Je pense", "J'ai vu", "Mon expérience". Pas de conditionnel.
- ZÉRO auto-promo. NE PAS dire "ma veille", "ma sélection", "mon site".
- 0 à 2 emojis max. JAMAIS en début de ligne.
- Pas de "game-changer", "révolutionnaire", "incroyable". Préfère "utile", "concret", "j'ai testé".
- Le lien {site_url} doit apparaître UNE SEULE fois, intégré naturellement (pas en CTA).
- 3-4 hashtags max, spécifiques (pas #IA tout seul).
- NE PAS lister les articles. Le post s'inspire de la veille sans la résumer.

CHECKLIST AVANT DE RÉPONDRE :
- [ ] Le hook arrêterait MON scroll si c'était quelqu'un d'autre ?
- [ ] Pas de mention de produit/outil que Renaud vend ?
- [ ] Opinion claire et assumée ?
- [ ] Quelqu'un pourrait être en désaccord ?
- [ ] Moins de 150 mots ?
- [ ] Question finale qui invite au commentaire ?

RÉPONDS EN JSON STRICT :
{{
  "post_text": "Le post complet prêt à publier",
  "hook": "La première ligne seule (sans emoji)",
  "post_type": "{post_type}",
  "hashtags": ["#tag1", "#tag2", "#tag3"],
  "word_count": 0
}}"""

POST_TYPES = ["observateur", "vulgarisateur", "questionneur"]


def _pick_post_type() -> str:
    """Alterne le type de post chaque semaine (observateur → vulgarisateur → questionneur)."""
    week_number = datetime.now(timezone.utc).isocalendar()[1]
    return POST_TYPES[week_number % len(POST_TYPES)]


def generate_weekly_edito(articles: list[dict], trends: list[str] = None, post_type: str = None) -> dict:
    """Génère l'édito LinkedIn hebdomadaire à partir des meilleurs articles."""
    if not articles:
        return {"error": "Aucun article pour générer l'édito"}

    post_type = post_type or _pick_post_type()

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
        return _mock_edito(articles, trends_str, post_type)

    try:
        prompt = EDITO_PROMPT.format(
            name=EXPERT_PROFILE["name"],
            title=EXPERT_PROFILE["title"],
            articles_summary=articles_summary,
            trends=trends_str,
            post_type=post_type,
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
        result["post_type"] = post_type
        result["status"] = "generated"

        logger.info(f"📝 Édito LinkedIn [{post_type}] généré ({len(result['post_text'])} chars, {result.get('word_count', '?')} mots)")
        return result

    except Exception as e:
        logger.error(f"❌ Erreur génération édito: {e}")
        return _mock_edito(articles, trends_str, post_type)


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


def _mock_edito(articles: list[dict], trends: str, post_type: str = "observateur") -> dict:
    """Édito simulé pour tests sans API key. 3 templates selon le type."""
    mock_posts = {
        "observateur": {
            "hook": "J'ai vu 30 entreprises déployer des agents IA cette année. La moitié n'a pas de data governance.",
            "post_text": f"""J'ai vu 30 entreprises déployer des agents IA cette année. La moitié n'a pas de data governance.

Le résultat : des hallucinations en production, des données sensibles qui fuient, et 6 mois perdus à corriger.

Le problème n'est pas la techno. AWS, Databricks, Vertex AI — les outils sont matures. Le problème, c'est qu'on donne accès à des données qu'on ne maîtrise pas.

Mon observation terrain : les boîtes qui réussissent ont structuré leur gouvernance AVANT de brancher l'IA. Pas après.

Plus de détails dans les sources que je compile chaque semaine → {SITE_URL}

Et vous, vous déployez vos agents sur des données gouvernées ?

#DataGovernance #AIAgents #IAenEntreprise""",
            "hashtags": ["#DataGovernance", "#AIAgents", "#IAenEntreprise"],
        },
        "vulgarisateur": {
            "hook": "L'AI Act expliqué comme un permis de conduire.",
            "post_text": f"""L'AI Act expliqué comme un permis de conduire.

Votre voiture (= votre IA) peut rouler. Mais il faut un permis (= conformité), une assurance (= gestion des risques), et un contrôle technique (= audit régulier).

Un système IA "haut risque", c'est comme conduire un bus scolaire. Plus de responsabilité, plus de contrôles.

La phrase à retenir : l'AI Act ne vous interdit pas d'innover. Il vous demande de savoir ce que vous faites.

J'en parle plus en détail ici → {SITE_URL}

#AIAct #RéglementationIA #Conformité""",
            "hashtags": ["#AIAct", "#RéglementationIA", "#Conformité"],
        },
        "questionneur": {
            "hook": "Un Data Catalog sans adoption, ça sert à quoi ?",
            "post_text": f"""Un Data Catalog sans adoption, ça sert à quoi ?

J'ai vu des équipes passer 18 mois à documenter 100% de leurs assets. Résultat : personne ne l'utilise.

Je pense qu'on se trompe de combat. Mieux vaut 20% des données bien documentées et utilisées que 100% dans un outil que personne n'ouvre.

Le vrai KPI d'un catalogue, c'est le nombre de recherches par semaine. Pas le taux de couverture.

J'explore ce sujet dans mes lectures de la semaine → {SITE_URL}

Vous mesurez quoi, vous, pour évaluer l'adoption ?

#DataCatalog #DataGovernance #DataManagement""",
            "hashtags": ["#DataCatalog", "#DataGovernance", "#DataManagement"],
        },
    }

    post = mock_posts.get(post_type, mock_posts["observateur"])
    return {
        "post_text": post["post_text"],
        "hook": post["hook"],
        "post_type": post_type,
        "hashtags": post["hashtags"],
        "word_count": len(post["post_text"].split()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(articles),
        "status": "mock",
    }
