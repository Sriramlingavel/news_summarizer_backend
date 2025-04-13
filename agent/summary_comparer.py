import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime, timedelta
import difflib

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini if API key is available
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
else:
    model = None
    print("Warning: GEMINI_API_KEY not found. Falling back to basic comparison.")

# Function to get yesterday's date in the required format for your storage system
def get_yesterday_date_string():
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")  # Adjust format as needed

# Function to retrieve previous day's summary
def get_previous_summary(user_id, topic):
    """
    Retrieve the previous day's summary for a specific user and topic.
    
    Args:
        user_id: The ID of the user
        topic: The topic of the summary
        
    Returns:
        The previous day's summary or None if not found
    """
    yesterday_date = get_yesterday_date_string()
    
    # Construct the file path where summaries are stored
    # Adjust this to match your actual storage structure
    summary_dir = os.path.join("summaries", user_id)
    summary_file = os.path.join(summary_dir, f"{topic}_{yesterday_date}.json")
    
    # Check if the file exists
    if os.path.exists(summary_file):
        try:
            with open(summary_file, 'r') as f:
                data = json.load(f)
                return data.get("summary")
        except Exception as e:
            print(f"Error retrieving previous summary: {e}")
            return None
    else:
        print(f"No previous summary found for user {user_id} on topic {topic}")
        return None

# Function to generate a current summary for a topic
def generate_current_summary(topic):
    """
    Generate a summary of the current news on a specific topic.
    
    Args:
        topic: The topic to summarize
        
    Returns:
        A summary of the current news on the topic
    """
    if model:
        try:
            # Create the prompt for Gemini
            prompt = f"""
            Please provide a comprehensive summary of the latest news regarding {topic}.
            Include major developments, key players, and significant events.

            Format your response as a concise news summary that covers the essential information.
            """
            
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error generating summary with Gemini API: {e}")
            return f"Failed to generate a summary for {topic}."
    else:
        return f"Cannot generate summary for {topic} - AI model not available."

# Function to save the current summary for future reference
def save_current_summary(user_id, topic, summary):
    """
    Save the current summary for a user and topic.
    
    Args:
        user_id: The ID of the user
        topic: The topic of the summary
        summary: The summary text
        
    Returns:
        True if saved successfully, False otherwise
    """
    today_date = datetime.now().strftime("%Y-%m-%d")  # Adjust format as needed
    
    # Construct the file path where summaries will be stored
    summary_dir = os.path.join("summaries", user_id)
    os.makedirs(summary_dir, exist_ok=True)  # Create directory if it doesn't exist
    summary_file = os.path.join(summary_dir, f"{topic}_{today_date}.json")
    
    try:
        with open(summary_file, 'w') as f:
            json.dump({
                "topic": topic,
                "date": today_date,
                "summary": summary
            }, f)
        return True
    except Exception as e:
        print(f"Error saving current summary: {e}")
        return False

# The compare_summaries function from your original code remains unchanged
def compare_summaries(yesterday_summary, today_summary, topic):
    """
    Compare yesterday's and today's summaries using Gemini AI or fallback to basic comparison.
    
    Args:
        yesterday_summary: The summary text from yesterday
        today_summary: The summary text from today
        topic: The topic of the news
        
    Returns:
        A detailed comparison highlighting changes, developments, and trends
    """
    if not yesterday_summary or not today_summary:
        if not yesterday_summary:
            return "No previous summary available for comparison."
        if not today_summary:
            return "No current summary available for comparison."
    
    # Check if Gemini is available
    if model:
        try:
            # Create the prompt for Gemini
            prompt = f"""
            Task: Compare these two news summaries on the topic of {topic} from consecutive days and identify key differences, developments, and trends.

            YESTERDAY'S SUMMARY:
            {yesterday_summary}

            TODAY'S SUMMARY:
            {today_summary}

            Please provide a detailed analysis that addresses:
            1. Major new developments that appeared today
            2. Stories that were in yesterday's news but not mentioned today
            3. Ongoing stories and how they have evolved
            4. Any shift in focus or tone in the coverage
            5. Notable quotes or statements that are new today

            Format your response as a concise news update highlighting the key changes and developments.
            """
            
            response = model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            print(f"Error using Gemini API: {e}")
            print("Falling back to basic comparison...")
            return fallback_comparison(yesterday_summary, today_summary)
    else:
        # Fallback comparison method if Gemini isn't available
        return fallback_comparison(yesterday_summary, today_summary)

