"""Data loading module for WahlOMat data."""
import json
import os
from pathlib import Path
from typing import Dict, List, Any


class DataLoader:
    """Loads WahlOMat data from JSON files."""
    
    def __init__(self, data_path: str):
        """
        Initialize the data loader.
        
        Args:
            data_path: Path to the directory containing the JSON data files
        """
        self.data_path = Path(data_path)
        self.statements: List[Dict[str, Any]] = []
        self.parties: List[Dict[str, Any]] = []
        self.opinions: List[Dict[str, Any]] = []
        self.answers: List[Dict[str, Any]] = []
        self.comments: List[Dict[str, Any]] = []
        self.overview: Dict[str, Any] = {}
        
    def load_all(self):
        """Load all data files."""
        self.load_statements()
        self.load_parties()
        self.load_answers()
        self.load_opinions()
        self.load_comments()
        self.load_overview()
        
    def load_statements(self):
        """Load statements.json."""
        file_path = self.data_path / "statement.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            self.statements = json.load(f)
            
    def load_parties(self):
        """Load party.json."""
        file_path = self.data_path / "party.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            self.parties = json.load(f)
            
    def load_answers(self):
        """Load answer.json."""
        file_path = self.data_path / "answer.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            self.answers = json.load(f)
            
    def load_opinions(self):
        """Load opinion.json."""
        file_path = self.data_path / "opinion.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            self.opinions = json.load(f)
            
    def load_comments(self):
        """Load comment.json."""
        file_path = self.data_path / "comment.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            self.comments = json.load(f)
            
    def load_overview(self):
        """Load overview.json."""
        file_path = self.data_path / "overview.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            self.overview = json.load(f)
            
    def get_party_opinion(self, party_id: int, statement_id: int) -> int:
        """
        Get a party's opinion on a statement.
        
        Args:
            party_id: Party ID
            statement_id: Statement ID
            
        Returns:
            Answer ID (0=agree, 1=disagree, 2=neutral)
        """
        for opinion in self.opinions:
            if opinion['party'] == party_id and opinion['statement'] == statement_id:
                return opinion['answer']
        raise ValueError(f"No opinion found for party {party_id} on statement {statement_id}")
        
    def get_answer_label(self, answer_id: int) -> str:
        """
        Get the label for an answer ID.
        
        Args:
            answer_id: Answer ID (0, 1, or 2)
            
        Returns:
            Answer label string
        """
        for answer in self.answers:
            if answer['id'] == answer_id:
                return answer['message']
        raise ValueError(f"Invalid answer ID: {answer_id}")

