from fastapi import FastAPI, HTTPException, Request
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
from agent.news_fetcher import fetch_news
from agent.summarizer import summarize_article
from agent.memory_manager import (
    save_user_memory, get_user_memory, get_all_user_interests, 
    get_interests_by_topic, get_yesterday_summary, get_today_summary,
    save_comparison_result, get_all_topics  # Added get_all_topics here
)
from agent.tagging import save_user_interests, extract_topics
from agent.personalizer import personalize_summary, analyze_user_interests
from agent.summary_comparer import compare_summaries, extract_key_changes
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware to allow requests from your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-vercel-app-url.vercel.app"],  # Update with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables from .env file
load_dotenv()

# Initialize the Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.middleware("http")
async def check_authorization(request: Request, call_next):
    # Define public routes that don't need authentication
    public_paths = ["/", "/docs", "/redoc", "/openapi.json"]
    
    # Skip auth check for public paths or specific endpoints you want to exempt
    if request.url.path in public_paths or request.url.path.startswith("/summarize/") or request.url.path.startswith("/test_personalization/") or request.url.path.startswith("/compare/"):
        return await call_next(request)
    
    # Check for token
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Updated version for newer Supabase client
    try:
        # For newer versions of Supabase client
        response = await supabase.auth.get_user(token)
        user = response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")
    
    request.state.user = user  # Attach user info to the request state
    response = await call_next(request)
    return response

@app.get("/")
def root():
    return {"message": "Welcome to News Summarizer AI"}

@app.get("/summarize/")
async def summarize_news(user_id: str, topic: str):
    # Check if the user has any saved memory (preferences)
    user_memory = get_user_memory(user_id)
    print(f"User Memory: {user_memory}")
    
    # Get all previous user interests
    all_user_interests = get_all_user_interests(user_id)
    print(f"Found {len(all_user_interests)} stored interests for user {user_id}")
    
    # Get interests organized by topic
    topic_interests_map = get_interests_by_topic(user_id)
    
    # Fallback for empty memory - default topics if none exist
    if not all_user_interests:
        print("No user interests found. Using default interests.")
        # You could customize default interests by topic
        if topic.lower() == "technology":
            all_user_interests = ["technology", "innovation", "gadgets"]
        elif topic.lower() == "sports":
            all_user_interests = ["sports", "competition", "teams"]
        else:
            all_user_interests = ["news", "current events", topic.lower()]
    
    # Fetch news - this stays the same
    articles = fetch_news(topic)
    
    # Generate and store new summaries for the user
    summaries = []
    for article in articles:
        # Create the basic summary
        basic_summary = summarize_article(article)
        
        # Personalize the summary using stored interests
        personalized_summary = personalize_summary(basic_summary, all_user_interests)
        
        # Extract topics from the basic summary (limited to top 5)
        new_topics = extract_topics(basic_summary)
        
        # Save the summary to memory (for future reference)
        memory_id = save_user_memory(user_id, topic, basic_summary)
        
        # Save the user interests (tags)
        save_user_interests(user_id, new_topics, memory_id)
        
        # Add both versions to the results
        summaries.append({
            "original": basic_summary,
            "personalized": personalized_summary,
            "matched_interests": [i for i in all_user_interests if i and i.lower() in basic_summary.lower()],
            "new_topics": new_topics
        })
    
    # Run analytics on the user's interests
    analytics = analyze_user_interests(all_user_interests, topic, topic_interests_map)
    
    return {
        "topic": topic, 
        "summaries": summaries,
        "analytics": analytics
    }

@app.get("/compare/")
async def compare_news(user_id: str, topic: str):
    """
    Compare today's news summary with yesterday's for a specific topic.
    
    Args:
        user_id: The user's ID
        topic: The topic to compare
    
    Returns:
        Comparison between yesterday and today's summaries
    """
    # Step 1: Retrieve Yesterday's Summary
    yesterday_data = get_yesterday_summary(user_id, topic)
    
    # Step 2: Retrieve Today's Summary
    today_data = get_today_summary(user_id, topic)
    
    # Check if we have both summaries
    if not yesterday_data:
        return {
            "topic": topic,
            "status": "no_yesterday_data",
            "message": "No summary available from yesterday for comparison.",
            "has_comparison": False
        }
    
    if not today_data:
        # If no summary for today, suggest generating one
        return {
            "topic": topic,
            "status": "no_today_data",
            "message": "No summary available for today. Please generate a summary first.",
            "has_comparison": False
        }
    
    # Get the actual summary texts
    yesterday_summary = yesterday_data["summary"]
    today_summary = today_data["summary"]
    
    # Step 3: Compare the summaries
    comparison_text = compare_summaries(yesterday_summary, today_summary, topic)
    
    # Extract key changes for quick reference
    key_changes = extract_key_changes(yesterday_summary, today_summary)
    
    # Step 4: Save the comparison result
    comparison_id = save_comparison_result(
        user_id,
        topic,
        yesterday_data["id"],
        today_data["id"],
        comparison_text
    )
    
    # Step 5: Return the comparison
    return {
        "topic": topic,
        "status": "success",
        "yesterday_date": yesterday_data.get("date", "unknown"),
        "today_date": today_data.get("date", "unknown"),
        "comparison": comparison_text,
        "key_changes": key_changes,
        "has_comparison": True,
        "comparison_id": comparison_id
    }

