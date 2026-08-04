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
from google.cloud import firestore
import httpx
from datetime import datetime, timezone
from google import genai
from config import GCP_PROJECT, GCP_LOCATION, GEMINI_API_KEY, EXPERT_PROFILE
from post_memory import (
    get_post_history_summary, check_duplicate, store_post_embedding, get_performance_insights,
    store_critic_lesson, get_critic_lessons,
    get_style_guidelines,
    update_source_scores, get_top_sources,
    store_hook_experiment, get_hook_patterns,
    get_visual_lessons,
)

logger = logging.getLogger(__name__)

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN", "")  # Format: urn:li:person:XXXXXX

SITE_URL = "https://renaudsecq.com/veille.html"

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

# Claude Opus 5 via Vertex AI — pour la génération de posts (meilleure qualité d'écriture)
CLAUDE_MODEL = "claude-opus-5"
# Claude Sonnet 5 via Vertex AI — pour le critic (near-Opus intelligence, moins cher)
CLAUDE_CRITIC_MODEL = "claude-sonnet-5"
# Claude désactivé — quota Vertex AI denied par Google pour les modèles Anthropic
# Le code garde le fallback pour réactivation future si le quota est débloqué
claude_client = None
logger.info(f"ℹ️ Claude désactivé (quota denied) — utilisation de Gemini {GEMINI_MODEL if GEMINI_MODEL else 'N/A'}")


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

MOTS INTERDITS (jargon AI-slop, jamais les utiliser) : game-changer, révolutionnaire, passionnant, incroyable, leverage, dive in, supercharge, unlock, seamless, transformative, delve, harness, "Et vous ?", "Qu'en pensez-vous". Écris comme un humain, pas comme un LLM.

{post_history}

ANTI-RÉPÉTION ABSOLUE : Le post que tu vas écrire DOIT avoir un angle radicalement différent des posts précédents ci-dessus. Si un post précédent parlait d'un outil, parle d'un autre. Si un post précédent était une revue, fais une analyse profonde. Varie les exemples, les chiffres, les références. NE JAMAIS reprendre la même structure ni le même angle.

{performance_insights}

{critic_lessons}

{style_guidelines}

{source_insights}

{hook_patterns}

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

--- AI_GOVERNANCE ---
Analyser un enjeu de gouvernance de l'IA issu de l'actualité de la semaine.
Structure :
1. Hook = un fait précis sur la régulation, la conformité ou la gouvernance de l'IA (EU AI Act, model governance, AI safety, risk management)
2. Le contexte réglementaire ou technique : pourquoi ce sujet est critique maintenant
3. L'implication concrète pour les équipes data/IA en entreprise (process, outils, organisation)
4. Une recommandation actionnable : ce qu'il faut faire (ou arrêter de faire)

RÈGLES POUR CE FORMAT :
- Ancre-toi sur les faits des articles de la semaine, pas sur des opinions générales
- Cite des textes réglementaires, frameworks ou standards précis (EU AI Act, NIST AI RMF, ISO 42001, etc.)
- Évite le sensationnalisme : la gouvernance est un sujet sérieux, traite-le avec rigueur
- Pas de conseil juridique : reste sur la dimension technique et organisationnelle

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
    3: "ai_governance",    # Jeudi : gouvernance de l'IA (EU AI Act, model governance, AI safety)
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
        "supercharge", "unlock", "seamless", "transformative",
        "delve", "harness",
    ]
    text_lower = post_text.lower()
    for phrase in BANNED:
        if phrase.lower() in text_lower:
            issues.append(f"Banned phrase: '{phrase}'")

    # Hook strength: first line must be a complete sentence
    first_line = post_text.split("\n")[0].strip()
    if len(first_line) < 20:
        issues.append("Hook trop court (< 20 chars)")
    if first_line.startswith(("👍", "🔥", "💡", "✅", "❌", "⚡", "🚀")):
        issues.append("Hook commence par un emoji")
    # Hook must end with proper punctuation (complete sentence check)
    if first_line and not first_line.endswith((".", "!", "?", ":", ";", "…")):
        issues.append(f"Hook incomplet (pas de ponctuation de fin): '{first_line[:60]}'")

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


def _batch_variety_check(db, post_type: str, hashtags: list[str]) -> dict:
    """Vérifie la variété sur les 5 derniers posts : pas 2x le même format, angle, ou hashtags.

    Returns:
        {"passed": bool, "issues": list[str], "recent_formats": list[str]}
    """
    from post_memory import get_recent_posts
    posts = get_recent_posts(db, limit=5)
    if not posts:
        return {"passed": True, "issues": [], "recent_formats": []}

    issues = []
    recent_formats = [p.get("post_type", "") for p in posts if p.get("post_type")]

    # 1. Pas 2x le même format sur les 3 derniers posts
    if len(recent_formats) >= 3:
        last_3 = recent_formats[:3]
        if last_3.count(post_type) >= 2:
            issues.append(f"Format '{post_type}' déjà utilisé {last_3.count(post_type)}x dans les 3 derniers posts — varier le format")

    # 2. Pas les mêmes hashtags que le post précédent
    if posts:
        last_hashtags = set(posts[0].get("hashtags", []))
        new_hashtags = set(hashtags)
        overlap = last_hashtags & new_hashtags
        if len(overlap) >= 2:
            issues.append(f"Hashtags répétés vs post précédent: {overlap} — utiliser des hashtags différents")

    # 3. Pas plus de 2x le même format sur 5 posts
    if recent_formats.count(post_type) >= 3:
        issues.append(f"Format '{post_type}' utilisé {recent_formats.count(post_type)}x sur 5 posts — trop répétitif")

    return {"passed": len(issues) == 0, "issues": issues, "recent_formats": recent_formats}


