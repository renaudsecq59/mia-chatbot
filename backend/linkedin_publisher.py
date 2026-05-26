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
    GEMINI_MODEL = "gemini-2.5-pro"
except Exception:
    gemini_client = None
    GEMINI_MODEL = None


EDITO_PROMPT = """Tu es le ghostwriter LinkedIn de {name}, {title}.
DATE : {today}. Nous sommes en 2026. NE JAMAIS mentionner 2024 ou 2025 comme événement récent.

PROFIL RENAUD (à utiliser pour ancrer le propos, pas pour se vanter) :
- Consultant freelance IA & Data chez Decathlon (Data Governance, Collibra, Vertex AI)
- Build des agents IA en production, des pipelines data, et des dashboards de gouvernance
- Formateur vibe coding (Cursor, Claude Code, Windsurf) — l'utilise au quotidien en mission
- Ex-manager d'équipes data (10+ personnes), connait les enjeux organisationnels
- Conviction forte : l'IA sans gouvernance des données est une bombe à retardement

OBJECTIF : Que chaque post apporte UNE chose que le lecteur ne savait pas avant.
Le lecteur idéal est un CDO, CTO ou Data Engineer en entreprise.

ARTICLES DE LA SEMAINE :
{articles_summary}

TENDANCES : {trends}

TYPE DE POST : {post_type}

=== FORMATS ===

--- REVUE_HEBDO ---
Le rendez-vous du lundi. Format reconnaissable.
Structure EXACTE :
1. Une phrase d'accroche sur LE fait de la semaine
2. 4-5 bullet points : chaque bullet = 1 fait + son implication en 1 ligne
3. "Ma sélection complète avec mes avis : {site_url}"
Pas de conclusion. Le lecteur scroll, absorbe, repart.

--- SIGNAL_FAIBLE ---
Repérer un signal que personne n'a encore connecté.
Structure :
1. Hook = un fait précis + une question implicite ("X vient de faire Y. C'est plus significatif qu'il n'y paraît.")
2. L'explication : pourquoi ce signal annonce un changement de fond (2-3 paragraphes denses)
3. Ce que ça implique concrètement pour les équipes data/IA en entreprise
4. Lien vers la veille

--- RETOUR_TERRAIN ---
Le plus différenciant. Du vécu, pas du théorique.
Structure :
1. Hook = un problème concret rencontré en mission ("En déployant X chez un client, on s'est heurtés à Y.")
2. Le contexte : quel projet, quelle stack, quel objectif
3. La solution ou le pattern trouvé
4. Le takeaway généralisable pour d'autres équipes
UTILISER les éléments du profil de Renaud pour ancrer le propos.

--- COMPARATIF ---
Couper court aux débats stériles avec des faits.
Structure :
1. Hook = "X vs Y : voici ce que disent les faits."
2. Critère 1 : fait objectif
3. Critère 2 : fait objectif
4. Critère 3 : fait objectif
5. Mon verdict : dans quel cas utiliser l'un vs l'autre

--- CHIFFRE_CLE ---
Format court et percutant.
Structure :
1. LE chiffre (gros, visible, mémorable)
2. D'où il vient (source crédible)
3. Pourquoi il devrait inquiéter ou enthousiasmer
4. Ce que ça change pour les pros data/IA

--- DECRYPTAGE ---
Vulgariser un sujet complexe sans infantiliser.
Structure :
1. Hook = le sujet en une phrase simple
2. L'analogie (1 phrase, pas plus)
3. Comment ça marche vraiment (2-3 paragraphes techniques mais lisibles)
4. Pourquoi c'est important pour l'entreprise

INTERDICTIONS ABSOLUES :
- "On me demande souvent", "J'ai eu l'occasion de" → INTERDIT
- "Game-changer", "révolutionnaire", "passionnant", "incroyable" → INTERDIT
- Questions rhétoriques finales ("Et vous ?") → INTERDIT
- Commencer par un emoji → INTERDIT
- Humble-brag → INTERDIT
- Phrases creuses sans information → INTERDIT (chaque phrase doit contenir un fait, un chiffre ou un nom)

EXIGENCES NON-NÉGOCIABLES :
1. Au moins 1 CHIFFRE ou DONNÉE FACTUELLE dans le post (%, montant, date, nombre d'utilisateurs, etc.)
2. Au moins 1 NOM PROPRE (outil, entreprise, personne, framework)
3. Au moins 1 PRISE DE POSITION claire (pas tiède, pas "ça dépend")
4. Le lien {site_url} intégré naturellement 1 seule fois
5. ENTRE 200 ET 300 MOTS
6. 2-3 hashtags techniques et spécifiques (pas #IA #Data qui sont trop larges)
7. 0-1 emoji max
8. Écriture naturelle en français. Pas de calque anglais.

RÉPONDS EN JSON STRICT :
{{
  "post_text": "Le post complet prêt à publier",
  "hook": "La première ligne seule",
  "post_type": "{post_type}",
  "hashtags": ["#tag1", "#tag2"],
  "word_count": 0
}}"""

# Lundi = revue hebdo, Jeudi = sujet de fond (rotation)
THURSDAY_TYPES = ["signal_faible", "retour_terrain", "comparatif", "chiffre_cle", "decryptage"]


