import json
from difflib import get_close_matches
import os

# Get the directory of the current file and construct the path to faqs.json
current_dir = os.path.dirname(os.path.abspath(__file__))
faq_path = os.path.join(current_dir, "..", "faqs.json")

def load_faqs():
    """Load FAQ data from JSON file"""
    try:
        with open(faq_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"FAQ file not found at: {faq_path}")
        return []
    except json.JSONDecodeError:
        print(f"Invalid JSON in FAQ file: {faq_path}")
        return []

def get_answer(user_input: str) -> str:
    """
    Get answer for user input using fuzzy matching
    
    Args:
        user_input (str): User's question
        
    Returns:
        str: Bot's answer or default message
    """
    try:
        faqs = load_faqs()
        if not faqs:
            return "Sorry, FAQ data is not available at the moment. Please try again later."
        
        user_input = user_input.lower().strip()
        
        # Extract questions and convert to lowercase
        questions = [item["question"].lower().strip() for item in faqs]
        
        # Find closest match with 50% similarity threshold
        match = get_close_matches(user_input, questions, n=1, cutoff=0.5)
        
        if match:
            # Find the original item with the matched question
            for item in faqs:
                if item["question"].lower().strip() == match[0]:
                    return item["answer"]
        
        return "Sorry, I couldn't find an answer to your question. Please check your question and try again."
    
    except Exception as e:
        print(f"Error in get_answer: {e}")
        return "Sorry, I encountered an error while processing your question. Please try again."