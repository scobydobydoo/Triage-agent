import os
import re
import math
from typing import List, Tuple, Dict
from collections import defaultdict


class TFIDFRetriever:

    def __init__(self):
        self.documents: List[Dict] = []
        self.idf: Dict[str, float] = {}
        self.tfidf_matrix: List[Dict[str, float]] = []
        self._is_fitted = False

    
    # TOKENIZATION
    
    def _tokenize(self, text: str) -> List[str]:
        STOPWORDS = {
            "a","an","the","is","it","in","on","at","to","for",
            "of","and","or","but","with","from","by","be","are",
            "was","were","have","has","had","do","does","did",
            "this","that","these","those","i","you","we","they",
            "my","your","our","their","if","can","will","may",
            "would","should","could","not","no","as","so","up",
            "also","when","then","than","any","all","more","some",
        }
        tokens = re.findall(r"\b[a-z]{2,}\b", text.lower())
        return [t for t in tokens if t not in STOPWORDS]

    
    # TF / IDF
    
    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        tf = defaultdict(float)
        for t in tokens:
            tf[t] += 1
        n = len(tokens) or 1
        return {t: c / n for t, c in tf.items()}

    def _compute_idf(self, token_sets):
        N = len(token_sets)
        all_terms = set(t for s in token_sets for t in s)

        for term in all_terms:
            df = sum(1 for s in token_sets if term in s)
            self.idf[term] = math.log((N + 1) / (df + 1)) + 1.0

    def _cosine(self, v1, v2):
        common = set(v1.keys()) & set(v2.keys())
        if not common:
            return 0.0

        dot = sum(v1[t] * v2[t] for t in common)
        norm1 = math.sqrt(sum(v**2 for v in v1.values()))
        norm2 = math.sqrt(sum(v**2 for v in v2.values()))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

   
    #  KEYWORD BOOST 
    
    def _keyword_boost(self, query, doc_text):
        q_words = set(query.lower().split())
        d_words = set(doc_text.lower().split())

        overlap = len(q_words & d_words)
        return overlap * 0.02 

    # LOAD CORPUS
    def load_corpus(self, corpus_dir: str):

        company_map = {
            "hackerrank.txt": "HackerRank",
            "claude.txt": "Claude",
            "visa.txt": "Visa",
        }

        self.documents = []

        for filename in os.listdir(corpus_dir):
            if not filename.endswith(".txt"):
                continue

            company = company_map.get(filename, "General")
            path = os.path.join(corpus_dir, filename)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            sections = re.split(r"={3,}[^=]+={3,}", content)
            headers = re.findall(r"={3,}([^=]+)={3,}", content)

            for i, section in enumerate(sections):
                section = section.strip()
                if not section:
                    continue

                section_name = headers[i-1].strip() if i > 0 and i-1 < len(headers) else "General"

                paragraphs = [p.strip() for p in section.split("\n\n") if p.strip()]

                for para in paragraphs:
                    if len(para) > 30:
                        self.documents.append({
                            "text": para,
                            "company": company,
                            "section": section_name
                        })

        self._fit()


    # FIT
    def _fit(self):
        tokens = [self._tokenize(doc["text"]) for doc in self.documents]
        token_sets = [set(t) for t in tokens]

        self._compute_idf(token_sets)

        self.tfidf_matrix = []
        for t in tokens:
            tf = self._compute_tf(t)
            tfidf = {w: tf[w] * self.idf.get(w, 1.0) for w in tf}
            self.tfidf_matrix.append(tfidf)

        self._is_fitted = True

    # RETRIEVE

    def retrieve(self, query: str, company: str = None, top_k: int = 5):

        if not self._is_fitted:
            return []

        query_tokens = self._tokenize(query)
        query_tf = self._compute_tf(query_tokens)
        query_vec = {t: query_tf[t] * self.idf.get(t, 1.0) for t in query_tf}

        results = []

        for i, doc_vec in enumerate(self.tfidf_matrix):
            base_score = self._cosine(query_vec, doc_vec)

            
            boost = self._keyword_boost(query, self.documents[i]["text"])

            score = base_score + boost

            
            if company and self.documents[i]["company"] == company:
                score *= 1.4

            results.append((self.documents[i], round(score, 4)))

       
        results.sort(key=lambda x: x[1], reverse=True)

        
        filtered = [(doc, s) for doc, s in results if s > 0.1]

        return filtered[:top_k]
    
    def retrieve_for_company(self, query: str, company: str, top_k: int = 5):
      

        results = self.retrieve(query, company=company, top_k=top_k * 2)

        company_results = [
            (doc, score) for doc, score in results
            if doc.get("company") == company
            ]

        if company_results:
            return company_results[:top_k]

        return results[:top_k]