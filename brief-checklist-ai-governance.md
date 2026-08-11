# BRIEF — Checklist AI Governance : 12 points à vérifier avant de déployer

## 1. OBJECTIF

Créer un PDF lead magnet de 4 pages, téléchargeable gratuitement sur renaudsecq.com en échange d'un email. La checklist doit être :
- **Actionnable** : chaque point est vérifiable immédiatement
- **Pédagogique** : un CDO/CTO/Data Engineer qui ne connaît pas encore l'AI Governance doit comprendre l'essentiel
- **Crédible** : niveau expert terrain, pas de bullshit, références réglementaires précises
- **On-brand** : cohérent avec le ton de Renaud Secq (expert qui build ET qui gouverne)

## 2. AUDIENCE CIBLE

- **Primaire** : CDO, CTO, Directors Data/IA dans des entreprises 500-5000 employés
- **Secondaire** : Data Engineers, ML Engineers, DPO, RSSI qui préparent la conformité
- **Niveau** : bon en technique, débutant à intermédiaire en AI Governance
- **Pain point** : "L'EU AI Act arrive, on ne sait pas par où commencer, on a déjà des modèles en prod"

## 3. CHARTRE GRAPHIQUE

### Couleurs (reprendre le site)
| Élément | Couleur | Usage |
|---------|---------|-------|
| Background principal | `#0b1220` | Fond sombre (pages 1 et 4) |
| Background clair | `#f4f6f8` | Fond clair (pages 2 et 3) |
| Accent bleu | `#3b66f5` | Highlights, icônes, numéros |
| Texte sombre | `#0b1220` | Texte sur fond clair |
| Texte clair | `#f4f6f8` | Texte sur fond sombre |
| Gris secondaire | `rgba(11,18,32,.6)` | Texte secondaire sur clair |
| Gris sombre secondaire | `rgba(244,246,248,.5)` | Texte secondaire sur sombre |
| Succès/vert | `#22c55e` | Checkmarks ✓ |
| Danger/rouge | `#ef4444` | Points critiques |

### Typographies (reprendre le site)
- **Titres** : Space Grotesk 700, letter-spacing -0.02em
- **Corps** : Instrument Sans 400/500
- **Code/labels/numéros** : IBM Plex Mono 400/500, letter-spacing 0.08em
- **Style labels** : `[ ENTRE CROCHETS ]` en mono, uppercase, petit (11px équivalent)

### Ton éditorial
- Code-style : `function_name()`, `→ command()`, `[ BRACKETS ]`
- Phrases courtes, percutantes
- Expert terrain, pas consultant en slides
- Français, avec termes techniques en anglais quand c'est l'usage (RAG, MCP, MLOps)

## 4. STRUCTURE DU PDF (4 pages)

---

### PAGE 1 — COUVERTURE (fond sombre #0b1220)

**Layout** : pleine page, centré verticalement

**Haut de page** :
```
[ RESSOURCE GRATUITE — V1.0 ]
```
Petit label mono en bleu `#3b66f5`

**Titre principal** (Space Grotesk 700, très grand) :
```
AI Governance
— 12 points à vérifier
avant de déployer
```

**Sous-titre** (Instrument Sans, gris clair) :
```
L'EU AI Act entre en application. 
Cette checklist vous donne les 12 contrôles 
obligatoires pour passer en production 
sans risque réglementaire.
```

**Bas de page** :
```
par Renaud Secq
Consultant Freelance IA & Data — Builder & Strategist
renaudsecq.com · linkedin.com/in/renaud-secq
```

**Visuel Nana Banana** (à générer) :
- Illustration style "blueprint technique" : un système IA stylisé vu en coupe, avec des points de contrôle numérotés 01-12 disposés autour d'un pipeline (data → model → deployment → monitoring)
- Style : traits fins, blueprint/cyanotype, couleurs limitées à #0b1220, #3b66f5, #f4f6f8
- Ratio : carré ou légèrement portrait, placé en bas ou en arrière-plan translucide

