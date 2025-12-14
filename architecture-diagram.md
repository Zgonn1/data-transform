# Algolia Search Integration Architecture
## Multi-Source Product Catalog Unification

---

## System Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                          ALGOLIA SEARCH INTEGRATION ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SOURCE SYSTEMS (LEFT)                                          │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  ┌──────────────────────────┐    ┌──────────────────────────┐    ┌──────────────────────┐   │
│  │  PHP + SQL E-Commerce    │    │ Node.js + MongoDB        │    │   Kafka Topic        │   │
│  │       Site               │    │    Catalog               │    │                      │   │ 
│  ├──────────────────────────┤    ├──────────────────────────┤    ├──────────────────────┤   │
│  │ • Internal API           │    │ • XML Catalog Feed       │    │ • Real-time Updates  │   │
│  │ • Product IDs only       │    │ • Full Product Data      │    │ • Price Changes      │   │
│  │ • Rate Limited:          │    │ • Pulled hourly          │    │ • Popularity Ranks   │   │
│  │   - 1000 records/req     │    │ • Secure HTTPS           │    │ • Ratings/Reviews    │   │
│  │   - 10 req/second max    │    │ • Availability source    │    │ • Multiple consumers │   │
│  │                          │    │                          │    │ • Secondary source   │   │
│  └────────────┬─────────────┘    └────────────┬─────────────┘    └────────────┬─────────┘   │ 
│               │                               │                               │             │
│               └───────────────────────────────┼───────────────────────────────┘             │
│                                               ▼                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
                                                 │
                                                 │ Data Ingestion
                                                 │
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                    INTEGRATION LAYER: SEARCH INDEXER SERVICE (CENTER)                       │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                        CORE PROCESSING ENGINE                                        │   │
│  ├──────────────────────────────────────────────────────────────────────────────────────┤   │
│  │                                                                                      │   │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────────────┐    │   │
│  │  │  XML Parser &    │  │ Kafka Consumer   │  │  API Validator & Reconciler      │    │   │
│  │  │  Cache Layer     │  │  (Event Handler) │  │  (PHP API for availability)      │    │   │
│  │  └────────┬─────────┘  └────────┬─────────┘  └───────────────┬──────────────────┘    │   │
│  │           │                     │                            │                       │   │
│  │           └─────────────────────┼────────────────────────────┘                       │   │
│  │                                 ▼                                                    │   │
│  │  ┌──────────────────────────────────────────────────────────────────────────────┐    │   │
│  │  │              DATA TRANSFORMATION & NORMALIZATION                             │	  │   │
│  │  │  • Parse XML structure                                                  	 │	  │   │
│  │  │  • Apply Kafka field whitelisting (price, popularity, rating only)       	 │	  │   │
│  │  │  • Merge data: XML as source of truth + Kafka enrichments               	 │	  │   │
│  │  │  • Validate required fields (name, objectID, etc.)                      	 │	  │   │
│  │  │  • Build hierarchical categories                                         	 │ 	  │   │
│  │  │  • Map to Algolia schema                                                 	 │ 	  │   │
│  │  └──────────────────────────┬───────────────────────────────────────────────────┘    │   │
│  │                             ▼                                                   	  │   │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐ 	  │   │
│  │  │           INDEXING STRATEGIES                                             	│ 	  │   │
│  │  │  • Batch Sync (Hourly): Full XML → Algolia bulk update                   	│	  │   │
│  │  │  • Real-time Updates: Kafka → Algolia partial updates                    	│	  │   │
│  │  │  • Error Handling: Retry logic, dead-letter queues, logging              	│	  │   │
│  │  │  • Source of Truth: XML > Kafka on conflicts                             	│ 	  │   │
│  │  │  • Full Reindex: Triggered rebuild from XML + Kafka replay                  │	  │   │
│  │  └──────────────────────────┬──────────────────────────────────────────────────┘	  │   │
│  │                             ▼                                                 	      │   │
│  │                    ┌──────────────────┐                                        	  │   │
│  │                    │ Algolia API      │                                        	  │   │
│  │                    │ Client Library   │                                          	  │   │
│  │                    └────────┬─────────┘                                        	  │   │
│  │                             │                                                   	  │   │
│  └─────────────────────────────┼────────────────────────────────────────────────────────┘   │
│                                │                                                      	  │
└────────────────────────────────┼────────────────────────────────────────────────────────────┘
                                 │
                                 │ Bulk & Partial Updates
                                 │
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              TARGET SYSTEM: ALGOLIA (RIGHT)                                 │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                          ALGOLIA PRIMARY INDEX                                       │   │
│  ├──────────────────────────────────────────────────────────────────────────────────────┤   │
│  │                                                                                      │   │
│  │  Record Schema:                                                                      │   │
│  │  {                                                                                   │   │
│  │    "name": "string",                      "objectID": "unique identifier",        	  │   │
│  │    "description": "text",                 "brand": "string",                      	  │   │
│  │    "categories": ["array"],               "hierarchicalCategories": {"nested"},   	  │   │
│  │    "price": "float",                      "pricerange": "string",                	  │   │
│  │    "image": "url",                        "url": "url",                           	  │  │
│  │    "freeshipping": "boolean",             "popularity": "integer",                │  │
│  │    "rating": "float",                     "type": "string"                        │  │
│  │  }                                                                                 │  │
│  │                                                                                      │  │
│  ├──────────────────────────────────────────────────────────────────────────────────────┤  │
│  │                         INDEX CONFIGURATION                                        │  │
│  ├──────────────────────────────────────────────────────────────────────────────────────┤  │
│  │  Searchable Attributes:   name, description, brand, categories                    │  │
│  │  Facets:                  categories, price range, brand, freeshipping             │  │
│  │  Custom Ranking:          popularity (desc), rating (desc)                        │  │
│  │  Typo Tolerance:          Enabled (1-2 typos)                                     │  │
│  │  Highlighting:            name, description                                       │  │
│  │  Analytics:               Enabled for search queries & click tracking             │  │
│  │                                                                                      │  │
│  └───────────────────────────────┬───────────────────────────────────────────────────────┘  │
│                                  │                                                         │
│                                  │ Query API                                              │
│                                  │                                                         │
└──────────────────────────────────┼─────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                     FRONTEND: REACT + ALGOLIA INSTANTSEARCH                                 │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                              DEMO SEARCH UI                                           │ │
│  ├────────────────────────────────────────────────────────────────────────────────────────┤ │
│  │                                                                                         │ │
│  │  • Keyword Search Input      • Category Facets (hierarchical)                          │ │
│  │  • Real-time Results         • Price Range Filter                                      │ │
│  │  • Hit Highlighting          • Brand Filter                                            │ │
│  │  • Result Count              • Shipping Filter (Free/Paid)                             │ │
│  │  • Sorting Options           • Sort by: Relevance, Price, Popularity, Rating          │ │
│  │  • Product Cards             • Analytics Tracking                                      │ │
│  │                                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                               │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Architecture Principles

