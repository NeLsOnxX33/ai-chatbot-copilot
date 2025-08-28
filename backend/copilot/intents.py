#intents.py

intents = {
    "reset_password": ["reset password", "forgot password", "change password"],
    "check_status": ["check status", "order status", "track order"],
    "contact_support": ["contact support", "talk to agent", "get help"],
}

def detect_intent(user_message: str) -> str:
    message = user_message.lower()
    for intent, keywords in intents.items():
        for word in keywords:
            if word in message:
                return intent
    return "unknown"

intents = {
    "greet" : ["hi", "hello", "hey"],
    "bye" : ["bye", "goodbye", "see you"],
    "help" : ["i need help", "can you help me", "support"]
}