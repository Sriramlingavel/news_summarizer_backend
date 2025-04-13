import spacy
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from datetime import datetime
from collections import Counter
import string

# Load environment variables
load_dotenv()

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Load spaCy's pre-trained model
nlp = spacy.load("en_core_web_sm")

def normalize_topic(topic):
    """Normalize a topic by removing punctuation, extra spaces, and converting to lowercase."""
    # Remove punctuation and convert to lowercase
    translator = str.maketrans('', '', string.punctuation)
    normalized = topic.translate(translator).lower().strip()
    
    # Handle common variations
    mapping = {
        "ai": ["artificial intelligence", "a.i.", "a.i"],
        "tech": ["technology", "technological"],
        "cryptocurrency": ["crypto", "cryptocurrencies", "bitcoin", "ethereum"],
        "climate change": ["global warming", "climate crisis"],
        # Add more mappings as needed
    }
    
    # Check if the normalized topic maps to a standard form
    for standard, variations in mapping.items():
        if normalized in variations:
            return standard
    
    return normalized

def calculate_topic_weight(topic, doc, is_entity=False, is_noun_phrase=False):
    """Calculate a weight for a topic based on various factors."""
    weight = 1.0
    
    # Entities are typically more important
    if is_entity:
        weight *= 1.5
    
    # Noun phrases can be meaningful
    if is_noun_phrase:
        weight *= 1.2
    
    # Topics appearing multiple times are more important
    topic_lower = topic.lower()
    count = sum(1 for token in doc if token.text.lower() == topic_lower)
    weight *= (1 + 0.2 * count)
    
    # Topics appearing at the beginning of the text might be more important
    first_100_chars = doc.text[:100].lower()
    if topic_lower in first_100_chars:
        weight *= 1.3
    
    # Longer topics might be more specific/meaningful (but not too long)
    topic_length = len(topic.split())
    if 2 <= topic_length <= 3:
        weight *= 1.2
    
    return weight

def extract_topics(summary: str, max_topics=5):
    """
    Extract meaningful topics from the summary with normalization and weighting.
    Returns only the top 5 most important topics.
    """
    doc = nlp(summary)
    
    # Create a dictionary to store topics and their weights
    topic_weights = {}
    
    # Extract named entities (organizations, locations, etc.)
    for ent in doc.ents:
        if ent.label_ in ['ORG', 'GPE', 'LOC', 'PRODUCT', 'EVENT', 'PERSON']:
            normalized_entity = normalize_topic(ent.text)
            if len(normalized_entity) > 3:
                weight = calculate_topic_weight(ent.text, doc, is_entity=True)
                topic_weights[normalized_entity] = max(topic_weights.get(normalized_entity, 0), weight)
    
    # Extract noun phrases but filter for relevance
    for chunk in doc.noun_chunks:
        # Filter out common pronouns and generic terms
        chunk_text = chunk.text.strip()
        if (len(chunk_text) > 3 and 
            not chunk_text.lower() in ['a', 'an', 'the', 'they', 'it', 'this', 'that', 'these', 'those']):
            normalized_chunk = normalize_topic(chunk_text)
            if len(normalized_chunk) > 3:
                weight = calculate_topic_weight(chunk_text, doc, is_noun_phrase=True)
                topic_weights[normalized_chunk] = max(topic_weights.get(normalized_chunk, 0), weight)
    
    # Extract keywords based on part-of-speech tags and frequency
    keyword_counter = Counter()
    for token in doc:
        if (token.pos_ in ['NOUN', 'PROPN'] and len(token.text) > 3 and not token.is_stop):
            keyword_counter[token.lemma_.lower()] += 1
    
    # Add keywords to the weighted topics
    for keyword, count in keyword_counter.items():
        normalized_keyword = normalize_topic(keyword)
        if len(normalized_keyword) > 3:
            weight = calculate_topic_weight(keyword, doc) * (1 + 0.1 * count)
            topic_weights[normalized_keyword] = max(topic_weights.get(normalized_keyword, 0), weight)
    
    # Remove very generic terms
    for generic_term in ['a', 'an', 'the', 'they', 'it', 'this', 'that', 'article', 'news', 'report', 'story']:
        if generic_term in topic_weights:
            del topic_weights[generic_term]
    
    # Get the top N topics by weight
    top_topics = sorted(topic_weights.items(), key=lambda x: x[1], reverse=True)[:max_topics]
    
    # Return just the topic names (not the weights)
    return [topic for topic, _ in top_topics]

def save_user_interests(user_id: str, topics: list, memory_id: str = None):
    """Store user interests (tags) in the user_memory table for a specific memory record."""
    try:
        # Limit to top 5 topics
        limited_topics = topics[:5] if topics else []
        
        if not memory_id:
            # If no specific memory_id provided, find the most recent entry
            response = supabase.table('user_memory') \
                .select('id') \
                .eq('user_id', user_id) \
                .order('timestamp', desc=True) \
                .limit(1) \
                .execute()
                
            if not response.data:
                print(f"No memory found for user {user_id}")
                return False
                
            memory_id = response.data[0]['id']
            
        # Update the user_interests field for this specific record
        update_response = supabase.table('user_memory') \
            .update({'user_interests': limited_topics}) \
            .eq('id', memory_id) \
            .execute()
            
        print(f"Update Response: {update_response}")
        return True
        
    except Exception as e:
        print(f"Error saving user interests: {e}")
        return False