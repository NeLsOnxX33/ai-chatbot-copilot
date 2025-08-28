from fastapi.templating import Jinja2Templates
from fastapi import Request, APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sqlite3
from copilot.auth import admin_required
from datetime import datetime
import pytz

router = APIRouter()
templates = Jinja2Templates(directory="templates")

class FeedbackInput(BaseModel):
    message: str
    rating: int

def convert_utc_to_local(utc_timestamp_str, timezone='Asia/Kolkata'):
    """Convert UTC timestamp to local timezone"""
    try:
        # Parse the UTC timestamp
        utc_dt = datetime.fromisoformat(utc_timestamp_str.replace('Z', '+00:00'))
        
        # Convert to local timezone
        local_tz = pytz.timezone(timezone)
        local_dt = utc_dt.astimezone(local_tz)
        
        return local_dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Error converting timestamp: {e}")
        return utc_timestamp_str

@router.get("/feedback/admin", response_class=HTMLResponse)
async def feedbackadmin(request: Request, _: None = Depends(admin_required)):
    """Admin feedback dashboard with authentication"""
    try:
        # Fetch feedback data from database
        conn = sqlite3.connect("chat_history.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, session_id, rating, comment, created_at 
            FROM feedback 
            ORDER BY created_at DESC
        """)
        feedback_data = cursor.fetchall()
        conn.close()

        # Convert to list of dictionaries for template with timezone conversion
        feedback_list = []
        for row in feedback_data:
            feedback_list.append({
                "id": row[0],
                "session_id": row[1],
                "rating": row[2],
                "comment": row[3] if row[3] else "",  # Ensure comment is not None
                "created_at": convert_utc_to_local(row[4]) if row[4] else "N/A"
            })

        # Calculate statistics
        total_feedback = len(feedback_list)
        
        # Calculate average rating
        ratings = [item["rating"] for item in feedback_list if item["rating"] is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        # Count comments (non-empty comments)
        comment_count = sum(1 for item in feedback_list if item["comment"] and item["comment"].strip())

        return templates.TemplateResponse(
            "admin_feedback.html", 
            {
                "request": request, 
                "feedback_data": feedback_list,
                "total_feedback": total_feedback,
                "avg_rating": round(avg_rating, 1),
                "comment_count": comment_count
            }
        )

    except Exception as e:
        print(f"Error in feedbackadmin: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading feedback data: {str(e)}")

@router.post("/submit_feedback")
async def submit_feedback(feedback: FeedbackInput):
    """Submit new feedback (legacy endpoint for compatibility)"""
    try:
        conn = sqlite3.connect("chat_history.db")
        cursor = conn.cursor()
        
        # Get current timestamp in UTC
        current_time = datetime.utcnow().isoformat()
        
        cursor.execute(
            "INSERT INTO feedback (session_id, rating, comment, created_at) VALUES (?, ?, ?, ?)",
            ("unknown", feedback.rating, feedback.message, current_time)
        )
        conn.commit()
        conn.close()

        return {"status": "success", "message": "Feedback submitted successfully"}
    except Exception as e:
        print(f"Error in submit_feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}")

@router.get("/feedback/stats")
async def get_feedback_stats():
    """Get feedback statistics"""
    try:
        conn = sqlite3.connect("chat_history.db")
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM feedback")
        total_count = cursor.fetchone()[0]
        
        # Get average rating
        cursor.execute("SELECT AVG(rating) FROM feedback WHERE rating IS NOT NULL")
        avg_rating = cursor.fetchone()[0] or 0
        
        # Get comment count
        cursor.execute("SELECT COUNT(*) FROM feedback WHERE comment IS NOT NULL AND comment != ''")
        comment_count = cursor.fetchone()[0]
        
        # Get rating distribution
        cursor.execute("SELECT rating, COUNT(*) FROM feedback WHERE rating IS NOT NULL GROUP BY rating ORDER BY rating")
        rating_distribution = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_feedback": total_count,
            "average_rating": round(avg_rating, 2),
            "comments_count": comment_count,
            "rating_distribution": rating_distribution
        }
        
    except Exception as e:
        print(f"Error getting feedback stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving feedback statistics: {str(e)}")