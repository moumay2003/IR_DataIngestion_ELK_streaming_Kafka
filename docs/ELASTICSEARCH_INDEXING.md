# 🔍 Elasticsearch: Indexation et Stockage - Guide Complet

## Architecture de l'Indexation dans votre Pipeline

```
┌─────────────┐      ┌─────────────┐      ┌────────────────────────────────┐
│  Logstash   │─────▶│ Elasticsearch│─────▶│  Index firefox-logs-2025.11.05 │
│  (output)   │      │   (REST API) │      │  ├─ Shard 0 (Primary)          │
└─────────────┘      └─────────────┘      │  │  ├─ Segment 1 (45 segments)  │
                                           │  │  ├─ Segment 2                │
                                           │  │  └─ ...                      │
                                           │  └─ 3,693,391 documents         │
                                           │     1.08 GB (1,077,423,324 B)  │
                                           └────────────────────────────────┘
```

---

## 1. 📥 **Comment les Données Arrivent dans Elasticsearch**

### **Étape 1: Logstash envoie via HTTP Bulk API**

Dans votre fichier `logstash.conf`:
```ruby
output {
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "firefox-logs-%{+YYYY.MM.dd}"  # Index dynamique par jour
  }
}
```

**Ce qui se passe:**
- Logstash accumule les documents (batch)
- Envoie par **Bulk API** (multiple documents en une requête)
- Vos stats: **31,256 opérations bulk** avec une moyenne de **21.6 KB par batch**
- Temps total d'indexation: **472 secondes** (7.8 minutes pour 3.69M docs)
- **Débit: ~7,813 documents/seconde** 🚀

### **Étape 2: Elasticsearch reçoit et traite**

```http
POST /firefox-logs-2025.11.05/_bulk
{"index":{"_index":"firefox-logs-2025.11.05"}}
{"@timestamp":"2025-11-05T18:53:37Z","test_name":"test_click.py","test_status":"passed",...}
{"index":{"_index":"firefox-logs-2025.11.05"}}
{"@timestamp":"2025-11-05T18:53:38Z","test_name":"test_rendering.py","test_status":"failed",...}
...
```

---

## 2. 🗂️ **Structure de l'Index Elasticsearch**

### **Index = Base de données**
```
firefox-logs-2025.11.05/
├─ Mappings (schéma)
│  ├─ @timestamp: date
│  ├─ test_name: text + keyword
│  ├─ test_status: keyword
│  ├─ test_duration: integer
│  └─ ... (40+ champs)
│
├─ Settings (configuration)
│  ├─ number_of_shards: 1
│  ├─ number_of_replicas: 0
│  └─ refresh_interval: 1s
│
└─ Documents (données)
   ├─ Document 1: {"_id": "abc123", "_source": {...}}
   ├─ Document 2: {"_id": "def456", "_source": {...}}
   └─ ... (3,693,391 docs)
```

### **Mapping Automatique (Dynamic Mapping)**

Elasticsearch détecte automatiquement les types:

| Champ | Type Détecté | Raison |
|-------|--------------|--------|
| `@timestamp` | `date` | Format ISO 8601 |
| `test_duration` | `integer` | Nombre entier |
| `test_name` | `text` + `keyword` | Texte avec multi-field |
| `test_status` | `keyword` | Chaîne exacte |
| `is_anomaly` | `boolean` | true/false |
| `elapsed_time` | `float` | Nombre décimal |

**Multi-fields (text + keyword):**
```json
"test_name": {
  "type": "text",              // Pour recherche full-text
  "fields": {
    "keyword": {
      "type": "keyword",       // Pour agrégations/tri exact
      "ignore_above": 512
    }
  }
}
```

**Usage:**
- `test_name` → Recherche: "test click element"
- `test_name.keyword` → Exact: "test_click.py TestClick.test_element"

---

## 3. 💾 **Stockage Physique des Données**

### **Architecture des Shards**

```
Index: firefox-logs-2025.11.05
└─ Shard 0 (Primary)
   ├─ Segment 1  (100 MB)
   ├─ Segment 2  (120 MB)
   ├─ Segment 3  (95 MB)
   └─ ... (45 segments totaux)
   
Total: 1.08 GB sur disque
```

