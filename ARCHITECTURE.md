# Architecture — renaudsecq.com & veille IA

## Schéma global

```
┌─────────────────────────────────────────────────────────────┐
│                     UTILISATEURS                             │
│                                                              │
│  Visiteurs renaudsecq.com          LinkedIn (abonnés)        │
└──────────┬──────────────────────────────┬────────────────────┘
           │                              │
           ▼                              ▼
┌─────────────────────┐        ┌─────────────────────┐
│   renaudsecq.com     │        │   LinkedIn API      │
│   (Domain Mapping)   │        │   /rest/posts       │
└──────────┬──────────┘        └──────────┬──────────┘
           │                              │
           ▼                              │
┌─────────────────────┐                   │
│  Cloud Run          │                   │
│  Service: mia-site  │                   │
│  (nginx:alpine)     │                   │
│                     │                   │
│  Sert les fichiers  │                   │
│  HTML/CSS/JS statiques│                 │
│  + images            │                  │
│                     │                   │
│  Pages:             │                   │
│  - index.html       │                   │
│  - article.html     │                   │
│  - veille.html      │                   │
│  - etudes-de-cas    │                   │
│  - mia-agency.html  │                   │
│  - confidentialite  │                   │
└──────────┬──────────┘                   │
           │                              │
           │ fetch()                      │
           ▼                              │
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  Cloud Run — Service: veille-backend                        │
│  (FastAPI / Python)                                          │
│                                                              │
│  URL: https://veille-backend-791183172510.europe-west1.run.app
│                                                              │
│  Endpoints:                                                  │
│  ├── GET  /api/linkedin/posts     → liste des posts          │
│  ├── POST /api/newsletter/subscribe → inscription            │
│  ├── POST /api/livre-blanc/download → lead + PDF             │
│  └── GET  /health                  → health check            │
│                                                              │
│  Modules:                                                    │
│  ├── main.py              → API FastAPI                      │
│  ├── linkedin_publisher.py → publication LinkedIn            │
│  │   ├── Scraping RSS (60 sources)                          │
│  │   ├── Génération LLM (Gemini)                            │
│  │   ├── Génération visuels (Gemini 3 Pro Image)            │
│  │   ├── Upload image + post LinkedIn                       │
│  │   └── Stockage Firestore (post_history)                  │
│  └── firestore            → DB NoSQL                         │
│                                                              │
└──────┬───────────────┬───────────────┬──────────────────────┘
       │               │               │
       ▼               ▼               ▼
┌────────────┐  ┌────────────┐  ┌────────────────────┐
│ Firestore  │  │ Secret     │  │ LinkedIn API       │
│            │  │ Manager    │  │                    │
│ Collections:│  │            │  │ - POST /rest/posts │
│ - post_history│ │ Secrets:  │  │ - Upload image     │
│ - newsletter │  │ LINKEDIN_ │  │ - Person URN       │
│ - livre_blanc│  │   ACCESS_ │  │                    │
│   _leads    │  │   TOKEN   │  └────────────────────┘
│             │  │ LINKEDIN_ │
│             │  │   PERSON_ │
│             │  │   URN     │
└────────────┘  └────────────┘
```

## Flux de déploiement (CI/CD)

