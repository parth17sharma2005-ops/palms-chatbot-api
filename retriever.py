# retriever.py - ENHANCED WITH SMARTER SEARCH
import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import re

class DocumentRetriever:
    def __init__(self, embeddings_file="embeddings/embeddings.npy", metadata_file="embeddings/metadata.json"):
        self.embeddings_file = embeddings_file
        self.metadata_file = metadata_file
        self.model = None
        self.embeddings = None
        self.metadata = None
        self.load_embeddings()
    
    def _ensure_model_loaded(self):
        if self.model is None:
            print("Loading advanced sentence transformer model...")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ AI Model ready for semantic understanding!")
    
    def load_embeddings(self):
        try:
            if os.path.exists(self.embeddings_file) and os.path.exists(self.metadata_file):
                self.embeddings = np.load(self.embeddings_file)
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                print(f"✅ Loaded {len(self.embeddings)} knowledge chunks")
            else:
                print("❌ No knowledge base found. Run chunk_and_embed.py first.")
                self.embeddings = np.array([])
                self.metadata = []
        except Exception as e:
            print(f"❌ Error loading knowledge: {e}")
            self.embeddings = np.array([])
            self.metadata = []
    
    def smart_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Advanced semantic search with query understanding"""
        if self.embeddings is None or len(self.embeddings) == 0:
            return []
        
        self._ensure_model_loaded()
        
        try:
            # Enhanced query understanding
            enhanced_query = self.enhance_query(query)
            print(f"🔍 AI Searching for: '{enhanced_query}'")
            
            # Generate embedding for the enhanced query
            query_embedding = self.model.encode([enhanced_query])[0]
            
            # Calculate semantic similarities
            similarities = np.dot(self.embeddings, query_embedding)
            norms = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
            similarities = similarities / norms
            
            # Get most relevant results
            actual_top_k = min(top_k, len(self.embeddings))
            top_indices = np.argpartition(similarities, -actual_top_k)[-actual_top_k:]
            top_indices = top_indices[np.argsort(similarities[top_indices])][::-1]
            
            # Return intelligent results
            results = []
            for idx in top_indices:
                if idx < len(self.metadata):
                    result = self.metadata[idx].copy()
                    result['similarity'] = float(similarities[idx])
                    result['relevance_score'] = self.calculate_relevance_score(result, query)
                    results.append(result)
            
            # Sort by relevance score
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            print(f"✅ AI Found {len(results)} relevant knowledge pieces")
            return results
            
        except Exception as e:
            print(f"❌ AI Search error: {e}")
            return []
    
    def enhance_query(self, query: str) -> str:
        """Make the query more effective for semantic search"""
        query = query.lower().strip()
        
        # Add context based on query type
        if any(word in query for word in ['price', 'cost', 'how much', 'pricing']):
            query += " pricing cost subscription plan"
        elif any(word in query for word in ['feature', 'what can', 'capability', 'do']):
            query += " features capabilities functions"
        elif any(word in query for word in ['client', 'customer', 'case study', 'testimonial']):
            query += " clients customers case studies testimonials"
        elif any(word in query for word in ['integrate', 'api', 'connect', 'compatible']):
            query += " integration api connectivity compatibility"
        
        return query
    
    def calculate_relevance_score(self, result: Dict, original_query: str) -> float:
        """Calculate smart relevance score considering multiple factors"""
        text = result.get('text', '').lower()
        similarity = result.get('similarity', 0)
        
        # Boost score for certain content types
        score = similarity
        
        # Boost for structured content (your manual improvements!)
        if any(marker in text for marker in ['key features:', 'benefits:', 'pricing tiers:', 'faq:']):
            score *= 1.3  # 30% boost for well-structured content
        
        # Boost for specific query matches
        original_query = original_query.lower()
        if any(word in text for word in original_query.split()):
            score *= 1.2
        
        return score

# Global retriever instance
_retriever = None

def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = DocumentRetriever()
    return _retriever

def retrieve(query: str, top_k: int = 5) -> List[Dict]:
    retriever = get_retriever()
    return retriever.smart_search(query, top_k)