"""In-memory semantic vector store.

Uses TF-IDF (word uni/bi-grams + character n-grams) embeddings with cosine
similarity. The interface (add documents, query, best_sentence) mirrors what a
FAISS/ChromaDB + transformer-embedding backend would expose, so it can be
swapped without touching the matcher.
"""
import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer


class VectorStore:
    def __init__(self, documents: dict, extra_corpus: list[str] | None = None):
        self.keys = list(documents.keys())
        corpus = [documents[k] or "" for k in self.keys] + (extra_corpus or [])
        self._word = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True, min_df=1)
        self._char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=1)
        self.ok = any(c.strip() for c in corpus)
        if self.ok:
            try:
                self._word.fit(corpus)
                self._char.fit(corpus)
                self.matrix = self._embed([documents[k] or "" for k in self.keys])
            except ValueError:  # empty vocabulary
                self.ok = False

    def _embed(self, texts: list[str]):
        w = self._word.transform(texts)
        c = self._char.transform(texts)
        m = hstack([w * 0.7, c * 0.3]).tocsr()
        norms = np.sqrt(m.multiply(m).sum(axis=1)).A1
        norms[norms == 0] = 1.0
        return m.multiply(1 / norms[:, None]).tocsr()

    def query(self, text: str) -> dict:
        """Cosine similarity of `text` against every stored document."""
        if not self.ok or not self.keys:
            return {k: 0.0 for k in self.keys}
        q = self._embed([text])
        sims = (self.matrix @ q.T).toarray().ravel()
        return {k: float(s) for k, s in zip(self.keys, sims)}

    def best_sentence(self, text: str, sentences: list[str]) -> tuple[str, float]:
        if not self.ok or not sentences:
            return "", 0.0
        q = self._embed([text])
        m = self._embed(sentences)
        sims = (m @ q.T).toarray().ravel()
        i = int(np.argmax(sims))
        return sentences[i], float(sims[i])
