---
description: Create a white paper / lead magnet PDF brief for Claude Design
---

# Workflow : Création de livre blanc / lead magnet

## Contexte
Créer un brief complet pour un livre blanc PDF (4 pages) destiné à être donné à Claude Design pour la mise en page. Le brief doit contenir tous les contenus, la charte graphique, et les instructions de design.

## Étapes

### 1. Recherche du sujet
- Faire une recherche web sur les meilleurs contenus publiés sur le sujet (au moins 2-3 searches)
- Identifier les frameworks, chiffres clés, et sources crédibles
- Analyser ce que les concurrents/experts disent et trouver l'angle unique

### 2. Définir la structure
- **Pas obligé de faire 12 points** — adapter au sujet. Peut être 7, 10, 15, ou organisé différemment (phases, layers, piliers)
- Choisir une structure qui sert le sujet, pas l'inverse
- Toujours 4 pages : couverture / contenu / schéma+essentiel / CTA

### 3. Rédiger les contenus — RÈGLES DE COPYWRITING

#### Niveau de langage
- **Cible : néophyte éclairé**, pas expert. Le lecteur est un décideur (CDO, CTO, Director) qui découvre le sujet
- **Pas de jargon non expliqué** — définir chaque terme technique à sa 1ère occurrence
- **Phrases courtes, concrètes, avec des exemples**
- **Éviter l'abstraction** — toujours donner un exemple réel
- **Ton : expert terrain qui vulgarise sans dumbing down**

#### Structure de chaque point
- **Titre** : clair, pas jargon
- **1 phrase** : qu'est-ce que c'est (simple)
- **1 phrase** : pourquoi c'est important (le problème que ça résout)
- **1 phrase** : comment faire concrètement (action)
- **Référentiel** : source ou framework

#### Page 3 — Éléments obligatoires
1. **Schéma visuel** du framework (pipeline, stack, cycle, etc.)
2. **"L'essentiel en 3 minutes"** — les 3 actions prioritaires
3. **Auto-évaluation / barème** — un système de score qui permet au lecteur de se situer
   - Exemple : compter combien de points sont déjà en place
   - 3 paliers : débutant / intermédiaire / mature
   - Chaque palier renvoie vers le CTA de la page 4
4. **Encart chiffres clés** ou **encart comparatif** selon le sujet

#### Page 4 — CTA
- 3 blocs : audit / cadrage gratuit / mission
- CTA Calendly
- À propos + mentions légales

### 4. Charte graphique (commune à tous les livres blancs)

#### Couleurs
- Background sombre : `#0b1220` (pages 1 et 4)
- Background clair : `#f4f6f8` (pages 2 et 3)
- Accent bleu : `#3b66f5`
- Accent secondaire : varie selon le livre blanc (violet `#8b5cf6`, vert, orange...)
- Texte sombre : `#0b1220`
- Texte clair : `#f4f6f8`
- Tags : `[CRITIQUE]` rouge `#ef4444`, `[OBLIGATOIRE]` bleu, `[STRATÉGIQUE]` vert `#22c55e`

#### Typographies
- Titres : Space Grotesk 700
- Corps : Instrument Sans 400/500
- Code/labels : IBM Plex Mono 400/500

#### Ton éditorial
- Code-style : `function_name()`, `→ command()`, `[ BRACKETS ]`
- Phrases courtes, percutantes
- Expert terrain, pas bullshit
- Français, termes techniques en anglais quand usage standard

### 5. Différenciation entre livres blancs
- Chaque livre blanc a un **accent secondaire** différent
- Chaque livre blanc a un **type de schéma** différent (pipeline, stack, cycle, matrice...)
- Le tag de couverture varie : "RESSOURCE GRATUITE", "LIVRE BLANC", "GUIDE PRATIQUE"...

### 6. Checklist qualité avant finalisation
- [ ] Un néophyte peut comprendre chaque point sans recherche externe
- [ ] Chaque terme technique est défini à sa 1ère occurrence
- [ ] Les textes sont rédigés par un copywriter, pas par un ingénieur
- [ ] La page 3 a un barème d'auto-évaluation
- [ ] La page 3 n'est pas vide — au moins 3 éléments (schéma + essentiel + auto-éval + encart)
- [ ] Le CTA est clair et actionnable
- [ ] Les sources/frameworks sont cités
- [ ] La différenciation visuelle avec les autres livres blancs est claire

### 7. Output
- Un fichier `brief-[sujet].md` à la racine du projet
- Contenu complet prêt à donner à Claude Design
- Pas de génération de visuels (fait par Claude Design directement)
