"""Scraper RSS pour récupérer les articles des sources configurées."""
import feedparser
import httpx
import hashlib
import logging
import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from dateutil import parser as date_parser
from typing import Optional
from config import RSS_SOURCES, MAX_ARTICLE_AGE_DAYS

logger = logging.getLogger(__name__)


def generate_article_id(url: str) -> str:
    """Génère un ID unique pour un article basé sur son URL."""
    return hashlib.md5(url.encode()).hexdigest()[:16]


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse une date depuis un flux RSS."""
    if not date_str:
        return None
    try:
        dt = date_parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def clean_html(text: str) -> str:
    """Retire les balises HTML d'un texte."""
    clean = re.sub(r'<[^>]+>', '', text or '')
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:500]


def extract_keywords(title: str) -> set[str]:
    """Extrait les mots-clés significatifs d'un titre pour détection de tendances."""
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                  'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                  'and', 'or', 'but', 'not', 'this', 'that', 'it', 'its',
                  'how', 'what', 'why', 'when', 'who', 'which', 'can', 'will',
                  'your', 'you', 'we', 'our', 'new', 'les', 'des', 'une', 'un',
                  'pour', 'dans', 'sur', 'par', 'est', 'sont', 'avec', 'qui',
                  'que', 'pas', 'plus', 'mais', 'comme', 'tout', 'tous'}
    words = set(re.findall(r'\b[a-zA-Z]{3,}\b', title.lower()))
    return words - stop_words


def is_fresh(published_str: str, max_age_days: int = MAX_ARTICLE_AGE_DAYS) -> bool:
    """Vérifie si un article est assez récent."""
    try:
        published = date_parser.parse(published_str)
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        return published >= cutoff
    except (ValueError, TypeError):
        return True  # En cas de doute, on garde


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
        
        for entry in feed.entries[:10]:
            article_url = entry.get('link', '')
            if not article_url:
                continue
                
            published = parse_date(
                entry.get('published', '') or entry.get('updated', '')
            )
            
            published_str = published.isoformat() if published else datetime.now(timezone.utc).isoformat()
            
            # Filtre fraîcheur : rejeter les articles trop vieux
            if not is_fresh(published_str):
                continue
            
            summary = clean_html(
                entry.get('summary', '') or entry.get('description', '')
            )
            
            articles.append({
                "id": generate_article_id(article_url),
                "title": entry.get('title', 'Sans titre'),
                "url": article_url,
                "summary_raw": summary,
                "source_name": source_name,
                "published": published_str,
                "author": entry.get('author', ''),
                "keywords": list(extract_keywords(entry.get('title', ''))),
            })
            
        logger.info(f"✅ {source_name}: {len(articles)} articles récents")
        
    except Exception as e:
        logger.warning(f"⚠️ {source_name}: erreur - {e}")
    
    return articles


def detect_trends(articles: list[dict]) -> list[dict]:
    """Détecte les sujets tendance (même sujet dans 3+ sources)."""
    keyword_counter = Counter()
    keyword_to_articles = {}
    
    for article in articles:
        for kw in article.get("keywords", []):
            keyword_counter[kw] += 1
            if kw not in keyword_to_articles:
                keyword_to_articles[kw] = []
            keyword_to_articles[kw].append(article["id"])
    
    # Un mot-clé est "trending" s'il apparaît dans 3+ articles de sources différentes
    trending_keywords = {kw for kw, count in keyword_counter.items() if count >= 3}
    
    if trending_keywords:
        logger.info(f"🔥 Tendances détectées: {', '.join(list(trending_keywords)[:10])}")
    
    # Boost les articles qui touchent un sujet tendance
    for article in articles:
        article_keywords = set(article.get("keywords", []))
        overlap = article_keywords & trending_keywords
        if overlap:
            article["is_trending"] = True
            article["trending_keywords"] = list(overlap)
            # Boost le poids de la source
            article["source_weight"] = article.get("source_weight", 1.0) * 1.3
        else:
            article["is_trending"] = False
            article["trending_keywords"] = []
    
    return articles


def deduplicate(articles: list[dict]) -> list[dict]:
    """Déduplique par URL + par similarité de titre."""
    seen_urls = set()
    seen_title_keys = set()
    unique = []
    
    for article in articles:
        # Dédup par URL
        if article["url"] in seen_urls:
            continue
        seen_urls.add(article["url"])
        
        # Dédup par titre similaire (mots-clés en commun > 60%)
        title_key = frozenset(article.get("keywords", [])[:5])
        is_duplicate = False
        for existing_key in seen_title_keys:
            if len(title_key) > 0 and len(existing_key) > 0:
                overlap = len(title_key & existing_key) / max(len(title_key), len(existing_key))
                if overlap > 0.6:
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            seen_title_keys.add(title_key)
            unique.append(article)
    
    return unique


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
    
    # Dédupliquer (URL + titre similaire)
    unique_articles = deduplicate(all_articles)
    
    # Détecter les tendances
    unique_articles = detect_trends(unique_articles)
    
    # Trier par date (plus récent d'abord)
    unique_articles.sort(key=lambda x: x.get("published", ""), reverse=True)
    
    removed = len(all_articles) - len(unique_articles)
    logger.info(f"\n📊 Total: {len(unique_articles)} articles uniques ({removed} doublons retirés)")
    trending = sum(1 for a in unique_articles if a.get("is_trending"))
    logger.info(f"🔥 {trending} articles sur des sujets tendance")
    return unique_articles


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    
    articles = asyncio.run(scrape_all_sources())
    print(f"\n{'='*60}")
    print(f"Total articles: {len(articles)}")
    print(f"Trending: {sum(1 for a in articles if a.get('is_trending'))}")
    print(f"\nTop 10 articles:")
    for a in articles[:10]:
        trend = "🔥" if a.get("is_trending") else "  "
        print(f"  {trend} [{a['category']}] {a['source_name']}: {a['title'][:70]}")