**Segments = Fichiers Lucene immutables**
- Chaque segment contient un sous-ensemble de documents
- Écriture: nouveau segment créé
- Lecture: tous les segments interrogés
- Merge: segments fusionnés périodiquement (background)

### **Vos Statistiques de Segments**

```
Total segments: 45
Merges effectués: 34
  ├─ Documents mergés: 3,856,618
  ├─ Taille mergée: 1.31 GB
  ├─ Temps merge: 138 secondes
  └─ Throttling: 27 secondes (pour limiter I/O)
```

### **Fichiers sur Disque (dans Docker volume)**

```
/usr/share/elasticsearch/data/nodes/0/indices/
└─ Ghkf2GE_SSegD5YYLjGGgQ/  (UUID de l'index)
   └─ 0/  (shard 0)
      ├─ _0.cfs   (segment file)
      ├─ _0.cfe   (compound file entries)
      ├─ _0.si    (segment info)
      ├─ segments_N  (segments metadata)
      └─ write.lock
```

---

## 4. 🔎 **Processus d'Indexation Détaillé**

### **Étape par Étape**

#### **1. Document arrive de Logstash**
```json
{
  "@timestamp": "2025-11-05T18:53:37.092Z",
  "test_name": "test_click.py TestClick.test_element",
  "test_status": "passed",
  "test_duration": 1142,
  "tags": ["test_event"]
}
```

#### **2. Analyse et Tokenisation (pour champs `text`)**
```
test_name: "test_click.py TestClick.test_element"
↓
Analyzer: standard
↓
Tokens: [test, click, py, testclick, test, element]
↓
Index inversé créé
```

#### **3. Index Inversé (pour recherche rapide)**
```
Term          | Document IDs
--------------|--------------
click         | [doc1, doc5, doc89, ...]
element       | [doc1, doc12, doc67, ...]
test          | [doc1, doc2, doc3, ...]
testclick     | [doc1, doc45, ...]
```

#### **4. Doc Values (pour agrégations/tri)**
```
Document ID | test_status | test_duration
------------|-------------|---------------
doc1        | passed      | 1142
doc2        | failed      | 5890
doc3        | passed      | 320
```

#### **5. Écriture dans Translog (durabilité)**
```
Translog (journal de transactions):
├─ Operation 1: INDEX doc1
├─ Operation 2: INDEX doc2
└─ ... (4,647 opérations en attente)

Taille: 1.6 MB
```

#### **6. Flush vers Segment (périodique)**
```
Toutes les 30s ou quand translog > 512MB:
├─ Écrire nouveau segment sur disque
├─ Vider translog
└─ Commit point créé
```

---

## 5. 📊 **Performances et Optimisations**

### **Vos Métriques de Performance**

| Métrique | Valeur | Signification |
|----------|--------|---------------|
| **Indexation** | 3,693,391 docs | Total indexé |
| Temps indexation | 460 secondes | 7.7 minutes |
| **Débit** | **8,020 docs/sec** | Très rapide! |
| Échecs indexation | 0 | ✅ Parfait |
| Taille stockage | 1.08 GB | Compressé |
| Segments | 45 | Normal |
| Refresh | 687 fois | Rend données cherchables |
| Refresh time | 80 secondes | Overhead acceptable |
| Flush | 65 fois | Persistance disque |

### **Refresh vs Flush**

**Refresh (toutes les 1s par défaut):**
- Rend nouveaux documents **cherchables**
- Crée nouveau segment en mémoire
- Pas d'écriture disque
- **687 refresh** effectués

**Flush (toutes les 30s):**
- Écrit segments sur **disque**
- Vide translog
- Garantit durabilité
- **65 flush** effectués

### **Opérations de Merge**

```
Merge automatique (background):
├─ 34 merges effectués
├─ 3,856,618 documents fusionnés
├─ 1.31 GB de données mergées
├─ Temps: 138 secondes
└─ Throttling: 27 secondes (limite I/O pour ne pas surcharger)
```

