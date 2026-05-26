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


EDITO_PROMPT = """Tu rédiges un post LinkedIn pour {name}, consultant IA & Data.

OBJECTIF : Partager une INFO UTILE et CONCRÈTE. Pas du personal branding.
Le lecteur doit apprendre quelque chose en 30 secondes de lecture.

ARTICLES DE LA SEMAINE (inspire-toi, ne copie pas) :
{articles_summary}

TENDANCES : {trends}

TYPE : {post_type}

=== REVUE_PRESSE ===
- Hook = fait marquant de la semaine (chiffre, annonce, changement)
- 4-5 infos clés en format scannable (tirets ou numéros)
- Pour chaque info : le FAIT + pourquoi ça compte (en 1 ligne)
- Pas de conclusion morale. Juste les faits.

=== OBSERVATEUR ===
- Hook = un fait surprenant ou contre-intuitif tiré de la veille
- 2 paragraphes : explication simple de pourquoi c'est important
- Pas de question finale artificielle

=== VULGARISATEUR ===
- Hook = un concept technique expliqué simplement
- Analogie concrète
- Ce que ça change en pratique pour quelqu'un qui build de l'IA

=== QUESTIONNEUR ===
- Hook = question directe sur un sujet clivant de la semaine
- Donner les 2 côtés du débat factuellement
- Prendre position brièvement

=== VERTEX_AI ===
- Hook = une annonce ou un changement concret Vertex AI / Google Cloud
- Ce que ça change en pratique (pas du marketing Google)
- Un tip technique actionnable si possible

=== VIBE_CODING ===
- Hook = un fait ou une découverte sur le coding assisté par IA
- Workflow concret, outil testé, résultat factuel
- Ce qui marche vs ce qui ne marche pas encore

INTERDICTIONS STRICTES :
- JAMAIS "On me demande souvent", "J'ai eu l'occasion de", "Mon expérience montre"
- JAMAIS de phrases pompeuses type coach LinkedIn
- JAMAIS "game-changer", "révolutionnaire", "passionnant", "incroyable"
- JAMAIS de question rhétorique en fin de post du style "Et vous, qu'en pensez-vous ?"
- JAMAIS commencer par un emoji
- PAS de "je" en mode humble-brag. Le "je" est OK uniquement pour un fait précis ("j'ai testé X, résultat : Y")

EXIGENCE DE FOND :
- Chaque paragraphe doit apporter une INFO NOUVELLE (chiffre, fait, nom d'outil, comparaison)
- Pas de phrases creuses ou de remplissage. Si une phrase n'apporte pas d'info, supprime-la.
- Le lecteur doit pouvoir résumer le post en bullet points factuels.
- Donne du CONTEXTE : pourquoi c'est important, qu'est-ce que ça change concrètement.

STYLE :
- Factuel, direct, dense en information. Comme un bon article de blog condensé.
- Phrases courtes mais complètes. Pas de style télégraphique.
- ENTRE 200 ET 300 MOTS. C'est LinkedIn, pas Twitter. Donne de la matière.
- 0-1 emoji max dans tout le post.
- 2-3 hashtags max, techniques et spécifiques.
- Le lien {site_url} intégré 1 seule fois, naturellement.

RÉPONDS EN JSON STRICT :
{{
  "post_text": "Le post complet prêt à publier",
  "hook": "La première ligne seule",
  "post_type": "{post_type}",
  "hashtags": ["#tag1", "#tag2"],
  "word_count": 0
}}"""

# Lundi = veille de la semaine, Jeudi = sujet de fond (alterne chaque semaine)
THURSDAY_TYPES = ["vertex_ai", "vibe_coding", "observateur", "vulgarisateur", "questionneur"]


def pick_post_type_for_today() -> str:
    """Retourne le type de post selon le jour : lundi=revue_presse, jeudi=fond."""
    today = datetime.now(timezone.utc)
    weekday = today.weekday()  # 0=lundi, 3=jeudi
    if weekday == 0:  # Lundi
        return "revue_presse"
    elif weekday == 3:  # Jeudi
        week_number = today.isocalendar()[1]
        return THURSDAY_TYPES[week_number % len(THURSDAY_TYPES)]
    else:
        # Si appelé un autre jour, on choisit le plus proche
        week_number = today.isocalendar()[1]
        return THURSDAY_TYPES[week_number % len(THURSDAY_TYPES)]


def generate_weekly_edito(articles: list[dict], trends: list[str] = None, post_type: str = None) -> dict:
    """Génère l'édito LinkedIn à partir des meilleurs articles."""
    if not articles:
        return {"error": "Aucun article pour générer l'édito"}

    post_type = post_type or pick_post_type_for_today()

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


