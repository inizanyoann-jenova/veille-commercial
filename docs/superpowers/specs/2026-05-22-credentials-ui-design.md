# Spec : Gestion des identifiants pour sites protégés

**Date :** 2026-05-22  
**Statut :** Approuvé

---

## Contexte

Huit scrapers du projet nécessitent une authentification utilisateur (email + mot de passe) avant de pouvoir collecter des appels d'offres. L'infrastructure de stockage chiffré (`credential_manager.py`) et le worker de test Playwright (`_test_login_worker.py`) existent déjà. Ce qui manque : une interface utilisateur pour saisir, tester et gérer ces identifiants, ainsi qu'un signalement clair dans l'UI quand un site est bloqué faute d'identifiants.

---

## Sites concernés

Les 8 sites déclarés dans `_ENV_MAP` de `credential_manager.py` :

| Clé site | Nom affiché | URL de login |
|---|---|---|
| `nukema` | Nukema | `https://www.actu.nukema.com/connexion` |
| `vaao` | VAAO | `https://www.vaao.fr/connexion` |
| `marcheonline` | Marché Online | URL à confirmer lors de l'implémentation |
| `dept974` | Marchés Publics 974 | URL à confirmer |
| `marchespublicsinfo` | Marchés Publics Info | URL à confirmer |
| `marches_securises` | Marchés Sécurisés | URL à confirmer |
| `instao` | Instao | URL à confirmer |
| `tendersgo` | Tenders Go | URL à confirmer |

Les sélecteurs CSS pour chaque site sont à extraire des scrapers existants lors de l'implémentation. Nukema est le seul déjà documenté dans `scraper_nukema.py`.

---

## Architecture

### Backend — 4 nouvelles routes dans `backend/main.py`

```
GET  /credentials              → liste des 8 sites avec statut auth
POST /credentials/{site}       → sauvegarde email + mot de passe
DELETE /credentials/{site}     → supprime les identifiants
POST /credentials/{site}/test  → teste la connexion via Playwright worker
```

**Dictionnaire centralisé `_LOGIN_CONFIG`** ajouté dans `backend/main.py` :
```python
_LOGIN_CONFIG: dict[str, dict] = {
    "nukema": {
        "url": "https://www.actu.nukema.com/connexion",
        "selectors": {
            "email": "input[type='email']",
            "password": "input[type='password']",
            "submit": "button[type='submit']",
        },
    },
    # … 7 autres sites
}
```

**`GET /credentials`** retourne :
```json
[
  { "site": "nukema", "label": "Nukema", "status": "configured", "email": "user@example.com" },
  { "site": "vaao",   "label": "VAAO",   "status": "missing",    "email": null },
  { "site": "instao", "label": "Instao", "status": "env_override","email": "from-env@example.com" }
]
```
Statuts possibles : `configured` (DB), `missing` (aucun), `env_override` (variable d'env, lecture seule).

**`POST /credentials/{site}/test`** :
- Lance `_test_login_worker.py` en sous-processus (pattern déjà utilisé dans le projet)
- Timeout : 30 secondes
- Retourne `{"ok": true}` ou `{"ok": false, "message": "…"}`
- Ne sauvegarde **pas** les identifiants — la sauvegarde est une étape séparée

**`POST /credentials/{site}`** body : `{"email": "…", "password": "…"}`
- Appelle `CredentialManager.save(site, email, password)`
- Le frontend appelle cette route uniquement après un test réussi (UX), mais la route accepte la sauvegarde directe si nécessaire

### Frontend — `CredentialsSection` dans `Parametres.jsx`

Nouvelle section ajoutée dans la page Paramètres, entre la section Collecte et la section Analyse LLM.

**Affichage :**
- Liste des 8 sites avec badge de statut coloré :
  - 🔴 `missing` — identifiants manquants
  - 🟢 `configured` — identifiants configurés en base
  - 🔵 `env_override` — lecture seule (variable d'environnement)
- Cliquer sur un site ouvre un formulaire inline :
  - Champ email
  - Champ mot de passe masqué (toggle affichage)
  - Bouton **"Tester la connexion"** → spinner + résultat Playwright
  - Bouton **"Sauvegarder"** (activé seulement après test OK)
  - Bouton **"Supprimer"** (visible si statut `configured`)

**Hooks React :**
- `useCredentials()` — `GET /credentials`
- `useSaveCredential()` — `POST /credentials/{site}`
- `useDeleteCredential()` — `DELETE /credentials/{site}`
- `useTestCredential()` — `POST /credentials/{site}/test` (timeout côté client : 35s)

Ces hooks sont ajoutés dans `frontend/src/hooks/useTenders.js` et les routes API dans `frontend/src/services/api.js`.

---

## Signalement d'erreur d'auth dans la collecte

### Changement dans les 8 scrapers concernés

En tête de chaque fonction de collecte, avant toute action Playwright :

```python
creds = CredentialManager.get("site")
if not creds:
    finish_scraper_run(db, run_id, nb_found=0, nb_new=0, error="CREDENTIALS_MISSING")
    return 0
```

Nukema a déjà un check partiel — on le remplace par ce pattern standardisé.

### Changement dans le frontend (`CollectSection`)

Quand `r.error === "CREDENTIALS_MISSING"` dans les résultats de collecte, afficher :
```
✗  Nukema   ⚠ Identifiants manquants — configurer ↗
```
Le lien "configurer ↗" scrolle vers la section CredentialsSection (ancre `#credentials`).

---

## Gestion des erreurs du worker Playwright

Le worker `_test_login_worker.py` retourne déjà des structures d'erreur détaillées. Le backend les transforme en message lisible :

| Cas | Message affiché |
|---|---|
| `ok: false, erreur_page: "…"` | "Identifiants incorrects : \<message>" |
| `ok: false, champ_manquant: "…"` | "Champ introuvable — sélecteur CSS à mettre à jour" |
| `ok: false, no_redirect: true` | "Connexion refusée sans message d'erreur" |
| Timeout 30s | "Test expiré — site trop lent ou inaccessible" |

---

## Périmètre hors-spec

- Pas de rotation automatique des sessions / cookies entre les collectes
- Pas de support TOTP / 2FA
- Pas de partage de credentials entre utilisateurs
- Les sélecteurs CSS manquants (7 sites sur 8) sont à compléter lors de l'implémentation en visitant chaque page de login

---

## Fichiers modifiés

| Fichier | Nature |
|---|---|
| `backend/main.py` | +4 routes, +`_LOGIN_CONFIG` dict |
| `frontend/src/pages/Parametres.jsx` | +`CredentialsSection` |
| `frontend/src/hooks/useTenders.js` | +4 hooks |
| `frontend/src/services/api.js` | +4 fonctions API |
| `scraper_vaao.py` | check CREDENTIALS_MISSING |
| `scraper_marcheonline.py` | check CREDENTIALS_MISSING |
| `scraper_nukema.py` | standardiser le check existant |
| `scraper_dept974.py` | check CREDENTIALS_MISSING |
| `scraper_marchespublicsinfo.py` | check CREDENTIALS_MISSING |
| `scraper_marchessecurises.py` | check CREDENTIALS_MISSING |
| `scraper_instao.py` | check CREDENTIALS_MISSING |
| `scraper_tendersgo.py` | check CREDENTIALS_MISSING |