```
┌──────────────────────────────────────────────────┐
│  Développeur — git push origin main              │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│  GitHub Actions — .github/workflows/deploy.yml   │
│                                                  │
│  ┌─────────────────────┐  ┌───────────────────┐  │
│  │  Job: deploy-backend │  │ Job: deploy-      │  │
│  │                      │  │   frontend        │  │
│  │  Condition:          │  │                   │  │
│  │  backend/** modifié  │  │  Toujours         │  │
│  │                      │  │                   │  │
│  │  1. checkout         │  │  1. checkout      │  │
│  │  2. setup-gcloud     │  │  2. setup-gcloud  │  │
│  │  3. configure-docker │  │  3. authenticate  │  │
│  │  4. gcloud builds    │  │  4. configure-    │  │
│  │     submit (backend) │  │     docker        │  │
│  │  5. gcloud run deploy│  │  5. gcloud run    │  │
│  │     --image          │  │     deploy        │  │
│  │     --set-secrets    │  │     mia-site      │  │
│  │     veille-backend   │  │     --source .    │  │
│  └──────────┬───────────┘  └────────┬──────────┘  │
│             │                       │             │
└─────────────┼───────────────────────┼─────────────┘
              │                       │
              ▼                       ▼
┌──────────────────────┐  ┌──────────────────────┐
│  Cloud Run           │  │  Cloud Run           │
│  veille-backend      │  │  mia-site            │
│  (FastAPI)           │  │  (nginx)             │
│                      │  │                      │
│  URL: veille-backend │  │  Domain mapping:     │
│  -791183172510       │  │  renaudsecq.com      │
│  .europe-west1.run.app│  │                      │
└──────────────────────┘  └──────────────────────┘
```

## Flux de publication LinkedIn

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Sources RSS │     │  Gemini LLM  │     │  Gemini 3    │
│  (60 sources)│────▶│  Génération  │────▶│  Pro Image   │
│              │     │  de texte    │     │  (visuel)    │
└──────────────┘     └──────┬───────┘     └──────┬───────┘
                            │                     │
                            ▼                     ▼
                     ┌──────────────────────────────┐
                     │  linkedin_publisher.py       │
                     │                              │
                     │  1. Troncature texte         │
                     │     (1250 chars si image,    │
                     │      3000 sans)              │
                     │  2. Upload image (Assets API)│
                     │  3. POST /rest/posts         │
                     │  4. Stockage Firestore       │
                     └──────────┬───────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
              ┌──────────┐          ┌──────────┐
              │ LinkedIn │          │ Firestore │
              │ (post    │          │ post_history│
              │  publié) │          │ (image_b64,│
              └──────────┘          │  post_text,│
                                    │  post_id)  │
                                    └──────────┘
```

## Flux utilisateur (frontend)

```
┌────────────┐     ┌────────────────┐     ┌──────────────────┐
│ Visiteur   │     │  mia-site      │     │  veille-backend  │
│ renaudsecq │────▶│  (nginx)       │────▶│  (FastAPI)       │
│ .com       │     │                │     │                  │
│            │     │  Sert HTML/    │     │  GET /api/       │
│ - Homepage │     │  CSS/JS        │     │    linkedin/posts│
│ - Article  │     │                │     │  → JSON avec     │
│ - Veille   │     │  fetch() vers  │     │    image_b64     │
└────────────┘     │  backend API   │     │                  │
                   └────────────────┘     └──────────────────┘
```

## Services GCP

| Service | Nom | Usage |
|---------|-----|-------|
| Cloud Run | `veille-backend` | API FastAPI |
| Cloud Run | `mia-site` | Frontend nginx |
| Cloud Run | `veille-frontend` | (legacy, non utilisé) |
| Firestore | `mia-chatbot-veille` | DB posts, leads, newsletter |
| Secret Manager | `mia-chatbot-veille` | Secrets LinkedIn |
| Artifact Registry | `mia-chatbot-veille` | Images Docker |
| Cloud Build | — | Build des images |
| Domain Mapping | `renaudsecq.com → mia-site` | Domaine personnalisé |

## GitHub Secrets

| Secret | Valeur |
|--------|--------|
| `GCP_PROJECT_ID` | `mia-chatbot-veille` |
| `GCP_SA_KEY` | JSON key de `github-deployer@mia-chatbot-veille.iam.gserviceaccount.com` |

## Rôles IAM (service account github-deployer)

- `roles/run.admin`
- `roles/cloudbuild.builds.editor`
- `roles/iam.serviceAccountUser`
- `roles/storage.admin`
- `roles/artifactregistry.admin`
- `roles/secretmanager.secretAccessor`
