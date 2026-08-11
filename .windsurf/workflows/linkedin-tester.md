---
description: Tester et scraper LinkedIn — se connecte automatiquement avec credentials stockés dans Secret Manager, extrait posts et réactions
---

# Skill: LinkedIn Tester

## Quand utiliser
- Vérifier les posts publiés sur un profil LinkedIn
- Analyser les réactions et commentaires sur les posts
- Vérifier que le pipeline de publication fonctionne
- Surveiller l'engagement LinkedIn

## Prérequis
- Google Secret Manager activé sur le projet `mia-chatbot-veille`
- Secrets créés : `LINKEDIN_LOGIN_EMAIL` et `LINKEDIN_LOGIN_PASSWORD`
- Node.js + Puppeteer installés (`npm install puppeteer`)
- `gcloud auth application-default login` fait

## Étapes

### 1. Vérifier les credentials
```bash
python3 -c "
from google.cloud import secretmanager
sm = secretmanager.SecretManagerServiceClient()
email = sm.access_secret_version(name='projects/mia-chatbot-veille/secrets/LINKEDIN_LOGIN_EMAIL/versions/latest').payload.data.decode()
print(f'Email: {email[:5]}***')
print('✅ Credentials OK')
"
```

### 2. Lancer le test
```bash
cd /Users/renaudsecq/Documents/freelance/mia-chatbot
python3 tools/linkedin_tester.py
```

### 3. Analyser les résultats
- Les posts extraits sont sauvegardés dans `tools/linkedin_results.json`
- Le script affiche un résumé avec réactions et commentaires par post
- Vérifier que les posts récents apparaissent bien

### 4. Tester une URL spécifique
```python
from tools.linkedin_tester import run_linkedin_test
data = run_linkedin_test("https://www.linkedin.com/in/renaud-secq/recent-activity/all/")
```

## Troubleshooting
- **Login failed** : Vérifier que les credentials sont à jour dans Secret Manager
- **Timeout** : LinkedIn peut être lent, augmenter le timeout dans le script
- **0 posts trouvés** : LinkedIn change souvent ses sélecteurs, le script utilise une détection par contenu (présence de "réaction"/"commentaire")
- **Captcha** : Si LinkedIn détecte un bot, il peut afficher un captcha. Utiliser headless: false pour debug