def _generate_alt_hook(original_hook: str, post_text: str, articles: list[dict], trends: str) -> str:
    """Génère un hook alternatif pour A/B testing."""
    try:
        prompt = f"""Génère UNE seule phrase d'accroche (hook) alternative pour ce post LinkedIn.
        Le hook doit être court (max 150 caractères), percutant, et différent de l'original.

        HOOK ORIGINAL: {original_hook}
        POST: {post_text[:500]}
        TENDANCES: {trends}

        Réponds avec UNIQUEMENT le hook, sans guillemets ni explication."""

        if claude_client:
            message = claude_client.messages.create(
                model=CLAUDE_CRITIC_MODEL,
                max_tokens=200,
                temperature=0.9,
                messages=[{"role": "user", "content": prompt}],
            )
            alt = message.content[0].text if message.content else ""
        elif gemini_client and GEMINI_FLASH_MODEL:
            from google.genai import types as genai_types
            response = gemini_client.models.generate_content(
                model=GEMINI_FLASH_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=200,
                    temperature=0.9,
                ),
            )
            alt = response.text or ""
        else:
            return ""

        alt = alt.strip().strip('"').strip("'")
        if alt and alt != original_hook and len(alt) < 300:
            return alt
        return ""
    except Exception as e:
        logger.warning(f"⚠️ Génération alt hook échouée: {e}")
        return ""


CRITIC_PROMPT = """Tu es un critique impitoyable de posts LinkedIn. Tu évalues ce post sur 6 dimensions, chacune notée de 0 à 10.

POST À ÉVALUER :
{post_text}

POSTS PRÉCÉDENTS (pour évaluer l'originalité) :
{recent_posts}

ÉVALUE SUR CES 6 DIMENSIONS :
1. HOOK — La première ligne est-elle une phrase COMPLÈTE qui crée une "open loop" ? Vérifie que ce n'est pas une phrase tronquée/incomplète. (0 = plate/tronquée, 10 = phrase complète et irrésistible)
2. INSIGHT — Le post apporte-t-il UNE chose que le lecteur ne savait pas ? (0 = évident/redite, 10 = révélation)
3. VOIX — Le ton est-il authentique, expert, pas du bullshit corporate ? (0 = creux/générique, 10 = voix unique reconnaissable)
4. ORIGINALITÉ — L'angle est-il différent des posts précédents ? (0 = même angle/redite, 10 = perspective totalement neuve)
5. FACTUALITÉ — Chaque chiffre/nom/fait est-il sourcé et crédible ? (0 = inventé/vague, 10 = tout est sourcé et précis)
6. LISIBILITÉ — Le post est-il facile à lire en scrollant ? (0 = mur de texte, 10 = rythme parfait, aérations, bullet points)

RÉPONDS EN JSON STRICT :
{{
  "scores": {{"hook": 0, "insight": 0, "voice": 0, "originality": 0, "factuality": 0, "readability": 0}},
  "average": 0.0,
  "verdict": "one-liner: pourquoi ce post marche ou pas",
  "worst_dimension": "la dimension la plus faible",
  "suggestion": "une phrase concrète pour améliorer"
}}"""


