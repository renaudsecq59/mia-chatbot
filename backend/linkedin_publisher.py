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
import re
import httpx
from datetime import datetime, timezone
from google import genai
from config import GCP_PROJECT, GCP_LOCATION, GEMINI_API_KEY, EXPERT_PROFILE
from post_memory import get_post_history_summary, check_duplicate, store_post_embedding

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
    GEMINI_FLASH_MODEL = "gemini-2.5-flash"
except Exception:
    gemini_client = None
    GEMINI_MODEL = None
    GEMINI_FLASH_MODEL = None


EDITO_PROMPT = """Tu es le ghostwriter LinkedIn de {name}, {title}.
DATE : {today}. Nous sommes en 2026. NE JAMAIS mentionner 2024 ou 2025 comme événement récent.

PROFIL RENAUD (à utiliser pour ancrer le propos, pas pour se vanter) :
- Consultant freelance IA & Data chez Decathlon (Data Governance, Collibra, Vertex AI)
- Build des agents IA en production, des pipelines data, et des dashboards de gouvernance
- Formateur vibe coding (Cursor, Claude Code, Windsurf) — l'utilise au quotidien en mission
- Ex-manager d'équipes data (10+ personnes), connait les enjeux organisationnels
- Conviction forte : l'IA sans gouvernance des données est une bombe à retardement

3 PILIERS ÉDITORIAUX (prioriser ces sujets) :
1. AI GOVERNANCE — EU AI Act, model governance, AI safety, compliance, risk management, régulation
2. DATA GOVERNANCE — data quality, catalog, lineage, Collibra, data mesh, data contracts, stewardship
3. VIBE CODING — cursor, claude code, copilot, windsurf, agent coding, vibe coding, dev assisté IA

OBJECTIF : Que chaque post apporte UNE chose que le lecteur ne savait pas avant.
Le lecteur idéal est un CDO, CTO ou Data Engineer en entreprise.

{post_history}

ANTI-RÉPÉTION ABSOLUE : Le post que tu vas écrire DOIT avoir un angle radicalement différent des posts précédents ci-dessus. Si un post précédent parlait d'un outil, parle d'un autre. Si un post précédent était une revue, fais une analyse profonde. Varie les exemples, les chiffres, les références. NE JAMAIS reprendre la même structure ni le même angle.

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
Partager un pattern ou une observation issue de la pratique terrain, ANCRÉ dans les ARTICLES DE LA SEMAINE.
Structure :
1. Hook = un problème technique ou organisationnel RÉEL cité dans les articles de la semaine
2. Pourquoi ce problème est fréquent en entreprise (observation générique, sans citer de client)
3. L'approche ou le pattern qui fonctionne (basé sur les articles + expertise générale du domaine)
4. Le takeaway concret pour les équipes data/IA

RÈGLES ABSOLUES POUR CE FORMAT :
- NE JAMAIS citer Decathlon, ni aucun autre client ou employeur par son nom
- NE JAMAIS inventer des chiffres (pertes, économies, délais) non cités dans les articles sources
- Si tu utilises des chiffres, ils DOIVENT provenir d'un des articles fournis
- Formuler avec "dans les équipes que je côtoie" ou "pattern fréquent en entreprise" — jamais de cas inventé
- L'objectif est de partager un PATTERN GÉNÉRIQUE issu des articles, pas de raconter une anecdote personnelle

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
- CITER "DECATHLON" ou tout autre nom de client/employeur → STRICTEMENT INTERDIT. Utiliser "un grand retailer" ou "en entreprise" à la place.
- INVENTER des chiffres (montants, pertes, économies, délais, pourcentages) NON PRÉSENTS dans les articles fournis → STRICTEMENT INTERDIT. Tout chiffre utilisé doit être issu des articles de la semaine.

EXIGENCES NON-NÉGOCIABLES :
1. Au moins 1 CHIFFRE ou DONNÉE FACTUELLE dans le post — UNIQUEMENT s'il est présent dans les articles fournis. Si aucun chiffre dans les articles, utilise une donnée de notoriété publique (statistique officielle). Ne jamais inventer.
2. Au moins 1 NOM PROPRE (outil, entreprise, personne, framework)
3. Au moins 1 PRISE DE POSITION claire (pas tiède, pas "ça dépend")
4. NE PAS inclure de lien URL dans post_text — le lien sera ajouté automatiquement en fin de post
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

# 5 posts/semaine — chaque jour a son format signature
DAILY_FORMAT = {
    0: "revue_hebdo",      # Lundi : le rendez-vous veille
    1: "decryptage",       # Mardi : vulgariser un concept complexe
    2: "signal_faible",    # Mercredi : un signal que personne n'a connecté
    3: "retour_terrain",   # Jeudi : du vécu en mission
    4: "chiffre_cle",      # Vendredi : un chiffre percutant (format court)
}


def pick_post_type_for_today() -> str:
    """Retourne le type de post selon le jour de la semaine (lun-ven, heure Paris)."""
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("Europe/Paris"))
    weekday = today.weekday()  # 0=lundi ... 4=vendredi
    return DAILY_FORMAT.get(weekday, "signal_faible")


def _quality_gate(post_text: str) -> dict:
    """Vérifie la qualité du post selon les best practices LinkedIn 2026.

    Returns:
        {"passed": bool, "issues": list[str]}
    """
    issues = []

    # Banned phrases (AI-slop detection)
    BANNED = [
        "game-changer", "game changer", "révolutionnaire", "passionnant", "incroyable",
        "leverage", "dive in", "let's dive", "unpack this", "buckle up",
        "in today's fast-paced", "now more than ever", "in an era of",
        "Et vous ?", "Qu'en pensez-vous", "What would you add",
        "The lesson?", "The takeaway is simple", "At the end of the day",
        "supercharge", "unlock", "seamless", "robust", "transformative",
        "delve", "harness",
    ]
    text_lower = post_text.lower()
    for phrase in BANNED:
        if phrase.lower() in text_lower:
            issues.append(f"Banned phrase: '{phrase}'")

    # Hook strength: first 210 chars should not start with a question or filler
    first_line = post_text.split("\n")[0]
    if len(first_line) < 20:
        issues.append("Hook trop court (< 20 chars)")
    if first_line.startswith(("👍", "🔥", "💡", "✅", "❌", "⚡", "🚀")):
        issues.append("Hook commence par un emoji")

    # Word count: 200-350 words sweet spot
    word_count = len(post_text.split())
    if word_count < 150:
        issues.append(f"Post trop court ({word_count} mots, min 150)")
    if word_count > 500:
        issues.append(f"Post trop long ({word_count} mots, max 500)")

    # Must contain at least 1 proper noun / tool name (heuristic: capitalized word > 3 chars)
    has_proper_noun = bool(re.search(r'\b[A-Z][a-z]{3,}\b', post_text))
    if not has_proper_noun:
        issues.append("Pas de nom propre détecté")

    return {"passed": len(issues) == 0, "issues": issues}


def score_articles_by_pillar(articles: list[dict]) -> list[dict]:
    """Score chaque article sur sa pertinence vs les 3 piliers éditoriaux.

    Utilise Gemini Flash pour un scoring rapide et économique.
    Ajoute un champ 'pillar_score' (0-10) et 'pillar' (nom du pilier) à chaque article.
    """
    if not gemini_client or not articles:
        return articles

    PILLAR_KEYWORDS = {
        "ai_governance": ["AI act", "model governance", "AI safety", "compliance", "risk", "regulation", "EU AI", "AI ethics", "algorithmic"],
        "data_governance": ["data quality", "catalog", "lineage", "Collibra", "data mesh", "data contract", "stewardship", "data governance", "metadata"],
        "vibe_coding": ["cursor", "claude code", "copilot", "windsurf", "vibe coding", "agent coding", "code assistant", "IDE", "coding agent"],
    }

    for article in articles:
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        best_pillar = None
        best_score = 0

        for pillar, keywords in PILLAR_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw.lower() in text)
            score = min(hits * 2, 10)  # 2 points par match, max 10
            if score > best_score:
                best_score = score
                best_pillar = pillar

        article["pillar"] = best_pillar or "general"
        article["pillar_score"] = best_score

    # Trier par pillar_score décroissant
    articles.sort(key=lambda a: a.get("pillar_score", 0), reverse=True)
    logger.info(f"📊 Articles scorés par pilier — top: {articles[0].get('pillar', '?')} ({articles[0].get('pillar_score', 0)}/10)" if articles else "📊 Aucun article à scorer")
    return articles


def generate_weekly_edito(articles: list[dict], trends: list[str] = None, post_type: str = None, db=None) -> dict:
    """Génère l'édito LinkedIn à partir des meilleurs articles.

    Args:
        db: Firestore client pour la mémoire des posts passés et la déduplication.
    """
    if not articles:
        return {"error": "Aucun article pour générer l'édito"}

    post_type = post_type or pick_post_type_for_today()

    # Scorer les articles par pertinence vs les 3 piliers
    articles = score_articles_by_pillar(articles)

    # Préparer le résumé des articles pour le LLM
    articles_summary = ""
    for i, a in enumerate(articles[:10], 1):
        pillar_tag = f"[{a.get('pillar', 'general')}:{a.get('pillar_score', 0)}/10]" if a.get('pillar_score') else ""
        articles_summary += f"{i}. {pillar_tag} {a['title']} ({a.get('source_name', 'Source')})\n"
        if a.get('summary'):
            articles_summary += f"   → {a['summary'][:150]}\n"
        if a.get('expert_opinion'):
            articles_summary += f"   💬 {a['expert_opinion'][:120]}\n"

    trends_str = ", ".join(trends[:8]) if trends else "AI governance, data governance, vibe coding"

    # Récupérer l'historique des posts pour l'anti-répétition
    post_history = get_post_history_summary(db, limit=5) if db else "Aucun historique disponible."

    if not gemini_client:
        logger.warning("⚠️ GenAI non disponible, édito simulé")
        return _mock_edito(articles, trends_str, post_type)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            prompt = EDITO_PROMPT.format(
                name=EXPERT_PROFILE["name"],
                title=EXPERT_PROFILE["title"],
                today=datetime.now(timezone.utc).strftime("%d %B 2026"),
                articles_summary=articles_summary,
                trends=trends_str,
                post_type=post_type,
                site_url=SITE_URL,
                post_history=post_history,
            )

            from google.genai import types as genai_types
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    max_output_tokens=4096,
                ),
            )
            raw_text = response.text
            if raw_text is None and response.candidates:
                parts = response.candidates[0].content.parts
                raw_text = "".join(p.text for p in parts if p.text)
            raw_text = (raw_text or "").strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            result = json.loads(raw_text)
            result["generated_at"] = datetime.now(timezone.utc).isoformat()
            result["article_count"] = len(articles)
            result["post_type"] = post_type
            result["status"] = "generated"
            result["generation_attempt"] = attempt + 1

            # Quality gate
            qg = _quality_gate(result.get("post_text", ""))
            result["quality_gate"] = qg
            if not qg["passed"]:
                logger.warning(f"⚠️ Quality gate issues (attempt {attempt+1}): {qg['issues']}")

            # Dedup check (skip on last attempt to always return something)
            if db and attempt < max_retries - 1:
                dup = check_duplicate(db, result.get("post_text", ""))
                result["dedup"] = dup
                if dup["is_duplicate"]:
                    logger.warning(f"🔄 Duplicate détecté (sim={dup['max_similarity']}) — regénération attempt {attempt+2}")
                    post_history += f"\n⚠️ ATTENTION: La tentative précédente était trop similaire à un post existant (similarity={dup['max_similarity']}). Change complètement d'angle."
                    continue

            logger.info(f"📝 Édito LinkedIn [{post_type}] généré (attempt {attempt+1}, {len(result['post_text'])} chars, {result.get('word_count', '?')} mots)")
            return result

        except Exception as e:
            logger.error(f"❌ Erreur génération édito (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                continue
            return _mock_edito(articles, trends_str, post_type)

    return _mock_edito(articles, trends_str, post_type)


INFOGRAPHIC_CONTENT_GENERATOR = """Tu es un expert en création d'infographics LinkedIn viraux sur la Data et l'IA.

