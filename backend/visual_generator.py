"""Générateur de visuels brandés pour LinkedIn."""
import os
import logging
from jinja2 import Template
from config import EXPERT_PROFILE, RSS_SOURCES

logger = logging.getLogger(__name__)

TEMPLATE_STAT_CHOC = """<!DOCTYPE html>
<html><head><style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 1200px; height: 628px;
    background: #0c0c0c;
    font-family: 'Inter', -apple-system, sans-serif;
    display: flex; flex-direction: column;
    justify-content: center; align-items: center;
    padding: 60px;
    position: relative;
    overflow: hidden;
  }
  .bg-glow {
    position: absolute; top: -100px; right: -100px;
    width: 400px; height: 400px;
    background: radial-gradient(circle, {{ color }}22 0%, transparent 70%);
    border-radius: 50%;
  }
  .stat {
    font-family: 'Inter', sans-serif;
    font-size: 140px; font-weight: 900;
    color: {{ color }};
    line-height: 1;
    margin-bottom: 16px;
    letter-spacing: -6px;
  }
  .subtitle {
    font-size: 36px; font-weight: 300;
    color: #f0f0f0;
    text-align: center;
    line-height: 1.3;
    max-width: 800px;
    margin-bottom: 24px;
  }
  .punchline {
    font-size: 24px; font-weight: 600;
    color: #999;
    text-align: center;
    max-width: 700px;
  }
  .footer {
    position: absolute; bottom: 40px; left: 60px; right: 60px;
    display: flex; justify-content: space-between; align-items: center;
    border-top: 1px solid rgba(255,255,255,0.07);
    padding-top: 20px;
  }
  .author { font-size: 16px; font-weight: 600; color: #666; }
  .category {
    font-size: 12px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 2px;
    color: {{ color }}; 
    padding: 6px 14px;
    border: 1px solid {{ color }}44;
    border-radius: 100px;
  }
</style></head>
<body>
  <div class="bg-glow"></div>
  <div class="stat">{{ stat }}</div>
  <div class="subtitle">{{ main_text }}</div>
  <div class="punchline">{{ subtitle }}</div>
  <div class="footer">
    <div class="author">{{ author }} · {{ author_title }}</div>
    <div class="category">{{ category }}</div>
  </div>
</body></html>"""


TEMPLATE_CITATION = """<!DOCTYPE html>
<html><head><style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 1200px; height: 628px;
    background: #0c0c0c;
    font-family: 'Inter', -apple-system, sans-serif;
    display: flex; flex-direction: column;
    justify-content: center;
    padding: 80px;
    position: relative;
    overflow: hidden;
  }
  .quote-mark {
    font-size: 120px; font-weight: 900;
    color: {{ color }};
    line-height: 0.6;
    margin-bottom: 20px;
    opacity: 0.6;
  }
  .quote {
    font-size: 38px; font-weight: 500;
    color: #f0f0f0;
    line-height: 1.4;
    max-width: 900px;
    font-style: italic;
    margin-bottom: 40px;
  }
  .author-block {
    display: flex; align-items: center; gap: 16px;
  }
  .author-line {
    width: 40px; height: 2px;
    background: {{ color }};
  }
  .author-info {}
  .author-name {
    font-size: 18px; font-weight: 700; color: #f0f0f0;
  }
  .author-title {
    font-size: 14px; font-weight: 400; color: #666;
  }
  .category {
    position: absolute; top: 40px; right: 60px;
    font-size: 12px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 2px;
    color: {{ color }};
    padding: 6px 14px;
    border: 1px solid {{ color }}44;
    border-radius: 100px;
  }
</style></head>
<body>
  <div class="category">{{ category }}</div>
  <div class="quote-mark">"</div>
  <div class="quote">{{ main_text }}</div>
  <div class="author-block">
    <div class="author-line"></div>
    <div class="author-info">
      <div class="author-name">{{ author }}</div>
      <div class="author-title">{{ author_title }}</div>
    </div>
  </div>
</body></html>"""