def _critic_evaluate(post_text: str, db) -> dict | None:
    """Agent Critic : Claude Sonnet 5 évalue le post sur 6 dimensions.

    Fallback sur Gemini Flash si Claude non disponible.

    Returns:
        {"scores": dict, "average": float, "verdict": str, "passed": bool} ou None si échec.
    """
    if not claude_client and not (gemini_client and GEMINI_FLASH_MODEL):
        return None

    try:
        from post_memory import get_recent_posts
        posts = get_recent_posts(db, limit=3) if db else []
        recent = "\n".join(f"- [{p.get('post_type', '?')}] {p.get('hook', p.get('post_text', '')[:80])}" for p in posts) or "Aucun"

        prompt = CRITIC_PROMPT.format(
            post_text=post_text[:2000],
            recent_posts=recent,
        )

        # Claude Sonnet 5 pour le critic (near-Opus, moins cher)
        # Fallback sur Gemini Flash si Claude 429
        raw = ""
        if claude_client:
            try:
                message = claude_client.messages.create(
                    model=CLAUDE_CRITIC_MODEL,
                    max_tokens=1024,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = message.content[0].text if message.content else ""
            except Exception as critic_err:
                if "429" in str(critic_err) and gemini_client and GEMINI_FLASH_MODEL:
                    logger.warning("⏳ Critic Claude 429 — fallback Gemini Flash")
                    from google.genai import types as genai_types
                    response = gemini_client.models.generate_content(
                        model=GEMINI_FLASH_MODEL,
                        contents=prompt,
                        config=genai_types.GenerateContentConfig(
                            response_mime_type="application/json",
                            max_output_tokens=1024,
                            temperature=0.3,
                        ),
                    )
                    raw = response.text or ""
                    if raw is None and response.candidates:
                        parts = response.candidates[0].content.parts
                        raw = "".join(p.text for p in parts if p.text)
                else:
                    raise
        else:
            from google.genai import types as genai_types
            response = gemini_client.models.generate_content(
                model=GEMINI_FLASH_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    max_output_tokens=1024,
                    temperature=0.3,
                ),
            )
            raw = response.text
            if raw is None and response.candidates:
                parts = response.candidates[0].content.parts
                raw = "".join(p.text for p in parts if p.text)
        raw = (raw or "").strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: extraire les scores avec regex si le JSON est malformé
            import re as _re
            scores = {}
            for dim in ["hook", "insight", "voice", "originality", "factuality", "readability"]:
                m = _re.search(rf'"?{dim}"?\s*:\s*(\d+)', raw, _re.IGNORECASE)
                if m:
                    scores[dim] = int(m.group(1))
            if not scores:
                raise
            result = {"scores": scores, "average": round(sum(scores.values()) / len(scores), 1) if scores else 0}
            # Extraire verdict et suggestion
            for field in ["verdict", "worst_dimension", "suggestion"]:
                m = _re.search(rf'"?{field}"?\s*:\s*"([^"]+)"', raw, _re.IGNORECASE)
                if m:
                    result[field] = m.group(1)
        avg = result.get("average", 0)
        if avg == 0 and result.get("scores"):
            scores = result["scores"]
            avg = round(sum(scores.values()) / len(scores), 1) if scores else 0
            result["average"] = avg

        result["passed"] = avg >= 6.0
        logger.info(f"🎭 Critic: avg={avg}/10 — verdict: {result.get('verdict', '?')}")
        return result

    except Exception as e:
        logger.warning(f"⚠️ Critic evaluation échoué: {e}")
        return None


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

    # Récupérer les insights de performance (quels posts marchent le mieux)
    performance_insights = get_performance_insights(db, limit=15) if db else "Aucune donnée de performance."

    # MÉCANISME 1: Leçons accumulées du critic
    critic_lessons = get_critic_lessons(db, limit=20) if db else ""

    # MÉCANISME 2: Guidelines de style basées sur les top posts
    style_guidelines = get_style_guidelines(db, limit=20) if db else ""

    # MÉCANISME 3: Sources qui génèrent le plus d'engagement
    source_insights = get_top_sources(db, limit=10) if db else ""

    # MÉCANISME 4: Patterns de hooks gagnants (A/B testing)
    hook_patterns = get_hook_patterns(db, limit=15) if db else ""

    # Batch variety check — vérifier la variété avant de générer
    batch_variety = _batch_variety_check(db, post_type, []) if db else {"passed": True, "issues": [], "recent_formats": []}
    if not batch_variety["passed"]:
        logger.warning(f"⚠️ Batch variety issues: {batch_variety['issues']}")
        # Si le format du jour est trop répétitif, forcer un autre format
        if batch_variety["recent_formats"]:
            all_formats = list(DAILY_FORMAT.values())
            used = set(batch_variety["recent_formats"][:3])
            available = [f for f in all_formats if f not in used]
            if available:
                old_type = post_type
                post_type = available[0]
                logger.info(f"🔄 Format changé de '{old_type}' → '{post_type}' pour éviter la répétition")

    if not claude_client and not gemini_client:
        logger.warning("⚠️ Ni Claude ni Gemini disponible, édito simulé")
        return _mock_edito(articles, trends_str, post_type)

    use_claude = claude_client is not None
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
                performance_insights=performance_insights,
                critic_lessons=critic_lessons,
                style_guidelines=style_guidelines,
                source_insights=source_insights,
                hook_patterns=hook_patterns,
            )

            # Utiliser Claude Opus 5 si disponible, sinon fallback Gemini
            if use_claude and claude_client:
                message = claude_client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=4096,
                    temperature=0.9,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw_text = message.content[0].text if message.content else ""
                logger.info(f"🧠 Post généré avec Claude Opus 5 (attempt {attempt+1})")
            else:
                from google.genai import types as genai_types
                response = gemini_client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        response_mime_type="application/json",
                        max_output_tokens=4096,
                        temperature=0.9,
                    ),
                )
                raw_text = response.text
                if raw_text is None and response.candidates:
                    parts = response.candidates[0].content.parts
                    raw_text = "".join(p.text for p in parts if p.text)
                logger.info(f"🧠 Post généré avec Gemini {GEMINI_MODEL} (attempt {attempt+1})")
            raw_text = (raw_text or "").strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            result = json.loads(raw_text)
            result["generated_at"] = datetime.now(timezone.utc).isoformat()
            result["article_count"] = len(articles)
            result["post_type"] = post_type
            result["status"] = "generated"
            result["generation_attempt"] = attempt + 1
            result["model_used"] = CLAUDE_MODEL if (use_claude and claude_client) else GEMINI_MODEL

            # Quality gate — bloquant : regénère si banned phrases ou problèmes
            qg = _quality_gate(result.get("post_text", ""))
            result["quality_gate"] = qg
            if not qg["passed"] and attempt < max_retries - 1:
                logger.warning(f"⚠️ Quality gate FAILED (attempt {attempt+1}): {qg['issues']} — regénération")
                post_history += f"\n⚠️ ATTENTION: La tentative précédente contenait ces problèmes: {', '.join(qg['issues'])}. Corrige-les absolument."
                continue

            # Dedup check (skip on last attempt to always return something)
            if db and attempt < max_retries - 1:
                dup = check_duplicate(db, result.get("post_text", ""))
                result["dedup"] = dup
                if dup["is_duplicate"]:
                    logger.warning(f"🔄 Duplicate détecté (sim={dup['max_similarity']}) — regénération attempt {attempt+2}")
                    post_history += f"\n⚠️ ATTENTION: La tentative précédente était trop similaire à un post existant (similarity={dup['max_similarity']}). Change complètement d'angle."
                    continue

            # Critic agent — Claude Sonnet 5 / Gemini Flash évalue la qualité (skip on last attempt)
            if attempt < max_retries - 1:
                critic = _critic_evaluate(result.get("post_text", ""), db)
                if critic:
                    result["critic"] = critic
                    # MÉCANISME 1: Stocker la leçon du critic pour l'accumuler
                    if db:
                        store_critic_lesson(db, critic, result.get("post_text", ""))
                    if not critic["passed"]:
                        logger.warning(f"🎭 Critic REJECTED (avg={critic['average']}/10) — worst: {critic.get('worst_dimension')} — regénération")
                        post_history += f"\n⚠️ ATTENTION: Le critique a noté ce post {critic['average']}/10. Dimension la plus faible: {critic.get('worst_dimension')}. Suggestion: {critic.get('suggestion')}. Améliore absolument."
                        continue

            # MÉCANISME 4: A/B testing des hooks — générer un 2e hook et garder le meilleur
            if db and result.get("hook") and attempt < max_retries - 1:
                try:
                    alt_hook = _generate_alt_hook(result.get("hook", ""), result.get("post_text", ""), articles, trends_str)
                    if alt_hook:
                        # Évaluer les 2 hooks avec le critic
                        hook_a_score = critic.get("average", 0) if critic else 0
                        hook_b_critic = _critic_evaluate(alt_hook + "\n" + result.get("post_text", "")[:500], db)
                        hook_b_score = hook_b_critic.get("average", 0) if hook_b_critic else 0

                        hooks = [result.get("hook", ""), alt_hook]
                        winner_idx = 0 if hook_a_score >= hook_b_score else 1
                        critic_scores = [
                            {"average": hook_a_score},
                            {"average": hook_b_score} if hook_b_critic else {}
                        ]

                        if winner_idx == 1:
                            result["hook"] = alt_hook
                            result["post_text"] = alt_hook + "\n\n" + result["post_text"].split("\n\n", 1)[1] if "\n\n" in result["post_text"] else alt_hook + "\n\n" + result["post_text"]
                            logger.info(f"🧪 A/B hook: hook B gagnant ({hook_b_score} vs {hook_a_score})")

                        # Stocker l'expérience
                        store_hook_experiment(db, hooks, winner_idx, critic_scores, result.get("post_id", ""))
                except Exception as ab_err:
                    logger.warning(f"⚠️ A/B hook échoué: {ab_err}")

            logger.info(f"📝 Édito LinkedIn [{post_type}] généré (attempt {attempt+1}, {len(result['post_text'])} chars, {result.get('word_count', '?')} mots)")
            return result

        except Exception as e:
            err_str = str(e)
            logger.error(f"❌ Erreur génération édito (attempt {attempt+1}): {e}")
            # Si Claude 429 (quota), fallback sur Gemini pour les retries suivants
            if "429" in err_str and use_claude and gemini_client:
                logger.warning(f"⏳ Claude 429 (quota) — fallback Gemini pour les retries suivants")
                use_claude = False
                if attempt < max_retries - 1:
                    continue
            elif "429" in err_str and attempt < max_retries - 1:
                # Attendre 65s avant retry (quota 1/min)
                import time
                logger.warning(f"⏳ Rate limit 429 — attente 65s avant retry...")
                time.sleep(65)
                continue
            if attempt < max_retries - 1:
                continue
            return _mock_edito(articles, trends_str, post_type)

    return _mock_edito(articles, trends_str, post_type)


