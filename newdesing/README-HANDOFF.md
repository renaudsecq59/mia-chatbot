# Site Renaud Secq — Handoff Windsurf / mise en prod

## Contenu du projet
- `Renaud Secq - Site.dc.html` — page d'accueil (hero canvas animé, piliers, preuves, méthode, offres, FAQ, contact)
- `Etudes de cas.dc.html` — 5 études de cas détaillées avec schémas SVG "blueprint" (FIG.01–05)
- `Veille.dc.html` — liste des articles (contenu d'exemple à remplacer)
- `Article.dc.html` — gabarit de page article (contenu d'exemple)
- `support.js` — runtime des fichiers .dc.html (nécessaire pour les ouvrir tels quels)
- `image-slot.js` — placeholder d'images drag & drop (portrait, visuels articles)
- `Article — standalone.html` — exemple d'export autonome (généré, ne pas éditer)
- `Refonte Directions.dc.html` — explorations design initiales (archive, pas à déployer)

## ⚠ Format .dc.html
Les pages utilisent un format de composant maison : un template dans `<x-dc>` + une classe logique JS, rendus par `support.js` (React). Deux options pour la prod :
1. **Conversion en HTML statique standard** (recommandé) : extraire le markup, remplacer les holes `{{ }}` et `sc-for`/`sc-if` par du HTML/JS vanilla, réécrire la logique (curseur custom, reveals au scroll, compteurs, canvas réseau du hero, formulaire) en script classique. Tout le style est déjà inline — aucune dépendance CSS externe hors Google Fonts.
2. Garder tel quel avec `support.js` servi à côté (fonctionne, mais runtime non standard).

## Direction artistique (image de marque)
- Fond clair `#f4f6f8`, encre `#0b1220`, accent bleu électrique `oklch(0.55 0.19 255)` (~`#3b66f5`), accent clair sur fond sombre `oklch(0.75 0.17 255)`
- Fontes : Space Grotesk (titres), Instrument Sans (texte), IBM Plex Mono (labels/UI, style `snake_case()`)
- Signature visuelle : schémas "blueprint" — fond encre, grille 40px, tracés bleus animés (dasharray + keyframes `flow`), labels FIG.0X
- Ton copy : direct, orienté DSI/CDO, "production réelle, pas des slides"

## Données vérifiées (ne pas inventer au-delà)
- Contact : renaudsecq@gmail.com · Calendly https://calendly.com/renaudsecq/30min · LinkedIn /in/renaud-secq-5593832a (20k abonnés)
- Dispo missions longues : décembre 2026
- Mentions légales : RENAISSANCE DIGITAL CONSULTING, SAS, SIREN 830 153 128, TVA FR13 830 153 128, 2 allée du Vert Galant 59840 Lompret, NAF 62.02A, RNE 2017
- Clients citables : Decathlon, Adeo, Auchan, Oney, La Redoute, Fnac, Publicis, Experian

## Chantiers restants (par priorité)
1. **Responsive mobile** — grilles desktop uniquement, débordent sur mobile
2. **Formulaire de contact** — actuellement mailto ; brancher Formspree/équivalent
3. **SEO** — title/description par page, Open Graph (partages LinkedIn), favicon, schema.org Person
4. **Version EN** — le toggle FR/EN dans la nav est décoratif
5. **Contenu à fournir par Renaud** : témoignage client nominatif (encart placeholder dans Preuves), portrait (image-slot "portrait"), vrais articles Veille, relecture FAQ
6. Page mentions légales & confidentialité dédiée
7. Mini-schémas blueprint sur la home (déclinaison des FIG. des études de cas)
