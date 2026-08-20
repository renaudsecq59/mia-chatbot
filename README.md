# renaudsecq.com — Portfolio & Veille IA

Site portfolio de Renaud Secq, consultant freelance IA & Data, avec backend de veille IA automatisée (scraping RSS, génération de posts LinkedIn via LLM, publication automatique).

## Architecture

Voir [ARCHITECTURE.md](./ARCHITECTURE.md) pour le schéma détaillé.

```
renaudsecq.com (domaine)
    │
    ├── Frontend (Cloud Run: mia-site)
    │   ├── nginx + HTML/CSS/JS vanilla
    │   ├── index.html, article.html, veille.html, etc.
    │   └── Dockerfile (nginx:alpine)
    │
    └── Backend (Cloud Run: veille-backend)
        ├── FastAPI (Python)
        ├── /api/linkedin/posts — liste des posts publiés
        ├── /api/newsletter/subscribe — inscription newsletter
        ├── /api/livre-blanc/download — lead capture + PDF
        └── Firestore — stockage posts, leads, newsletter
```

## Déploiement

**Automatique via GitHub Actions** — push sur `main` déclenche :

| Job | Service Cloud Run | Condition | Build |
|-----|-------------------|-----------|-------|
| `deploy-backend` | `veille-backend` | Si `backend/**` modifié | `backend/Dockerfile` |
| `deploy-frontend` | `mia-site` | Toujours | `Dockerfile` racine (nginx) |

### Prérequis (GitHub Secrets)

| Secret | Description |
|--------|-------------|
| `GCP_PROJECT_ID` | `mia-chatbot-veille` |
| `GCP_SA_KEY` | JSON key du service account `github-deployer@mia-chatbot-veille.iam.gserviceaccount.com` |

### Service account GCP

Le service account `github-deployer@mia-chatbot-veille.iam.gserviceaccount.com` doit avoir les rôles :
- `roles/run.admin` — déployer sur Cloud Run
- `roles/cloudbuild.builds.editor` — build les images
- `roles/iam.serviceAccountUser` — utiliser les SA de runtime
- `roles/storage.admin` — stockage des sources de build
- `roles/artifactregistry.admin` — push des images Docker
- `roles/secretmanager.secretAccessor` — accès aux secrets

### Secrets GCP (Secret Manager)

| Secret | Usage |
|--------|-------|
| `LINKEDIN_ACCESS_TOKEN` | Token API LinkedIn |
| `LINKEDIN_PERSON_URN` | `urn:li:person:W65nyyQ59M` |

### Domaine

`renaudsecq.com` est un **domain mapping Cloud Run** pointant vers le service `mia-site` (pas Firebase Hosting).

## Structure du repo

```
.
├── index.html              # Page d'accueil
├── article.html            # Page article (post LinkedIn individuel)
├── veille.html             # Page liste des articles de veille
├── confidentialite.html    # Page confidentialité
├── mia-agency.html         # Page offres
├── etudes-de-cas.html      # Page études de cas
├── preview.html            # Page preview
├── callback.html           # Callback OAuth
├── favicon.svg             # Favicon
├── robots.txt              # SEO
├── sitemap.xml             # SEO
├── photo-000.jpg           # Photo de profil
├── Dockerfile              # Image frontend (nginx:alpine)
├── nginx.conf              # Config nginx
├── .github/workflows/
│   ├── deploy.yml          # CI/CD Cloud Run (backend + frontend)
│   └── ci.yml              # Lint + tests + audit
├── backend/
│   ├── main.py             # API FastAPI
│   ├── linkedin_publisher.py  # Publication LinkedIn
│   ├── Dockerfile          # Image backend
│   ├── requirements.txt    # Dépendances Python
│   └── tests/              # Tests pytest
├── livreblanc/             # PDFs lead magnet
├── plan.md                 # Suivi des actions
└── ARCHITECTURE.md         # Schéma d'architecture
```

## Développement local

### Frontend
```bash
# Servir localement avec nginx ou python
python3 -m http.server 8080
# Ouvrir http://localhost:8080
```

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Stack

- **Frontend** : HTML/CSS/JS vanilla, fonts Google (Space Grotesk, IBM Plex Mono, Instrument Sans)
- **Backend** : Python, FastAPI, Firestore
- **LLM** : Gemini (génération de posts), Google Sheets (sources RSS)
- **Infra** : GCP Cloud Run, Secret Manager, Artifact Registry
- **CI/CD** : GitHub Actions
- **Domaine** : renaudsecq.com (domain mapping Cloud Run)