INFOGRAPHIC_CONTENT_GENERATOR = """Tu es un expert en création d'infographics LinkedIn viraux sur la Data et l'IA.

À partir du post LinkedIn ci-dessous, génère le CONTENU STRUCTURÉ d'un infographic éducatif en JSON.

POST :
{post_text}

RÈGLES STRICTES:
- Le titre doit être court et percutant (5-7 mots max, en MAJUSCULES)
- Le sous-titre donne le contexte (10-15 mots max)
- Chaque section heading: 2-4 mots en MAJUSCULES
- Chaque section body: 10-15 mots max, factuel et concret (pas d'opinion)
- Le key_stat doit être un CHIFFRE précis extrait du post
- Évite le jargon technique, vise un public CDO/CTO
- Le texte doit être PARFAITEMENT orthographié en français

L'infographic doit capturer l'ESSENTIEL du post sous forme visuelle et didactique.
Pense au style "Save for later" de LinkedIn : un visuel que les gens bookmarkent.

Réponds en JSON strict :
{{
  "title": "TITRE COURT EN MAJUSCULES",
  "subtitle": "Sous-titre contextuel",
  "sections": [
    {{
      "number": "1",
      "heading": "TITRE COURT",
      "body": "Texte factuel concis (10-15 mots max)"
    }}
  ],
  "key_stat": "Chiffre clé extrait du post",
  "color_theme": "purple|blue|green|orange",
  "author": "Renaud Secq"
}}

Génère entre 4 et 6 sections. Chaque section doit apporter une information concrète, pas du blabla."""


def _generate_image_prompt(post_text: str, post_type: str, db=None) -> str:
    """Utilise Gemini Pro pour générer le contenu d'un infographic, puis crée le prompt Imagen."""
    try:
        # Récupérer les leçons visuelles passées
        visual_feedback = get_visual_lessons(db, limit=15) if db else ""

        # Étape 1 : Gemini génère le contenu structuré de l'infographic
        content_prompt = INFOGRAPHIC_CONTENT_GENERATOR.format(post_text=post_text[:1000])
        if visual_feedback:
            content_prompt += f"\n\n{visual_feedback}"
        content_response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=content_prompt,
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

        # Étape 2 : Prompt structuré pour Gemini 3 Pro Image
        # Instructions ultra-précises pour un rendu professionnel
        prompt = (
            f"Create a vertical infographic image (1080x1440 pixels, 3:4 portrait ratio).\n\n"
            f"LAYOUT (top to bottom):\n"
            f"1. HEADER ZONE (top 15% of image):\n"
            f"   - Large bold title in {accent} color, font size ~48px, centered\n"
            f"   - Title: \"{title}\"\n"
            f"   - Subtitle below in dark gray (#374151), font size ~20px, centered\n"
            f"   - Subtitle: \"{subtitle}\"\n"
            f"   - Thin horizontal divider line in {accent} below subtitle\n\n"
            f"2. CONTENT ZONE (middle 70% of image):\n"
            f"   - {len(sections)} numbered sections stacked vertically with equal spacing\n"
            f"   - Each section has:\n"
            f"     * Left: a circular badge with the section number, {accent} background, white text, ~40px diameter\n"
            f"     * Right of badge: section heading in bold dark text (#1F2937), ~18px\n"
            f"     * Below heading: body text in medium gray (#6B7280), ~14px, max 2 lines\n"
            f"   - Sections content:\n{sections_lines}\n\n"
        )
        if key_stat:
            prompt += (
                f"3. KEY STAT ZONE (below sections):\n"
                f"   - A highlighted box with light {accent} background (10% opacity)\n"
                f"   - Key statistic in large bold {accent} text, centered\n"
                f"   - Stat: \"{key_stat}\"\n\n"
            )
        prompt += (
            f"4. FOOTER ZONE (bottom 5% of image):\n"
            f"   - Small text: \"{data.get('author', 'Renaud Secq')} — Consultant IA & Data\"\n"
            f"   - Dark gray (#9CA3AF), ~12px, centered\n\n"
            f"VISUAL SPECIFICATIONS:\n"
            f"   - Background: pure white (#FFFFFF)\n"
            f"   - Accent color: {accent}\n"
            f"   - Typography: Inter or Helvetica Neue, clean sans-serif\n"
            f"   - All text MUST be in French, perfectly spelled, no typos\n"
            f"   - All text MUST be fully readable, no overlap, no truncation\n"
            f"   - Use generous whitespace between sections (at least 20px padding)\n"
            f"   - Style: professional, minimalist, corporate — like a McKinsey or BCG infographic\n"
            f"   - NO photographs, NO gradients, NO 3D effects, NO shadows\n"
            f"   - Flat design only with clean geometric shapes\n"
            f"   - Vertical connector line between section badges in light gray (#E5E7EB)\n"
        )
        if visual_feedback:
            prompt += f"\nCORRECTIONS FROM PREVIOUS FEEDBACK:\n{visual_feedback}\n"
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


