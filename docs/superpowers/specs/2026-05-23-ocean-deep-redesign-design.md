# Spec — Redesign "Océan Profond" (Design 2)

**Date :** 2026-05-23
**Périmètre :** Toute l'app React (frontend/)
**Approche CSS :** Tailwind étendu (tokens dans tailwind.config.js)
**Fonts :** Google Fonts CDN
**Animations :** Transitions hover/focus simples uniquement

---

## 1. Système de tokens (tailwind.config.js + index.html)

### 1.1 Palette ocean dans tailwind.config.js

```js
colors: {
  ocean: {
    deep:   '#040d1a',   // fond global (body/Layout)
    navy:   '#071428',   // sidebar, headers
    panel:  '#0a1c35',   // cartes, surfaces élevées
    border: 'rgba(0,200,255,0.08)', // bordures subtiles
    glow:   'rgba(0,200,255,0.15)', // box-shadow accent
    cyan:   '#00c8ff',   // accent primaire, liens actifs
    teal:   '#00e5c0',   // accent secondaire, tendances +
    coral:  '#ff6b6b',   // alertes, urgences, erreurs
    gold:   '#ffd700',   // avertissements, délais proches
    text:   '#ddeeff',   // texte principal
    muted:  'rgba(150,200,240,0.4)', // texte secondaire
  }
}
```

### 1.2 Familles de polices dans tailwind.config.js

```js
fontFamily: {
  serif: ['Playfair Display', 'Georgia', 'serif'],
  sans:  ['DM Sans', 'system-ui', 'sans-serif'],
  mono:  ['DM Mono', 'Inconsolata', 'monospace'],
}
```

### 1.3 Google Fonts dans index.html

```html
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
```

---

## 2. Layout.jsx

| Élément | Classe Tailwind |
|---|---|
| Fond global | `bg-ocean-deep` |
| Header 52px | `bg-ocean-navy border-b border-ocean-border` |
| Titre page | `font-serif text-xl font-bold text-ocean-text` |
| `<main>` | `bg-ocean-deep` |

Le header affiche : titre de page (Playfair Display) + date courante à droite en `font-mono text-xs text-ocean-muted`.

---

## 3. Sidebar.jsx

### 3.1 Structure générale
- Largeur 260px
- Fond : `bg-gradient-to-b from-ocean-navy to-ocean-deep`
- Bordure droite : `border-r border-ocean-border`

### 3.2 Zone logo
- Icône ronde 44px : `bg-gradient-to-br from-ocean-cyan/20 to-ocean-teal/10 border border-ocean-cyan/25 rounded-xl`
- Texte "OI" : `font-serif text-ocean-cyan`
- Titre "DEF Océan Indien" : `font-serif font-bold text-ocean-text`
- Sous-titre "Veille Marchés" : `font-sans text-xs uppercase tracking-widest text-ocean-muted`
- Capsule statut : fond `bg-ocean-teal/8 border border-ocean-teal/15 rounded-full`, point pulse `bg-ocean-teal animate-pulse`, texte `font-mono text-xs text-ocean-teal`

### 3.3 Navigation
Chaque `NavItem` :
- Inactif : `text-ocean-muted hover:text-ocean-text hover:bg-ocean-cyan/4`
- Actif : `text-ocean-cyan bg-gradient-to-r from-ocean-cyan/8 to-transparent border-l-2 border-ocean-cyan`
- Icône wrap : `w-7 h-7 rounded-lg bg-white/5 border border-white/6` — actif : `bg-ocean-cyan/15 border-ocean-cyan/30`
- Badge urgences : `bg-ocean-coral text-white rounded-full text-xs shadow shadow-ocean-coral/40`

### 3.4 Section Collecte
- Sources : chips `font-mono text-xs`, inactif `bg-ocean-cyan/5 border border-ocean-cyan/12 text-ocean-muted`, actif `bg-ocean-cyan/12 border-ocean-cyan/30 text-ocean-cyan`
- Bouton Collecte : `bg-gradient-to-r from-ocean-cyan/12 to-ocean-teal/8 border border-ocean-cyan/20 text-ocean-cyan rounded-lg hover:shadow hover:shadow-ocean-cyan/15`
- Sources verrouillées : `opacity-30 cursor-not-allowed`

---

## 4. KpiGrid.jsx

- Grille 5 colonnes (md), gap 14px
- Carte : `bg-ocean-panel border border-ocean-border rounded-xl p-5`
- Hover : `hover:-translate-y-0.5 hover:shadow-lg hover:shadow-ocean-cyan/6 transition-all duration-200`
- Bande colorée 3px en haut par KPI :

| KPI | Couleur bande |
|---|---|
| Total marchés | `border-t-2 border-ocean-cyan` |
| À qualifier | `border-t-2 border-ocean-muted` |
| En cours | `border-t-2 border-ocean-teal` |
| Soumis | `border-t-2 border-ocean-gold` |
| Gagnés | `border-t-2 border-ocean-teal` |

- Label : `font-sans text-xs uppercase tracking-widest text-ocean-muted`
- Valeur : `font-serif text-4xl font-bold text-ocean-text`
- Skeleton chargement : `bg-ocean-panel/50 animate-pulse rounded-xl`

