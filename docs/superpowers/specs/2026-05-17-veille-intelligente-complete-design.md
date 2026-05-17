# Design — Veille Intelligente Complète (Approche 3)

**Date :** 2026-05-17
**Projet :** DEF Océan Indien — Veille Marchés
**Périmètre :** `app.py` · `email_digest.py` (nouveau) · `score_adaptive.py` (nouveau) · `pages/direction.py` (nouveau) · `pages/parametres.py` · `fiche_logic.py` · `models.py` · `database.py`

---

## Contexte & pain points adressés

| ID | Pain point | Lot |
|---|---|---|
| A | Trop de bruit — difficile de trouver les GO sans ouvrir l'app | Lot 1 + Lot 2 |
| B | Infos insuffisantes (titre + description) pour qualifier GO/non-GO | Lot 2 |
| D | Rapport Direction chronophage et peu riche | Lot 1 |

---

## Vue d'ensemble

| ID | Feature | Lot | Fichiers principaux |
|---|---|---|---|
| 1 | Digest email quotidien | 1 | `email_digest.py`, `send_digest.py`, `pages/parametres.py`, `.env` |
| 2 | Page Direction exécutive + export PDF | 1 | `pages/direction.py` |
| 3 | Enrichissement LLM structuré | 2 | `llm_analyzer.py`, `models.py`, fiche dans `app.py` |
| 4 | Score adaptatif | 2 | `score_adaptive.py`, `models.py`, `database.py`, `app.py` |
| 5 | Croisement DECP (historique acheteur) | 2 | `fiche_logic.py` |

**Ordre d'implémentation recommandé :** Lot 1 en premier (Features 1 + 2) — résultats immédiats sur A et D. Lot 2 ensuite (Features 3 + 4 + 5) — valeur progressive à mesure que la base de décisions s'enrichit.

---

## Architecture générale

### Nouveaux fichiers

| Fichier | Rôle |
|---|---|
| `email_digest.py` | Construction HTML + envoi SMTP du digest |
| `send_digest.py` | Script autonome (20 lignes) pour Planificateur Windows |
| `score_adaptive.py` | Calcul TF-IDF simplifié + mise à jour `adaptive_score` |
| `pages/direction.py` | Page Streamlit vue Direction + export PDF |

### Nouvelles colonnes / tables

| Élément | Type | Table |
|---|---|---|
| `llm_structured` | JSON | `tenders` |
| `adaptive_score` | Integer | `tenders` |
| `score_weights` | Nouvelle table | — |

### Dépendances à ajouter

| Package | Usage | Notes |
|---|---|---|
| `smtplib` + `email` | Envoi digest | Stdlib Python — zéro dépendance |
| `kaleido` | Export images Plotly → PDF | `pip install kaleido` |
| `reportlab` | Génération PDF Direction | `pip install reportlab` |

---

## Feature 1 — Digest email quotidien

### Contenu de l'email

**Objet :** `[DEF OI] 3 nouveaux marchés GO — 17 mai 2026`

Structure HTML en trois sections :

1. **✅ GO (score ≥ 65)** — tableau complet : titre · domaine · territoire · score · deadline · lien source
   > *"Ces marchés sont qualifiés et prêts à traiter"*

2. **🔍 À étudier (score 35–64)** — liste compacte : titre · score · deadline
   > *"Ces marchés méritent un regard — ouvre la fiche pour décider"*

3. **⚠️ Urgences (deadline < 7 jours)** — marchés GO avec deadline imminente, fond rouge

**Pied :** lien `Ouvrir l'app → http://localhost:8501`

**Règle :** si aucun nouveau marché GO ni À étudier dans les 24h → email non envoyé.

### Logique (`email_digest.py`)

```python
def build_digest(since_hours: int = 24) -> dict | None:
    """Retourne {"subject": ..., "html": ...} ou None si rien à envoyer."""

def send_digest(smtp_config: dict) -> bool:
    """Construit et envoie le digest. Retourne True si envoyé."""
```

### Configuration (`.env`)

```
DIGEST_SMTP_HOST=smtp.gmail.com
DIGEST_SMTP_PORT=587
DIGEST_SMTP_USER=...
DIGEST_SMTP_PASSWORD=...   # mot de passe app Gmail
DIGEST_TO=inizan.yoann@gmail.com
DIGEST_HOUR=7              # heure d'envoi (défaut 7h00)
```

### Deux modes de déclenchement

**Mode 1 — Script autonome** (`send_digest.py`) :
- Planifiable via Planificateur de tâches Windows
- Déclencheur : tous les jours à 07:00
- Action : `python send_digest.py`
- Fonctionne même si Streamlit est fermé