VISUAL_CRITIC_PROMPT = """Tu es un critique visuel d'infographics LinkedIn. Analyse cette image et évalue sa qualité.

Réponds UNIQUEMENT avec un JSON valide, sans texte avant ou après, dans ce format exact:
{"readability": 8, "spelling": 7, "layout": 8, "visual_appeal": 7, "text_accuracy": 9, "average": 7.8, "issues": ["problème 1", "problème 2"], "verdict": "1-2 phrases", "passed": true}

Critères (chaque dimension notée de 0 à 10):
- readability: le texte est-il lisible ? Pas de chevauchement, taille suffisante ?
- spelling: y a-t-il des fautes d'orthographe dans le texte de l'image ?
- layout: la structure est-elle claire ? Alignement, espacement, hiérarchie visuelle ?
- visual_appeal: est-ce professionnel et esthétique ? Digne d'un partage LinkedIn ?
- text_accuracy: le texte correspond-il au contenu du post ? Pas d'hallucination ?
- average: moyenne des 5 scores
- passed: true si average >= 7, false sinon"""


def _visual_critic(image_bytes: bytes, post_text: str) -> dict | None:
    """Évalue la qualité d'un infographic via Gemini (vision).

    Returns: {"readability": int, "spelling": int, "layout": int,
              "visual_appeal": int, "text_accuracy": int, "average": float,
              "issues": list, "verdict": str, "passed": bool} ou None.
    """
    if not gemini_client:
        return None
    try:
        import base64
        from google.genai import types as genai_types

        image_b64 = base64.b64encode(image_bytes).decode()

        prompt = VISUAL_CRITIC_PROMPT + f"\n\nPOST ORIGINAL (pour vérifier la cohérence du texte):\n{post_text[:500]}"

        response = gemini_client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=[
                genai_types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                prompt,
            ],
            config=genai_types.GenerateContentConfig(
                max_output_tokens=1024,
                temperature=0.3,
            ),
        )

        raw = response.text or ""
        if raw is None and response.candidates:
            parts = response.candidates[0].content.parts
            raw = "".join(p.text for p in parts if p.text)

        raw = (raw or "").strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: extraire les scores avec regex
            result = {}
            for dim in ["readability", "spelling", "layout", "visual_appeal", "text_accuracy"]:
                m = re.search(rf'"{dim}"\s*:\s*(\d+(?:\.\d+)?)', raw)
                if m:
                    result[dim] = float(m.group(1))
            m_avg = re.search(r'"average"\s*:\s*(\d+(?:\.\d+)?)', raw)
            if m_avg:
                result["average"] = float(m_avg.group(1))
            m_passed = re.search(r'"passed"\s*:\s*(true|false)', raw, re.I)
            if m_passed:
                result["passed"] = m_passed.group(1).lower() == "true"
            if not result:
                logger.warning(f"⚠️ Visual critic JSON parse échoué: {raw[:200]}")
                return None

        # Calculer l'average si manquant
        if "average" not in result:
            scores = [result.get(d, 0) for d in ["readability", "spelling", "layout", "visual_appeal", "text_accuracy"] if d in result]
            result["average"] = round(sum(scores) / len(scores), 1) if scores else 0
        else:
            result["average"] = round(float(result["average"]), 1)
        result["passed"] = result.get("average", 0) >= 7
        logger.info(f"👁️ Visual critic: avg={result['average']}/10, passed={result['passed']}, issues={result.get('issues', [])[:3]}")
        return result
    except Exception as e:
        logger.warning(f"⚠️ Visual critic échoué: {e}")
        return None


FORMAT_SELECTOR_PROMPT = """Tu es un expert en design de contenu LinkedIn. Analyse ce post et choisis le format visuel le plus adapté.

POST :
{post_text}

Formats disponibles:
- infographic: sections numérotées structurées. Idéal pour: listes, étapes, points multiples, résumé structuré.
- quote_card: citation percutante en grand format. Idéal pour: une phrase forte, une insight mémorable, une citation d'expert.
- comparison: tableau comparatif 2 colonnes. Idéal pour: comparer 2 outils/approches/concepts, avant/après, pour/contre.
- stat_highlight: un chiffre choc en très grand format. Idéal pour: un statistique marquante, un chiffre surprenant, une donnée clé.

Choisis le format qui mettra LE MIEUX en valeur le contenu de ce post.

Réponds en JSON strict:
{{"format": "infographic|quote_card|comparison|stat_highlight", "reason": "1 phrase courte expliquant le choix"}}"""