---

## 5. TendersTable.jsx

### 5.1 Conteneur
`bg-ocean-panel border border-ocean-border rounded-xl overflow-hidden`

### 5.2 Toolbar
- Titre : `font-serif text-base font-semibold text-ocean-text`
- Compteur pill : `bg-ocean-cyan/8 border border-ocean-cyan/12 rounded-full font-mono text-xs text-ocean-cyan/60`
- Search input : `bg-ocean-navy border border-ocean-border rounded-lg font-sans text-sm text-ocean-text placeholder:text-ocean-muted focus:border-ocean-cyan/20`

### 5.3 Filtres (pills)
- Inactif : `border border-ocean-border text-ocean-muted hover:border-ocean-cyan/20 hover:text-ocean-text`
- Actif : `bg-ocean-cyan/10 border-ocean-cyan/25 text-ocean-cyan`

### 5.4 Table
- En-têtes `th` : `font-mono text-xs uppercase tracking-widest text-ocean-muted bg-black/20`
- Cellules `td` : `font-sans text-xs text-ocean-text/80 border-b border-ocean-cyan/4`
- Hover ligne : `hover:bg-ocean-cyan/2 cursor-pointer transition-colors`

### 5.5 Badges statut
| Statut | Style |
|---|---|
| Nouveau | `bg-ocean-cyan/8 text-ocean-cyan` |
| En cours | `bg-ocean-gold/10 text-ocean-gold` |
| Soumis | `bg-ocean-teal/10 text-ocean-teal` |
| Analyse IA | `bg-white/5 text-ocean-muted` |

### 5.6 Score IA (si colonne présente)
Mini barre : `bg-white/6 rounded-full h-1`, fill `bg-gradient-to-r from-ocean-cyan to-ocean-teal`

---

## 6. TenderDetail.jsx

- Overlay : `bg-ocean-panel border border-ocean-border rounded-xl`
- Titre : `font-serif font-semibold text-ocean-text`
- Labels : `font-sans text-xs uppercase tracking-widest text-ocean-muted`
- Valeurs : `font-mono text-sm text-ocean-text/80`
- Bouton fermeture : `text-ocean-muted hover:text-ocean-text transition-colors`

---

## 7. Pages

### 7.1 Dashboard.jsx
Aucun changement logique. Padding 24px, fond hérité `ocean-deep`.

### 7.2 Analytics.jsx
- Conteneurs graphiques Recharts : `bg-ocean-panel border border-ocean-border rounded-xl`
- Couleurs de séries Recharts : cyan `#00c8ff`, teal `#00e5c0`, coral `#ff6b6b`, gold `#ffd700`
- Axes/grilles Recharts : `stroke="rgba(0,200,255,0.1)"`

### 7.3 Direction.jsx + Guide.jsx
- Titres h1/h2 : `font-serif`
- Corps : `font-sans text-ocean-text`
- Texte secondaire : `text-ocean-muted`

### 7.4 Urgences.jsx + UrgenceCard.jsx
- Cartes : fond `ocean-panel`, accent gauche `border-l-2 border-ocean-coral`
- Badge compteur : `bg-ocean-coral text-white`
- Texte urgence : `text-ocean-coral` pour les délais proches

### 7.5 Parametres.jsx
- Tabs actifs : `border-b-2 border-ocean-cyan text-ocean-cyan`
- Inputs : `bg-ocean-navy border border-ocean-border text-ocean-text focus:border-ocean-cyan/30`
- Boutons d'action primaires : `bg-ocean-cyan/12 border border-ocean-cyan/20 text-ocean-cyan hover:bg-ocean-cyan/18`
- `DuplicatePair.jsx` : fond `ocean-panel`, bordures `ocean-border`

---

## 8. Ordre d'implémentation et commits git

Selon la règle projet (un commit par fichier) :

1. `frontend/tailwind.config.js` — ajout palette ocean + fontFamily
2. `frontend/index.html` — ajout Google Fonts CDN
3. `frontend/src/components/Layout.jsx` — thème ocean
4. `frontend/src/components/Sidebar.jsx` — thème ocean complet
5. `frontend/src/components/KpiGrid.jsx` — thème ocean
6. `frontend/src/components/TendersTable.jsx` — thème ocean
7. `frontend/src/components/TenderDetail.jsx` — thème ocean
8. `frontend/src/components/UrgenceCard.jsx` — thème ocean
9. `frontend/src/components/DuplicatePair.jsx` — thème ocean
10. `frontend/src/pages/Dashboard.jsx` — ajustements padding/fond si nécessaire
11. `frontend/src/pages/Analytics.jsx` — couleurs Recharts
12. `frontend/src/pages/Direction.jsx` — typographie
13. `frontend/src/pages/Guide.jsx` — typographie
14. `frontend/src/pages/Urgences.jsx` — thème ocean
15. `frontend/src/pages/Parametres.jsx` — thème ocean complet

---

## 9. Ce qui ne change pas

- Logique métier, hooks, API calls : aucune modification
- Structure des composants (props, états) : inchangée
- Tests existants : aucun test visuel, pas d'impact sur les tests unitaires
- `scraper_*.py`, `backend/main.py` : non concernés
