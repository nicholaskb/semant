"""
Configuration for Brain Rot project.

All parameters are centralized here for easy modification.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BrainRotConfig:
    """Configuration for Brain Rot pipeline."""
    
    # GCS Configuration
    gcs_bucket_name: str = "brainrot-trends"
    
    # BigQuery Configuration
    bigquery_project: Optional[str] = None  # Uses default project if None
    bigquery_dataset: str = "bigquery-public-data.google_trends"
    bigquery_table: str = "top_terms"
    time_range_weeks: int = 1  # Parameterized: query last N weeks
    
    # Google Trends Configuration
    pytrends_regions: Optional[List[str]] = None  # ["US", "IT"] - defaults below
    max_trending_topics_per_region: int = 50
    
    # Tokenization Configuration
    min_word_length: int = 2
    max_word_length: int = 15
    filter_profanity: bool = True
    parts_of_speech: Optional[List[str]] = None  # ["NOUN", "VERB"] - defaults below
    
    # AI Configuration
    ai_model: str = "gemini-1.5-flash"  # Using Gemini as specified
    combinations_per_run: int = 15  # Generate 10-20 combinations
    
    # Italian Language Configuration
    include_modern_slang: bool = True
    include_traditional_phrases: bool = True
    include_abbreviations: bool = True
    avoid_cultural_sensitivity: bool = True
    
    # Image Generation Configuration
    image_style: str = "meme-style, surreal, vibrant colors"
    aspect_ratio: str = "9:16"  # Social media format
    variations_per_combination: int = 2
    
    # Output Configuration
    output_format: Optional[List[str]] = None  # ["json", "csv"] - defaults below
    store_in_gcs: bool = True
    store_locally: bool = True
    
    def __post_init__(self):
        """Set defaults for mutable fields."""
        if self.pytrends_regions is None:
            self.pytrends_regions = ["US", "IT"]
        
        if self.parts_of_speech is None:
            self.parts_of_speech = ["NOUN", "VERB"]
        
        if self.output_format is None:
            self.output_format = ["json", "csv"]


# Global config instance
config = BrainRotConfig()