### 1. **Source of Truth Hierarchy**
```
PRIMARY (XML Catalog)
  ↓ Provides: structural data, descriptions, categories
  ↓
SECONDARY (Kafka Updates)
  ↓ Provides: real-time price, popularity, rating changes
  ↓
TERTIARY (PHP API)
  ↓ Provides: product availability/visibility signal
  ↓
CONFLICT RESOLUTION: XML always wins on data discrepancies
```

### 2. **Data Flow Patterns**

**Batch Synchronization (Hourly):**
```
XML Catalog (fetch) → Parse → Validate against PHP API → Normalize → Algolia Bulk Update
```

**Real-time Updates (Continuous):**
```
Kafka Topic → Consumer → Field Whitelist (price, popularity, rating) → Algolia Partial Update
```

**Full Reindex (On-demand):**
```
XML Catalog (full) + Kafka Replay (recent window) → Complete re-derivation → Fresh Algolia index
```

### 3. **Constraint Management**

| Constraint | Handling Strategy |
|-----------|------------------|
| PHP API: 1000 records/request | Paginate into batches of 1000 |
| PHP API: 10 requests/second max | Implement request throttling & queue |
| No dev/staging environments | Production-only, test with feature flags |
| Kafka sync issues | XML is source of truth, Kafka acts as cache layer |
| Multiple Kafka consumers | Idempotent updates (by objectID), partial updates safe |

### 4. **Reliability Features**

- **Error Handling:** Retry logic with exponential backoff, dead-letter queues for failed messages
- **Monitoring & Logging:** All transforms logged, Algolia indexing successes/failures tracked
- **Eventual Consistency:** Kafka eventual consistency achieved via hourly XML refresh
- **Rollback:** Full reindex can be triggered to rebuild from XML + Kafka replay on previous offset

---

## Implementation Phases

### Phase 1: Core Batch Sync (Week 1-2)
- XML Parser
- Schema mapping to Algolia
- PHP API integration for availability
- Hourly scheduled job
- Algolia account setup & initial indexing

### Phase 2: Real-time Kafka Integration (Week 2-3)
- Kafka consumer setup
- Field whitelist & transformation
- Partial update logic
- Monitoring & alerting

### Phase 3: Demo UI & Presentation (Week 3-4)
- React + InstantSearch frontend
- Faceting & search UX
- Dashboard configuration walkthrough
- Architecture diagram & documentation

### Phase 4: Optimization & Hardening (Ongoing)
- Performance tuning (cache strategy, batch sizes)
- Dead-letter queue processing
- Full reindex automation
- Analytics & insights review

---

## Deliverables Summary

| Deliverable | Responsibility | Timeline |
|-------------|----------------|----------|
| Data Ingestion Script | Search Indexer codebase (public repo) | Before 1st interview |
| Algolia Account Setup | Admin access w/ support enabled | Before 1st interview |
| Client Question Responses | Professional written answers | Before 1st interview |
| Architecture Presentation | Diagram + reasoning document | 2nd interview |
| UI Code Walkthrough | Demo + live component breakdown | 2nd interview |
| Dashboard Config Demo | Relevance, facets, analytics walkthrough | 2nd interview |

---

## Risk Mitigation

| Risk | Mitigation |
|-----|-----------|
| XML catalog unavailable | Cache latest version, use Kafka updates only (degraded) |
| Kafka consumer lag | Idempotent updates allow replay from stored offsets |
| PHP API rate limits hit | Queue manager with backoff, or read availability from XML (cached) |
| Algolia quota exceeded | Batch size tuning, record size optimization, feature flag for non-search fields |
| Data consistency issues | Full reindex on schedule, Kafka offset checkpointing |
