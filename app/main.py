from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Task
from app.schemas import TaskCreate, TaskRead


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Только для первого локального прототипа.
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


app = FastAPI(title="Tasks API", lifespan=lifespan)

DbSession = Annotated[Session, Depends(get_db)]


@app.post("/tasks", response_model=TaskRead, status_code=201)
def create_task(data: TaskCreate, db: DbSession):
    task = Task(title=data.title)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get("/tasks", response_model=list[TaskRead])
def list_tasks(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    query = select(Task).order_by(Task.id).limit(limit).offset(offset)
    return db.scalars(query).all()


@app.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: DbSession):
    task = db.get(Task, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@app.get("/health/live")
def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
def readiness(db: DbSession):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from None

    return {"status": "ready"}