#!/bin/bash
set -e

# Configuration
PROJECT_ID="mia-chatbot-veille"
REGION="europe-west1"
SERVICE_NAME="veille-backend"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Déploiement de la veille IA & Data sur Cloud Run"
echo "=================================================="

# 1. Vérifier que gcloud est configuré
echo "📋 Vérification de la configuration gcloud..."
gcloud config set project ${PROJECT_ID}

# 2. Activer les APIs nécessaires
echo "🔧 Activation des APIs Google Cloud..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com \
  cloudscheduler.googleapis.com \
  --project=${PROJECT_ID}

# 3. Build de l'image Docker
echo "🐳 Build de l'image Docker..."
cd backend
gcloud builds submit --tag ${IMAGE_NAME} --project=${PROJECT_ID}

# 4. Déploiement sur Cloud Run
echo "☁️  Déploiement sur Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars "GCP_PROJECT=${PROJECT_ID}" \
  --project=${PROJECT_ID}

# 5. Récupérer l'URL du service
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --format 'value(status.url)' \
  --project=${PROJECT_ID})

echo ""
echo "✅ Déploiement terminé !"
echo "=================================================="
echo "📍 URL du backend: ${SERVICE_URL}"
echo ""
echo "🧪 Tester l'API:"
echo "   curl ${SERVICE_URL}/health"
echo ""
echo "📊 Scraper les articles:"
echo "   curl ${SERVICE_URL}/api/scrape"
echo ""
echo "📝 Générer un édito LinkedIn:"
echo "   curl ${SERVICE_URL}/api/linkedin/edito"
echo ""
echo "🔐 Variables d'environnement à configurer:"
echo "   - ANTHROPIC_API_KEY (pour Claude)"
echo "   - LINKEDIN_ACCESS_TOKEN (pour auto-publish)"
echo "   - LINKEDIN_PERSON_URN (pour auto-publish)"
echo ""
echo "Pour ajouter une variable:"
echo "   gcloud run services update ${SERVICE_NAME} \\"
echo "     --region ${REGION} \\"
echo "     --set-env-vars KEY=VALUE \\"
echo "     --project=${PROJECT_ID}"
