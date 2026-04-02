import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from openai import OpenAI

def load_local_env() -> None:
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        existing = (os.getenv(key) or "").strip()
        if not existing:
            os.environ[key] = value


def get_groq_api_key() -> str:
    api_key = (os.getenv("GROQ_API_KEY") or "").strip().strip('"').strip("'")
    if api_key.lower().startswith("bearer "):
        api_key = api_key[7:].strip()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is not set. Add it to backend/.env or export it in your backend terminal.",
        )
    if not api_key.startswith("gsk_"):
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY format looks invalid. It should start with 'gsk_'.",
        )
    return api_key


load_local_env()

# We tell the OpenAI client to send requests to Groq's servers instead
client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=get_groq_api_key())

# --- 1. DATABASE SETUP ---
DATABASE_URL = "postgresql://admin:password123@localhost:5433/builder_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Layer 1: The Versioned Schema Registry Table
class SkillTable(Base):
    __tablename__ = "agent_skills"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    system_prompt = Column(Text)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. PYDANTIC MODELS ---
class ChatRequest(BaseModel):
    skill_name: str
    user_prompt: str

# --- 3. THE "QUEEN" ADAPTER LOGIC ---
def compile_prompt(system_rules: str, user_text: str) -> list:
    return [
        {"role": "system", "content": system_rules},
        {"role": "user", "content": user_text}
    ]

# --- 4. API ENDPOINTS ---

@app.post("/api/seed-skill")
def seed_test_skill(db: Session = Depends(get_db)):
    existing = db.query(SkillTable).filter(SkillTable.name == "sarcastic-reviewer").first()
    if not existing:
        new_skill = SkillTable(
            name="sarcastic-reviewer",
            system_prompt="You are a senior developer reviewing code. You are extremely sarcastic and slightly condescending, but your technical advice is flawless."
        )
        db.add(new_skill)
        db.commit()
        return {"status": "Skill seeded!"}
    return {"status": "Skill already exists."}

@app.post("/api/chat")
def execute_agent(req: ChatRequest, db: Session = Depends(get_db)):
    # 1. Fetch Skill from DB
    skill = db.query(SkillTable).filter(SkillTable.name == req.skill_name).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found in Registry.")
    
    # 2. Queen Adapter Formatting
    compiled_messages = compile_prompt(skill.system_prompt, req.user_prompt)
    
    # 3. Synchronous LLM Call (Routed to Groq via OpenAI client)
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b", # Your target model
            messages=compiled_messages,
            temperature=0.7
        )
        final_answer = response.choices[0].message.content
        return {"status": "success", "agent_response": final_answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))