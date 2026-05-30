# scratch/test_pgvector.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import SessionLocal
from core.models import IntentRoutingKnowledge
from core.ollama_client import get_embedding

db = SessionLocal()
print("Connected to DB successfully.")

try:
    print("Generating embedding for query...")
    query = "Lên camp mới cho sản phẩm G-Agent Tech"
    query_vector = get_embedding(query)
    print(f"Success! Query vector generated: length={len(query_vector)}")
    
    print("Executing pgvector query...")
    distance_expr = IntentRoutingKnowledge.embedding.cosine_distance(query_vector)
    
    results = (
        db.query(IntentRoutingKnowledge, distance_expr)
        .filter(IntentRoutingKnowledge.is_active == True)
        .order_by(distance_expr)
        .limit(3)
        .all()
    )
    
    print(f"Query completed successfully! Found {len(results)} results:")
    for record, distance in results:
        print(f" - Utterance: {record.utterance}, Intent: {record.intent_category}, Distance: {distance}")
        
except Exception as e:
    print(f"Error during pgvector query: {e}")
finally:
    db.close()
