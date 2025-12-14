# data-transform
Algolia integration mock 

PROBLEM: 

Systems: 
PHP+SQL: 
Internal API accessed within private network.
Provides ProdID (objectID). 
Up to 1k results per request, not more than 10 calls/s. 

Node+Mongo: 
Catalog.xml url accessible.
Updated every 1h. Contains all products on the website. 
The only way for the website to get product information is by pulling the catalog and connecting each product via ProdID (objectID).  

Kafka:
Topic from external  3rd party.
Includes product param updates. 
 
Additional:
Prod only environment, sync issues with kafka.
Catalogxml source of truth when sync errors/fails. 
The main goal is to produce a unified and accurate product catalog to be indexed by Algolia. 

Approach: 
1. Data Mapping following requirements 
2. Data ingestion Script creation. apiresponse.json provides product id (objectID) xmloutput.xml is accessible via URL. Has all products available, and matches products from apiresponse.json by product id (objectID) kafkamessage.json include product parameter updates. 
3. Parse>Resolve Conflicts> Output. 


## Key Architecture Principles ##

1. Source of Truth Hierarchy

PRIMARY (XML Catalog)
  ↓ Provides: structural data, descriptions, categories
  ↓
SECONDARY (Kafka Updates)
  ↓ Provides: real-time price, popularity, rating changes
  ↓
TERTIARY (PHP API)
  ↓ Provides: product availability/visibility signal
  ↓
CONFLICT RESOLUTION: XML always wins on data discrepancies vs Kafka. 
CONDITION: If objectID is not in apiresponse.json exclude from output.

2.Data Flow Patterns 

Batch Synchronization (Hourly): 
XML Catalog (fetch) → Parse → Validate against PHP API → Normalize → Algolia Bulk Update

Real-time Updates (Continuous):
Kafka Topic → Consumer → Field Whitelist (price, popularity, rating) → Algolia Partial Update

Full Reindex (On-demand):
XML Catalog (full) + Kafka Replay (recent window) → Complete re-derivation → Fresh Algolia index


TODO: 
1. Architecture Diagram.
2. Data parser and aggregator script. 
3. Output to match Expected Algolia Payload.
4. Load up to Algolia. 
5. Configure Algolia. 
6. Create Demo UI. 
