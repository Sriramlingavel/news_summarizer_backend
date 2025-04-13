import spacy
from collections import Counter

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def get_interest_similarity(interest, summary):
    """Calculate how strongly an interest matches a summary."""
    # Direct match gets highest score
    if interest.lower() in summary.lower():
        return 1.0
    
    # Use NLP to check for semantic similarity
    interest_doc = nlp(interest)
    summary_doc = nlp(summary)
    
    # Check for partial matches
    for token in interest_doc:
        if token.text.lower() in summary.lower() and len(token.text) > 3:
            return 0.7
    
    # Check for lemma matches
    interest_lemmas = set([token.lemma_.lower() for token in interest_doc 
                         if not token.is_stop and len(token.text) > 3])
    summary_lemmas = set([token.lemma_.lower() for token in summary_doc 
                        if not token.is_stop])
    
    overlap = interest_lemmas.intersection(summary_lemmas)
    if overlap:
        return 0.5 * (len(overlap) / len(interest_lemmas))
    
    return 0.0

def personalize_summary(summary: str, user_interests: list):
    """
    Enhance or personalize a summary based on stored user interests.
    
    Args:
        summary: The original summary text
        user_interests: List of user interests/topics
        
    Returns:
        Enhanced summary with personalization
    """
    if not user_interests:
        return summary  # No personalization if no interests
        
    # Calculate match scores for each interest
    interest_scores = {}
    for interest in user_interests:
        if not interest:
            continue
            
        score = get_interest_similarity(interest, summary)
        if score > 0:
            interest_scores[interest] = score
    
    # Sort interests by match score
    matching_interests = sorted(interest_scores.items(), key=lambda x: x[1], reverse=True)
    
    # If there are matching interests, enhance the summary
    if matching_interests:
        # Get top 3 matching interests
        top_interests = matching_interests[:3]
        
        # Create different personalization messages based on match strength
        strong_matches = [interest for interest, score in top_interests if score >= 0.7]
        weak_matches = [interest for interest, score in top_interests if 0 < score < 0.7]
        
        personalization_msg = ""
        
        if strong_matches:
            personalization_msg += f"\n[PERSONALIZED: This directly relates to your interests in {', '.join(strong_matches)}]"
        
        if weak_matches:
            relation = "also relates to" if strong_matches else "partially relates to"
            personalization_msg += f"\n[PERSONALIZED: This {relation} your interests in {', '.join(weak_matches)}]"
            
        # Add personalization to the end of the summary
        enhanced_summary = summary + personalization_msg
        return enhanced_summary
    
    return summary  # Return original if no matching interests

def analyze_user_interests(user_interests, current_topic, topic_interests_map):
    """
    Analyze user interests and compare to current topic.
    
    Args:
        user_interests: List of all user interests
        current_topic: The current topic being summarized
        topic_interests_map: Dictionary mapping topics to interests
        
    Returns:
        Dictionary with analytics insights
    """
    if not user_interests:
        return {"message": "Not enough data for analysis"}
        
    # Calculate frequency and recency of interests
    interest_frequency = Counter(user_interests)
    
    # Get top interests overall
    top_interests = interest_frequency.most_common(5)
    
    # Compare current topic to previous topics
    related_topics = []
    current_topic_interests = topic_interests_map.get(current_topic, [])
    
    for topic, interests in topic_interests_map.items():
        if topic != current_topic and interests:
            # Calculate overlap between interests
            common_interests = set(interests) & set(current_topic_interests)
            if common_interests:
                # Calculate a more nuanced similarity score
                similarity_score = len(common_interests) / max(1, len(set(interests + current_topic_interests)))
                
                # Adjust score based on interest strength
                adjusted_score = similarity_score
                for interest in common_interests:
                    # Interests that appear more frequently are weighted higher
                    if interest in interest_frequency:
                        adjusted_score *= (1 + 0.1 * min(interest_frequency[interest], 10))
                
                related_topics.append({
                    "topic": topic,
                    "common_interests": list(common_interests),
                    "similarity_score": adjusted_score
                })
    
    # Sort related topics by similarity
    related_topics = sorted(related_topics, key=lambda x: x["similarity_score"], reverse=True)
    
    # Provide trend analysis
    interest_growth = {}
    # Normally this would use timestamps, but since we don't have that in the data structure,
    # we'll just note which interests are growing in frequency
    
    return {
        "top_interests": top_interests,
        "related_topics": related_topics[:3],  # Limit to top 3 related topics
        "interest_count_by_topic": {t: len(set(i)) for t, i in topic_interests_map.items()},
        "total_unique_interests": len(interest_frequency),
        "user_profile": {
            "primary_interests": [interest for interest, _ in top_interests[:3]],
            "interest_diversity": min(10, len(interest_frequency) / max(1, len(topic_interests_map)))
        }
    }