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
from google import genai
from config import GCP_PROJECT, GCP_LOCATION, GEMINI_API_KEY, EXPERT_PROFILE

logger = logging.getLogger(__name__)

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN", "")  # Format: urn:li:person:XXXXXX

SITE_URL = "https://renaudsecq59.github.io/mia-chatbot/veille.html"

try:
    if GEMINI_API_KEY:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    else:
        gemini_client = genai.Client(
            vertexai=True,
            project=GCP_PROJECT,
            location=GCP_LOCATION,
        )
    GEMINI_MODEL = "gemini-2.5-flash"
except Exception:
    gemini_client = None
    GEMINI_MODEL = None


EDITO_PROMPT = """Tu es le ghostwriter LinkedIn de {name}, {title}.

CONTEXTE : Chaque semaine, Renaud publie un post LinkedIn basé sur sa veille IA & Data.
L'objectif : le positionner comme EXPERT reconnu, PAS comme curateur de contenu.

ARTICLES LUS CETTE SEMAINE (contexte, ne pas citer directement) :
{articles_summary}

TENDANCES DÉTECTÉES : {trends}

TYPE DE POST CETTE SEMAINE : {post_type}

=== SI TYPE = REVUE_PRESSE (lundi - donne de la valeur) ===
Structure :
- Hook = "Cette semaine dans l'IA & Data : [tendance principale]"
- 5-7 articles clés avec pour chacun : titre court + ton avis en 1 ligne (max 15 mots)
- Format liste numérotée, très scannable
- Conclusion : 1 phrase sur ce que ça change
- Lien vers la veille complète
- Max 150 mots TOTAL

=== SI TYPE = OBSERVATEUR (génère des partages) ===
Structure :
- Hook = observation terrain contre-intuitive inspirée d'un article de la semaine
- 2-3 paragraphes : développement avec exemples concrets
- Question ouverte finale pour créer le débat

=== SI TYPE = VULGARISATEUR (génère des saves) ===
Structure :
- Hook = concept complexe (vu dans les articles) promis en version simple
- Analogie du quotidien
- Application concrète
- Une phrase à retenir

=== SI TYPE = QUESTIONNEUR (génère des commentaires) ===
Structure :
- Hook = question polarisante inspirée d'un sujet d'actualité de la semaine
- Point de vue nuancé de Renaud
- Invitation explicite à donner son avis

=== SI TYPE = VERTEX_AI (bonnes pratiques, actus Google Cloud AI) ===
Structure :
- Hook = annonce ou retour terrain sur Vertex AI / Google Cloud AI
- 2-3 paragraphes : ce que ça change concrètement en prod, avec son expérience
- Partage un tip/best practice que Renaud utilise en mission
- Ton : praticien qui build, pas évangéliste Google
- Hashtags : #VertexAI #GoogleCloud #MLOps

=== SI TYPE = VIBE_CODING (dernières techniques de dev assisté par IA) ===
Structure :
- Hook = observation ou découverte récente sur le vibe coding / dév assisté par IA
- 2-3 paragraphes : workflow concret, outils testés (Cursor, Windsurf, Claude Code, etc.)
- Ce qui marche vraiment vs le hype, avec exemples personnels
- Ton : développeur pragmatique qui teste tout
- Hashtags : #VibeCoding #AIAssisted #DeveloperExperience

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

POST_TYPES = ["revue_presse", "vertex_ai", "observateur", "vibe_coding", "vulgarisateur", "questionneur"]


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

    if not gemini_client:
        logger.warning("⚠️ GenAI non disponible, édito simulé")
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

        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(raw_text)
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
    """Édito simulé pour tests sans API key. 4 templates selon le type."""
    mock_posts = {
        "revue_presse": {
            "hook": "Cette semaine dans l'IA & Data : l'IA agentique accélère, la gouvernance suit (enfin).",
            "post_text": f"""Cette semaine dans l'IA & Data : l'IA agentique accélère, la gouvernance suit (enfin).

1. Google Cloud lance Gemini Live Agents → Les agents vocaux temps réel arrivent en prod.
2. AWS Nova 2 Sonic pour les agents → Amazon rattrape son retard sur l'IA conversationnelle.
3. Databricks Unity Catalog Open APIs → Enfin de l'interop entre catalogues. Game changer.
4. Snowflake Cortex Code pour FP&A → L'IA générative s'attaque à la finance. Cas d'usage concret.
5. OpenAI x Databricks : GPT-5.5 en entreprise → Les LLMs deviennent des briques d'infra.

Ce qui change : l'IA passe de POC à plateforme. Les boîtes qui n'ont pas leur gouvernance vont souffrir.

Détails et sources → {SITE_URL}

#VeilleIA #AIAgents #DataGovernance""",
            "hashtags": ["#VeilleIA", "#AIAgents", "#DataGovernance"],
        },
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
        "vertex_ai": {
            "hook": "Agent Executor de Google Cloud : le runtime distribué pour agents IA en prod.",
            "post_text": f"""Agent Executor de Google Cloud : le runtime distribué pour agents IA en prod.

J'ai testé la semaine dernière. Le concept : découpler l'orchestration de l'exécution. Chaque tool call est un job isolé.

Pourquoi c'est important : les agents qui tournent 10+ minutes crashent. Avec Agent Executor, chaque étape est retry-able indépendamment.

Mon tip : combinez avec Vertex AI Pipelines pour le monitoring. Un agent sans observabilité, c'est une boîte noire en prod.

Détails dans ma veille → {SITE_URL}

#VertexAI #GoogleCloud #MLOps #AgentsIA""",
            "hashtags": ["#VertexAI", "#GoogleCloud", "#MLOps", "#AgentsIA"],
        },
        "vibe_coding": {
            "hook": "J'ai codé un backend complet en 2h sans écrire une ligne moi-même. Voici ce que j'en retiens.",
            "post_text": f"""J'ai codé un backend complet en 2h sans écrire une ligne moi-même. Voici ce que j'en retiens.

Workflow : Cursor + Claude en mode agent. Je décris l'archi, l'agent code, je review.

Ce qui marche : CRUD, intégrations API, tests unitaires. L'IA est un junior ultra-rapide.

Ce qui ne marche pas encore : logique métier complexe, sécurité, optimisation perf. Là, il faut reprendre la main.

Mon take : le vibe coding n'est pas du "no code". C'est du code à vitesse x10 pour ceux qui SAVENT déjà coder.

Plus de détails → {SITE_URL}

#VibeCoding #CursorAI #DeveloperExperience #IACode""",
            "hashtags": ["#VibeCoding", "#CursorAI", "#DeveloperExperience", "#IACode"],
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