def generate_visual(post_text: str, post_type: str) -> bytes | None:
    """Génère un visuel IA (Imagen 3) pour illustrer le post LinkedIn."""
    if not gemini_client:
        logger.warning("⚠️ GenAI non dispo, pas de visuel")
        return None

    # Prompt adapté au type de post
    style_prompts = {
        "revue_presse": "Clean modern infographic style, abstract data visualization with flowing lines and nodes, blue and purple gradient, minimalist tech aesthetic, no text",
        "vertex_ai": "Abstract cloud computing visualization, neural network connections in Google Cloud colors (blue, green, yellow, red), modern 3D render, no text",
        "vibe_coding": "Developer workspace with AI assistance visualization, code floating in air with glowing highlights, dark theme with neon accents, futuristic IDE concept, no text",
        "observateur": "Abstract thought leadership visualization, interconnected ideas as geometric shapes, warm earth tones with accent colors, modern art style, no text",
        "vulgarisateur": "Educational diagram style, complex concept simplified into clean visual metaphor, friendly colors, whiteboard aesthetic with modern touch, no text",
        "questionneur": "Two contrasting perspectives visualization, split composition, bold geometric shapes, debate concept in abstract form, no text",
    }

    style = style_prompts.get(post_type, style_prompts["observateur"])

    # Extraire le sujet principal du post pour contextualiser l'image
    hook = post_text.split("\n")[0][:100]
    image_prompt = f"""Create a professional LinkedIn post illustration.
Topic: {hook}
Style: {style}
Format: 1200x627px landscape, suitable for LinkedIn feed.
IMPORTANT: No text, no words, no letters in the image. Pure visual illustration."""

    try:
        from google.genai import types
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=image_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        # Extraire l'image de la réponse
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                image_bytes = part.inline_data.data
                logger.info(f"🎨 Visuel généré ({len(image_bytes)} bytes)")
                return image_bytes

        logger.warning("⚠️ Aucune image dans la réponse Gemini")
        return None

    except Exception as e:
        logger.error(f"❌ Erreur génération visuel: {e}")
        return None


def _upload_image_to_linkedin(image_bytes: bytes) -> str | None:
    """Upload une image sur LinkedIn et retourne l'asset URN."""
    if not LINKEDIN_ACCESS_TOKEN or not LINKEDIN_PERSON_URN:
        return None

    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202405",
    }

    # Étape 1 : Enregistrer l'upload
    register_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": LINKEDIN_PERSON_URN,
            "serviceRelationships": [
                {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
            ]
        }
    }

    try:
        reg_response = httpx.post(
            "https://api.linkedin.com/v2/assets?action=registerUpload",
            headers=headers,
            json=register_payload,
            timeout=30,
        )

        if reg_response.status_code != 200:
            logger.error(f"❌ LinkedIn register upload failed: {reg_response.status_code} {reg_response.text[:200]}")
            return None

        reg_data = reg_response.json()
        upload_url = reg_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_urn = reg_data["value"]["asset"]

        # Étape 2 : Uploader le binaire
        upload_headers = {
            "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
            "Content-Type": "image/png",
        }

        upload_response = httpx.put(
            upload_url,
            headers=upload_headers,
            content=image_bytes,
            timeout=60,
        )

        if upload_response.status_code in (200, 201):
            logger.info(f"🖼️ Image uploadée sur LinkedIn: {asset_urn}")
            return asset_urn
        else:
            logger.error(f"❌ LinkedIn image upload failed: {upload_response.status_code}")
            return None

    except Exception as e:
        logger.error(f"❌ Erreur upload image LinkedIn: {e}")
        return None


def publish_to_linkedin(post_text: str, image_bytes: bytes = None) -> dict:
    """Publie un post sur LinkedIn (avec ou sans image)."""
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

        # Upload de l'image si dispo
        asset_urn = None
        if image_bytes:
            asset_urn = _upload_image_to_linkedin(image_bytes)

        # Construire le payload selon qu'on a une image ou non
        if asset_urn:
            payload = {
                "author": LINKEDIN_PERSON_URN,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": post_text},
                        "shareMediaCategory": "IMAGE",
                        "media": [
                            {
                                "status": "READY",
                                "media": asset_urn,
                                "title": {"text": "Veille IA & Data"},
                                "description": {"text": "Illustration générée par IA"},
                            }
                        ]
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
            }
        else:
            payload = {
                "author": LINKEDIN_PERSON_URN,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": post_text},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
            }

        response = httpx.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.status_code == 201:
            post_id = response.headers.get("X-RestLi-Id", "unknown")
            logger.info(f"✅ Post LinkedIn publié ! ID: {post_id} (image: {bool(asset_urn)})")
            return {
                "status": "published",
                "post_id": post_id,
                "post_text": post_text,
                "has_image": bool(asset_urn),
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