**Mode 2 — APScheduler dans `app.py`** :
- Job quotidien à l'heure configurée dans `.env`
- Guard Streamlit : `if "digest_scheduler" not in st.session_state`
- Fonctionne uniquement quand l'app est ouverte

**Mode 3 — Bouton manuel dans `pages/parametres.py`** :
- Section "📧 Digest email" avec bouton "Envoyer maintenant"
- Affiche un aperçu du dernier email généré
- Affiche le statut du dernier envoi (date + nb marchés inclus)

---

## Feature 2 — Page Direction (`pages/direction.py`)

### Structure

**Bloc 1 — 4 KPIs clés** (ligne `st.metric`)

| KPI | Requête |
|---|---|
| Opportunités actives | `COUNT` GO + Soumis, `is_blacklisted == False` |
| CA prévisionnel | `SUM(amount)` WHERE status IN ('Soumis', 'En cours') |
| CA gagné (cumul) | `SUM(amount)` WHERE status = 'Gagné' |
| Taux de conversion | `COUNT(Gagné) / COUNT(Soumis) * 100` |

**Bloc 2 — Graphique "Activité 90 jours"**
- Barres empilées par semaine : À qualifier · GO · Soumis · Gagné · Perdu
- `px.bar` avec `barmode="stack"`, palette DEF OI (rouge `#cc2222`)
- Montre l'activité de la veille et la progression dans le pipeline