@app.get("/test_personalization/")
async def test_personalization(user_id: str):
    """Test endpoint to verify that personalization is working correctly."""
    # Get all user interests
    all_interests = get_all_user_interests(user_id)
    
    if not all_interests:
        # Use fallback interests for testing
        all_interests = ["technology", "sports", "news", "current events"]
        print("No user interests found. Using default interests for testing.")
    
    # Create test summaries - one that matches interests, one that doesn't
    import random
    test_interests = random.sample(all_interests, min(3, len(all_interests)))
    
    # Create a summary that contains those interests
    matching_summary = f"This is a test summary that contains your interests in {', '.join(test_interests)}."
    
    # Create a summary with no matches
    non_matching_summary = "This test summary talks about topics that don't match any of your stored interests."
    
    # Apply personalization to both
    personalized_matching = personalize_summary(matching_summary, all_interests)
    personalized_non_matching = personalize_summary(non_matching_summary, all_interests)
    
    return {
        "user_id": user_id,
        "all_interests": all_interests,
        "test_results": [
            {
                "original": matching_summary,
                "personalized": personalized_matching,
                "interests_matched": test_interests,
                "personalization_applied": matching_summary != personalized_matching
            },
            {
                "original": non_matching_summary,
                "personalized": personalized_non_matching,
                "interests_matched": [],
                "personalization_applied": non_matching_summary != personalized_non_matching
            }
        ]
    }

@app.get("/interests")
async def get_user_interests():
    """Get all unique topics that have been stored"""
    try:
        # Use the fixed get_all_topics function
        topics = get_all_topics()
        
        # Format the response
        interests = [
            {
                "topic": topic, 
                "last_searched": timestamp
            } 
            for topic, timestamp in topics
        ]
        
        return {"interests": interests}
    except Exception as e:
        error_message = f"Error fetching interests: {str(e)}"
        print(error_message)  # Log the error to the console
        raise HTTPException(status_code=500, detail=error_message)
    
@app.get("/debug/table-structure")
async def debug_table_structure():
    """Debug endpoint to check the structure of the user_memory table."""
    try:
        # Try to get a single row to check if table exists and its structure
        response = supabase.table('user_memory').select('*').limit(1).execute()
        
        if response.data:
            # Table exists and has data
            sample_row = response.data[0]
            column_names = list(sample_row.keys())
            
            # Get total count of records
            count_response = supabase.table('user_memory').select('*', count='exact').execute()
            record_count = count_response.count if hasattr(count_response, 'count') else "Unknown"
            
            return {
                "table_exists": True,
                "has_data": True,
                "column_names": column_names,
                "sample_row": sample_row,
                "record_count": record_count
            }
        else:
            # Table exists but has no data
            return {
                "table_exists": True,
                "has_data": False,
                "message": "Table exists but contains no data"
            }
    except Exception as e:
        return {
            "table_exists": False,
            "error": str(e),
            "message": "Failed to query table structure"
        }

@app.get("/debug/test-direct-insert")
async def debug_direct_insert():
    """Try a direct insert into the user_memory table with minimal fields."""
    try:
        # Prepare minimal test data
        test_data = {
            'user_id': 'debug_user',
            'topic': 'test_topic',
            'summary': 'This is a direct test summary.',
            'timestamp': datetime.now().isoformat()
        }
        
        # Attempt direct insert
        response = supabase.table('user_memory').insert(test_data).execute()
        
        if response.data and len(response.data) > 0:
            inserted_id = response.data[0].get('id', 'unknown')
            return {
                "success": True,
                "message": "Successfully inserted test data",
                "inserted_id": inserted_id,
                "response": response.data[0]
            }
        else:
            return {
                "success": False,
                "message": "Insert API call completed but no data returned",
                "response": response
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to insert test data"
        }

@app.get("/debug/test-interests-update")
async def debug_interests_update():
    """Test updating user_interests for an existing record."""
    try:
        # First, insert a test record
        test_data = {
            'user_id': 'debug_user',
            'topic': 'test_topic',
            'summary': 'Test summary for interests update.',
            'timestamp': datetime.now().isoformat()
        }
        
        insert_response = supabase.table('user_memory').insert(test_data).execute()
        
        if not insert_response.data or len(insert_response.data) == 0:
            return {
                "success": False,
                "message": "Failed to create test record for interests update"
            }
        
        # Get the ID of the inserted record
        record_id = insert_response.data[0]['id']
        
        # Now try to update the user_interests field
        test_interests = ["test1", "test2", "debug"]
        update_response = supabase.table('user_memory')\
            .update({'user_interests': test_interests})\
            .eq('id', record_id)\
            .execute()
            
        if update_response.data and len(update_response.data) > 0:
            return {
                "success": True,
                "message": "Successfully updated user_interests",
                "record_id": record_id,
                "updated_record": update_response.data[0]
            }
        else:
            return {
                "success": False,
                "message": "Update API call completed but no data returned",
                "record_id": record_id
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to update user_interests"
        }