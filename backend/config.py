"""Configuration des sources RSS et paramètres de l'application."""
import os

# Clé API Anthropic (Claude)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Projet Google Cloud
GCP_PROJECT = os.getenv("GCP_PROJECT", "mia-chatbot-veille")

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
    "title": "Consultant Freelance IA & Data",
    "expertise": [
        "Développement agentique & multi-agents",
        "Data & AI Governance (Collibra, EU AI Act)",
        "Product Management IA"
    ],
    "tone": "Expert pragmatique, orienté business. Vulgarise sans simplifier. Donne des avis tranchés basés sur l'expérience terrain.",
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
    }
}
