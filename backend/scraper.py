"""Scraper RSS pour récupérer les articles des sources configurées."""
import feedparser
import httpx
import hashlib
import logging
from datetime import datetime, timezone
from dateutil import parser as date_parser
from typing import Optional
from config import RSS_SOURCES

logger = logging.getLogger(__name__)


def generate_article_id(url: str) -> str:
    """Génère un ID unique pour un article basé sur son URL."""
    return hashlib.md5(url.encode()).hexdigest()[:16]


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse une date depuis un flux RSS."""
    if not date_str:
        return None
    try:
        return date_parser.parse(date_str).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def clean_html(text: str) -> str:
    """Retire les balises HTML d'un texte."""
    import re
    clean = re.sub(r'<[^>]+>', '', text or '')
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:500]  # Max 500 chars pour le résumé


async def fetch_feed(source_name: str, url: str) -> list[dict]:
    """Récupère un flux RSS et retourne les articles."""
    articles = []
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (MIA Veille Bot; +https://renaudsecq59.github.io/mia-chatbot/veille.html)"
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
        feed = feedparser.parse(response.text)
        
        for entry in feed.entries[:10]:  # Max 10 articles par source
            article_url = entry.get('link', '')
            if not article_url:
                continue
                
            published = parse_date(
                entry.get('published', '') or entry.get('updated', '')
            )
            
            summary = clean_html(
                entry.get('summary', '') or entry.get('description', '')
            )
            
            articles.append({
                "id": generate_article_id(article_url),
                "title": entry.get('title', 'Sans titre'),
                "url": article_url,
                "summary_raw": summary,
                "source_name": source_name,
                "published": published.isoformat() if published else datetime.now(timezone.utc).isoformat(),
                "author": entry.get('author', ''),
            })
            
        logger.info(f"✅ {source_name}: {len(articles)} articles récupérés")
        
    except Exception as e:
        logger.warning(f"⚠️ {source_name}: erreur - {e}")
    
    return articles


async def scrape_all_sources() -> list[dict]:
    """Scrape toutes les sources RSS configurées."""
    all_articles = []
    
    for category_id, category in RSS_SOURCES.items():
        logger.info(f"\n📂 Catégorie: {category['label']}")
        
        for source in category["sources"]:
            articles = await fetch_feed(source["name"], source["url"])
            
            for article in articles:
                article["category"] = category_id
                article["category_label"] = category["label"]
                article["category_emoji"] = category["emoji"]
                article["category_color"] = category["color"]
                article["source_weight"] = source["weight"]
            
            all_articles.extend(articles)
    
    # Dédupliquer par URL
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        if article["url"] not in seen_urls:
            seen_urls.add(article["url"])
            unique_articles.append(article)
    
    logger.info(f"\n📊 Total: {len(unique_articles)} articles uniques (sur {len(all_articles)} bruts)")
    return unique_articles


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    
    articles = asyncio.run(scrape_all_sources())
    print(f"\n{'='*60}")
    print(f"Total articles: {len(articles)}")
    for a in articles[:5]:
        print(f"  [{a['category']}] {a['source_name']}: {a['title'][:80]}")