---

### PAGE 2 — LES 12 POINTS (fond clair #f4f6f8)

**En-tête** :
```
[ 01 — LA CHECKLIST ]
Les 12 contrôles obligatoires
```

**Layout** : grille 2 colonnes × 6 lignes, ou 3 colonnes × 4 lignes

Chaque point suit ce format :

```
┌─────────────────────────────┐
│ 01  [CRITIQUE]               │
│ Classification des risques   │
│ EU AI Act                    │
│                              │
│ Identifier si votre système  │
│ est à risque minimal,        │
│ limité, haut ou inacceptable.│
│ → Sans cette étape, tout     │
│   le reste n'a pas de sens.  │
│                              │
│ ✓ Référentiel : Annexes III  │
│   EU AI Act                  │
└─────────────────────────────┘
```

### Les 12 points (contenu complet) — version optimisée

**01 — Classification des risques EU AI Act** `[CRITIQUE]`
> Identifier si votre système est à risque minimal, limité, haut ou inacceptable. C'est la fondation : sans classification, pas d'obligations claires.
> → Vérifier : votre système score-t-il dans l'Annexe III (recrutement, scoring, biométrie, éducation, infrastructure critique) ? Vérifier aussi les pratiques interdites (Art. 5) : social scoring, reconnaissance émotionnelle au travail, manipulation subliminale.
> ✓ Référentiel : Art. 5 & 6, Annexes II & III EU AI Act

**02 — Registre IA & Shadow AI** `[CRITIQUE]`
> Inventorier tous vos systèmes d'IA — y compris ceux que les employés utilisent sans autorisation (ChatGPT, Claude, Copilot, Gemini). Un registre = nom, cas d'usage, modèle, données utilisées, propriétaire, niveau de risque, date de mise en prod.
> → Le Shadow AI est le risk #1. Si vous ne pouvez pas lister vos IA en 1h, vous avez un problème. Détectez les outils non-soumis : extensions navigateur, APIs personnelles, meeting bots.
> ✓ Format : registre interne auditable + politique d'usage IA

**03 — Documentation technique & model cards** `[OBLIGATOIRE]`
> Pour chaque IA à risque élevé : description du système, données d'entraînement, métriques de performance, biais connus, limites d'usage, instructions pour les deployers. Pas d'IA en prod sans fiche technique versionnée.
> → Minimum : 1 model card par système, signée par le business owner + legal + tech. Conservation 10 ans après mise sur le marché.
> ✓ Référentiel : Art. 11 & 13 EU AI Act (Annex IV)

**04 — Évaluation de conformité & FRIA** `[OBLIGATOIRE]`
> Avant la mise en production d'une IA à risque élevé : auto-audit structuré. Tester sur données représentatives, mesurer les taux d'erreur par sous-groupe, documenter. Pour les organismes publics et secteurs crédit/assurance : Fundamental Rights Impact Assessment obligatoire.
> → Pas un audit externe (pas encore), mais un auto-audit structuré avec baseline mesurable avant déploiement.
> ✓ Référentiel : Art. 9, 15 & 27 EU AI Act

**05 — Monitoring post-market & biais** `[CRITIQUE]`
> Une fois en prod, tout dérive : biais, performance, distribution des données. Monitoring continu qui mesure les performances par cohortes (genre, âge, origine), détecte le data drift, et alerte quand un seuil est franchi. Le plan de monitoring post-market doit être documenté avant le go-live.
> → Sans monitoring, vous ne pouvez pas prouver que votre IA reste équitable. Les alertes doivent aller à l'équipe qui peut corriger, pas à une boîte mail que personne ne lit.
> ✓ Référentiel : Art. 12, 15 & 72 EU AI Act | Outils : Fairlearn, Vertex AI Model Monitoring

