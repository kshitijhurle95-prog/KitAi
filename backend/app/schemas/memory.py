"""Schemas for vector memory and knowledge graph endpoints."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class MemorySearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]


class ConceptNode(BaseModel):
    id: str
    category: Optional[str] = "general"


class ConceptEdge(BaseModel):
    source: str
    target: str
    relation: Optional[str] = "prerequisite_of"


class ConceptMapResponse(BaseModel):
    topic: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
