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

# Nombre max d'articles par jour
MAX_ARTICLES_PER_DAY = 15

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
        "label": "IA en entreprise",
        "emoji": "🤖",
        "color": "#6c63ff",
        "sources": [
            {"name": "Medium #llm", "url": "https://medium.com/feed/tag/llm", "weight": 1.0},
            {"name": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml", "weight": 1.2},
            {"name": "Ars Technica AI", "url": "https://arstechnica.com/ai/feed/", "weight": 1.0},
            {"name": "The Register AI", "url": "https://www.theregister.com/software/ai_ml/headlines.atom", "weight": 0.9},
            {"name": "LangChain Blog", "url": "https://blog.langchain.dev/rss/", "weight": 1.0},
            {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "weight": 1.0},
            {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "weight": 0.9},
            {"name": "a16z AI", "url": "https://a16z.com/tag/ai/feed/", "weight": 1.1},
        ]
    },
    "data_governance": {
        "label": "Data & Gouvernance",
        "emoji": "📊",
        "color": "#00d4ff",
        "sources": [
            {"name": "Medium #ai-governance", "url": "https://medium.com/feed/tag/ai-governance", "weight": 1.2},
            {"name": "Medium #data-catalog", "url": "https://medium.com/feed/tag/data-catalog", "weight": 1.0},
            {"name": "Medium #data-governance", "url": "https://medium.com/feed/tag/data-governance", "weight": 1.0},
            {"name": "Medium #data-quality", "url": "https://medium.com/feed/tag/data-quality", "weight": 1.0},
            {"name": "Towards Data Science", "url": "https://towardsdatascience.com/feed", "weight": 0.9},
            {"name": "KDnuggets", "url": "https://www.kdnuggets.com/feed", "weight": 0.9},
            {"name": "Medium #data-mesh", "url": "https://medium.com/feed/tag/data-mesh", "weight": 0.8},
        ]
    },
    "reglementation": {
        "label": "Réglementation & Éthique IA",
        "emoji": "⚖️",
        "color": "#c8ff00",
        "sources": [
            {"name": "EU AI Act", "url": "https://artificialintelligenceact.eu/feed/", "weight": 1.3},
            {"name": "CNIL", "url": "https://www.cnil.fr/fr/rss.xml", "weight": 1.2},
            {"name": "IAPP", "url": "https://iapp.org/news/feed/", "weight": 1.1},
            {"name": "Stanford HAI", "url": "https://hai.stanford.edu/news/rss.xml", "weight": 1.1},
            {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/", "weight": 1.0},
        ]
    },
    "tendances": {
        "label": "Tendances & Outils",
        "emoji": "💡",
        "color": "#ff6b6b",
        "sources": [
            {"name": "ZDNet AI", "url": "https://www.zdnet.com/topic/artificial-intelligence/rss.xml", "weight": 0.9},
            {"name": "Hacker News AI", "url": "https://hnrss.org/newest?q=AI+agents", "weight": 0.8},
            {"name": "Papers with Code", "url": "https://paperswithcode.com/latest/rss", "weight": 0.9},
            {"name": "ArXiv cs.AI", "url": "http://export.arxiv.org/rss/cs.AI", "weight": 0.7},
            {"name": "Reddit r/LocalLLaMA", "url": "https://www.reddit.com/r/LocalLLaMA/.rss", "weight": 0.7},
        ]
    }
}
