# Spec — Personnalisation des couleurs via Paramètres

**Date :** 2026-05-23  
**Statut :** Approuvé

## Résumé

Ajouter un onglet "Apparence" dans `Parametres.jsx` permettant à l'utilisateur de modifier 4 couleurs clés de l'interface via des sélecteurs natifs `<input type="color">`. Les couleurs sont appliquées immédiatement via des variables CSS et persistées en `localStorage`.

---

## Architecture

### Approche : Variables CSS + localStorage

L'approche choisie est la seule à supporter les modificateurs d'opacité Tailwind (`bg-ocean-cyan/20`, etc.) tout en permettant un changement en temps réel sans rebuild.

**Format des variables :** les couleurs configurables sont stockées en canaux RGB séparés (format `R G B`) dans les variables CSS, ce qui permet à Tailwind d'injecter l'opacité via `rgb(var(--color-X) / <alpha-value>)`.

---

## Fichiers modifiés

### 1. `frontend/src/index.css`

Ajouter les variables CSS par défaut dans `:root` :

```css
:root {
  --color-ocean-deep:  4 13 26;       /* #040d1a */
  --color-ocean-cyan:  0 200 255;     /* #00c8ff */
  --color-ocean-coral: 255 107 107;   /* #ff6b6b */
  --color-ocean-text:  221 238 255;   /* #ddeeff */
}
```

Les couleurs `navy`, `panel`, `border`, `glow`, `teal`, `gold`, `muted` restent en valeurs fixes dans `tailwind.config.js` (non exposées à l'utilisateur).

### 2. `frontend/tailwind.config.js`

Convertir les 4 couleurs configurables au format `rgb(var(...) / <alpha-value>)` :

```js
ocean: {
  deep:   'rgb(var(--color-ocean-deep) / <alpha-value>)',
  cyan:   'rgb(var(--color-ocean-cyan) / <alpha-value>)',
  coral:  'rgb(var(--color-ocean-coral) / <alpha-value>)',
  text:   'rgb(var(--color-ocean-text) / <alpha-value>)',
  // Couleurs fixes (inchangées) :
  navy:   '#071428',
  panel:  '#0a1c35',
  border: 'rgba(0,200,255,0.08)',
  glow:   'rgba(0,200,255,0.15)',
  teal:   '#00e5c0',
  gold:   '#ffd700',
  muted:  'rgba(150,200,240,0.4)',
}
```

### 3. `frontend/src/main.jsx`

Au démarrage de l'app, charger les couleurs sauvegardées depuis `localStorage` et les appliquer sur `document.documentElement` avant le premier rendu :

```js
const THEME_KEY = 'theme-colors'
const DEFAULTS = {
  deep:  '4 13 26',
  cyan:  '0 200 255',
  coral: '255 107 107',
  text:  '221 238 255',
}

function applyTheme(colors) {
  for (const [key, val] of Object.entries(colors)) {
    document.documentElement.style.setProperty(`--color-ocean-${key}`, val)
  }
}

const saved = JSON.parse(localStorage.getItem(THEME_KEY) || 'null')
applyTheme(saved ?? DEFAULTS)
```

### 4. `frontend/src/pages/Parametres.jsx`

Ajouter un onglet `🎨 Apparence` avec un composant `ApparenceTab` contenant :

**4 sélecteurs de couleur :**

| Label | Variable CSS | Défaut |
|---|---|---|
| Fond | `--color-ocean-deep` | `#040d1a` |
| Couleur principale | `--color-ocean-cyan` | `#00c8ff` |
| Alerte | `--color-ocean-coral` | `#ff6b6b` |
| Texte | `--color-ocean-text` | `#ddeeff` |

**Comportement :**
- `onChange` sur chaque `<input type="color">` : convertit le hex → format `R G B`, applique la variable CSS immédiatement sur `document.documentElement`
- Bouton **Appliquer** : sauvegarde l'état courant en `localStorage` sous la clé `theme-colors`
- Bouton **Réinitialiser** : remet les 4 valeurs par défaut, applique et efface `localStorage`
- **Aperçu en direct** : un mini-bandeau de prévisualisation sous les sélecteurs (bouton, badge, texte)

**Conversion hex → RGB :**

```js
function hexToRgbString(hex) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `${r} ${g} ${b}`
}
```

---

## Persistance

- Clé localStorage : `theme-colors`
- Valeur : objet JSON `{ deep, cyan, coral, text }` en format `"R G B"`
- Chargement au démarrage dans `main.jsx` (avant le rendu React)
- Aucune API backend : tout est côté client

---

## Ce qui n'est pas inclus

- Thèmes prédéfinis (hors scope)
- Modification de `navy`, `panel`, `border`, `teal`, `gold`, `muted` (hors scope)
- Synchronisation multi-onglets (hors scope)
