#!/usr/bin/env python3
"""
Agent testeur LinkedIn — se connecte automatiquement et scrape les posts + réactions.
Utilise Puppeteer (via subprocess) pour piloter un navigateur headless.
Credentials stockées dans Google Secret Manager.
"""

import subprocess
import json
import logging
import sys
import os
import time
import base64

from google.cloud import secretmanager

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

GCP_PROJECT = os.getenv("GCP_PROJECT", "mia-chatbot-veille")


def get_linkedin_credentials():
    """Récupère les credentials LinkedIn depuis Google Secret Manager."""
    sm = secretmanager.SecretManagerServiceClient()

    email_secret = f"projects/{GCP_PROJECT}/secrets/LINKEDIN_LOGIN_EMAIL/versions/latest"
    password_secret = f"projects/{GCP_PROJECT}/secrets/LINKEDIN_LOGIN_PASSWORD/versions/latest"

    email = sm.access_secret_version(name=email_secret).payload.data.decode()
    password = sm.access_secret_version(name=password_secret).payload.data.decode()

    return email, password


def generate_login_script(email: str, password: str, target_url: str) -> str:
    """Génère un script Node.js pour Puppeteer qui se connecte et scrape LinkedIn."""
    return f"""
const puppeteer = require('puppeteer');

(async () => {{
  const browser = await puppeteer.launch({{
    headless: false,
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    userDataDir: '/Users/renaudsecq/.puppeteer-profile',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-blink-features=AutomationControlled',
      '--window-size=1280,900'
    ]
  }});

  const page = await browser.newPage();
  await page.setViewport({{ width: 1280, height: 900 }});

  // Anti-detection: user-agent réaliste
  await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36');
  await page.evaluateOnNewDocument(() => {{
    Object.defineProperty(navigator, 'webdriver', {{ get: () => false }});
  }});

  // 1. Aller sur LinkedIn login
  console.log('→ Navigation vers LinkedIn login...');
  await page.goto('https://www.linkedin.com/login', {{ waitUntil: 'networkidle2' }});
  await new Promise(r => setTimeout(r, 2000));

  // 2. Remplir le formulaire
  console.log('→ Attente du formulaire...');
  try {{
    await page.waitForSelector('#username', {{ timeout: 15000 }});
  }} catch (e) {{
    console.log('→ Selector #username non trouvé, screenshot de debug...');
    await page.screenshot({{ path: '/Users/renaudsecq/Documents/freelance/mia-chatbot/tools/login_debug.png' }});
    console.log('→ URL actuelle: ' + page.url());
    console.log('→ HTML: ' + (await page.content()).substring(0, 2000));
    // Si on est déjà connecté (session existante), skip login
    if (page.url().includes('feed') || page.url().includes('in/')) {{
      console.log('→ Déjà connecté, skip login');
    }} else {{
      throw e;
    }}
  }}
  if (await page.$('#username')) {{
    console.log('→ Remplissage du formulaire...');
    await page.type('#username', '{email}', {{ delay: 50 }});
    await page.type('#password', '{password}', {{ delay: 50 }});
    await new Promise(r => setTimeout(r, 500));

  // 3. Cliquer sur se connecter
  console.log('→ Clic sur Se connecter...');
  await Promise.all([
    page.waitForNavigation({{ waitUntil: 'networkidle2', timeout: 20000 }}).catch(() => {{
      console.log('→ Pas de navigation, vérification du state...');
    }}),
    page.click('button[type="submit"]'),
  ]);

  await new Promise(r => setTimeout(r, 5000));

  // 4. Vérifier si on est connecté
  const currentUrl = page.url();
  console.log('→ URL après login: ' + currentUrl);

  if (currentUrl.includes('authwall') || currentUrl.includes('login')) {{
    console.log('→ Login échoué, retry avec Enter...');
    await page.keyboard.press('Enter');
    await new Promise(r => setTimeout(r, 5000));
  }}
  }} // fin if #username

  // 5. Aller sur la page cible
  console.log('→ Navigation vers: {target_url}');
  await page.goto('{target_url}', {{ waitUntil: 'networkidle2' }});
  await new Promise(r => setTimeout(r, 5000));

  // 6. Scroller pour charger les posts
  for (let i = 0; i < 5; i++) {{
    await page.evaluate(() => window.scrollBy(0, 800));
    await new Promise(r => setTimeout(r, 2000));
  }}

  // 7. Extraire les posts
  const posts = await page.evaluate(() => {{
    const results = [];
    // LinkedIn utilise des sélecteurs dynamiques, on cherche par contenu
    const allDivs = document.querySelectorAll('div');
    allDivs.forEach(div => {{
      const text = div.innerText || '';
      if (text.length > 100 && text.length < 3000) {{
        // Détecter les posts par la présence de réactions
        if (text.includes('réaction') || text.includes('reaction') || text.includes('commentaire') || text.includes('comment')) {{
          // Éviter les doublons (parent contenant déjà l'enfant)
          const parent = div.parentElement;
          if (parent && parent.innerText === text) return;
          results.push({{
            text: text.substring(0, 1500),
            html: div.innerHTML.substring(0, 500)
          }});
        }}
      }}
    }});
    // Dedup par texte
    const seen = new Set();
    return results.filter(r => {{
      const key = r.text.substring(0, 100);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    }}).slice(0, 10);
  }});

  // 8. Prendre un screenshot
  const screenshot = await page.screenshot({{ encoding: 'base64', fullPage: false }});

  // 9. Retourner les résultats
  console.log(JSON.stringify({{
    posts: posts,
    postCount: posts.length,
    url: page.url(),
    title: await page.title()
  }}));

  await browser.close();
}})();
"""


