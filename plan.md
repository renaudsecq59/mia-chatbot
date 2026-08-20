# Plan — renaudsecq.com & veille IA

Suivi des actions du site portfolio + backend veille IA & Data.
Rôles : `chef-de-projet`, `developpeur`, `ux-designer`.

Voir [ARCHITECTURE.md](./ARCHITECTURE.md) pour le schéma d'architecture.
Voir [README.md](./README.md) pour la documentation GitHub.

---

## Actions effectuées

### Site & SEO
- [x] Open Graph, Twitter Card, JSON-LD Schema.org sur 5 pages
- [x] Google Analytics 4 (G-FBBW1K1RJW)
- [x] robots.txt + sitemap.xml
- [x] Correction note interne éditoriale dans index.html (section PREUVES)

### Backend veille IA
- [x] 60 sources RSS (premium + Medium + Google News), 337 articles scrapés
- [x] Prompt LinkedIn : persona reader, few-shot examples, critic loop, research agent, fact-checker
- [x] Déduplication : threshold 0.75, post_history 10
- [x] Déploiement Cloud Run : `https://veille-backend-791183172510.europe-west1.run.app`
- [x] Endpoint newsletter `/api/newsletter/subscribe`
- [x] Endpoint livre blanc `/api/livre-blanc/download` (lead capture + PDF)
- [x] Endpoint `/api/linkedin/posts` retourne `image_b64` pour affichage frontend

### Lead magnet — Livre blanc AI Governance
- [x] PDF créé : `livreblanc/AIgovernance-renaudsecq-12pointsaverifier.pdf`
- [x] Section livre blanc dans index.html avec formulaire (prénom, nom, société, email)
- [x] Opt-in newsletter optionnel dans le formulaire
- [x] Validation backend : tous les champs obligatoires
- [x] Stockage des leads dans Firestore (`livre_blanc_leads`)
- [x] Téléchargement automatique du PDF après soumission
- [x] Backend déployé et testé (curl OK)

### LinkedIn
- [x] Analyse de 20 posts (top : Gaspillage infra 213 impressions, Synthèse hebdo 178 impressions + 5 likes)
- [x] Vanity URL confirmée : `renaud-secq-5593832a`
- [x] Credentials dans GCP Secret Manager
- [x] Publication via nouvelle API `/rest/posts` (image upload + post)
- [x] Génération visuels via Gemini 3 Pro Image
- [x] **Fix troncature texte** : 1250 chars max si image attachée, 3000 sans image
- [x] Troncature propre à la dernière phrase complète avant la limite

### Frontend — Homepage & Articles
- [x] Cards veille HP : titre (1ère ligne du post_text), image thumbnail, tag, date
- [x] **Fix UX cards** : images en `object-fit: cover` (240px desktop, 200px mobile)
- [x] Titres clampés à 2 lignes max (`-webkit-line-clamp: 2`)
- [x] Grid responsive : 3 colonnes desktop → 1 colonne mobile
- [x] Cards de hauteur uniforme
- [x] `article.html` affiche l'image via `image_b64` de l'API
- [x] Hover states avec translateY + shadow + border color

### CI/CD & Déploiement
- [x] GitHub Actions CI : lint ruff + tests pytest + audit pip-audit + SonarCloud
- [x] GitHub Actions deploy backend : auto Cloud Run `veille-backend` si `backend/**` modifié
- [x] GitHub Actions deploy frontend : auto Cloud Run `mia-site` (nginx Dockerfile) à chaque push
- [x] Service account GCP `github-deployer` créé avec rôles IAM nécessaires
- [x] GitHub Secrets : `GCP_PROJECT_ID`, `GCP_SA_KEY` configurés
- [x] Secrets LinkedIn injectés via `--set-secrets` (Secret Manager)
- [x] Domain mapping `renaudsecq.com → mia-site` (Cloud Run, pas Firebase)
- [x] `ruff.toml` — config lint (Python 3.11, règles E/W/F/I/B/UP/C4/S)
- [x] `backend/requirements-dev.txt` — deps de dev (ruff, pytest, pip-audit)
- [x] `backend/pytest.ini` — config tests
- [x] `backend/tests/` — 9 tests (health, livre blanc, newsletter) — tous passent
- [x] `sonar-project.properties` — config SonarCloud
- [x] Lint ruff : 0 erreur après auto-fix

### Documentation
- [x] README.md — documentation GitHub complète
- [x] ARCHITECTURE.md — schéma d'architecture (flux déploiement, flux LinkedIn, flux utilisateur)
- [x] Rôles définis : Développeur, UX Designer, Chef de projet (avec instructions déploiement)

---

## Actions à faire

### LinkedIn API
- [ ] Créer une nouvelle app LinkedIn avec Community Management API pour `r_member_social`
- [ ] Activer les métriques d'engagement via API

### SEO & Indexation
- [ ] Soumettre le sitemap à Google Search Console
- [ ] Vérifier l'indexation des nouvelles pages

### Marketing & Contenu
- [ ] Planifier une campagne LinkedIn pour promouvoir le livre blanc
- [ ] Créer un post LinkedIn dédié au lancement du livre blanc
- [ ] Étudier l'ajout d'autres lead magnets (webinar replay, template audit)

### Sécurité
- [ ] Auditer les règles Firestore (collection `livre_blanc_leads` en lecture publique ?)
- [ ] Vérifier le rate-limiting sur l'endpoint `/api/livre-blanc/download`
- [ ] Confirmer que le PDF n'est pas accessible sans formulaire (URL devinable)

### UX
- [ ] Tester le formulaire livre blanc sur mobile
- [ ] Ajouter un message de confirmation plus riche après téléchargement
- [ ] Étudier un A/B test sur le titre du livre blanc
- [ ] **Action user** : Créer compte SonarCloud → lier repo → ajouter `SONAR_TOKEN` dans GitHub Secrets

---

## Dernière mise à jour
2026-08-20 — Fix UX cards HP + CI/CD Cloud Run (mia-site) + documentation