def _select_visual_format(post_text: str, post_type: str, db=None) -> str:
    """Sélectionne le format visuel le plus adapté au contenu du post.

    1. Gemini analyse le post et recommande un format
    2. Évite les 2 derniers formats utilisés (rotation anti-monotonie)
    3. Fallback sur post_type si l'analyse échoue
    """
    # Récupérer l'historique récent pour la rotation
    recent_formats = []
    try:
        if db:
            docs = (
                db.collection("visual_lessons")
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(5)
                .stream()
            )
            for doc in docs:
                fmt = doc.to_dict().get("visual_format")
                if fmt:
                    recent_formats.append(fmt)
    except Exception:
        pass

    # Étape 1 : Gemini analyse le contenu et recommande un format
    recommended = None
    reason = ""
    try:
        prompt = FORMAT_SELECTOR_PROMPT.format(post_text=post_text[:1500])
        response = gemini_client.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=prompt,
        )
        raw = (response.text or "").strip()
        if raw is None and response.candidates:
            parts = response.candidates[0].content.parts
            raw = "".join(p.text for p in parts if p.text)
        raw = (raw or "").strip()
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()
        data = json.loads(raw)
        recommended = data.get("format", "").strip().lower()
        reason = data.get("reason", "")
        valid_formats = ["infographic", "quote_card", "comparison", "stat_highlight"]
        if recommended not in valid_formats:
            recommended = None
    except Exception as e:
        logger.warning(f"⚠️ Format selector IA échoué: {e}")

    # Étape 2 : Si le format recommandé est dans les 2 derniers utilisés, essayer le 2e choix
    if recommended and recommended in recent_formats[:2]:
        logger.info(f"🎨 Format {recommended} recommandé mais utilisé récemment, rotation...")
        # Garder recommended comme 2e choix, prendre un format différent
        rotation_order = ["infographic", "comparison", "stat_highlight", "quote_card"]
        for fmt in rotation_order:
            if fmt != recommended and fmt not in recent_formats[:2]:
                logger.info(f"🎨 Format visuel sélectionné: {fmt} (rotation, recommandé={recommended}, reason={reason})")
                return fmt

    if recommended:
        logger.info(f"🎨 Format visuel sélectionné: {recommended} (IA, reason={reason})")
        return recommended

    # Fallback : rotation basée sur post_type
    if post_type == "citation_inspirante":
        preferred = ["quote_card", "stat_highlight", "infographic"]
    elif post_type in ("analyse_profonde", "signal_faible"):
        preferred = ["infographic", "comparison", "stat_highlight"]
    elif post_type == "revue_hebdo":
        preferred = ["infographic", "comparison"]
    elif post_type == "ai_governance":
        preferred = ["infographic", "comparison", "stat_highlight"]
    elif post_type == "tutoriel_rapide":
        preferred = ["comparison", "infographic", "stat_highlight"]
    else:
        preferred = ["infographic", "quote_card", "comparison", "stat_highlight"]

    for fmt in preferred:
        if fmt not in recent_formats[:2]:
            logger.info(f"🎨 Format visuel fallback: {fmt} (post_type={post_type}, recent={recent_formats[:3]})")
            return fmt

    logger.info(f"🎨 Format visuel fallback: {preferred[0]} (post_type={post_type})")
    return preferred[0]


QUOTE_CARD_GENERATOR = """Tu es un expert en création de quote cards LinkedIn virales sur la Data et l'IA.

À partir du post LinkedIn ci-dessous, extrait la phrase la plus percutante et génère le contenu d'une quote card en JSON.

POST :
{post_text}

RÈGLES:
- La citation doit être une phrase DU post (pas inventée)
- Maximum 15 mots, idéalement 8-12 mots
- Doit être une insight, pas une description
- Le contexte donne la source ou l'auteur référencé

Réponds en JSON strict :
{{
  "quote": "La phrase percutante extraite du post",
  "attribution": "Source ou auteur mentionné",
  "context": "Contexte en 5-8 mots",
  "color_theme": "purple|blue|green|orange"
}}"""


COMPARISON_GENERATOR = """Tu es un expert en création de tableaux comparatifs LinkedIn sur la Data et l'IA.

À partir du post LinkedIn ci-dessous, génère un tableau comparatif en JSON.

POST :
{post_text}

RÈGLES:
- Identifie 2 concepts/tools/approches comparés dans le post
- 3-4 critères de comparaison max
- Chaque cellule: 3-6 mots max
- Factuel, pas d'opinion

Réponds en JSON strict :
{{
  "title": "TITRE COMPARATIF COURT",
  "left_label": "Concept A",
  "right_label": "Concept B",
  "rows": [
    {{"criterion": "CRITÈRE", "left": "valeur A", "right": "valeur B"}}
  ],
  "color_theme": "purple|blue|green|orange"
}}"""


STAT_HIGHLIGHT_GENERATOR = """Tu es un expert en création de visuels "chiffre choc" pour LinkedIn.

À partir du post LinkedIn ci-dessous, extrait LE chiffre le plus marquant et génère le contenu d'un stat highlight en JSON.

POST :
{post_text}

RÈGLES:
- Le chiffre doit être extrait du post (pas inventé)
- Le contexte explique le chiffre en 8-12 mots
- La source doit être mentionnée

Réponds en JSON strict :
{{
  "big_number": "13x",
  "context": "Baisse du coût de l'IA en 4 mois",
  "source": "Latent Space",
  "takeaway": "L'IA devient accessible à tous les budgets",
  "color_theme": "purple|blue|green|orange"
}}"""