À partir du post LinkedIn ci-dessous, génère le CONTENU STRUCTURÉ d'un infographic éducatif en JSON.

POST :
{post_text}

L'infographic doit capturer l'ESSENTIEL du post sous forme visuelle et didactique.
Pense au style "Save for later" de LinkedIn : un visuel que les gens bookmarkent parce qu'il résume parfaitement un concept.

Réponds en JSON strict :
{{
  "title": "Titre principal en majuscules (5-7 mots max, percutant)",
  "subtitle": "Sous-titre accrocheur (10-15 mots)",
  "sections": [
    {{
      "number": "1",
      "heading": "TITRE SECTION (3-4 mots)",
      "body": "Explication courte et factuelle (15-20 mots max)"
    }}
  ],
  "key_stat": "UN chiffre clé ou fait marquant (ex: '70% des projets IA échouent')",
  "color_theme": "purple|blue|green|orange",
  "author": "Renaud Secq"
}}

Génère entre 4 et 6 sections. Chaque section doit apporter une information concrète, pas du blabla."""


def _generate_image_prompt(post_text: str, post_type: str) -> str:
    """Utilise Gemini Pro pour générer le contenu d'un infographic, puis crée le prompt Imagen."""
    try:
        # Étape 1 : Gemini génère le contenu structuré de l'infographic
        content_response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=INFOGRAPHIC_CONTENT_GENERATOR.format(post_text=post_text[:1000]),
        )
        raw = content_response.text
        if raw is None and content_response.candidates:
            parts = content_response.candidates[0].content.parts
            raw = "".join(p.text for p in parts if p.text)
        raw = (raw or "").strip()
        # Nettoyer le JSON
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()

        import json
        data = json.loads(raw)

        title = data.get("title", "DATA & AI INSIGHTS")
        subtitle = data.get("subtitle", "")
        sections = data.get("sections", [])[:6]
        key_stat = data.get("key_stat", "")
        color = data.get("color_theme", "purple")

        color_map = {
            "purple": "purple and violet (#6B46C1)",
            "blue": "electric blue and indigo (#2563EB)",
            "green": "emerald green (#059669)",
            "orange": "deep orange (#EA580C)",
        }
        accent = color_map.get(color, color_map["purple"])

        # Construire les sections numérotées pour le prompt
        sections_lines = "\n".join(
            [f"{s['number']}. {s['heading']} — {s['body']}" for s in sections]
        )

        # Étape 2 : Prompt structuré pour Nano Banana Pro (Gemini 3 Pro Image)
        prompt = (
            f"Create a professional LinkedIn infographic in portrait format (3:4 ratio).\n\n"
            f"TITLE at top: {title}\n"
            f"SUBTITLE: {subtitle}\n\n"
            f"{len(sections)} numbered sections, each with a simple minimalist icon on the left "
            f"and the text on the right:\n{sections_lines}\n\n"
        )
        if key_stat:
            prompt += f"Highlighted key statistic box: {key_stat}\n\n"
        prompt += (
            f"Bottom credit: {data.get('author', 'Renaud Secq')} — Consultant IA & Data\n\n"
            f"STYLE: clean modern flat design, white background, {accent} accents, "
            f"professional minimalist line icons, clear bold sans-serif typography, "
            f"well-structured grid with vertical connector line, plenty of whitespace. "
            f"All text must be perfectly spelled and readable in French. "
            f"LinkedIn viral 'save for later' infographic style."
        )
        logger.info(f"📊 Infographic: {title} | {len(sections)} sections")
        return prompt

    except Exception as e:
        logger.warning(f"⚠️ Fallback infographic prompt: {e}")
        hook = post_text.split("\n")[0][:80]
        return (
            f"Create a professional LinkedIn infographic in portrait format (3:4 ratio) "
            f"with white background and purple accents, large bold title \"{hook[:50]}\", "
            f"4-5 numbered sections with minimalist icons, clean flat design, "
            f"perfectly readable French text, structured grid layout."
        )