**Pourquoi merger?**
- Réduit nombre de segments (45 actuellement)
- Améliore performance de recherche
- Supprime documents marqués deleted
- Optimise compression

---

## 6. 🔍 **Recherche et Requêtes**

### **Comment Elasticsearch Cherche**

#### **Requête Simple**
```http
GET /firefox-logs-2025.11.05/_search
{
  "query": {
    "match": {
      "test_name": "click"
    }
  }
}
```

**Processus:**
1. **Parse query** → cherche "click"
2. **Consulte index inversé** → trouve doc IDs [1, 5, 89, ...]
3. **Lit doc values** → récupère scores
4. **Trie résultats** par score
5. **Fetch documents** depuis _source
6. **Retourne JSON**

#### **Requête avec Agrégation**
```http
GET /firefox-logs-2025.11.05/_search
{
  "size": 0,
  "aggs": {
    "tests_by_status": {
      "terms": {
        "field": "test_status"
      }
    }
  }
}
```

**Processus:**
1. **Lit doc values** de `test_status` (rapide, columnar)
2. **Compte occurrences** pour chaque valeur
3. **Retourne buckets:**
```json
{
  "aggregations": {
    "tests_by_status": {
      "buckets": [
        {"key": "passed", "doc_count": 3500000},
        {"key": "failed", "doc_count": 150000},
        {"key": "skipped", "doc_count": 43391}
      ]
    }
  }
}
```

### **Vos Statistiques de Recherche**

```
Recherches effectuées: 3 queries
Temps total: 332 ms
Moyenne: 110 ms par query
Fetch: 1 fois (récupération documents)
Contextes ouverts: 0 (pas de scroll actif)
```

---

## 7. 🎯 **Index Lifecycle Management**

### **Rotation des Index (Time-based)**

Votre configuration actuelle:
```
firefox-logs-2025.01.01  → 1.8M docs (614 MB)
firefox-logs-2025.11.05  → 3.7M docs (1.08 GB)
firefox-anomalies-2025.01.01 → 27K docs (11 MB)
firefox-anomalies-2025.11.05 → 4.2K docs (12 MB)
```

**Avantages:**
- ✅ Facilite suppression de vieilles données
- ✅ Optimise recherches (scope temporel)
- ✅ Réduit taille des segments
- ✅ Parallélise requêtes sur plusieurs jours

### **Stratégie de Rétention (exemple)**

```
Jour 0-7:    Index chauds (recherches fréquentes)
Jour 8-30:   Index tièdes (recherches occasionnelles)
Jour 31-90:  Index froids (archivage)
Jour 90+:    Suppression automatique
```

---

## 8. 📈 **Double Indexation (Logs + Anomalies)**

### **Architecture de Votre Output Logstash**

```ruby
output {
  # TOUS les logs → index principal
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "firefox-logs-%{+YYYY.MM.dd}"
  }

  # SEULEMENT anomalies → index séparé
  if "anomaly" in [tags] {
    elasticsearch {
      hosts => ["http://elasticsearch:9200"]
      index => "firefox-anomalies-%{+YYYY.MM.dd}"
    }
  }
}
```

**Résultat:**

| Index | Documents | Taille | Ratio |
|-------|-----------|--------|-------|
| firefox-logs-2025.11.05 | 3,693,391 | 1.08 GB | 100% |
| firefox-anomalies-2025.11.05 | 4,255 | 12 MB | 0.12% |

**Avantages:**
- ✅ Recherche rapide des anomalies (petit index)
- ✅ Analyse séparée des problèmes
- ✅ Alertes spécifiques sur anomalies
- ✅ Dashboards dédiés

---

## 9. 🛠️ **Commandes Utiles**

### **Vérifier Santé de l'Index**
```powershell
Invoke-WebRequest -Uri "http://localhost:9200/_cat/indices/firefox-*?v"
```

### **Voir Mapping Complet**
```powershell
Invoke-WebRequest -Uri "http://localhost:9200/firefox-logs-2025.11.05/_mapping" | ConvertFrom-Json
```