**06 — Transparence & information utilisateurs** `[OBLIGATOIRE]`
> Les personnes qui interagissent avec une IA doivent savoir qu'elles interagissent avec une IA. Notification claire, explicite, au moment de l'interaction. Le contenu généré par IA (deepfakes, synthetic media) doit être marqué comme tel.
> → Un chatbot doit dire "Je suis une IA", pas se faire passer pour un humain. Les contenus synthétiques doivent être marqués machine-readable.
> ✓ Référentiel : Art. 50 EU AI Act (en vigueur août 2026)

**07 — Contrôle humain & kill-switch** `[OBLIGATOIRE]`
> Pour les IA à risque élevé : un humain peut superviser, interrompre ou outrepasser les décisions. Pas d'IA en mode "pilote automatique" sans circuit de validation. Définir un kill-switch testé, des escalades claires, et les conditions d'arrêt automatique.
> → Définir qui, quand, comment un humain peut stopper le système. Le kill-switch doit être testé en conditions réelles, pas seulement sur papier.
> ✓ Référentiel : Art. 14 EU AI Act

**08 — Cybersécurité, robustesse & vendors IA** `[OBLIGATOIRE]`
> Les systèmes d'IA doivent être protégés contre les attaques (prompt injection, data poisoning, model extraction). Tests de robustesse avant et après déploiement. Pour les outils IA tiers (Copilot, ChatGPT Enterprise) : auditer la rétention des données, le training sur vos données, les sous-traitants, les certifications (SOC 2, ISO 27001).
> → Au minimum : pen-test IA + audit des accès aux données d'entraînement + vendor assessment pour chaque outil IA acheté.
> ✓ Référentiel : Art. 15 EU AI Act + NIST AI RMF + ISO 27001

**09 — Qualité & classification des données** `[CRITIQUE]`
> Garbage in, garbage out — mais aussi "illegal in, illegal out". Vérifier que les données sont : licites, représentatives, pertinentes, exemptes d'erreurs, documentées. Connecter la sensibilité des données (public / interne / confidentiel / restreint) aux outils IA autorisés. Les données personnelles et réglementées exigent des contrôles renforcés.
> → Pas de données grattées sans vérifier le consentement et les biais. Pas de données confidentielles dans ChatGPT sans environnement dédié.
> ✓ Référentiel : Art. 10 EU AI Act + RGPD Art. 5

**10 — RGPD, DPIA & droits des personnes** `[CRITIQUE]`
> Toute IA qui traite des données personnelles doit respecter le RGPD : base légale, minimisation, droit d'information, DPIA si risque élevé. L'AI Act ne remplace pas le RGPD, il s'ajoute. Les personnes ont droit à une explication des décisions automatisées (Art. 86 AI Act).
> → Si votre IA traite des données personnelles sans DPIA, arrêtez tout. Le délai de notification d'incident IA (15 jours, Art. 73) est différent du RGPD (72h, Art. 33) — votre plan doit couvrir les deux.
> ✓ Référentiel : RGPD Art. 22 & 35 + AI Act Art. 73 & 86 + CNIL recommandations IA

**11 — Logging, incidents & change management** `[OBLIGATOIRE]`
> Logger automatiquement chaque décision importante : input, output, timestamp, modèle utilisé, version. En cas d'incident : containment, notification régulateur, rollback, post-mortem. Toute modification de modèle, prompt, ou données déclenche une re-évaluation.
> → Sans logs, pas d'audit possible. Sans plan d'incident testé, pas de réponse possible. Sans change management, une mise à jour peut casser la conformité.
> ✓ Référentiel : Art. 12, 72 & 73 EU AI Act + NIST AI RMF Manage

**12 — Gouvernance, AI literacy & décommissionnement** `[STRATÉGIQUE]`
> Désigner un responsable AI Governance, définir un comité de revue, planifier les audits annuels. Former les équipes à l'AI literacy (obligation Art. 4 déjà en vigueur). Définir les conditions de retrait propre d'un système IA (décommissionnement sans augmentation du risque).
> → Sans propriétaire, rien ne se passe. Nommez quelqu'un. Sans formation, les équipes créent du shadow AI sans le savoir. Sans plan de retrait, un système obsolète reste en prod indéfiniment.
> ✓ Référentiel : Art. 4 EU AI Act + ISO 42001 + NIST AI RMF Govern