def generate_visual(post_text: str, post_type: str) -> bytes | None:
    """Génère un infographic IA (Nano Banana Pro / Gemini 3 Pro Image) pour le post LinkedIn."""
    if not gemini_client:
        logger.warning("⚠️ GenAI non dispo, pas de visuel")
        return None

    # Étape 1 : Gemini génère le contenu structuré + le prompt infographic
    image_prompt = _generate_image_prompt(post_text, post_type)
    logger.info(f"🖼️ Prompt infographic: {image_prompt[:120]}...")

    try:
        from google import genai as image_genai
        from google.genai import types as genai_types

        # Nano Banana Pro requiert la location "global"
        client = image_genai.Client(vertexai=True, project=GCP_PROJECT, location="global")
        response = client.models.generate_content(
            model="gemini-3-pro-image",
            contents=image_prompt,
            config=genai_types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                logger.info(f"🎨 Infographic Nano Banana Pro généré ({len(image_bytes)} bytes)")
                return image_bytes

        logger.warning("⚠️ Aucune image dans la réponse Nano Banana Pro")
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
    # LinkedIn /rest/posts API : limite réelle = 3000 chars (texte + image OK)
    MAX_COMMENTARY_CHARS = 3000
    if len(post_text) > MAX_COMMENTARY_CHARS:
        # Troncature propre à la dernière phrase complète avant la limite
        truncated = post_text[:MAX_COMMENTARY_CHARS]
        last_period = max(truncated.rfind('. '), truncated.rfind('!\n'), truncated.rfind('?\n'), truncated.rfind('.\n'))
        if last_period > 600:
            post_text = truncated[:last_period + 1]
        else:
            post_text = truncated.rstrip()
        logger.warning(f"⚠️ post_text tronqué à {len(post_text)} chars (original > {MAX_COMMENTARY_CHARS})")
    logger.info(f"📤 Publication LinkedIn: {len(post_text)} chars")

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
