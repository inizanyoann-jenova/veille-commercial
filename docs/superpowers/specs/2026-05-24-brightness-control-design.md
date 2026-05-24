# Design : Contrôle de luminosité ajustable

**Date :** 2026-05-24  
**Statut :** Approuvé

## Objectif

L'interface est jugée trop sombre. Ajouter un slider de luminosité dans l'onglet **Paramètres > Apparence** permettant à l'utilisateur d'ajuster la luminosité globale de l'interface, avec persistance entre les sessions.

## Approche retenue

**CSS `filter: brightness()` sur `<main>`** — variable CSS `--app-brightness` appliquée au contenu principal uniquement (pas à `<html>` pour éviter les conflits z-index avec la sidebar et le header).

## Fichiers concernés

| Fichier | Modification |
|---|---|
| `frontend/src/utils/theme.js` | Ajout de `BRIGHTNESS_KEY`, `applyBrightness(value)`, `loadSavedBrightness()` |
| `frontend/src/index.css` | `:root { --app-brightness: 1 }` — valeur par défaut |
| `frontend/src/components/Layout.jsx` | Appel `loadSavedBrightness()` au montage via `useEffect` ; `filter: brightness(var(--app-brightness))` sur `<main>` via style inline ou classe |
| `frontend/src/pages/Parametres.jsx` | Slider dans `ApparenceTab` avec live preview et persistance via "Appliquer" |

## Détail technique

### theme.js

```js
export const BRIGHTNESS_KEY = 'app-brightness'
export const DEFAULT_BRIGHTNESS = 1.0

export function applyBrightness(value) {
  document.documentElement.style.setProperty('--app-brightness', value)
}

export function loadSavedBrightness() {
  const saved = parseFloat(localStorage.getItem(BRIGHTNESS_KEY))
  const value = isNaN(saved) ? DEFAULT_BRIGHTNESS : Math.min(2.0, Math.max(0.5, saved))
  applyBrightness(value)
}
```

### index.css

```css
:root {
  --app-brightness: 1;
}
```

### Layout.jsx

- Import `loadSavedBrightness` depuis `../utils/theme`
- `useEffect(() => { loadSavedBrightness() }, [])` au montage
- Ajouter `style={{ filter: 'brightness(var(--app-brightness))' }}` sur le `<main>`

### ApparenceTab (Parametres.jsx)

- État local `brightness` initialisé depuis localStorage (`BRIGHTNESS_KEY`, défaut `1.0`)
- Slider `<input type="range" min="0.5" max="2.0" step="0.05">`
- Label affichant `Math.round(brightness * 100) + '%'`
- `onChange` : appelle `applyBrightness(value)` immédiatement (live preview)
- Bouton "Appliquer" existant : inclure `localStorage.setItem(BRIGHTNESS_KEY, brightness)` en plus des couleurs
- Bouton "Réinitialiser" existant : remettre brightness à `1.0`, appeler `applyBrightness(1.0)`, supprimer la clé localStorage

## UX

- Plage : `0.5` (50%, très sombre) → `2.0` (200%, très lumineux)
- Pas : `0.05`
- Défaut : `1.0` (100%)
- Application : immédiate pendant le glissement (live preview)
- Persistance : via le bouton "Appliquer" existant
- Réinitialisation : via le bouton "Réinitialiser" existant
- Affichage de la valeur en % à côté du slider

## Contraintes

- Le filtre s'applique sur `<main>` uniquement — la sidebar et le header ne sont pas affectés (pas de conflits z-index)
- Compatible avec le système de thème de couleurs existant (mêmes boutons Appliquer/Réinitialiser)
- Aucune dépendance supplémentaire

## Tests

- `theme.test.js` : ajouter tests pour `applyBrightness` et `loadSavedBrightness`
- `Parametres.apparence.test.jsx` : vérifier que le slider est rendu et que `applyBrightness` est appelée au changement
