# Plan — renaudsecq.com & veille IA

Suivi des actions du site portfolio + backend veille IA & Data.
Agents disponibles : `chef-de-projet`, `developpeur`, `ux-designer`, `security`, `marketing`.

---

## Actions effectuées

### Site & SEO
- [x] Open Graph, Twitter Card, JSON-LD Schema.org sur 5 pages
- [x] Google Analytics 4 (G-FBBW1K1RJW)
- [x] robots.txt + sitemap.xml
- [x] Correction note interne éditoriale dans index.html (section PREUVES)
- [x] Exclusion `newdesing/` du déploiement (amplify.yml + firebase.json)

### Backend veille IA
- [x] 60 sources RSS (premium + Medium + Google News), 337 articles scrapés
- [x] Prompt LinkedIn : persona reader, few-shot examples, critic loop, research agent, fact-checker
- [x] Déduplication : threshold 0.75, post_history 10
- [x] Déploiement Cloud Run : `https://veille-backend-791183172510.europe-west1.run.app`
- [x] Endpoint newsletter `/api/newsletter/subscribe`
- [x] Endpoint livre blanc `/api/livre-blanc/download` (lead capture + PDF)

### Lead magnet — Livre blanc AI Governance
- [x] PDF créé : `livreblanc/AIgovernance-renaudsecq-12pointsaverifier.pdf`
- [x] Section livre blanc dans index.html avec formulaire (prénom, nom, société, email)
- [x] Opt-in newsletter optionnel dans le formulaire
- [x] Validation backend : tous les champs obligatoires
- [x] Stockage des leads dans Firestore (`livre_blanc_leads`)
- [x] Téléchargement automatique du PDF après soumission
- [x] Backend déployé et testé (curl OK)
- [x] Commit + push sur main

### LinkedIn
- [x] Analyse de 20 posts (top : Gaspillage infra 213 impressions, Synthèse hebdo 178 impressions + 5 likes)
- [x] Vanity URL confirmée : `renaud-secq-5593832a`
- [x] Credentials dans GCP Secret Manager

---

## Actions à faire

### Lead magnet — Livre blanc
- [ ] Vérifier que `https://renaudsecq.com` affiche bien la nouvelle section (après déploiement Amplify)
- [ ] Tester le formulaire en production (téléchargement PDF réel)
- [ ] Configurer un email automatique de suivi aux leads (welcome + PDF en pièce jointe)
- [ ] Créer d'autres livres blancs (Context Layer, Data Governance checklist)

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
- [ ] Tester le formulaire sur mobile
- [ ] Ajouter un message de confirmation plus riche après téléchargement
- [ ] Étudier un A/B test sur le titre du livre blanc

---

## Dernière mise à jour
2026-08-11 — Ajout livre blanc + agents
