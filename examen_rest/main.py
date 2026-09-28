from collections.abc import Generator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine
from models import Laptop


class LaptopCreate(BaseModel):
    marca: str
    modelo: str
    ram_gb: int


class LaptopResponse(LaptopCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    disponible: bool


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as database:
        if database.scalar(select(Laptop.id).limit(1)) is not None:
            return
        database.add_all(
            [
                Laptop(id=1, marca="Dell", modelo="Latitude 5440", ram_gb=16),
                Laptop(
                    id=2,
                    marca="Lenovo",
                    modelo="ThinkPad E14",
                    ram_gb=8,
                    disponible=False,
                ),
                Laptop(id=3, marca="HP", modelo="ProBook 450", ram_gb=16),
            ]
        )
        database.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(lifespan=lifespan)


def get_database() -> Generator[Session, None, None]:
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()


@app.get("/")
def root() -> dict[str, str]:
    return {"mensaje": "API del laboratorio de cómputo"}


@app.get("/laptops", response_model=list[LaptopResponse])
def list_laptops(database: Session = Depends(get_database)) -> list[Laptop]:
    return list(database.scalars(select(Laptop).order_by(Laptop.id)))


@app.get("/laptops/disponibles", response_model=list[LaptopResponse])
def list_available_laptops(database: Session = Depends(get_database)) -> list[Laptop]:
    query = select(Laptop).where(Laptop.disponible.is_(True)).order_by(Laptop.id)
    return list(database.scalars(query))


@app.get("/laptops/{laptop_id}", response_model=LaptopResponse)
def get_laptop(laptop_id: int, database: Session = Depends(get_database)) -> Laptop:
    laptop = database.get(Laptop, laptop_id)
    if laptop is None:
        raise HTTPException(status_code=404, detail="Laptop no encontrada")
    return laptop


@app.post(
    "/laptops",
    response_model=LaptopResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_laptop(data: LaptopCreate, database: Session = Depends(get_database)) -> Laptop:
    laptop = Laptop(**data.model_dump(), disponible=True)
    database.add(laptop)
    database.commit()
    database.refresh(laptop)
    return laptop
