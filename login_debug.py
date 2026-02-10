
import sys
import os
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm

# Add the User project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../User")))

from dotenv import load_dotenv
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../User/.env"))
load_dotenv(env_path)

from backend.app.database.core import SessionLocal
from backend.app.user.service import authenticate_user
# Ensure Conversation is loaded for User relationship
from backend.app.entities.conversation import Conversation

async def debug_login():
    print("Attempting to debug login...")
    async with SessionLocal() as db:
        class MockForm:
            def __init__(self, username, password):
                self.username = username
                self.password = password
        
        # We know ad@gmail.com exists with password 123456 from check_user.py
        form_data = MockForm(username="ad@gmail.com", password="123456")
        
        try:
            user = await authenticate_user(db, form_data)
            print(f"Login successful for {user.email}")
            
            from backend.app.user.service import create_access_token
            token = await create_access_token(user.id, user.email)
            print(f"Token generation successful: {token[:20]}...")
        except Exception as e:
            print(f"Login failed: {e}")
            import traceback
            traceback.print_exc()

async def debug_registration():
    print("\nAttempting to debug registration...")
    async with SessionLocal() as db:
        from backend.app.user.models import UserCreate
        from backend.app.user.service import create_user
        import random
        import string
        
        rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        email = f"debug_agent_{rand_str}@example.com"
        
        user_in = UserCreate(
            name="Debug Agent",
            email=email,
            password="password123",
            phone="1234567890"
        )
        
        try:
            print(f"Creating user {email}...")
            user = await create_user(db, user_in)
            print(f"User created: {user.id}")
            
            # Force role update
            from backend.app.entities.user import UserRole
            user.role = UserRole.AGENT
            await db.commit()
            print("Role updated to AGENT")
            
        except Exception as e:
            msg = f"Registration failed: {e}"
            print(msg)
            import traceback
            with open("debug_error.log", "w") as f:
                f.write(msg + "\n")
                traceback.print_exc(file=f)

async def debug_list_tickets():
    print("\nAttempting to list tickets...")
    async with SessionLocal() as db:
        from sqlalchemy import select
        from backend.app.entities.tickets import Ticket
        result = await db.execute(select(Ticket))
        tickets = result.scalars().all()
        print(f"Found {len(tickets)} tickets.")
        for t in tickets:
            print(f" - {t.title} ({t.status}) [UserID: {t.user_id}]")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # asyncio.run(debug_login())
    # asyncio.run(debug_registration())
    asyncio.run(debug_list_tickets())