def _generate_quote_card_prompt(post_text: str, db=None) -> str:
    """Génère un prompt pour une quote card."""
    try:
        visual_feedback = get_visual_lessons(db, limit=15) if db else ""
        content_prompt = QUOTE_CARD_GENERATOR.format(post_text=post_text[:1000])
        if visual_feedback:
            content_prompt += f"\n\n{visual_feedback}"
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=content_prompt,
        )
        raw = response.text or ""
        if raw is None and response.candidates:
            parts = response.candidates[0].content.parts
            raw = "".join(p.text for p in parts if p.text)
        raw = (raw or "").strip()
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()

        import json
        data = json.loads(raw)

        quote = data.get("quote", "")
        attribution = data.get("attribution", "")
        context = data.get("context", "")
        color = data.get("color_theme", "purple")

        color_map = {
            "purple": "purple and violet (#6B46C1)",
            "blue": "electric blue (#2563EB)",
            "green": "emerald green (#059669)",
            "orange": "deep orange (#EA580C)",
        }
        accent = color_map.get(color, color_map["purple"])

        prompt = (
            f"Create a vertical quote card image (1080x1440 pixels, 3:4 portrait ratio).\n\n"
            f"LAYOUT:\n"
            f"1. Large decorative quotation mark at top in {accent}, ~120px, semi-transparent\n"
            f"2. CENTER: The quote in large bold text, dark color (#1F2937), ~36px, centered, max 3 lines:\n"
            f"   \"{quote}\"\n"
            f"3. Below quote: thin horizontal line in {accent}\n"
            f"4. Attribution in medium gray (#6B7280), ~18px:\n"
            f"   — {attribution}\n"
            f"5. Context in smaller gray (#9CA3AF), ~14px:\n"
            f"   {context}\n"
            f"6. Bottom: \"Renaud Secq — Consultant IA & Data\" in small gray text\n\n"
            f"VISUAL SPECIFICATIONS:\n"
            f"   - Background: very light gray (#F9FAFB) or white\n"
            f"   - Accent: {accent}\n"
            f"   - Typography: Inter or Helvetica Neue\n"
            f"   - All text in French, perfectly spelled\n"
            f"   - Generous whitespace, minimalist\n"
            f"   - NO photographs, NO gradients, NO 3D\n"
            f"   - Flat design, corporate style\n"
        )
        if visual_feedback:
            prompt += f"\nCORRECTIONS:\n{visual_feedback}\n"
        logger.info(f"📊 Quote card: \"{quote[:50]}...\"")
        return prompt
    except Exception as e:
        logger.warning(f"⚠️ Fallback quote card: {e}")
        hook = post_text.split("\n")[0][:80]
        return (
            f"Create a vertical quote card (1080x1440, 3:4 ratio) with white background, "
            f"large purple quotation mark, centered quote \"{hook[:60]}\" in bold dark text, "
            f"attribution below, minimalist flat design, French text."
        )


def _generate_comparison_prompt(post_text: str, db=None) -> str:
    """Génère un prompt pour un tableau comparatif."""
    try:
        visual_feedback = get_visual_lessons(db, limit=15) if db else ""
        content_prompt = COMPARISON_GENERATOR.format(post_text=post_text[:1000])
        if visual_feedback:
            content_prompt += f"\n\n{visual_feedback}"
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=content_prompt,
        )
        raw = response.text or ""
        if raw is None and response.candidates:
            parts = response.candidates[0].content.parts
            raw = "".join(p.text for p in parts if p.text)
        raw = (raw or "").strip()
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()

        import json
        data = json.loads(raw)

        title = data.get("title", "COMPARATIF")
        left_label = data.get("left_label", "A")
        right_label = data.get("right_label", "B")
        rows = data.get("rows", [])[:4]
        color = data.get("color_theme", "purple")

        color_map = {
            "purple": "purple (#6B46C1)",
            "blue": "blue (#2563EB)",
            "green": "green (#059669)",
            "orange": "orange (#EA580C)",
        }
        accent = color_map.get(color, color_map["purple"])

        rows_text = "\n".join(
            f"   {r['criterion']} | {r['left']} | {r['right']}"
            for r in rows
        )

        prompt = (
            f"Create a vertical comparison table image (1080x1440 pixels, 3:4 portrait ratio).\n\n"
            f"LAYOUT:\n"
            f"1. HEADER: Title \"{title}\" in bold {accent}, ~36px, centered\n"
            f"2. Two-column table header:\n"
            f"   Left column header: \"{left_label}\" in {accent} background, white text\n"
            f"   Right column header: \"{right_label}\" in dark gray (#374151) background, white text\n"
            f"3. Table rows (alternating white and light gray #F3F4F6 backgrounds):\n{rows_text}\n"
            f"   Each row: criterion label on far left in bold, then two values\n"
            f"4. Bottom: \"Renaud Secq — Consultant IA & Data\" in small gray text\n\n"
            f"VISUAL SPECIFICATIONS:\n"
            f"   - Background: white (#FFFFFF)\n"
            f"   - Accent: {accent}\n"
            f"   - Typography: Inter or Helvetica Neue\n"
            f"   - All text in French, perfectly spelled\n"
            f"   - Clean table borders, aligned columns\n"
            f"   - NO photographs, NO gradients, NO 3D\n"
            f"   - Flat design, corporate style\n"
        )
        if visual_feedback:
            prompt += f"\nCORRECTIONS:\n{visual_feedback}\n"
        logger.info(f"📊 Comparison: {title} | {len(rows)} rows")
        return prompt
    except Exception as e:
        logger.warning(f"⚠️ Fallback comparison: {e}")
        return (
            f"Create a vertical comparison table (1080x1440, 3:4 ratio) with white background, "
            f"purple header, two-column table with 3-4 rows, clean borders, "
            f"French text, flat corporate design."
        )


