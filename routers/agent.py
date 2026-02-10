
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Annotated
import uuid
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm

# Imports from User module (will be resolved via sys.path in main.py)
from backend.app.database.core import get_db
from backend.app.entities.tickets import Ticket
from backend.app.entities.user import User, UserRole
from backend.app.user.service import authenticate_user, create_access_token, verify_token, get_user_by_email
from backend.app.security import oauth2_scheme

router = APIRouter(prefix="/agent", tags=["agent"])

class Token(BaseModel):
    access_token: str
    token_type: str

class TicketUpdate(BaseModel):
    status: str

class AgentReply(BaseModel):
    message: str

# Dependency to check if user is agent
async def get_current_agent(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    try:
        email = await verify_token(token)
    except Exception:
         raise HTTPException(status_code=401, detail="Could not validate credentials")
         
    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Check Role
    if user.role != UserRole.AGENT:
         raise HTTPException(status_code=403, detail="Access forbidden: Agents only")
    
    return user

@router.get("/me")
async def get_me(current_agent: User = Depends(get_current_agent)):
    return {
        "id": current_agent.id,
        "name": current_agent.name,
        "email": current_agent.email,
        "role": current_agent.role
    }


class AgentRegister(BaseModel):
    name: str
    email: str
    password: str
    phone: str

@router.post("/register", response_model=Token)
async def register_agent(user: AgentRegister, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    existing = await get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Importing UserCreate from User module
    from backend.app.user.models import UserCreate
    
    # Map input to UserCreate
    user_create = UserCreate(
        name=user.name,
        email=user.email,
        password=user.password,
        phone=user.phone
    )
    
    from backend.app.user.service import create_user as service_create_user
    new_user = await service_create_user(db, user_create)
    
    # Force update role to AGENT
    new_user.role = UserRole.AGENT
    await db.commit()
    await db.refresh(new_user)
    
    # Generate token
    token = await create_access_token(new_user.id, new_user.email)
    return Token(access_token=token, token_type="bearer") 


@router.post("/login", response_model=Token)
async def login_agent(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: AsyncSession = Depends(get_db)):
    # Authenticate user (checks password)
    print(f"DEBUG: Login attempt for: {form_data.username}")
    try:
        user = await authenticate_user(db, form_data)
        print(f"DEBUG: User authenticated: {user.email if user else 'None'}")
    except HTTPException as e:
        print(f"DEBUG: Login error for {form_data.username}: {e.detail}")
        raise e
    except Exception as e:
        print(f"DEBUG: Unexpected error in authenticate_user: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
        
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # Check Role
    print(f"DEBUG: Checking role for {user.email}: {user.role}")
    if user.role != UserRole.AGENT:
         print(f"DEBUG: User {user.email} is NOT an agent")
         raise HTTPException(status_code=403, detail="User is not an agent")

    # Reuse User token creation
    try:
        token = await create_access_token(user.id, user.email)
        print(f"DEBUG: Token generated successfully for {user.email}")
        return Token(access_token=token, token_type="bearer")
    except Exception as e:
        print(f"DEBUG: Error creating token: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Token generation failed")

@router.get("/tickets")
async def get_all_tickets(current_agent: User = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket).order_by(Ticket.created_at.desc()))
    return result.scalars().all()

@router.get("/ticket/{ticket_id}")
async def get_ticket(ticket_id: uuid.UUID, current_agent: User = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    # Eager load user to display user info
    result = await db.execute(select(Ticket).options(selectinload(Ticket.user)).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.put("/ticket/{ticket_id}/status")
async def update_status(ticket_id: uuid.UUID, update: TicketUpdate, current_agent: User = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    ticket.status = update.status
    await db.commit()
    await db.refresh(ticket)
    return ticket

@router.post("/ticket/{ticket_id}/reply")
async def reply_ticket(ticket_id: uuid.UUID, reply: AgentReply, current_agent: User = Depends(get_current_agent), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Appending to description as a simple log
    new_content = f"\n\n[AGENT {current_agent.name}]: {reply.message}"
    ticket.description = (ticket.description or "") + new_content
    
    await db.commit()
    await db.refresh(ticket)
    return {"message": "Reply added", "ticket": ticket}
