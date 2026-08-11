"""Configuration des sources RSS et paramètres de l'application."""
import os

# Projet Google Cloud
GCP_PROJECT = os.getenv("GCP_PROJECT", "mia-chatbot-veille")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")

# Gemini API Key (Google AI Studio - gratuit)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Scoring minimum pour garder un article
MIN_SCORE = 7.0

# Scoring minimum pour générer un post LinkedIn
MIN_SCORE_LINKEDIN = 8.0

# Nombre max d'articles par semaine
MAX_ARTICLES_PER_WEEK = 15

# Nombre de jours max pour un article (filtre fraîcheur)
MAX_ARTICLE_AGE_DAYS = 7

# Profil expert
EXPERT_PROFILE = {
    "name": "Renaud Secq",
    "title": "Consultant Freelance IA & Data — Builder & Strategist",
    "expertise": [
        "Mise en place de solutions IA end-to-end (Vertex AI, AWS, Databricks, agents IA)",
        "Architecture data & plateformes cloud (Snowflake, BigQuery, data pipelines)",
        "Data & AI Governance (Collibra, catalogues, qualité, EU AI Act)",
        "Management d'équipes tech & data, pilotage de programmes",
        "Stratégie IA en entreprise (ROI, adoption, change management)",
    ],
    "tone": "Expert terrain qui build ET qui gouverne. Parle autant code que stratégie. Avis tranchés, pas de bullshit. Focus: AI Governance, Data Governance, Vibe Coding.",
    "linkedin_url": "https://www.linkedin.com/in/renaud-secq-5593832a/",
    "photo_url": "photo-000.jpg"
}

