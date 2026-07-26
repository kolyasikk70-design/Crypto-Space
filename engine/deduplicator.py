import re
from difflib import SequenceMatcher
from typing import List, Set
from database import Database

class Deduplicator:
    def __init__(self, db: Database, threshold: float = 0.60):
        self.db = db
        self.threshold = threshold

    def _clean_tokens(self, text: str) -> Set[str]:
        words = re.findall(r'\w+', text.lower())
        stopwords = {"the", "a", "an", "in", "on", "of", "to", "for", "and", "is", "at", "by", "with", "from", "в", "на", "и", "с", "по", "для", "о", "об", "что", "как", "это"}
        return set(w for w in words if w not in stopwords and len(w) > 2)

    def compute_similarity(self, text1: str, text2: str) -> float:
        tokens1 = self._clean_tokens(text1)
        tokens2 = self._clean_tokens(text2)

        if not tokens1 or not tokens2:
            return 0.0

        # Containment ratio: overlap relative to smaller set size (prevents length disparity bias)
        overlap = len(tokens1.intersection(tokens2))
        smaller_size = min(len(tokens1), len(tokens2))
        containment = overlap / float(smaller_size) if smaller_size > 0 else 0.0

        seq_ratio = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        
        return max(containment, seq_ratio)

    def is_duplicate(self, title: str, summary: str = "") -> bool:
        combined = f"{title} {summary}"
        recent_posts = self.db.get_recent_posts(limit=40)

        for post in recent_posts:
            existing_text = f"{post.get('title', '')} {post.get('content', '')}"
            sim = self.compute_similarity(combined, existing_text)
            if sim >= self.threshold:
                return True

        return False
