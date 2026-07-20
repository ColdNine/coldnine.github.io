"""Korean keyword extraction and summarization.

Keyword extraction: Okt noun tokenization + TF-IDF scoring.
Summarization: TextRank over Korean sentences.
"""

import logging
import re
from collections import Counter
from typing import Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sumy.models.dom import ObjectDocumentModel, Paragraph, Sentence
from sumy.summarizers.text_rank import TextRankSummarizer

logger = logging.getLogger(__name__)

# Common Korean stopwords / functional nouns that are rarely meaningful as keywords.
STOPWORDS = {
    "것", "등", "수", "이", "그", "저", "때", "년", "월", "일", "위", "중", "및",
    "관련", "통해", "대한", "기자", "오늘", "지난해", "올해", "현재", "이번", "이날",
    "우리", "자신", "때문", "이후", "이상", "정도", "가운데", "그리고",
}

_okt = None


def _get_okt():
    """Lazily initialize the KoNLPy Okt tokenizer (starts a JVM on first use)."""
    global _okt
    if _okt is None:
        from konlpy.tag import Okt

        try:
            _okt = Okt()
        except Exception as exc:  # JVM init failures raise various exception types
            raise RuntimeError(
                "Failed to initialize KoNLPy Okt tokenizer (JVM init failed). "
                "Ensure a JDK (Java 9+) is installed and discoverable."
            ) from exc
    return _okt


def tokenize_nouns(text: str) -> List[str]:
    """Extract noun tokens from Korean text using the Okt tokenizer."""
    okt = _get_okt()
    return okt.nouns(text)


def filter_tokens(tokens: List[str]) -> List[str]:
    """Remove stopwords and single-character tokens."""
    return [t for t in tokens if len(t) > 1 and t not in STOPWORDS]


def _tfidf_scores_single_document(tokens: List[str]) -> Dict[str, float]:
    """Simple TF scoring with a repetition-based weighting for a single document.

    Used when no corpus is available for real inverse-document-frequency weighting.
    """
    counts = Counter(tokens)
    total = sum(counts.values())
    scores = {}
    for term, count in counts.items():
        tf = count / total
        # Terms that recur across the document are more likely a true topical keyword.
        idf_like = 1.0 + (count - 1) * 0.15
        scores[term] = tf * idf_like
    return scores


def _tfidf_scores_corpus(joined_documents: List[str]) -> List[Dict[str, float]]:
    """Compute true TF-IDF scores for the first document relative to a corpus."""
    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform(joined_documents)
    feature_names = vectorizer.get_feature_names_out()
    results = []
    for row in matrix:
        row_scores = {feature_names[idx]: row[0, idx] for idx in row.nonzero()[1]}
        results.append(row_scores)
    return results


def extract_keywords_tfidf(
    text: str, n_keywords: int = 7, corpus: Optional[List[str]] = None
) -> List[str]:
    """Extract the top N keywords from Korean article text.

    Tokenizes `text` into nouns via KoNLPy's Okt, filters stopwords/short tokens,
    and scores remaining terms with TF-IDF. If `corpus` (other article texts) is
    given, TF-IDF is computed against that corpus for real IDF weighting; otherwise
    falls back to a single-document term-frequency approximation.
    """
    if not text or not text.strip():
        return []

    try:
        tokens = filter_tokens(tokenize_nouns(text))
    except RuntimeError as exc:
        logger.error("Keyword extraction failed: %s", exc)
        return []

    if not tokens:
        return []

    if corpus:
        try:
            other_tokens = [filter_tokens(tokenize_nouns(doc)) for doc in corpus]
        except RuntimeError as exc:
            logger.warning(
                "Corpus tokenization failed, falling back to single-document scoring: %s",
                exc,
            )
            scores = _tfidf_scores_single_document(tokens)
        else:
            joined = [" ".join(tokens)] + [" ".join(t) for t in other_tokens]
            scores = _tfidf_scores_corpus(joined)[0]
    else:
        scores = _tfidf_scores_single_document(tokens)

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [term for term, _ in ranked[:n_keywords]]


# Splits on '.', '!', '?' followed by whitespace -- nltk's punkt (used by sumy's
# built-in Tokenizer) doesn't support Korean, so sentence/word splitting is custom here.
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")


class _KoreanTokenizer:
    """Minimal sumy-compatible tokenizer: regex sentence split + whitespace word split."""

    def to_sentences(self, text: str) -> List[str]:
        text = text.strip()
        if not text:
            return []
        return [s.strip() for s in _SENTENCE_SPLIT_PATTERN.split(text) if s.strip()]

    def to_words(self, sentence: str) -> List[str]:
        return sentence.split()


def split_korean_sentences(text: str) -> List[str]:
    """Split Korean text into sentences on '.', '!', '?' boundaries."""
    return _KoreanTokenizer().to_sentences(text)


def summarize_textrank(text: str, sentence_count: int = 4) -> str:
    """Generate an extractive summary of `text` using the TextRank algorithm.

    Splits `text` into sentences, ranks them via TextRank (PageRank over a
    sentence-similarity graph), and returns the top `sentence_count` sentences
    in their original document order, joined into a single string. Falls back
    to the first `sentence_count` sentences if TextRank fails or the article
    is too short to rank meaningfully.
    """
    sentences = split_korean_sentences(text)
    if not sentences:
        return ""
    if len(sentences) <= sentence_count:
        return " ".join(sentences)

    try:
        tokenizer = _KoreanTokenizer()
        # Built directly (not via sumy's PlaintextParser): that parser treats any
        # all-uppercase line as a heading, which misfires on Korean text containing
        # acronyms like "AI"/"IPO" with no lowercase letters, dropping the paragraph.
        document = ObjectDocumentModel(
            [Paragraph(Sentence(s, tokenizer) for s in sentences)]
        )
        summarizer = TextRankSummarizer()
        ranked_sentences = summarizer(document, sentence_count)
        summary = " ".join(str(s) for s in ranked_sentences)
        if summary.strip():
            return summary
        logger.warning("TextRank returned an empty summary, falling back to first sentences")
    except Exception as exc:
        logger.warning(
            "TextRank summarization failed, falling back to first %d sentences: %s",
            sentence_count, exc,
        )

    return " ".join(sentences[:sentence_count])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sample = (
        "앤트로픽, 메타와 15조원 규모 연산 자원 임대 계약 논의. 앤트로픽은 메타의 데이터센터를 활용해 "
        "AI 모델 학습을 위한 연산 자원을 확보할 계획이다. 업계는 이번 계약이 앤트로픽의 IPO 준비와 "
        "맞물려 있다고 분석한다."
    )
    print(extract_keywords_tfidf(sample, n_keywords=5))
    print(summarize_textrank(sample, sentence_count=2))
