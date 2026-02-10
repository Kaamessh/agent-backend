
import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add the User project root to sys.path so we can reuse User backend code
# This resolves 'backend.app...' imports found in User files
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../User")))

# Load .env from User directory
from dotenv import load_dotenv
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../User/.env"))
print(f"DEBUG: Loading .env from {env_path}")
load_dotenv(env_path)
print(f"DEBUG: DATABASE_URL in env: {os.getenv('DATABASE_URL')}")

# Now imports from 'backend' will find 'User/backend'
from backend.app.database.core import Base, engine
from backend.app.entities.conversation import Conversation
from routers.agent import router as agent_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="AI Agent Portal", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Agent Portal API!"}