def _generate_stat_highlight_prompt(post_text: str, db=None) -> str:
    """Génère un prompt pour un stat highlight (chiffre choc)."""
    try:
        visual_feedback = get_visual_lessons(db, limit=15) if db else ""
        content_prompt = STAT_HIGHLIGHT_GENERATOR.format(post_text=post_text[:1000])
        if visual_feedback:
            content_prompt += f"\n\n{visual_feedback}"
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=content_prompt,
        )
        raw = response.text or ""
        if raw is None and response.candidates:
            parts = response.candidates[0].content.parts
            raw = "".join(p.text for p in parts if p.text)
        raw = (raw or "").strip()
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()

        import json
        data = json.loads(raw)

        big_number = data.get("big_number", "")
        context = data.get("context", "")
        source = data.get("source", "")
        takeaway = data.get("takeaway", "")
        color = data.get("color_theme", "purple")

        color_map = {
            "purple": "purple (#6B46C1)",
            "blue": "blue (#2563EB)",
            "green": "green (#059669)",
            "orange": "orange (#EA580C)",
        }
        accent = color_map.get(color, color_map["purple"])

        prompt = (
            f"Create a vertical stat highlight image (1080x1440 pixels, 3:4 portrait ratio).\n\n"
            f"LAYOUT:\n"
            f"1. TOP THIRD: The big number \"{big_number}\" in HUGE bold {accent} text, ~180px, centered\n"
            f"2. MIDDLE: Context line \"{context}\" in dark gray (#1F2937), ~24px, centered, max 2 lines\n"
            f"3. Below context: thin horizontal line in {accent}\n"
            f"4. Takeaway: \"{takeaway}\" in medium gray (#6B7280), ~18px, centered\n"
            f"5. Source: \"Source: {source}\" in small gray (#9CA3AF), ~14px\n"
            f"6. Bottom: \"Renaud Secq — Consultant IA & Data\" in small gray text\n\n"
            f"VISUAL SPECIFICATIONS:\n"
            f"   - Background: white (#FFFFFF) with subtle {accent} geometric accent shapes in corners\n"
            f"   - The big number is the FOCAL POINT — it should dominate the image\n"
            f"   - Typography: Inter or Helvetica Neue\n"
            f"   - All text in French, perfectly spelled\n"
            f"   - Generous whitespace\n"
            f"   - NO photographs, NO gradients, NO 3D\n"
            f"   - Flat design, corporate style\n"
        )
        if visual_feedback:
            prompt += f"\nCORRECTIONS:\n{visual_feedback}\n"
        logger.info(f"📊 Stat highlight: {big_number} | {context[:50]}")
        return prompt
    except Exception as e:
        logger.warning(f"⚠️ Fallback stat highlight: {e}")
        return (
            f"Create a vertical stat highlight (1080x1440, 3:4 ratio) with white background, "
            f"one huge purple number in center, context text below, minimalist flat design, "
            f"French text, corporate style."
        )


def generate_visual(post_text: str, post_type: str, db=None) -> bytes | None:
    """Génère un visuel IA avec critique visuelle et régénération si nécessaire.

    Pipeline:
    1. Sélectionne le format visuel (infographic, quote_card, comparison, stat_highlight)
    2. Gemini génère le contenu structuré + le prompt adapté au format
    3. Gemini 3 Pro Image génère l'image
    4. Visual critic évalue l'image (readability, spelling, layout)
    5. Si critic < 7/10, régénération (max 2 tentatives)
    6. Leçon visuelle stockée en Firestore pour amélioration continue
    """
    if not gemini_client:
        logger.warning("⚠️ GenAI non dispo, pas de visuel")
        return None

    # Sélectionner le format visuel adapté au contenu
    visual_format = _select_visual_format(post_text, post_type, db=db)
    logger.info(f"🎨 Format visuel: {visual_format}")

    max_visual_attempts = 2
    for v_attempt in range(max_visual_attempts):
        # Étape 1 : Générer le prompt selon le format sélectionné
        if visual_format == "quote_card":
            image_prompt = _generate_quote_card_prompt(post_text, db=db)
        elif visual_format == "comparison":
            image_prompt = _generate_comparison_prompt(post_text, db=db)
        elif visual_format == "stat_highlight":
            image_prompt = _generate_stat_highlight_prompt(post_text, db=db)
        else:
            image_prompt = _generate_image_prompt(post_text, post_type, db=db)
        if v_attempt > 0:
            # Ajouter les feedbacks du critic au prompt pour la régénération
            image_prompt += f"\n\nCORRECTIONS À APPLIQUER: {visual_issues_feedback}"
        logger.info(f"🖼️ Prompt {visual_format} (attempt {v_attempt+1}): {image_prompt[:120]}...")

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

            image_bytes = None
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    break

            if not image_bytes:
                logger.warning(f"⚠️ Aucune image dans la réponse (attempt {v_attempt+1})")
                if v_attempt < max_visual_attempts - 1:
                    continue
                return None

            logger.info(f"🎨 {visual_format} généré ({len(image_bytes)} bytes, attempt {v_attempt+1})")

            # Étape 2 : Visual critic
            critic = _visual_critic(image_bytes, post_text)
            if critic:
                # Stocker la leçon visuelle en Firestore
                if db:
                    try:
                        db.collection("visual_lessons").add({
                            "scores": {k: v for k, v in critic.items() if k in ["readability", "spelling", "layout", "visual_appeal", "text_accuracy"]},
                            "average": critic.get("average", 0),
                            "issues": critic.get("issues", []),
                            "verdict": critic.get("verdict", ""),
                            "passed": critic.get("passed", False),
                            "attempt": v_attempt + 1,
                            "visual_format": visual_format,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        })
                        logger.info(f"👁️ Leçon visuelle stockée (avg={critic.get('average', 0)})")
                    except Exception:
                        pass

                if critic.get("passed", False):
                    logger.info(f"✅ Visual critic PASSED — image validée")
                    return image_bytes
                else:
                    logger.warning(f"⚠️ Visual critic REJECTED (avg={critic.get('average', 0)}) — issues: {critic.get('issues', [])}")
                    # Préparer le feedback pour la régénération
                    visual_issues_feedback = "; ".join(critic.get("issues", []))
                    if v_attempt < max_visual_attempts - 1:
                        continue
                    # Dernier attempt — garder l'image même si imparfaite
                    logger.warning("⚠️ Dernier attempt visuel — publication malgré les issues")
                    return image_bytes

            # Pas de critic → garder l'image
            return image_bytes

        except Exception as e:
            logger.error(f"❌ Erreur génération visuel (attempt {v_attempt+1}): {e}")
            if v_attempt < max_visual_attempts - 1:
                continue
            return None

    return None


def _upload_image_to_linkedin(image_bytes: bytes) -> str | None:
    """Upload une image sur LinkedIn via la nouvelle API Images et retourne l'image URN."""
    if not LINKEDIN_ACCESS_TOKEN or not LINKEDIN_PERSON_URN:
        return None

    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "LinkedIn-Version": "202607",
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
            "LinkedIn-Version": "202607",
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
