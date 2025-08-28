from fastapi import APIRouter, Form, Request, Response, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import hashlib
import secrets

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Enhanced admin users with hashed passwords (in production, use proper password hashing)
ADMIN_USERS = {
    "nelson": {
        "password": "sirnelson",  
        "role": "super_admin",
        "name": "Nelson",
        "permissions": ["read", "write", "delete", "manage_users"]
    },
    "vani": {
        "password": "vani@123", 
        "role": "admin",
        "name": "Vani Ma'am",
        "permissions": ["read", "write"]
    },
    "imran": {
        "password": "imran@123",
        "role": "manager", 
        "name": "Imran",
        "permissions": ["read", "write"]
    }
}

def hash_password(password: str) -> str:
    """Hash password using SHA-256 (use bcrypt in production)"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return hash_password(plain_password) == hashed_password

@router.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display admin login page"""
    error = request.query_params.get("error")
    success = request.query_params.get("success")
    
    error_message = None
    success_message = None
    
    if error == "invalid":
        error_message = "Invalid username or password. Please try again."
    elif error == "session":
        error_message = "Your session has expired. Please log in again."
    
    if success == "logout":
        success_message = "You have been successfully logged out."
    
    return templates.TemplateResponse(
        "admin_login.html", 
        {
            "request": request, 
            "error": error_message,
            "success": success_message
        }
    )

@router.post("/admin/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """Process admin login"""
    try:
        # Convert to lowercase for case-insensitive login
        username = username.lower().strip()
        
        # Validate credentials
        if username in ADMIN_USERS and ADMIN_USERS[username]["password"] == password:
            # Create secure session
            session_token = secrets.token_urlsafe(32)
            
            response = RedirectResponse(url="/feedback/admin", status_code=302)
            
            # Set secure cookies
            response.set_cookie(
                key="admin_auth", 
                value="true", 
                httponly=True,
                secure=False,  # Set to True in production with HTTPS
                samesite="lax",
                max_age=3600  # 1 hour session
            )
            response.set_cookie(
                key="admin_user", 
                value=username, 
                httponly=True,
                secure=False,
                samesite="lax",
                max_age=3600
            )
            response.set_cookie(
                key="admin_role", 
                value=ADMIN_USERS[username]["role"], 
                httponly=True,
                secure=False,
                samesite="lax",
                max_age=3600
            )
            response.set_cookie(
                key="session_token", 
                value=session_token, 
                httponly=True,
                secure=False,
                samesite="lax",
                max_age=3600
            )
            
            return response
        else:
            # Invalid credentials
            return RedirectResponse(url="/admin/login?error=invalid", status_code=302)
            
    except Exception as e:
        print(f"Login error: {e}")
        return RedirectResponse(url="/admin/login?error=invalid", status_code=302)

@router.get("/admin/logout")
async def logout():
    """Logout endpoint to clear admin session"""
    response = RedirectResponse(url="/admin/login?success=logout", status_code=302)
    
    # Clear all session cookies
    response.delete_cookie(key="admin_auth")
    response.delete_cookie(key="admin_user")
    response.delete_cookie(key="admin_role")
    response.delete_cookie(key="session_token")
    
    return response

def admin_required(request: Request):
    """Dependency to check admin authentication"""
    if request.cookies.get("admin_auth") != "true":
        raise HTTPException(
            status_code=401, 
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Additional session validation
    username = request.cookies.get("admin_user")
    if not username or username not in ADMIN_USERS:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    return True

def get_current_admin(request: Request):
    """Get current admin user info"""
    if request.cookies.get("admin_auth") != "true":
        raise HTTPException(status_code=401, detail="Authentication required")

    username = request.cookies.get("admin_user")
    if not username or username not in ADMIN_USERS:
        raise HTTPException(status_code=401, detail="Invalid session")

    user_data = ADMIN_USERS[username].copy()
    user_data["username"] = username
    return user_data

def super_admin_required(request: Request):
    """Dependency for super admin only access"""
    if request.cookies.get("admin_auth") != "true":
        raise HTTPException(status_code=401, detail="Authentication required")

    role = request.cookies.get("admin_role")
    if role != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    return True

def has_permission(request: Request, required_permission: str):
    """Check if current admin has specific permission"""
    admin = get_current_admin(request)
    return required_permission in admin.get("permissions", [])