def run_linkedin_test(target_url: str = "https://www.linkedin.com/in/renaud-secq-5593832a/recent-activity/all/"):
    """
    Se connecte à LinkedIn, scrape les posts et réactions.
    Retourne un dict avec les posts trouvés.
    """
    logger.info("🔑 Récupération des credentials depuis Secret Manager...")
    email, password = get_linkedin_credentials()

    logger.info("🤿 Génération du script Puppeteer...")
    script = generate_login_script(email, password, target_url)

    # Écrire le script dans le dossier du projet pour accès à node_modules
    script_path = "/Users/renaudsecq/Documents/freelance/mia-chatbot/tools/linkedin_scraper.js"
    with open(script_path, "w") as f:
        f.write(script)

    logger.info("🚀 Lancement du navigateur Puppeteer...")
    try:
        result = subprocess.run(
            ["node", script_path],
            capture_output=True,
            text=True,
            timeout=90,
            cwd="/Users/renaudsecq/Documents/freelance/mia-chatbot"
        )

        if result.returncode != 0:
            logger.error(f"❌ Erreur Puppeteer: {result.stderr}")
            return {"error": result.stderr, "posts": []}

        # Parser la sortie JSON
        output_lines = result.stdout.strip().split('\n')
        for line in output_lines:
            try:
                data = json.loads(line)
                if "posts" in data:
                    logger.info(f"✅ {data['postCount']} posts trouvés sur {data['url']}")
                    return data
            except json.JSONDecodeError:
                continue

        logger.warning("⚠️ Pas de JSON valide dans la sortie")
        return {"error": "No JSON output", "raw": result.stdout[:2000], "posts": []}

    except subprocess.TimeoutExpired:
        logger.error("❌ Timeout (60s)")
        return {"error": "Timeout", "posts": []}
    finally:
        # Nettoyer
        if os.path.exists(script_path):
            os.remove(script_path)


def analyze_posts(posts: list) -> dict:
    """
    Analyse les posts extraits et retourne un résumé.
    """
    if not posts:
        return {"total": 0, "message": "Aucun post trouvé"}

    analysis = {
        "total": len(posts),
        "posts": []
    }

    for i, post in enumerate(posts):
        text = post.get("text", "")
        # Extraire les métriques (réactions, commentaires)
        reactions = 0
        comments = 0

        if "réaction" in text.lower():
            import re
            match = re.search(r'(\d+)\s*réaction', text, re.IGNORECASE)
            if match:
                reactions = int(match.group(1))

        if "commentaire" in text.lower():
            import re
            match = re.search(r'(\d+)\s*commentaire', text, re.IGNORECASE)
            if match:
                comments = int(match.group(1))

        analysis["posts"].append({
            "index": i + 1,
            "reactions": reactions,
            "comments": comments,
            "preview": text[:200] + "..." if len(text) > 200 else text
        })

    return analysis


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 Agent Testeur LinkedIn")
    print("=" * 60)

    data = run_linkedin_test()

    if data.get("error"):
        print(f"\n❌ Erreur: {data['error']}")
        sys.exit(1)

    analysis = analyze_posts(data.get("posts", []))

    print(f"\n📊 Résumé: {analysis['total']} posts trouvés")
    print("-" * 60)

    for post in analysis.get("posts", []):
        print(f"\n📝 Post #{post['index']}")
        print(f"   👍 Réactions: {post['reactions']}")
        print(f"   💬 Commentaires: {post['comments']}")
        print(f"   📄 Aperçu: {post['preview']}")

    # Sauvegarder les résultats
    output_path = "/Users/renaudsecq/Documents/freelance/mia-chatbot/tools/linkedin_results.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Résultats sauvegardés: {output_path}")
