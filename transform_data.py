#!/usr/bin/env python3
"""
DATA TRANSFORMATION & NORMALIZATION SCRIPT

This script:
- Parses xmloutput.xml structure
- Applies kafkamessage.json field whitelisting (type, price_range, url, free_shipping, popularity, rating) 
  against apiresponse.json for existing objects
- Merges data: XML as source of truth + Kafka enrichments
- Validates against apiresponse.json for existing objectID, excludes if no match
- Maps to Algolia schema (expectedalgoliapayloadcopy.json)
"""

import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Set, Optional
from html import unescape


def parse_xml(xml_file: str) -> List[Dict]:
    """Parse XML structure and extract row data."""
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    rows = []
    for row in root.findall('row'):
        row_data = {}
        
        # Extract basic fields
        for field in ['name', 'description', 'brand', 'price', 'image', 'objectID']:
            elem = row.find(field)
            if elem is not None and elem.text:
                row_data[field] = unescape(elem.text.strip())
        
        # Extract multiple categories
        categories = []
        for cat in row.findall('categories'):
            if cat.text:
                categories.append(unescape(cat.text.strip()))
        if categories:
            row_data['categories'] = categories
        
        # Extract hierarchicalCategories
        hierarchical_cats = row.find('hierarchicalCategories')
        if hierarchical_cats is not None:
            hier_cats = {}
            for lvl in ['lvl0', 'lvl1', 'lvl2', 'lvl3']:
                lvl_elem = hierarchical_cats.find(lvl)
                if lvl_elem is not None and lvl_elem.text:
                    hier_cats[lvl] = unescape(lvl_elem.text.strip())
            if hier_cats:
                row_data['hierarchicalCategories'] = hier_cats
        
        # Convert price to float if present
        if 'price' in row_data:
            try:
                row_data['price'] = float(row_data['price'])
            except ValueError:
                pass
        
        rows.append(row_data)
    
    return rows


def load_kafka_enrichments(kafka_file: str, valid_object_ids: Set[str]) -> Dict[str, Dict]:
    """
    Load Kafka enrichments and create lookup for whitelisted fields.
    Only includes enrichments for objects that exist in apiresponse.json
    """
    with open(kafka_file, 'r') as f:
        kafka_data = json.load(f)
    
    # Whitelisted fields from Kafka
    WHITELISTED_FIELDS = ['type', 'price_range', 'url', 'free_shipping', 'popularity', 'rating']
    
    enrichments = {}
    for item in kafka_data:
        object_id = item.get('objectID')
        
        # Only include enrichments for objects that exist in API response
        if object_id and object_id in valid_object_ids:
            enrichment = {}
            for field in WHITELISTED_FIELDS:
                if field in item:
                    enrichment[field] = item[field]
            
            if enrichment:
                enrichments[object_id] = enrichment
    
    return enrichments


def load_api_response(api_file: str) -> Set[str]:
    """Load API response and extract valid objectIDs."""
    with open(api_file, 'r') as f:
        api_data = json.load(f)
    
    valid_object_ids = set()
    for item in api_data:
        object_id = item.get('objectID')
        if object_id:
            valid_object_ids.add(str(object_id))
    
    return valid_object_ids


def transform_to_algolia_schema(xml_row: Dict, kafka_enrichments: Dict) -> Optional[Dict]:
    """
    Transform XML row to Algolia schema format.
    Merges XML (source of truth) with Kafka enrichments (whitelisted fields only).
    """
    object_id = str(xml_row.get('objectID', ''))
    
    # Start with XML data as source of truth
    algolia_item = {
        'name': xml_row.get('name', ''),
        'description': xml_row.get('description', ''),
        'brand': xml_row.get('brand', ''),
        'categories': xml_row.get('categories', []),
        'hierarchicalCategories': xml_row.get('hierarchicalCategories', {}),
        'image': xml_row.get('image', ''),
        'objectID': object_id
    }
    
    # Get price from XML (source of truth - never override with Kafka)
    price = xml_row.get('price')
    
    # Apply Kafka enrichments (whitelisted fields only) if available
    if object_id in kafka_enrichments:
        enrich = kafka_enrichments[object_id]
        
        # Apply all whitelisted fields from Kafka enrichments
        # Exclude 'price' - always use XML price
        for field, value in enrich.items():
            if field != 'price':  # Price always comes from XML
                algolia_item[field] = value
    
    # Set price from XML (convert to float if needed)
    if price is not None:
        algolia_item['price'] = float(price) if isinstance(price, (int, float, str)) else None
    
    return algolia_item


def main():
    """Main transformation function."""
    
    # File paths
    XML_FILE = 'xmloutput.xml'
    KAFKA_FILE = 'kafkamessage.json'
    API_FILE = 'apiresponse.json'
    OUTPUT_FILE = 'algolia_transformed.json'
    
    print("Loading data files...")
    
    # Load API response to get valid objectIDs
    valid_object_ids = load_api_response(API_FILE)
    print(f"Found {len(valid_object_ids)} valid objectIDs in API response")
    
    # Load Kafka enrichments (only for valid objectIDs)
    kafka_enrichments = load_kafka_enrichments(KAFKA_FILE, valid_object_ids)
    print(f"Loaded {len(kafka_enrichments)} Kafka enrichments for valid objects")
    
    # Parse XML (source of truth)
    xml_rows = parse_xml(XML_FILE)
    print(f"Parsed {len(xml_rows)} rows from XML")
    
    # Transform and validate
    transformed = []
    excluded_count = 0
    
    for xml_row in xml_rows:
        object_id = str(xml_row.get('objectID', ''))
        
        # Validate objectID against API response
        if object_id not in valid_object_ids:
            excluded_count += 1
            print(f"Excluding objectID {object_id} - not found in API response")
            continue
        
        # Transform to Algolia schema
        algolia_item = transform_to_algolia_schema(xml_row, kafka_enrichments)
        
        if algolia_item:
            transformed.append(algolia_item)
    
    print(f"\nTransformation complete:")
    print(f"  - Included: {len(transformed)} items")
    print(f"  - Excluded: {excluded_count} items")
    
    # Write output
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(transformed, f, indent=2, ensure_ascii=False)
    
    print(f"\nOutput written to: {OUTPUT_FILE}")
    
    return transformed


if __name__ == '__main__':
    main()
