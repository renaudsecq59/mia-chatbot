---
description: Déployer le backend sur Google Cloud Run
---

# Déploiement sur Google Cloud Run

## Prérequis
- `gcloud` CLI installé et authentifié (`gcloud auth login`)
- Projet GCP : `mia-chatbot-veille`
- Région : `europe-west1`

## Étapes

1. Vérifier que gcloud est configuré sur le bon projet
```bash
gcloud config set project mia-chatbot-veille
```
// turbo

2. Build et pousser l'image Docker du backend
```bash
cd backend && gcloud builds submit --tag gcr.io/mia-chatbot-veille/veille-backend --project mia-chatbot-veille
```

3. Déployer sur Cloud Run
```bash
gcloud run deploy veille-backend \
  --image gcr.io/mia-chatbot-veille/veille-backend \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars "GCP_PROJECT=mia-chatbot-veille" \
  --project mia-chatbot-veille
```

4. Récupérer l'URL du service déployé
```bash
gcloud run services describe veille-backend --region europe-west1 --format 'value(status.url)' --project mia-chatbot-veille
```

5. Tester que le déploiement fonctionne
```bash
curl $(gcloud run services describe veille-backend --region europe-west1 --format 'value(status.url)' --project mia-chatbot-veille)/health
```

## Variables d'environnement à vérifier
- `ANTHROPIC_API_KEY` — pour Claude (scoring + édito)
- `LINKEDIN_ACCESS_TOKEN` — pour auto-publish
- `LINKEDIN_PERSON_URN` — pour auto-publish

Pour ajouter une variable :
```bash
gcloud run services update veille-backend --region europe-west1 --set-env-vars KEY=VALUE --project mia-chatbot-veille
```
