#!/usr/bin/env python3
"""
Tokenization pipeline for trending topics.

Filters and processes words for Italian brain rot content generation.
"""
import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Set
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google.cloud import storage
from loguru import logger

from scripts.brainrot.config import config

load_dotenv()

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tag import pos_tag
    from nltk.tokenize import word_tokenize
    NLTK_AVAILABLE = True
    
    # Download required NLTK data
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    
    try:
        nltk.data.find('taggers/averaged_perceptron_tagger')
    except LookupError:
        nltk.download('averaged_perceptron_tagger', quiet=True)
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
        
except ImportError:
    NLTK_AVAILABLE = False
    logger.warning("NLTK not available. Install with: pip install nltk")

try:
    from better_profanity import profanity
    PROFANITY_AVAILABLE = True
except ImportError:
    PROFANITY_AVAILABLE = False
    logger.warning("better_profanity not available. Install with: pip install better-profanity")


class TrendTokenizer:
    """Tokenize and filter trending topics."""
    
    def __init__(self):
        """Initialize tokenizer."""
        self.stop_words = set()
        if NLTK_AVAILABLE:
            try:
                self.stop_words = set(stopwords.words('english'))
            except LookupError:
                logger.warning("English stopwords not available, downloading...")
                import nltk
                nltk.download('stopwords', quiet=True)
                self.stop_words = set(stopwords.words('english'))
            
            # Add Italian stopwords if available
            try:
                italian_stopwords = set(stopwords.words('italian'))
                self.stop_words.update(italian_stopwords)
            except (LookupError, OSError):
                logger.debug("Italian stopwords not available")
        
        # POS tag mapping
        self.pos_map = {
            'NN': 'NOUN',
            'NNS': 'NOUN',
            'NNP': 'NOUN',
            'NNPS': 'NOUN',
            'VB': 'VERB',
            'VBD': 'VERB',
            'VBG': 'VERB',
            'VBN': 'VERB',
            'VBP': 'VERB',
            'VBZ': 'VERB'
        }
    
    def tokenize_trends(
        self,
        trends: List[Dict[str, Any]],
        language: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Tokenize trending topics into individual words.
        
        Args:
            trends: List of trending topic dictionaries
            language: Language code ("en" or "it")
            
        Returns:
            List of tokenized words with metadata
        """
        all_tokens = []
        
        for trend in trends:
            term = trend.get("term", "")
            if not term:
                continue
            
            # Tokenize the term
            tokens = self._tokenize_term(term, language)
            
            for token in tokens:
                all_tokens.append({
                    "word": token["word"],
                    "pos": token["pos"],
                    "original_term": term,
                    "language": language,
                    "source_rank": trend.get("rank", 0),
                    "source_score": trend.get("score", 0)
                })
        
        # Remove duplicates while preserving metadata
        unique_tokens = self._deduplicate_tokens(all_tokens)
        
        # Filter tokens
        filtered_tokens = self._filter_tokens(unique_tokens)
        
        logger.info(f"Tokenized {len(trends)} trends into {len(filtered_tokens)} unique tokens")
        return filtered_tokens
    
    def _tokenize_term(self, term: str, language: str) -> List[Dict[str, str]]:
        """Tokenize a single term."""
        if not NLTK_AVAILABLE:
            # Fallback: simple word splitting
            words = re.findall(r'\b\w+\b', term.lower())
            return [{"word": w, "pos": "UNKNOWN"} for w in words]
        
        # Use NLTK for proper tokenization
        try:
            tokens = word_tokenize(term.lower())
            tagged = pos_tag(tokens)
        except Exception as e:
            logger.warning(f"Tokenization failed for '{term}': {e}")
            # Fallback: simple word splitting
            words = re.findall(r'\b\w+\b', term.lower())
            return [{"word": w, "pos": "UNKNOWN"} for w in words]
        
        result = []
        for word, pos_tag_val in tagged:
            # Map NLTK POS tags to our format
            pos = self.pos_map.get(pos_tag_val, "OTHER")
            
            # Only include nouns and verbs if configured
            if config.parts_of_speech and pos in config.parts_of_speech:
                result.append({
                    "word": word,
                    "pos": pos
                })
        
        return result
    
    def _deduplicate_tokens(self, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate tokens, keeping the one with highest score."""
        seen = {}
        
        for token in tokens:
            word = token["word"]
            score = token.get("source_score", 0)
            
            if word not in seen or seen[word]["source_score"] < score:
                seen[word] = token
        
        return list(seen.values())
    
    def _filter_tokens(self, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter tokens based on configuration."""
        filtered = []
        
        for token in tokens:
            word = token["word"]
            
            # Length filter
            if len(word) < config.min_word_length or len(word) > config.max_word_length:
                continue
            
            # Stop words filter
            if word.lower() in self.stop_words:
                continue
            
            # Profanity filter
            if config.filter_profanity:
                if PROFANITY_AVAILABLE:
                    try:
                        # better_profanity uses censor() or check() method
                        if profanity.contains_profanity(word):
                            continue
                    except AttributeError:
                        # Fallback if API changed
                        try:
                            if profanity.check(word):
                                continue
                        except AttributeError:
                            # Use basic check as last resort
                            if self._basic_profanity_check(word):
                                continue
                else:
                    # Basic profanity check
                    if self._basic_profanity_check(word):
                        continue
            
            # Part of speech filter (check if config.parts_of_speech is initialized)
            if config.parts_of_speech and token["pos"] not in config.parts_of_speech:
                continue
            
            # Only alphanumeric (allow hyphens and apostrophes for compound words)
            # Remove special chars but keep hyphens/apostrophes for valid words
            if not word.replace('-', '').replace("'", '').isalnum():
                continue
            
            filtered.append(token)
        
        return filtered
    
    def _basic_profanity_check(self, word: str) -> bool:
        """Basic profanity check without external library."""
        # Simple blacklist (expand as needed)
        bad_words = {
            "damn", "hell", "crap", "ass", "bitch", "fuck", "shit"
        }
        return word.lower() in bad_words
    
    def save_to_gcs(
        self,
        tokens: List[Dict[str, Any]],
        country_code: str
    ) -> str:
        """Save tokenized data to GCS."""
        storage_client = storage.Client()
        bucket = storage_client.bucket(config.gcs_bucket_name)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Map country codes to consistent directory names
        country_dir = "us_trends" if country_code.upper() == "US" else "italian_trends"
        filename = f"{country_dir}/tokenized/tokens_{timestamp}.json"
        
        blob = bucket.blob(filename)
        blob.upload_from_string(
            json.dumps(tokens, indent=2),
            content_type="application/json"
        )
        
        logger.info(f"Saved {len(tokens)} tokens to gs://{config.gcs_bucket_name}/{filename}")
        return filename


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("Trend Tokenization")
    logger.info("=" * 60)
    
    # Load trends from GCS
    storage_client = storage.Client()
    bucket = storage_client.bucket(config.gcs_bucket_name)
    
    tokenizer = TrendTokenizer()
    
    # Process US trends
    logger.info("\nProcessing US trends...")
    us_blobs = list(bucket.list_blobs(prefix="us_trends/raw/"))
    if us_blobs:
        latest_blob = max(us_blobs, key=lambda b: b.time_created)
        us_data = json.loads(latest_blob.download_as_text())
        us_tokens = tokenizer.tokenize_trends(us_data, language="en")
        tokenizer.save_to_gcs(us_tokens, "US")
        logger.info(f"✅ US tokens: {len(us_tokens)}")
    
    # Process Italian trends
    logger.info("\nProcessing Italian trends...")
    it_blobs = list(bucket.list_blobs(prefix="italian_trends/raw/"))
    if it_blobs:
        latest_blob = max(it_blobs, key=lambda b: b.time_created)
        it_data = json.loads(latest_blob.download_as_text())
        it_tokens = tokenizer.tokenize_trends(it_data, language="it")
        tokenizer.save_to_gcs(it_tokens, "IT")
        logger.info(f"✅ Italian tokens: {len(it_tokens)}")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Tokenization complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