---

### PAGE 3 — LE SCHÉMA + L'ESSENTIEL (fond clair #f4f6f8)

**En-tête** :
```
[ 02 — LE PIPELINE ]
D'où viennent les 12 points
```

**Schéma explicatif à faire par Claude Design** :

Un diagramme horizontal type pipeline, 4 étapes connectées par des flèches :

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ GOUVERNE │ ──→ │  DONNÉES │ ──→ │  MODÈLE  │ ──→ │ DÉPLOI.  │ ──→ │ MONITOR. │
│          │     │          │     │          │     │          │     │          │
│ 01 02 12 │     │ 09 10    │     │ 03 04 09 │     │ 02 04 06 │     │ 05 07 08 │
│          │     │          │     │          │     │     11   │     │     11   │
└──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
```

- 5 étapes : Gouverne → Données → Modèle → Déploiement → Monitoring
- Chaque étape est une "carte" avec un titre, une icône simple, et les numéros des points qui s'y appliquent
- Style : traits fins, minimaliste, couleurs du site
- Le pipeline montre que l'AI Governance traverse tout le cycle, ce n'est pas une étape finale

**Sous le schéma — "L'essentiel en 3 minutes"** :

```
SI VOUS NE FAITES QUE 3 CHOSES :
→ 01. Classifiez vos risques et détectez le shadow AI (points 01 & 02)
→ 02. Construisez votre registre IA + politique d'usage (point 02)
→ 03. Mettez du monitoring + kill-switch en prod (points 05 & 07)

LE RESTE S'ENCHAÎNE NATURELLEMENT.
```

**Encart "Sanctions"** (fond #0b1220, texte clair, petit) :
```
[ SANCTIONS EU AI ACT ]
Risque inacceptable : interdiction + amende jusqu'à 35M€ ou 7% CA
Risque élevé non conforme : amende jusqu'à 15M€ ou 3% CA
Autres infractions : amende jusqu'à 7M€ ou 1% CA
```

**Encart "Deadlines"** (fond #0b1220, texte clair, petit, à côté ou sous sanctions) :
```
[ DEADLINES EU AI ACT ]
Pratiques interdites (Art. 5) : en vigueur depuis fév. 2025
AI Literacy (Art. 4) : en vigueur depuis fév. 2025
GPAI (Art. 53) : en vigueur depuis août 2025
Transparence (Art. 50) : août 2026
Risque élevé Annex III : décembre 2027
Risque élevé Annex I : août 2028
```

---

### PAGE 4 — CTA + À PROPOS (fond sombre #0b1220)

**Haut** :
```
[ 03 — PROCHAINES ÉTAPES ]
```

**Titre** :
```
Vous avez la checklist.
Maintenant, passez à l'action.
```

**3 blocs côte à côte** (style cartes avec bordures) :

```
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│ 01                  │  │ 02                  │  │ 03                  │
│ Auto-audit          │  │ Cadrage             │  │ Mise en conformité  │
│                     │  │                     │  │                     │
│ Remplissez la       │  │ 30 min avec moi     │  │ Je vous accompagne  │
│ checklist sur vos   │  │ pour prioriser      │  │ sur 3-6 mois :      │
│ systèmes existants  │  │ vos actions         │  │ registre, doc,      │
│ → 1 à 2 jours       │  │ → gratuit           │  │ monitoring, audits  │
│                     │  │                     │  │ → mission régie     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

**CTA principal** (bouton style site) :
```
→ reserver_30_min() · calendly.com/renaudsecq/30min
```

**Bas de page — À propos** :
```
Renaud Secq
Consultant Freelance IA & Data — Builder & Strategist

20 ans dans le digital. 8 ans freelance grands comptes.
Data Governance → AI Governance → Software Engineering 3.0.
Missions chez Decathlon, Adeo, Auchan, Oney, La Redoute.

renaudsecq.com · linkedin.com/in/renaud-secq · @renaudsecq
```