def pick_post_type_for_today() -> str:
    """Retourne le type de post selon le jour : lundi=revue_hebdo, jeudi=fond (rotation)."""
    today = datetime.now(timezone.utc)
    weekday = today.weekday()  # 0=lundi, 3=jeudi
    if weekday == 0:  # Lundi
        return "revue_hebdo"
    elif weekday == 3:  # Jeudi
        week_number = today.isocalendar()[1]
        return THURSDAY_TYPES[week_number % len(THURSDAY_TYPES)]
    else:
        # Si appelé un autre jour, on choisit selon la semaine
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
            today=datetime.now(timezone.utc).strftime("%d %B 2026"),
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

    # Identité visuelle cohérente : palette sombre + accent cyan/doré + style géométrique épuré
    # Chaque type a sa variation mais le style reste reconnaissable
    BASE_STYLE = "Dark navy background (#0a1628), clean geometric shapes, minimal flat design, professional tech aesthetic, accent colors cyan (#00d4ff) and gold (#c8a951), subtle gradient, NO text NO words NO letters"
    style_prompts = {
        "revue_hebdo": f"{BASE_STYLE}, grid layout of 5 abstract icons representing different tech topics, dashboard feel, weekly digest concept",
        "signal_faible": f"{BASE_STYLE}, single bright signal point radiating connections outward, radar/sonar aesthetic, one bright element emerging from noise",
        "retour_terrain": f"{BASE_STYLE}, abstract construction/building metaphor, layers being assembled, hands-on engineering feel, blueprint aesthetic",
        "comparatif": f"{BASE_STYLE}, split composition with two geometric forms side by side, balance scale concept, versus layout",
        "chiffre_cle": f"{BASE_STYLE}, large abstract number/chart dominating the frame, bold data visualization, single impactful metric feel",
        "decryptage": f"{BASE_STYLE}, complex mechanism being opened/revealed, layers peeling back, magnifying glass or lens concept, x-ray aesthetic",
    }

    style = style_prompts.get(post_type, style_prompts["signal_faible"])

    # Extraire le sujet principal du post pour contextualiser l'image
    hook = post_text.split("\n")[0][:100]
    image_prompt = f"""Create a professional LinkedIn post illustration.
Topic: {hook}
Style: {style}
Format: 1200x627px landscape, suitable for LinkedIn feed.
IMPORTANT: No text, no words, no letters in the image. Pure visual illustration."""

    try:
        import vertexai
        from vertexai.preview.vision_models import ImageGenerationModel

        vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
        model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")

        response = model.generate_images(
            prompt=image_prompt,
            number_of_images=1,
            aspect_ratio="16:9",
            safety_filter_level="block_few",
            person_generation="allow_adult",
        )

        if response.images:
            image_bytes = response.images[0]._image_bytes
            logger.info(f"🎨 Visuel Imagen 3 généré ({len(image_bytes)} bytes)")
            return image_bytes

        logger.warning("⚠️ Aucune image dans la réponse Imagen")
        return None

    except Exception as e:
        logger.error(f"❌ Erreur génération visuel: {e}")
        return None


def _upload_image_to_linkedin(image_bytes: bytes) -> str | None:
    """Upload une image sur LinkedIn via la nouvelle API Images et retourne l'image URN."""
    if not LINKEDIN_ACCESS_TOKEN or not LINKEDIN_PERSON_URN:
        return None

    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "LinkedIn-Version": "202506",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    # Étape 1 : Initialiser l'upload via la nouvelle API images
    init_payload = {
        "initializeUploadRequest": {
            "owner": LINKEDIN_PERSON_URN,
        }
    }

    try:
        init_response = httpx.post(
            "https://api.linkedin.com/rest/images?action=initializeUpload",
            headers=headers,
            json=init_payload,
            timeout=30,
        )

        if init_response.status_code != 200:
            logger.error(f"❌ LinkedIn init upload failed: {init_response.status_code} {init_response.text[:200]}")
            return None

        init_data = init_response.json()
        upload_url = init_data["value"]["uploadUrl"]
        image_urn = init_data["value"]["image"]

        # Étape 2 : Uploader le binaire
        upload_headers = {
            "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
            "Content-Type": "application/octet-stream",
        }

        upload_response = httpx.put(
            upload_url,
            headers=upload_headers,
            content=image_bytes,
            timeout=60,
        )

        if upload_response.status_code in (200, 201):
            logger.info(f"🖼️ Image uploadée sur LinkedIn: {image_urn}")
            return image_urn
        else:
            logger.error(f"❌ LinkedIn image upload failed: {upload_response.status_code}")
            return None

    except Exception as e:
        logger.error(f"❌ Erreur upload image LinkedIn: {e}")
        return None


def publish_to_linkedin(post_text: str, image_bytes: bytes = None) -> dict:
    """Publie un post sur LinkedIn via la nouvelle API Posts (/rest/posts)."""
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
            "LinkedIn-Version": "202506",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        # Upload de l'image si dispo
        image_urn = None
        if image_bytes:
            image_urn = _upload_image_to_linkedin(image_bytes)

        # Construire le payload avec la nouvelle API Posts
        payload = {
            "author": LINKEDIN_PERSON_URN,
            "commentary": post_text,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
        }

        if image_urn:
            payload["content"] = {
                "media": {
                    "id": image_urn,
                    "title": "Veille IA & Data",
                }
            }

        response = httpx.post(
            "https://api.linkedin.com/rest/posts",
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.status_code in (200, 201):
            post_id = response.headers.get("X-RestLi-Id", response.headers.get("x-restli-id", "unknown"))
            logger.info(f"✅ Post LinkedIn publié ! ID: {post_id} (image: {bool(image_urn)})")
            return {
                "status": "published",
                "post_id": post_id,
                "post_text": post_text,
                "has_image": bool(image_urn),
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
