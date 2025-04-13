import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timedelta
import uuid

# Load environment variables from .env file
load_dotenv()

# Initialize the Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def save_user_memory(user_id: str, topic: str, summary: str):
    """
    Save user memory to Supabase and return the memory ID.
    """
    try:
        # Get current timestamp
        current_time = datetime.now()
        timestamp = current_time.isoformat()
        
        # Create record without the date field
        response = supabase.table('user_memory').insert({
            'user_id': user_id,
            'topic': topic,
            'summary': summary,
            'timestamp': timestamp
            # Removed the 'date' field
        }).execute()
        
        print(f"Insert Response: {response}")
        
        if response.data and len(response.data) > 0:
            memory_id = response.data[0]['id']
            print(f"Successfully saved memory for user {user_id}.")
            return memory_id
        else:
            print(f"Failed to save memory for user {user_id}.")
            return None
            
    except Exception as e:
        print(f"Error saving memory: {e}")
        return None

def save_user_interests(user_id: str, interests: list, memory_id: str):
    """Update the user_interests field for an existing memory entry"""
    try:
        # Update the existing record by adding the interests
        response = supabase.table('user_memory')\
            .update({'user_interests': interests})\
            .eq('id', memory_id)\
            .execute()
        
        print(f"Update Interests Response: {response}")
        
        if response.data and len(response.data) > 0:
            print(f"Successfully saved interests for memory ID: {memory_id}")
            return True
        else:
            print(f"Failed to save interests for memory ID: {memory_id}")
            return False
            
    except Exception as e:
        print(f"Error saving interests: {e}")
        return False

def get_user_memory(user_id: str):
    """Retrieve a user's memory (preferences and summaries)"""
    response = supabase.table('user_memory').select('*').eq('user_id', user_id).execute()

    # Print the full response for debugging
    print(f"Raw response: {response}")

    if not response.data:
        print(f"No memory found for user: {user_id}")
        return []

    return response.data

def get_yesterday_summary(user_id: str, topic: str):
    """
    Get the most recent summary from yesterday for the specified topic.
    """
    # Calculate yesterday's date range
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = (today - timedelta(days=1)).isoformat()
    yesterday_end = today.isoformat()
    
    try:
        response = supabase.table('user_memory') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('topic', topic) \
            .gte('timestamp', yesterday_start) \
            .lt('timestamp', yesterday_end) \
            .order('timestamp', desc=True) \
            .limit(1) \
            .execute()
            
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            print(f"No summary found for yesterday for user {user_id} on topic {topic}")
            return None
            
    except Exception as e:
        print(f"Error getting yesterday's summary: {e}")
        return None

def get_today_summary(user_id: str, topic: str):
    """
    Get the most recent summary from today for the specified topic.
    """
    # Calculate today's date range
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    try:
        response = supabase.table('user_memory') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('topic', topic) \
            .gte('timestamp', today_start) \
            .order('timestamp', desc=True) \
            .limit(1) \
            .execute()
            
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            print(f"No summary found for today for user {user_id} on topic {topic}")
            return None
            
    except Exception as e:
        print(f"Error getting today's summary: {e}")
        return None
    
def save_comparison_result(user_id: str, topic: str, yesterday_id: str, today_id: str, comparison: str):
    """
    Save the comparison result in the user_memory table.
    """
    try:
        # Get current timestamp
        current_time = datetime.now()
        timestamp = current_time.isoformat()
        
        # Insert a new record as a comparison entry
        response = supabase.table('user_memory').insert({
            'user_id': user_id,
            'topic': topic,
            'summary': comparison,  # Store comparison text in summary field
            'timestamp': timestamp,
            'is_comparison': True,  # Flag to identify this as a comparison entry
            'yesterday_id': yesterday_id,
            'today_id': today_id
        }).execute()
        
        if response.data and len(response.data) > 0:
            comparison_id = response.data[0]['id']
            print(f"Successfully saved comparison for user {user_id}")
            return comparison_id
        else:
            print(f"Failed to save comparison for user {user_id}")
            return None
            
    except Exception as e:
        print(f"Error saving comparison: {e}")
        return None
    
def get_all_user_interests(user_id: str):
    """Get all stored interests for a user from previous summaries."""
    try:
        # Query all user memory entries that have interests
        response = supabase.table('user_memory') \
            .select('user_interests') \
            .eq('user_id', user_id) \
            .not_.is_('user_interests', 'null') \
            .execute()
            
        if not response.data:
            print(f"No interests found for user {user_id}")
            return []
        
        # Extract all interests and flatten the list
        all_interests = []
        for item in response.data:
            if item['user_interests']:
                all_interests.extend(item['user_interests'])
        
        # Remove duplicates and return
        return list(set([i for i in all_interests if i]))
        
    except Exception as e:
        print(f"Error getting user interests: {e}")
        return []

def get_interests_by_topic(user_id: str):
    """Get user interests organized by topic."""
    try:
        # Query all user memory entries with interests
        response = supabase.table('user_memory') \
            .select('topic, user_interests') \
            .eq('user_id', user_id) \
            .not_.is_('user_interests', 'null') \
            .execute()
            
        if not response.data:
            return {}
        
        # Organize interests by topic
        topics_map = {}
        for item in response.data:
            topic = item['topic']
            if topic not in topics_map:
                topics_map[topic] = []
                
            if item['user_interests']:
                topics_map[topic].extend(item['user_interests'])
        
        # Remove duplicates within each topic
        for topic in topics_map:
            topics_map[topic] = list(set([i for i in topics_map[topic] if i]))
            
        return topics_map
        
    except Exception as e:
        print(f"Error getting interests by topic: {e}")
        return {}
    
def get_all_topics():
    """Get all stored topics with their last updated timestamp."""
    try:
        # Query the database to get all unique topics with their last updated timestamp
        result = supabase.table("user_memory") \
            .select("topic, timestamp") \
            .execute()
        
        if not result.data:
            print("No topics found in the database")
            return []
        
        # Process results to get unique topics with latest timestamp
        topics_dict = {}
        for item in result.data:
            topic = item.get('topic')
            timestamp = item.get('timestamp')
            
            if not topic or not timestamp:
                continue
            
            # Keep only the latest timestamp for each topic
            if topic not in topics_dict or timestamp > topics_dict[topic]:
                topics_dict[topic] = timestamp
        
        # Convert to list of tuples sorted by most recent first
        topics_list = [(topic, timestamp) for topic, timestamp in topics_dict.items()]
        topics_list.sort(key=lambda x: x[1], reverse=True)
        
        return topics_list
    except Exception as e:
        print(f"Error retrieving topics: {e}")
        return []