TEMPLATE_ARTICLE = """<!DOCTYPE html>
<html><head><style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    width: 1200px; height: 628px;
    background: #0c0c0c;
    font-family: 'Inter', -apple-system, sans-serif;
    display: flex; flex-direction: column;
    justify-content: space-between;
    padding: 60px;
    position: relative;
    overflow: hidden;
  }
  .top {
    display: flex; align-items: center; gap: 12px;
  }
  .emoji { font-size: 28px; }
  .cat-label {
    font-size: 14px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 2px;
    color: {{ color }};
  }
  .source {
    font-size: 14px; color: #666; margin-left: auto;
  }
  .title {
    font-size: 44px; font-weight: 800;
    color: #f0f0f0;
    line-height: 1.15;
    letter-spacing: -1px;
    max-width: 900px;
  }
  .bullets {
    display: flex; flex-direction: column; gap: 12px;
  }
  .bullet {
    display: flex; align-items: center; gap: 12px;
    font-size: 20px; color: #999;
  }
  .bullet-dot {
    width: 8px; height: 8px; min-width: 8px;
    background: {{ color }};
    border-radius: 50%;
  }
  .footer {
    display: flex; justify-content: space-between; align-items: center;
    border-top: 1px solid rgba(255,255,255,0.07);
    padding-top: 20px;
  }
  .author { font-size: 16px; font-weight: 600; color: #666; }
  .tag-list { display: flex; gap: 8px; }
  .tag {
    font-size: 12px; font-weight: 500;
    padding: 4px 12px; border-radius: 100px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.07);
    color: #666;
  }
</style></head>
<body>
  <div class="top">
    <span class="emoji">{{ emoji }}</span>
    <span class="cat-label">{{ category }}</span>
    <span class="source">{{ source }}</span>
  </div>
  <div class="title">{{ main_text }}</div>
  <div class="bullets">
    {% for bullet in bullets %}
    <div class="bullet">
      <div class="bullet-dot"></div>
      {{ bullet }}
    </div>
    {% endfor %}
  </div>
  <div class="footer">
    <div class="author">{{ author }} · Veille IA & Data</div>
    <div class="tag-list">
      {% for tag in tags %}
      <span class="tag">{{ tag }}</span>
      {% endfor %}
    </div>
  </div>
</body></html>"""


TEMPLATES = {
    "stat_choc": TEMPLATE_STAT_CHOC,
    "citation_expert": TEMPLATE_CITATION,
    "article_resume": TEMPLATE_ARTICLE,
}


def generate_visual_html(article: dict) -> str:
    """Génère le HTML du visuel pour un article."""
    visual_type = article.get("visual_type", "article_resume")
    visual_data = article.get("visual_data", {})
    category_id = article.get("category", "ia_entreprise")
    category_config = RSS_SOURCES.get(category_id, {})
    
    template_str = TEMPLATES.get(visual_type, TEMPLATE_ARTICLE)
    template = Template(template_str)
    
    # Extraire les bullets du résumé si template article
    summary = article.get("summary", "")
    bullets = [s.strip() for s in summary.split('.') if len(s.strip()) > 20][:3]
    
    html = template.render(
        color=category_config.get("color", "#c8ff00"),
        emoji=category_config.get("emoji", "📊"),
        category=category_config.get("label", "IA"),
        source=article.get("source_name", ""),
        author=EXPERT_PROFILE["name"],
        author_title=EXPERT_PROFILE["title"],
        main_text=visual_data.get("main_text", article.get("title", "")),
        subtitle=visual_data.get("subtitle", ""),
        stat=visual_data.get("stat", ""),
        bullets=bullets,
        tags=article.get("tags", [])[:4],
    )
    
    return html


def save_visual_html(article: dict, output_dir: str = "templates/output") -> str:
    """Sauvegarde le HTML du visuel dans un fichier."""
    os.makedirs(output_dir, exist_ok=True)
    html = generate_visual_html(article)
    filepath = os.path.join(output_dir, f"visual_{article['id']}.html")
    with open(filepath, "w") as f:
        f.write(html)
    logger.info(f"  🎨 Visuel HTML sauvegardé: {filepath}")
    return filepath
