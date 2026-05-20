#!/bin/bash
set -e

# Configuration
PROJECT_ID="mia-chatbot-veille"
REGION="europe-west1"
SERVICE_NAME="veille-backend"

echo "⏰ Configuration du cron hebdomadaire"
echo "======================================"

# Récupérer l'URL du service Cloud Run
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --format 'value(status.url)' \
  --project=${PROJECT_ID})

if [ -z "$SERVICE_URL" ]; then
  echo "❌ Service ${SERVICE_NAME} non trouvé. Déploie d'abord avec ./deploy.sh"
  exit 1
fi

echo "📍 Service URL: ${SERVICE_URL}"

# Créer le job Cloud Scheduler pour scraper + publier LinkedIn
# Tous les lundis à 9h (Europe/Paris)
echo "📅 Création du job 'veille-hebdo-linkedin'..."
gcloud scheduler jobs create http veille-hebdo-linkedin \
  --location ${REGION} \
  --schedule "0 9 * * 1" \
  --time-zone "Europe/Paris" \
  --uri "${SERVICE_URL}/api/scrape" \
  --http-method POST \
  --oidc-service-account-email "${PROJECT_ID}@appspot.gserviceaccount.com" \
  --project ${PROJECT_ID} \
  --description "Scrape RSS + génère et publie l'édito LinkedIn hebdomadaire" \
  || echo "⚠️  Job existe déjà, mise à jour..."

# Si le job existe déjà, le mettre à jour
gcloud scheduler jobs update http veille-hebdo-linkedin \
  --location ${REGION} \
  --schedule "0 9 * * 1" \
  --time-zone "Europe/Paris" \
  --uri "${SERVICE_URL}/api/scrape" \
  --project ${PROJECT_ID} \
  2>/dev/null || true

echo ""
echo "✅ Cron configuré !"
echo "======================================"
echo "📅 Fréquence: Tous les lundis à 9h (heure de Paris)"
echo "🎯 Action: Scrape RSS + génère édito + publie sur LinkedIn"
echo ""
echo "🧪 Tester manuellement:"
echo "   gcloud scheduler jobs run veille-hebdo-linkedin --location ${REGION} --project ${PROJECT_ID}"
echo ""
echo "📊 Voir les logs:"
echo "   gcloud scheduler jobs describe veille-hebdo-linkedin --location ${REGION} --project ${PROJECT_ID}"