# Sources RSS organisées par catégorie
# PRINCIPE : qualité > quantité. Sources premium + accessibles > blogs génériques
RSS_SOURCES = {
    "ia_pratique": {
        "label": "IA en pratique (experts terrain)",
        "emoji": "🤖",
        "color": "#6c63ff",
        "sources": [
            # Experts premium — contenu original, pas du relayage
            {"name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/", "weight": 1.5},
            {"name": "Latent Space", "url": "https://www.latent.space/feed", "weight": 1.5},
            {"name": "Chip Huyen", "url": "https://huyenchip.com/feed.xml", "weight": 1.4},
            {"name": "Eugene Yan", "url": "https://eugeneyan.com/rss/", "weight": 1.4},
            {"name": "Hamel Husain", "url": "https://hamel.dev/index.xml", "weight": 1.4},
            {"name": "AI Snake Oil", "url": "https://www.aisnakeoil.com/feed", "weight": 1.3},
            # Sources accessibles — vulgarisation pour néophyte éclairé
            {"name": "Last Week in AI", "url": "https://lastweekin.ai/feed", "weight": 1.2},
            # Substack — experts IA accessibles
            {"name": "The Pragmatic Engineer (Substack)", "url": "https://newsletter.pragmaticengineer.com/feed", "weight": 1.3},
            {"name": "One Useful Thing (Substack)", "url": "https://www.oneusefulthing.org/feed", "weight": 1.3},
            # Nouveaux — agents IA & strategy
            {"name": "LangChain Blog", "url": "https://blog.langchain.dev/rss/", "weight": 1.4},
            {"name": "Google Research Blog", "url": "https://research.google/blog/rss/", "weight": 1.3},
            # Agents IA — sources spécialisées agentic
            {"name": "Inside AI Agents (Substack)", "url": "https://insideaiagents.substack.com/feed", "weight": 1.4},
            # Medium — tags IA, weight réduit pour ne pas noyer les sources premium
            {"name": "Medium #artificial-intelligence", "url": "https://medium.com/feed/tag/artificial-intelligence", "weight": 0.8},
            {"name": "Medium #large-language-models", "url": "https://medium.com/feed/tag/large-language-models", "weight": 0.8},
            {"name": "Medium #ai-agents", "url": "https://medium.com/feed/tag/ai-agents", "weight": 0.8},
            # Medium publications premium — éditorialisées, meilleure qualité que les tags
            {"name": "Towards Data Science", "url": "https://towardsdatascience.com/feed", "weight": 1.1},
            {"name": "Towards AI", "url": "https://pub.towardsai.net/feed", "weight": 1.1},
            {"name": "KDnuggets", "url": "https://www.kdnuggets.com/feed", "weight": 1.1},
            {"name": "MarkTechPost AI", "url": "https://www.marktechpost.com/feed", "weight": 1.0},
            # Google News — couvre des centaines de sources en une requête
            {"name": "Google News: AI agents enterprise", "url": "https://news.google.com/rss/search?q=AI+agents+enterprise+deployment&hl=en&gl=US&ceid=US:en", "weight": 1.0},
            {"name": "Google News: LLM production (FR)", "url": "https://news.google.com/rss/search?q=IA+agents+entreprise&hl=fr&gl=FR&ceid=FR:fr", "weight": 1.0},
        ]
    },
    "infra_mlops": {
        "label": "Infra, MLOps & Plateformes",
        "emoji": "⚙️",
        "color": "#00d4ff",
        "sources": [
            # Blogs vendor premium — annonces produit, benchmarks
            {"name": "Google Cloud AI", "url": "https://cloudblog.withgoogle.com/products/ai-machine-learning/rss/", "weight": 1.3},
            {"name": "Databricks Blog", "url": "https://www.databricks.com/feed", "weight": 1.2},
            {"name": "Snowflake Blog", "url": "https://www.snowflake.com/feed/", "weight": 1.2},
            {"name": "DeepMind Blog", "url": "https://deepmind.google/blog/rss.xml", "weight": 1.3},
            # Media tech — accessible mais crédible
            {"name": "InfoQ AI/ML", "url": "https://feed.infoq.com/ai-ml-data-eng/", "weight": 1.2},
            {"name": "W&B Blog", "url": "https://wandb.ai/fully-connected/rss.xml", "weight": 1.2},
            {"name": "HN Front Page AI", "url": "https://hnrss.org/newest?points=100&q=AI+OR+LLM+OR+agent+OR+MLOps", "weight": 1.3},
            # Medium — MLOps & data engineering, weight réduit
            {"name": "Medium #mlops", "url": "https://medium.com/feed/tag/mlops", "weight": 0.8},
            {"name": "Medium #data-engineering", "url": "https://medium.com/feed/tag/data-engineering", "weight": 0.8},
            {"name": "Medium #machine-learning-engineering", "url": "https://medium.com/feed/tag/machine-learning-engineering", "weight": 0.8},
            # Medium publications premium
            {"name": "Analytics Vidhya", "url": "https://www.analyticsvidhya.com/feed/", "weight": 1.0},
            # Google News — MLOps & AI infra
            {"name": "Google News: MLOps AI infrastructure", "url": "https://news.google.com/rss/search?q=MLOps+AI+infrastructure+platform&hl=en&gl=US&ceid=US:en", "weight": 1.0},
        ]
    },
    "governance_regulation": {
        "label": "Gouvernance & Régulation IA",
        "emoji": "⚖️",
        "color": "#c8ff00",
        "sources": [
            # Sources officielles — crédibilité maximale
            {"name": "EU AI Act", "url": "https://artificialintelligenceact.eu/feed/", "weight": 1.4},
            {"name": "CNIL", "url": "https://www.cnil.fr/fr/rss.xml", "weight": 1.3},
            {"name": "Stanford HAI", "url": "https://hai.stanford.edu/news/rss.xml", "weight": 1.2},
            # Media accessible — grand public tech
            {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/", "weight": 1.3},
            {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "weight": 1.1},
            # Substack — governance experts accessibles
            {"name": "AI Policy Brief (Substack)", "url": "https://aipolicybrief.substack.com/feed", "weight": 1.2},
            {"name": "AI Governance Today (Substack)", "url": "https://aigovernancetoday.substack.com/feed", "weight": 1.3},
            {"name": "AI Governance Brief", "url": "https://aigovernancebrief.org/feed/", "weight": 1.3},
            {"name": "AI Governance Daily", "url": "https://burns-media.com/ai-governance/feed/", "weight": 1.2},
            # Consulting — perspectives business accessibles
            # Medium — governance & ethics, weight réduit
            {"name": "Medium #ai-ethics", "url": "https://medium.com/feed/tag/ai-ethics", "weight": 0.8},
            {"name": "Medium #ai-regulation", "url": "https://medium.com/feed/tag/ai-regulation", "weight": 0.8},
            {"name": "Medium #responsible-ai", "url": "https://medium.com/feed/tag/responsible-ai", "weight": 0.8},
            # Google News — AI governance & regulation
            {"name": "Google News: AI regulation governance", "url": "https://news.google.com/rss/search?q=AI+regulation+governance+enterprise&hl=en&gl=US&ceid=US:en", "weight": 1.0},
            {"name": "Google News: IA régulation (FR)", "url": "https://news.google.com/rss/search?q=IA+r%C3%A9gulation+gouvernance+entreprise&hl=fr&gl=FR&ceid=FR:fr", "weight": 1.0},
        ]
    },
    "vibe_coding": {
        "label": "Vibe Coding & Dev assisté IA",
        "emoji": "⚡",
        "color": "#ff9f43",
        "sources": [
            # Sources premium — annonces officielles
            {"name": "Anthropic Blog (mirror)", "url": "https://raw.githubusercontent.com/taobojlen/anthropic-rss-feed/main/anthropic_news_rss.xml", "weight": 1.5},
            {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "weight": 1.3},
            {"name": "GitHub Blog", "url": "https://github.blog/feed/", "weight": 1.3},
            # HN — signaux de la communauté
            {"name": "HN Vibe Coding", "url": "https://hnrss.org/newest?points=50&q=vibe+coding+OR+cursor+OR+copilot+OR+claude+code+OR+windsurf", "weight": 1.3},
            # Vibe coding — ressources spécialisées
            {"name": "Windsurf Blog", "url": "https://windsurf.com/feed.xml", "weight": 1.3},
            # Medium — seulement les tags les plus pertinents
            {"name": "Medium #ai-coding", "url": "https://medium.com/feed/tag/ai-coding", "weight": 0.8},
            {"name": "Medium #cursor", "url": "https://medium.com/feed/tag/cursor", "weight": 0.8},
            {"name": "Medium #chatgpt", "url": "https://medium.com/feed/tag/chatgpt", "weight": 0.7},
            {"name": "Medium #copilot", "url": "https://medium.com/feed/tag/copilot", "weight": 0.8},
            # Medium publications premium
            {"name": "Better Programming", "url": "https://medium.com/feed/better-programming", "weight": 1.0},
            # Google News — vibe coding & AI dev tools
            {"name": "Google News: AI coding tools", "url": "https://news.google.com/rss/search?q=AI+coding+tools+cursor+copilot&hl=en&gl=US&ceid=US:en", "weight": 1.0},
        ]
    },
    "data_governance": {
        "label": "Data Governance & Quality",
        "emoji": "📊",
        "color": "#2ecc71",
        "sources": [
            # Experts — practitioners, pas de marketing
            {"name": "Dataversity", "url": "https://www.dataversity.net/feed/", "weight": 1.2},
            {"name": "The Data Governor", "url": "https://thedatagovernor.com/feed/", "weight": 1.4},
            {"name": "LightsOnData", "url": "https://lightsondata.com/feed", "weight": 1.2},
            # Substack — data governance practitioners
            {"name": "Data Governed (Substack)", "url": "https://datagoverned.substack.com/feed", "weight": 1.3},
            {"name": "Data Governance Circle (Substack)", "url": "https://datagovernancecircle.substack.com/feed", "weight": 1.2},
            # Vendor blogs with governance focus
            {"name": "Monte Carlo Data", "url": "https://www.montecarlodata.com/feed/", "weight": 1.1},
            # Medium — seulement les tags les plus pertinents
            {"name": "Medium #data-governance", "url": "https://medium.com/feed/tag/data-governance", "weight": 0.8},
            {"name": "Medium #data-mesh", "url": "https://medium.com/feed/tag/data-mesh", "weight": 0.8},
            {"name": "Medium #data-quality", "url": "https://medium.com/feed/tag/data-quality", "weight": 0.8},
            {"name": "Medium #data-catalog", "url": "https://medium.com/feed/tag/data-catalog", "weight": 0.8},
            # Medium publications premium
            {"name": "Towards Data Science (Governance)", "url": "https://towardsdatascience.com/feed", "weight": 1.0},
            # Google News — data governance
            {"name": "Google News: Data governance enterprise", "url": "https://news.google.com/rss/search?q=data+governance+enterprise+quality&hl=en&gl=US&ceid=US:en", "weight": 1.0},
            {"name": "Google News: Gouvernance données (FR)", "url": "https://news.google.com/rss/search?q=gouvernance+donn%C3%A9es+entreprise&hl=fr&gl=FR&ceid=FR:fr", "weight": 1.0},
        ]
    },
    "business_accessible": {
        "label": "IA & Business (accessible)",
        "emoji": "💡",
        "color": "#f59e0b",
        "sources": [
            # Sources business grand public — pour élargir l'audience
            {"name": "Wired AI", "url": "https://www.wired.com/feed/tag/ai/latest/rss", "weight": 1.2},
            {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "weight": 1.1},
            # Substack business accessible
            {"name": "Not Boring AI (Substack)", "url": "https://www.notboring.co/feed", "weight": 1.1},
            # Sources généralistes tech — accessible grand public
            {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "weight": 1.2},
            {"name": "Sifted AI", "url": "https://sifted.eu/tag/artificial-intelligence/feed", "weight": 1.1},
            # Google News — IA business généraliste (FR + EN)
            {"name": "Google News: AI business strategy", "url": "https://news.google.com/rss/search?q=artificial+intelligence+business+strategy&hl=en&gl=US&ceid=US:en", "weight": 1.0},
            {"name": "Google News: IA entreprise (FR)", "url": "https://news.google.com/rss/search?q=intelligence+artificielle+entreprise+strat%C3%A9gie&hl=fr&gl=FR&ceid=FR:fr", "weight": 1.0},
        ]
    }
}