# The fallback_comparison function from your original code remains unchanged
def fallback_comparison(yesterday_summary, today_summary):
    """
    Fallback method for comparing summaries without using AI.
    Uses difflib to find differences between the two texts.
    
    Args:
        yesterday_summary: The summary text from yesterday
        today_summary: The summary text from today
        
    Returns:
        A basic comparison highlighting differences
    """
    # Split the summaries into sentences
    yesterday_sentences = [s.strip() + '.' for s in yesterday_summary.split('.') if s.strip()]
    today_sentences = [s.strip() + '.' for s in today_summary.split('.') if s.strip()]
    
    # Find new sentences in today's summary
    new_today = [s for s in today_sentences if s not in yesterday_sentences]
    
    # Find sentences that were in yesterday's summary but not in today's
    removed = [s for s in yesterday_sentences if s not in today_sentences]
    
    # Generate the comparison report
    comparison = "# Summary Comparison\n\n"
    
    if new_today:
        comparison += "## New Developments Today\n"
        for sentence in new_today:
            comparison += f"- {sentence}\n"
        comparison += "\n"
    
    if removed:
        comparison += "## Stories No Longer Mentioned\n"
        for sentence in removed:
            comparison += f"- {sentence}\n"
        comparison += "\n"
    
    # Add overall assessment
    if len(new_today) > len(removed):
        comparison += "## Overall Assessment\n"
        comparison += "Today's news contains more new information than yesterday.\n"
    elif len(removed) > len(new_today):
        comparison += "## Overall Assessment\n"
        comparison += "Several stories from yesterday are no longer being covered today.\n"
    else:
        comparison += "## Overall Assessment\n"
        comparison += "The coverage between yesterday and today has shifted, with similar amounts of new and discontinued content.\n"
    
    return comparison

# The extract_key_changes function from your original code remains unchanged
def extract_key_changes(yesterday_summary, today_summary):
    """
    Extract the key changes between two summaries.
    
    Args:
        yesterday_summary: The summary from yesterday
        today_summary: The summary from today
        
    Returns:
        A list of key changes (additions, removals, modifications)
    """
    # Split summaries into words
    yesterday_words = set(yesterday_summary.lower().split())
    today_words = set(today_summary.lower().split())
    
    # Find new words in today's summary
    new_words = today_words - yesterday_words
    
    # Find words that were removed
    removed_words = yesterday_words - today_words
    
    return {
        "new_terms": list(new_words)[:10],  # Limit to 10 terms
        "removed_terms": list(removed_words)[:10]  # Limit to 10 terms
    }

# Now, let's create a function to handle the /compare route
def handle_compare_route(user_id, topic):
    """
    Handle the /compare route - generate current summary and compare with previous day.
    
    Args:
        user_id: The ID of the user requesting the comparison
        topic: The topic to compare summaries for
        
    Returns:
        A comparison of yesterday's and today's summaries
    """
    # Step 1: Get yesterday's summary
    yesterday_summary = get_previous_summary(user_id, topic)
    
    # Step 2: Generate today's summary
    current_summary = generate_current_summary(topic)
    
    # Step 3: Save today's summary for future comparisons
    save_current_summary(user_id, topic, current_summary)
    
    # Step 4: Compare the summaries
    comparison = compare_summaries(yesterday_summary, current_summary, topic)
    
    return {
        "topic": topic,
        "yesterday_summary": yesterday_summary,
        "today_summary": current_summary,
        "comparison": comparison,
        "key_changes": extract_key_changes(yesterday_summary or "", current_summary or "")
    }

# Example usage in a Flask/FastAPI app
"""
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/compare', methods=['POST'])
def compare():
    data = request.json
    user_id = data.get('user_id')
    topic = data.get('topic')
    
    if not user_id or not topic:
        return jsonify({"error": "user_id and topic are required"}), 400
    
    result = handle_compare_route(user_id, topic)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
"""

# Or with FastAPI
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class CompareRequest(BaseModel):
    user_id: str
    topic: str

@app.post('/compare')
def compare(request: CompareRequest):
    result = handle_compare_route(request.user_id, request.topic)
    return result
"""