**Bloc 3 — Tableau "Pipeline en cours"**
- Marchés GO + Soumis uniquement
- Colonnes : Titre · Domaine · Territoire · Statut · Deadline · Montant estimé
- Trié par deadline croissante
- Vue lecture seule (pas de boutons d'action)

**Bloc 4 — Export PDF**
- Bouton `📄 Télécharger le rapport PDF`
- Contenu : page de garde (DEF OI + date + périmètre 974/976) · 4 KPIs · graphique 90 jours · tableau pipeline
- Généré avec `reportlab` + `kaleido` pour les graphiques
- Nom fichier : `Rapport_Direction_DEF_AAAAMMJJ.pdf`

### Ce qui ne change pas
- La page Analytics existante (détails techniques conservés)
- L'export Excel existant
- La page Direction est une vue supplémentaire, pas un remplacement

---

## Feature 3 — Enrichissement LLM structuré

### Nouveau champ `Tender.llm_structured` (JSON)

Migration idempotente dans `init_db()` :
```sql
ALTER TABLE tenders ADD COLUMN llm_structured JSON DEFAULT NULL
```

### Nouveau prompt LLM

Le LLM reçoit titre + description + montant (si disponible) et retourne un JSON strict :

```json
{
  "budget_estime": "150 000 €",
  "type_travaux": "Installation neuve",
  "lots": ["Lot 1 — Détection incendie", "Lot 2 — SSI"],
  "keywords_techniques": ["ERP type J", "SSI catégorie A", "NF S 61-931"],
  "acheteur_type": "Établissement scolaire",
  "niveau_concurrence": "Élevé",
  "recommandation": "GO",
  "score_confiance": 78,
  "justification": "ERP type J avec SSI catégorie A, correspondance directe avec nos métiers SSI/CMSI."
}
```

### Déclenchement

- **Automatique** : après chaque collecte, uniquement si `llm_structured IS NULL` ET `relevance_score >= SCORE_ETUDE` (35)
- **Manuel** : bouton "🔄 Ré-analyser" sur la fiche (écrase l'existant)
- **Guard** : si description < 50 caractères → `llm_structured` reste NULL, aucune erreur

### Affichage dans la fiche

Nouvelle section **"🤖 Analyse structurée"** sous le résumé narratif existant :

```
Budget estimé    150 000 €        Type             Installation neuve
Lots             Lot 1 — Détection · Lot 2 — SSI
Concurrence      Élevée           Confiance LLM    78 %
Recommandation   ✅ GO
Justification    ERP type J avec SSI catégorie A...
```

L'analyse narrative `llm_analysis` existante est conservée intacte.

---

## Feature 4 — Score adaptatif

### Nouveau champ `Tender.adaptive_score` (Integer, nullable)

Migration idempotente dans `init_db()` :
```sql
ALTER TABLE tenders ADD COLUMN adaptive_score INTEGER DEFAULT NULL
```

### Nouvelle table `score_weights`

```python
class ScoreWeight(Base):
    __tablename__ = "score_weights"

    keyword     = Column(String, primary_key=True)
    weight_go   = Column(Float, default=0.0)
    weight_nogo = Column(Float, default=0.0)
    updated_at  = Column(DateTime)
```

### Algorithme (`score_adaptive.py`)

```python
def recompute_adaptive_scores(db) -> int:
    """
    1. Collecte les tenders avec décision connue (Soumis/Gagné = positif, Perdu = négatif)
    2. TF-IDF simplifié : poids de chaque mot selon fréquence GO vs non-GO
    3. Persiste les poids dans score_weights
    4. Pour chaque tender non décidé : calcule adaptive_score (0–100)
    5. Met à jour Tender.adaptive_score en batch
    6. Retourne le nb de tenders mis à jour
    """
```

### Déclenchement

- Recalcul automatique 1× par semaine via APScheduler (job existant dans `app.py`)
- Bouton "🔄 Recalculer le score adaptatif" dans `pages/parametres.py`

### Garde-fou

Si moins de 10 décisions historiques → `adaptive_score` masqué partout + message dans Paramètres :
`"Pas encore assez de données (X/10 décisions enregistrées)"`

### Affichage

- Nouvelle colonne **"Score adaptatif"** dans le tableau principal (masquable via checkbox sidebar)
- Option de tri "Trier par score adaptatif" dans la sidebar
- Badge `🧠 Score adaptatif : 74` dans la fiche marché (si disponible)

---

## Feature 5 — Croisement DECP (historique acheteur)

### Logique (`fiche_logic.py`)

```python
def get_acheteur_history(db, tender: Tender) -> dict:
    """
    Extrait les mots-clés significatifs du titre du tender,
    cherche d'autres tenders qui les contiennent.
    Retourne :
    {
      "nb_total": 4,
      "nb_go": 2,
      "nb_gagnes": 1,
      "montant_total_gagne": 85000,
      "derniers": [Tender, ...]   # 3 plus récents
    }
    """
```

Extraction des mots-clés : les 3 premiers tokens du titre de longueur ≥ 4 caractères, après suppression des mots vides courants (le, la, les, de, du, des, un, une, et, en, au, aux, sur, pour, par).
Recherche via `func.lower(Tender.title).contains(keyword)` — même pattern que full-text existant.
Aucune nouvelle table, requête sur données déjà en base.

### Affichage dans la fiche

Nouvelle section **"🏛️ Historique acheteur"**, visible uniquement si `nb_total >= 2` :

```
Cet acheteur a publié 4 marchés similaires dans la base
  ✅ 2 GO  ·  🏆 1 Gagné  ·  💰 85 000 € gagnés

  → Installation SSI Groupe scolaire...   Gagné   mars 2025
  → Maintenance détection incendie...     Perdu   jan 2025
  → Mise en conformité SSI...             GO      (en cours)
```

Chaque ligne est cliquable → ouvre la fiche du marché correspondant.
Si aucune correspondance → section masquée, sans message d'erreur.

---

## Migrations requises

Toutes idempotentes, dans `init_db()` de `database.py` :

```sql
-- Tender : colonnes nouvelles
ALTER TABLE tenders ADD COLUMN llm_structured JSON DEFAULT NULL
ALTER TABLE tenders ADD COLUMN adaptive_score INTEGER DEFAULT NULL

-- Nouvelle table score_weights
CREATE TABLE IF NOT EXISTS score_weights (
    keyword    TEXT PRIMARY KEY,
    weight_go  REAL DEFAULT 0.0,
    weight_nogo REAL DEFAULT 0.0,
    updated_at DATETIME
)
```

---

## Critères de succès

| Feature | Critère |
|---|---|
| 1 — Digest | Email reçu à 7h avec la bonne structure GO / À étudier / Urgences ; non envoyé si aucun nouveau marché |
| 2 — Direction | Page s'affiche sans erreur avec données vides ; export PDF téléchargeable |
| 3 — LLM structuré | JSON valide stocké dans `llm_structured` ; affiché dans la fiche ; aucune erreur si description courte |
| 4 — Score adaptatif | Recalcul s'exécute sans bloquer l'UI ; masqué si < 10 décisions ; tri fonctionnel dans le tableau |
| 5 — Historique acheteur | Section visible si ≥ 2 correspondances ; masquée sinon ; liens vers fiches fonctionnels |

---

## Ce qui ne change pas

- Les scrapers existants et leur logique
- L'analyse narrative `llm_analysis` existante
- Le scoring `relevance_score` actuel (l'adaptatif est un complément, pas un remplacement)
- Le pipeline Kanban, les filtres sidebar, les fiches marchés existantes
- Le credential manager et le source registry
- Le CSS et le layout existants
