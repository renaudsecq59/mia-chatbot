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
RSS_SOURCES = {
    "ia_entreprise": {
        "label": "IA & Plateformes Cloud",
        "emoji": "🤖",
        "color": "#6c63ff",
        "sources": [
            {"name": "Google Cloud AI", "url": "https://cloudblog.withgoogle.com/products/ai-machine-learning/rss/", "weight": 1.3},
            {"name": "AWS ML Blog", "url": "https://aws.amazon.com/blogs/machine-learning/feed/", "weight": 1.2},
            {"name": "Databricks Blog", "url": "https://www.databricks.com/feed", "weight": 1.3},
            {"name": "Snowflake Blog", "url": "https://www.snowflake.com/feed/", "weight": 1.1},
            {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml", "weight": 1.1},
            {"name": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml", "weight": 1.1},
            {"name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/", "weight": 1.2},
            {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "weight": 1.2},
        ]
    },
    "data_governance": {
        "label": "Data & Gouvernance",
        "emoji": "📊",
        "color": "#00d4ff",
        "sources": [
            {"name": "Medium #ai-governance", "url": "https://medium.com/feed/tag/ai-governance", "weight": 1.2},
            {"name": "Medium #data-governance", "url": "https://medium.com/feed/tag/data-governance", "weight": 1.1},
            {"name": "Medium #data-quality", "url": "https://medium.com/feed/tag/data-quality", "weight": 1.0},
            {"name": "Towards Data Science", "url": "https://towardsdatascience.com/feed", "weight": 0.9},
            {"name": "Ars Technica AI", "url": "https://arstechnica.com/ai/feed/", "weight": 0.9},
        ]
    },
    "reglementation": {
        "label": "Réglementation & Éthique IA",
        "emoji": "⚖️",
        "color": "#c8ff00",
        "sources": [
            {"name": "EU AI Act", "url": "https://artificialintelligenceact.eu/feed/", "weight": 1.3},
            {"name": "CNIL", "url": "https://www.cnil.fr/fr/rss.xml", "weight": 1.2},
            {"name": "Commission EU Digital", "url": "https://digital-strategy.ec.europa.eu/en/rss.xml", "weight": 1.2},
            {"name": "AI Snake Oil", "url": "https://www.aisnakeoil.com/feed", "weight": 1.2},
            {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/", "weight": 1.0},
            {"name": "Stanford HAI", "url": "https://hai.stanford.edu/news/rss.xml", "weight": 1.1},
        ]
    },
    "business_strategie": {
        "label": "Business & Stratégie IA",
        "emoji": "💼",
        "color": "#ff6b6b",
        "sources": [
            {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "weight": 1.0},
            {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "weight": 0.9},
            {"name": "Import AI", "url": "https://jack-clark.net/feed/", "weight": 1.2},
            {"name": "InfoQ AI/ML", "url": "https://feed.infoq.com/ai-ml-data-eng/", "weight": 1.0},
            {"name": "a16z AI", "url": "https://a16z.com/tag/ai/feed/", "weight": 1.1},
            {"name": "Wired AI", "url": "https://www.wired.com/feed/tag/ai/latest/rss", "weight": 0.9},
        ]
    },
    "vibe_coding": {
        "label": "Vibe Coding & Dev IA",
        "emoji": "⚡",
        "color": "#ff9f43",
        "sources": [
            {"name": "Cursor Blog", "url": "https://www.cursor.com/blog/rss.xml", "weight": 1.4},
            {"name": "Anthropic Blog", "url": "https://www.anthropic.com/blog/rss.xml", "weight": 1.3},
            {"name": "GitHub Blog", "url": "https://github.blog/feed/", "weight": 1.2},
            {"name": "Hacker News AI", "url": "https://hnrss.org/newest?q=vibe+coding+OR+cursor+OR+copilot+OR+ai+coding", "weight": 1.1},
            {"name": "Dev.to #ai", "url": "https://dev.to/feed/tag/ai", "weight": 0.9},
            {"name": "Codeium Blog", "url": "https://codeium.com/blog/rss.xml", "weight": 1.1},
        ]
    }
}
