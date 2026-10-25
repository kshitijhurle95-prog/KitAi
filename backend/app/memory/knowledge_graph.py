"""NetworkX-based Concept Knowledge Graph for prerequisites and mastery tracking."""
import json
from pathlib import Path
from typing import Dict, Any, List
import networkx as nx
from app.config import settings
from app.utils.logger import logger

GRAPH_FILE = settings.DATA_DIR / "concept_graph.json"


class ConceptKnowledgeGraph:
    """Maintains a directed graph of concepts and their prerequisite relationships."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self._load()

    def _load(self):
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        if GRAPH_FILE.exists():
            try:
                with open(GRAPH_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.graph = nx.node_link_graph(data, directed=True)
                    logger.info(f"Loaded concept graph with {self.graph.number_of_nodes()} concepts.")
            except Exception as e:
                logger.warning(f"Failed to load concept graph: {e}")
                self._seed_default_graph()
        else:
            self._seed_default_graph()

    def _save(self):
        try:
            data = nx.node_link_data(self.graph)
            with open(GRAPH_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save concept graph: {e}")

    def _seed_default_graph(self):
        """Seed foundational CS, Math, and AI concept dependencies."""
        self.graph.clear()
        foundations = [
            # CS Foundations
            ("Variables & Data Types", "Control Flow (If/Else, Loops)", "CS"),
            ("Control Flow (If/Else, Loops)", "Functions & Scope", "CS"),
            ("Functions & Scope", "Recursion", "CS"),
            ("Functions & Scope", "Data Structures (Arrays, Lists)", "CS"),
            ("Data Structures (Arrays, Lists)", "Hash Maps & Sets", "CS"),
            ("Data Structures (Arrays, Lists)", "Trees & Graphs", "CS"),
            ("Trees & Graphs", "Graph Search (BFS & DFS)", "CS"),
            ("Recursion", "Dynamic Programming", "CS"),

            # Math Foundations
            ("Basic Algebra", "Functions & Graphs", "Math"),
            ("Functions & Graphs", "Calculus (Derivatives)", "Math"),
            ("Calculus (Derivatives)", "Calculus (Integrals)", "Math"),
            ("Basic Algebra", "Linear Algebra (Vectors & Matrices)", "Math"),

            # AI & ML
            ("Calculus (Derivatives)", "Gradient Descent & Optimization", "AI"),
            ("Linear Algebra (Vectors & Matrices)", "Neural Networks Architecture", "AI"),
            ("Gradient Descent & Optimization", "Deep Learning Training", "AI"),
            ("Neural Networks Architecture", "Transformers & Attention Mechanism", "AI"),
            ("Transformers & Attention Mechanism", "Large Language Models", "AI")
        ]

        for prereq, target, cat in foundations:
            self.graph.add_node(prereq, category=cat)
            self.graph.add_node(target, category=cat)
            self.graph.add_edge(prereq, target, relation="prerequisite_of")

        self._save()

    def add_concept_relation(self, prereq: str, concept: str, category: str = "General"):
        self.graph.add_node(prereq, category=category)
        self.graph.add_node(concept, category=category)
        self.graph.add_edge(prereq, concept, relation="prerequisite_of")
        self._save()

    def get_prerequisites(self, concept: str) -> List[str]:
        if concept in self.graph:
            return list(nx.ancestors(self.graph, concept))
        return []

    def get_concept_subgraph(self, topic: str, depth: int = 2) -> Dict[str, Any]:
        """Returns JSON-compatible nodes and links centered on topic."""
        matches = [n for n in self.graph.nodes if topic.lower() in n.lower()]
        target_nodes = set(matches) if matches else set(list(self.graph.nodes)[:10])

        expanded = set(target_nodes)
        for node in target_nodes:
            try:
                expanded.update(self.graph.predecessors(node))
                expanded.update(self.graph.successors(node))
            except Exception:
                pass

        subgraph = self.graph.subgraph(expanded) if expanded else self.graph
        return {
            "topic": topic,
            "nodes": [{"id": n, "category": self.graph.nodes[n].get("category", "General")} for n in subgraph.nodes],
            "edges": [{"source": u, "target": v, "relation": d.get("relation", "prerequisite_of")} for u, v, d in subgraph.edges(data=True)]
        }


concept_graph = ConceptKnowledgeGraph()
