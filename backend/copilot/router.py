import sqlite3
import uuid
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from copilot.actions import get_answer
import logging
from datetime import datetime, timezone
import csv
import smtplib
from email.mime.text import MIMEText
import os

router = APIRouter()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────
# Database Setup
# ─────────────────────────────────────
def init_db():
    """Initialize the database with proper tables and indexes"""
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()

    # Create sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            message TEXT NOT NULL,
            sender TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions (session_id)
        )
    ''')

    # Create indexes for better performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_messages_session_id 
        ON chat_messages (session_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
        ON chat_messages (timestamp)
    ''')

    # Create feedback table with proper timezone handling
    cursor.execute('''
         CREATE TABLE IF NOT EXISTS feedback (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             session_id TEXT,
             rating INTEGER,
             comment TEXT,
             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
             FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

# Initialize database on module load
init_db()

# ─────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    session_id: str

class MessageHistory(BaseModel):
    message: str
    sender: str
    timestamp: str

class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[MessageHistory]

class SessionResponse(BaseModel):
    session_id: str

class FeedbackInput(BaseModel):
    session_id: str
    rating: Optional[int] = None
    comment: Optional[str] = ""

# Email Configuration (set these in environment variables)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "your_email@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "your_app_password")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")

def send_email_notification(session_id, rating, comment):
    """Send email notification for new feedback"""
    if not all([SMTP_USERNAME, SMTP_PASSWORD, ADMIN_EMAIL]):
        logger.warning("Email configuration incomplete, skipping notification")
        return
    
    try:
        subject = f"New Chatbot Feedback - Rating: {rating}/5"
        body = f"""
        New feedback received from chatbot:
        
        Session ID: {session_id}
        Rating: {rating}/5
        Comment: {comment if comment else 'No comment provided'}
        Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_USERNAME
        msg['To'] = ADMIN_EMAIL

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
            smtp.sendmail(SMTP_USERNAME, ADMIN_EMAIL, msg.as_string())
            
        logger.info(f"Email notification sent for feedback from session {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")

# ─────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────
def create_session() -> str:
    """Create a new chat session"""
    session_id = str(uuid.uuid4())
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    
    try:
        current_time = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            'INSERT INTO chat_sessions (session_id, created_at) VALUES (?, ?)', 
            (session_id, current_time)
        )
        conn.commit()
        logger.info(f"Created new session: {session_id}")
    except sqlite3.IntegrityError:
        logger.error(f"Session {session_id} already exists")
        raise HTTPException(status_code=500, detail="Failed to create unique session")
    finally:
        conn.close()
    
    return session_id

def save_message(session_id: str, message: str, sender: str):
    """Save a message to the database with proper timestamp"""
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    
    try:
        # Ensure session exists
        if not session_exists(session_id):
            cursor.execute(
                'INSERT INTO chat_sessions (session_id, created_at) VALUES (?, ?)', 
                (session_id, datetime.now(timezone.utc).isoformat())
            )
        
        # Save message with UTC timestamp
        current_time = datetime.now(timezone.utc).isoformat()
        cursor.execute('''
            INSERT INTO chat_messages (session_id, message, sender, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (session_id, message, sender, current_time))
        conn.commit()
        logger.info(f"Saved {sender} message for session {session_id}")
    except Exception as e:
        logger.error(f"Error saving message: {e}")
        raise HTTPException(status_code=500, detail="Failed to save message")
    finally:
        conn.close()

def get_chat_history(session_id: str) -> List[MessageHistory]:
    """Retrieve chat history for a session"""
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT message, sender, timestamp
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
        ''', (session_id,))
        messages = cursor.fetchall()
        logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
        
        return [MessageHistory(
            message=msg[0],
            sender=msg[1],
            timestamp=msg[2]
        ) for msg in messages]
    
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        return []
    finally:
        conn.close()

def session_exists(session_id: str) -> bool:
    """Check if a session exists"""
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT COUNT(*) FROM chat_sessions WHERE session_id = ?', (session_id,))
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        logger.error(f"Error checking session existence: {e}")
        return False
    finally:
        conn.close()

def clear_session_messages(session_id: str) -> int:
    """Clear all messages for a session and return count of deleted messages"""
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    
    try:
        # Count messages before deleting
        cursor.execute("SELECT COUNT(*) FROM chat_messages WHERE session_id = ?", (session_id,))
        count = cursor.fetchone()[0]
        
        # Delete messages
        cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        conn.commit()
        
        logger.info(f"Cleared {count} messages for session {session_id}")
        return count
    
    except Exception as e:
        logger.error(f"Error clearing messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear messages")
    finally:
        conn.close()

# ─────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────

@router.post("/", response_model=ChatResponse)
async def chat(request: Request):
    """Main chat endpoint with improved error handling"""
    try:
        data = await request.json()
        user_message = data.get("message", "").strip()
        session_id = data.get("session_id")
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")

        # Create new session if not provided or invalid
        if not session_id or not session_exists(session_id):
            session_id = create_session()
            logger.info(f"Created new session for chat: {session_id}")

        # Save user message
        save_message(session_id, user_message, "user")

        # Get bot response
        try:
            bot_response = get_answer(user_message)
            if not bot_response or bot_response.strip() == "":
                bot_response = "Sorry, I couldn't understand your question. Please try again."
        except Exception as e:
            logger.error(f"Error getting bot response: {e}")
            bot_response = "Sorry, I encountered an error processing your request. Please try again."

        # Save bot response
        save_message(session_id, bot_response, "bot")

        logger.info(f"Chat completed for session: {session_id}")
        return ChatResponse(reply=bot_response, session_id=session_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_session_history(session_id: str):
    """Get chat history for a specific session"""
    try:
        messages = get_chat_history(session_id) if session_exists(session_id) else []
        return ChatHistoryResponse(session_id=session_id, messages=messages)
    except Exception as e:
        logger.error(f"Error fetching chat history for {session_id}: {e}")
        return ChatHistoryResponse(session_id=session_id, messages=[])

@router.post("/session", response_model=SessionResponse)
async def create_new_session():
    """Create a new chat session"""
    try:
        session_id = create_session()
        return SessionResponse(session_id=session_id)
    except Exception as e:
        logger.error(f"Error creating new session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")

@router.delete("/clear/{session_id}")
def clear_chat_history(session_id: str):
    """Clear chat history for a specific session"""
    try:
        if not session_exists(session_id):
            return {
                "status": "success",
                "message": "Session not found, nothing to clear."
            }
        
        deleted_count = clear_session_messages(session_id)
        
        return {
            "status": "success",
            "message": f"Successfully cleared {deleted_count} messages.",
            "deleted_count": deleted_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while clearing chat history")

@router.get("/sessions")
async def get_all_sessions():
    """Get all chat sessions with message counts"""
    try:
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT cs.session_id, cs.created_at,
                   COUNT(cm.id) as message_count
            FROM chat_sessions cs
            LEFT JOIN chat_messages cm ON cs.session_id = cm.session_id
            GROUP BY cs.session_id, cs.created_at
            ORDER BY cs.created_at DESC
        ''')
        sessions = cursor.fetchall()
        conn.close()

        return [
            {
                "session_id": s[0], 
                "created_at": s[1], 
                "message_count": s[2]
            }
            for s in sessions
        ]

    except Exception as e:
        logger.error(f"Error retrieving sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete an entire session and all its messages"""
    try:
        if not session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        
        # Delete messages first (foreign key constraint)
        cursor.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
        # Then delete session
        cursor.execute('DELETE FROM chat_sessions WHERE session_id = ?', (session_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Deleted session: {session_id}")
        return {"status": "success", "message": "Session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")
    
@router.post("/feedback")
async def submit_feedback(feedback: FeedbackInput):
    """Submit feedback with proper timestamp handling"""
    try:
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        
        # Insert feedback with UTC timestamp
        current_time = datetime.now(timezone.utc).isoformat()
        cursor.execute('''
            INSERT INTO feedback (session_id, rating, comment, created_at)
            VALUES (?, ?, ?, ?)
        ''', (feedback.session_id, feedback.rating, feedback.comment, current_time))
        conn.commit()
        conn.close()
        
        # Send email notification (optional)
        send_email_notification(feedback.session_id, feedback.rating, feedback.comment)

        logger.info(f"Feedback submitted for session {feedback.session_id}")
        return {"status": "success", "message": "Feedback submitted successfully"}
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}")
    
@router.get("/feedback/view")
def get_feedback_list(rating: Optional[int] = None, date: Optional[str] = None):
    """Get feedback list with optional filters"""
    try:
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()

        query = "SELECT id, session_id, rating, comment, created_at FROM feedback WHERE 1=1"
        params = []

        if rating:
            query += " AND rating = ?"
            params.append(rating)

        if date:
            query += " AND DATE(created_at) = ?"
            params.append(date)

        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "session_id": row[1],
                "rating": row[2],
                "comment": row[3],
                "created_at": row[4],
            }
            for row in results
        ]
    except Exception as e:
        logger.error(f"Error retrieving feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve feedback")

@router.get("/feedback/export")
def export_feedback_to_csv():
    """Export feedback data to CSV file"""
    try:
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM feedback ORDER BY created_at DESC")
        rows = cursor.fetchall()

        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"feedback_export_{timestamp}.csv"
        
        # Create exports directory if it doesn't exist
        os.makedirs("./exports", exist_ok=True)
        filepath = f"./exports/{filename}"

        # Write CSV file
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Session ID', 'Rating', 'Comment', 'Created At'])
            writer.writerows(rows)

        conn.close()
        logger.info(f"Feedback exported to {filepath}")
        return {"status": "success", "file": filepath, "records": len(rows)}
        
    except Exception as e:
        logger.error(f"Error exporting feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to export feedback")
    


