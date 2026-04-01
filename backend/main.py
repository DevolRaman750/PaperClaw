from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Database Setup (Connecting to Docker Postgres)
DATABASE_URL = "postgresql://admin:password123@127.0.0.1:5433/builder_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define a simple table for our Milestone
class DummyTable(Base):
    __tablename__ = "dummy_data"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, index=True)

# Create the table in the database
Base.metadata.create_all(bind=engine)

# 2. FastAPI App Setup
app = FastAPI()

# 3. STRICT CORS POLICY (Crucial for Agent Architecture)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Explicitly allow Next.js
    allow_credentials=True,
    allow_methods=["*"], # Allow POST, GET, OPTIONS, etc.
    allow_headers=["*"],
)

# 4. Pydantic Model for incoming data
class DummyInput(BaseModel):
    text: str

# 5. The API Endpoint
@app.post("/api/save-dummy")
def save_dummy_string(data: DummyInput):
    db = SessionLocal()
    try:
        new_entry = DummyTable(content=data.text)
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        return {"status": "success", "saved_id": new_entry.id, "content": new_entry.content}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()