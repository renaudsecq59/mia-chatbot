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
            "hook": "On me demande souvent quel cloud choisir pour l'IA. La vraie réponse : ça n'a aucune importance.",
            "post_text": f"""On me demande souvent quel cloud choisir pour l'IA. La vraie réponse : ça n'a aucune importance.

Vertex AI, SageMaker, Databricks — j'ai déployé des modèles sur les trois. Le bottleneck n'est jamais la plateforme.

C'est toujours le même trio : données mal préparées, équipe pas staffée, et zéro mesure de ROI.

J'ai vu un projet passer de POC à production en 6 semaines. Le secret ? Pas le choix du cloud. Un sponsor business qui savait exactement quel problème résoudre.

J'en parle dans mes lectures de la semaine → {SITE_URL}

Vous, c'est quoi le vrai bottleneck de vos projets IA ?

#IAenEntreprise #VertexAI #Databricks""",
            "hashtags": ["#IAenEntreprise", "#VertexAI", "#Databricks"],
        },
        "vulgarisateur": {
            "hook": "Un agent IA, c'est un stagiaire très rapide avec une mémoire parfaite.",
            "post_text": f"""Un agent IA, c'est un stagiaire très rapide avec une mémoire parfaite.

Il exécute exactement ce que vous lui demandez. Ni plus, ni moins. Si le brief est flou, le résultat sera flou.

La différence avec un stagiaire humain : il ne vous dira jamais "j'ai pas compris". Il inventera une réponse.

C'est pour ça que le vrai travail d'un projet IA, c'est le cadrage. Pas le prompt engineering.

Les outils mûrissent vite — j'en parle ici → {SITE_URL}

#AgentsIA #IAenEntreprise #LLM""",
            "hashtags": ["#AgentsIA", "#IAenEntreprise", "#LLM"],
        },
        "questionneur": {
            "hook": "Faut-il un CTO pour piloter l'IA ou un CDO ?",
            "post_text": f"""Faut-il un CTO pour piloter l'IA ou un CDO ?

Je manage des équipes data et IA depuis 3 ans. Et la question revient à chaque mission.

Le CTO veut builder. Le CDO veut gouverner. Les deux ont raison. Les deux ont tort seuls.

Mon expérience : les projets IA qui marchent ont un binôme tech-data au sommet. Pas un chef unique.

Le vrai risque, c'est le silo entre ceux qui codent et ceux qui gèrent la donnée.

J'explore ce sujet dans mes lectures → {SITE_URL}

Et dans votre boîte, qui pilote l'IA ?

#ManagementIA #DataStrategy #Leadership""",
            "hashtags": ["#ManagementIA", "#DataStrategy", "#Leadership"],
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