### **Statistiques Détaillées**
```powershell
Invoke-WebRequest -Uri "http://localhost:9200/firefox-logs-2025.11.05/_stats" | ConvertFrom-Json
```

### **Forcer Merge (optimisation)**
```powershell
Invoke-WebRequest -Method POST -Uri "http://localhost:9200/firefox-logs-2025.11.05/_forcemerge?max_num_segments=1"
```

### **Compter Documents**
```powershell
Invoke-WebRequest -Uri "http://localhost:9200/firefox-logs-2025.11.05/_count"
```

### **Recherche Simple**
```powershell
$body = @{
  query = @{
    match = @{
      test_status = "failed"
    }
  }
  size = 10
} | ConvertTo-Json

Invoke-WebRequest -Method POST -Uri "http://localhost:9200/firefox-logs-*/_search" -Body $body -ContentType "application/json"
```

---

## 10. 📦 **Résumé: Votre Pipeline Complet**

```
┌──────────────────────────────────────────────────────────────────┐
│                    FIREFOX BUILD LOGS PIPELINE                    │
└──────────────────────────────────────────────────────────────────┘

1. INGESTION
   ├─ 400+ fichiers .txt lus par Python producer
   ├─ Envoyés à Kafka topic "firefox-build-logs"
   └─ Vitesse: ~1000 lignes/seconde

2. STREAMING
   ├─ Kafka stocke messages (3 partitions)
   ├─ Retention: 7 jours
   └─ Compression: GZIP

3. PARSING (Logstash)
   ├─ Consomme Kafka en continu
   ├─ 10+ Grok patterns appliqués
   ├─ Extraction: test_name, test_status, test_duration, warnings, etc.
   └─ Détection anomalies (tags)

4. INDEXATION (Elasticsearch)
   ├─ Bulk API: 31,256 batches
   ├─ Débit: 8,020 docs/sec
   ├─ Stockage: 1.08 GB (compressé)
   ├─ Segments: 45
   └─ Double indexation: logs + anomalies

5. VISUALISATION (Kibana)
   ├─ Data Views: firefox-logs-*, firefox-anomalies-*
   ├─ Dashboards: Build Overview, Anomaly Detection, Performance
   └─ Temps réel: refresh 15s

TOTAUX:
├─ 3,693,391 logs indexés
├─ 4,255 anomalies détectées (0.12%)
├─ 460 secondes d'indexation
└─ 1.08 GB stockés (ratio 2.6:1)
```

---

## 11. 🎓 **Concepts Avancés**

### **Inverted Index (Index Inversé)**
Structure de données qui permet recherche full-text rapide:
```
Document 1: "test click button"
Document 2: "test rendering engine"
Document 3: "click element handler"

Index inversé:
test    → [doc1, doc2]
click   → [doc1, doc3]
button  → [doc1]
rendering → [doc2]
engine  → [doc2]
element → [doc3]
handler → [doc3]
```

### **Doc Values**
Structure columnaire pour agrégations/tri:
```
┌────────┬──────────┬──────────────┐
│ Doc ID │  Status  │   Duration   │
├────────┼──────────┼──────────────┤
│   1    │ passed   │    1142      │
│   2    │ failed   │    5890      │
│   3    │ passed   │     320      │
└────────┴──────────┴──────────────┘
```

### **Translog**
Journal de transactions pour durabilité:
- Écrit avant indexation
- Replay après crash
- Vide après flush

### **Scoring (Relevance)**
TF-IDF + BM25:
- TF: Term Frequency (fréquence du terme)
- IDF: Inverse Document Frequency (rareté du terme)
- BM25: Amélioration moderne de TF-IDF

---

## 🎯 Conclusion

Votre pipeline traite **3.7 millions de logs** avec:
- ✅ **Débit: 8,020 docs/sec**
- ✅ **Stockage optimisé: 1.08 GB**
- ✅ **0 échecs d'indexation**
- ✅ **Recherche < 110ms**
- ✅ **Détection 4,255 anomalies**

L'indexation Elasticsearch transforme vos logs bruts en une base de données interrogeable en temps réel avec des performances exceptionnelles! 🚀
