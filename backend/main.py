from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from copilot.router import handle_user_message

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AI Copilot backend is running."}

@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    user_message = body.get("message", "")
    response = handle_user_message(user_message)
    return {"response": response}
