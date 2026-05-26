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
    "tone": "Expert terrain qui build ET qui gouverne. Parle autant code que stratégie. Avis tranchés, pas de bullshit.",
    "linkedin_url": "https://www.linkedin.com/in/renaud-secq-5593832a/",
    "photo_url": "photo-000.jpg"
}

# Sources RSS organisées par catégorie
# PRINCIPE : des experts individuels > des blogs corporate marketing
RSS_SOURCES = {
    "ia_pratique": {
        "label": "IA en pratique (experts terrain)",
        "emoji": "🤖",
        "color": "#6c63ff",
        "sources": [
            {"name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/", "weight": 1.5},
            {"name": "Latent Space", "url": "https://www.latent.space/feed", "weight": 1.5},
            {"name": "Chip Huyen", "url": "https://huyenchip.com/feed.xml", "weight": 1.4},
            {"name": "Lilian Weng", "url": "https://lilianweng.github.io/index.xml", "weight": 1.3},
            {"name": "Eugene Yan", "url": "https://eugeneyan.com/rss/", "weight": 1.4},
            {"name": "Hamel Husain", "url": "https://hamel.dev/feed.xml", "weight": 1.4},
            {"name": "The Batch (Andrew Ng)", "url": "https://www.deeplearning.ai/the-batch/feed/", "weight": 1.2},
            {"name": "Last Week in AI", "url": "https://lastweekin.ai/feed", "weight": 1.2},
            {"name": "AI Snake Oil", "url": "https://www.aisnakeoil.com/feed", "weight": 1.3},
            {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml", "weight": 1.1},
            {"name": "a16z AI", "url": "https://a16z.com/category/ai/feed/", "weight": 1.3},
        ]
    },
    "infra_mlops": {
        "label": "Infra, MLOps & Plateformes",
        "emoji": "⚙️",
        "color": "#00d4ff",
        "sources": [
            {"name": "Google Cloud AI", "url": "https://cloudblog.withgoogle.com/products/ai-machine-learning/rss/", "weight": 1.1},
            {"name": "Databricks Blog", "url": "https://www.databricks.com/feed", "weight": 1.1},
            {"name": "Snowflake Blog", "url": "https://www.snowflake.com/feed/", "weight": 1.1},
            {"name": "InfoQ AI/ML", "url": "https://feed.infoq.com/ai-ml-data-eng/", "weight": 1.2},
            {"name": "Pragmatic Engineer", "url": "https://newsletter.pragmaticengineer.com/feed", "weight": 1.3},
            {"name": "W&B Blog", "url": "https://wandb.ai/fully-connected/rss.xml", "weight": 1.2},
            {"name": "DeepMind Blog", "url": "https://deepmind.google/blog/rss.xml", "weight": 1.2},
            {"name": "HN Front Page AI", "url": "https://hnrss.org/newest?points=100&q=AI+OR+LLM+OR+agent+OR+MLOps", "weight": 1.2},
        ]
    },
    "governance_regulation": {
        "label": "Gouvernance & Régulation IA",
        "emoji": "⚖️",
        "color": "#c8ff00",
        "sources": [
            {"name": "EU AI Act", "url": "https://artificialintelligenceact.eu/feed/", "weight": 1.3},
            {"name": "CNIL", "url": "https://www.cnil.fr/fr/rss.xml", "weight": 1.2},
            {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/", "weight": 1.1},
            {"name": "Stanford HAI", "url": "https://hai.stanford.edu/news/rss.xml", "weight": 1.1},
            {"name": "Ars Technica AI", "url": "https://arstechnica.com/ai/feed/", "weight": 1.0},
            {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "weight": 1.1},
            {"name": "Le Journal de l'IA", "url": "https://www.journaldelai.com/feed/", "weight": 1.2},
        ]
    },
    "vibe_coding": {
        "label": "Vibe Coding & Dev assisté IA",
        "emoji": "⚡",
        "color": "#ff9f43",
        "sources": [
            {"name": "Anthropic Blog", "url": "https://www.anthropic.com/blog/rss.xml", "weight": 1.4},
            {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "weight": 1.2},
            {"name": "GitHub Blog", "url": "https://github.blog/feed/", "weight": 1.2},
            {"name": "HN Vibe Coding", "url": "https://hnrss.org/newest?points=50&q=vibe+coding+OR+cursor+OR+copilot+OR+claude+code+OR+windsurf", "weight": 1.3},
            {"name": "Dev.to #ai", "url": "https://dev.to/feed/tag/ai", "weight": 0.9},
            {"name": "Cursor Blog", "url": "https://www.cursor.com/blog/rss.xml", "weight": 1.3},
        ]
    }
}