**Mentions légales footer** (tout petit) :
```
© 2026 Renaissance Digital Consulting — SAS · SIREN 830 153 128
Document gratuit — diffusion autorisée avec citation de la source.
```

---

## 5. VISUELS NANA BANANA — PROMPTS

### Visuel 1 — Couverture (page 1)
```
A technical blueprint-style illustration of an AI governance pipeline. 
Dark navy background (#0b1220). Fine cyan-blue lines (#3b66f5) forming 
a schematic diagram showing: data nodes flowing into a central AI model 
core, then branching to deployment and monitoring checkpoints. 
12 numbered control points (01-12) arranged around the pipeline as 
small circles with numbers. Style: architectural blueprint, 
cyanotype aesthetic, minimal, precise, technical. No text labels 
except numbers. White/light gray accents (#f4f6f8). Square format.
```

### Visuel 2 — Icône pipeline (page 3, alternative au schéma Claude Design)
```
A minimalist flat illustration of a 4-stage AI pipeline: 
data (database cylinder), model (neural network nodes), 
deployment (rocket or server), monitoring (gauge/dashboard). 
Connected by flowing arrows. Colors: blue #3b66f5 on light 
gray #f4f6f8 background. Clean geometric style, no gradients, 
professional tech aesthetic. Wide horizontal format.
```

### Visuel 3 — Décor page 4 (optionnel)
```
Abstract geometric pattern suggesting a governance framework: 
interconnected nodes forming a structured mesh, some nodes 
highlighted in blue #3b66f5. Dark navy #0b1220 background. 
Minimal, technical, elegant. Wide format, low opacity for 
background use.
```

## 6. INSTRUCTIONS POUR CLAUDE DESIGN

### Format de sortie
- PDF A4 portrait, 4 pages
- Print-ready : 300 DPI, marges 15mm
- Export aussi en version web (HTML/CSS ou PDF optimisé écran)

### Hiérarchie visuelle
1. **Numéros 01-12** : très visibles, gros, en bleu `#3b66f5`, mono
2. **Tags** `[CRITIQUE]` / `[OBLIGATOIRE]` / `[STRATÉGIQUE]` : petits, colorés
   - `[CRITIQUE]` → rouge `#ef4444`
   - `[OBLIGATOIRE]` → bleu `#3b66f5`
   - `[STRATÉGIQUE]` → vert `#22c55e`
3. **Titres des points** : Space Grotesk 700, taille moyenne
4. **Descriptions** : Instrument Sans 400, gris secondaire
5. **Flèches →** : accent bleu, mono

### Alternance fond sombre / clair
- Page 1 : sombre `#0b1220` (impact, couverture)
- Page 2 : clair `#f4f6f8` (lisibilité, densité d'info)
- Page 3 : clair `#f4f6f8` (continuité, schéma)
- Page 4 : sombre `#0b1220` (conversion, CTA)

### Détails techniques
- Les 12 points en page 2 doivent tenir sur une seule page → utiliser une grille compacte 3×4 ou 2×6
- Chaque point : numéro + tag + titre + description courte (max 3 lignes) + réf réglementaire
- Le schéma page 3 doit être lisible même imprimé en N&B
- Ajouter un QR code en page 4 pointant vers `renaudsecq.com/#contact`

## 7. CHECKLIST QUALITÉ AVANT PUBLICATION

- [ ] Les 12 points couvrent l'intégralité du cycle (data → model → deploy → monitor)
- [ ] Chaque point renvoie à un article précis de l'EU AI Act ou du RGPD
- [ ] Le ton est cohérent avec le site (expert terrain, pas bullshit)
- [ ] Aucun jargon non expliqué
- [ ] Le CTA Calendly est visible et cliquable (ou QR code)
- [ ] Testé en impression N&B
- [ ] Version mobile lisible (si HTML)
- [ ] Mentions légales présentes
