from sqlalchemy import Column, Enum, MetaData
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from ...core.clients.exceptions import UserNotBindError
from ...resources import data_dir
from ..clients.lxns.models.oauth import OAuth2Token
from ..merge.models import ServiceName, Theme

db = data_dir / "user.db"

metadata_user = MetaData()


class UserBase(SQLModel):
    __abstract__ = True
    metadata = metadata_user


class User(UserBase, table=True):
    ID: int = Field(default=None, primary_key=True, index=True, exclude=True)
    qqid: int
    friend_code: int | None = Field(default=None)
    access_token: str | None = Field(default=None)
    refresh_token: str | None = Field(default=None)
    service: ServiceName = Field(
        default=ServiceName.DIVINGFISH, sa_column=Column(Enum(ServiceName))
    )
    theme: Theme = Field(default=Theme.PRISM_PLUS, sa_column=Column(Enum(Theme)))


engine = create_async_engine(f"sqlite+aiosqlite:///{str(db)}", echo=False)


async def create_database():
    async with engine.begin() as connect:
        await connect.run_sync(metadata_user.create_all)


async def get_user(qqid: int) -> User:
    async with AsyncSession(engine) as session:
        statement = select(User).where(User.qqid == qqid)
        result = await session.exec(statement)
        user = result.first()
        if user is None:
            raise UserNotBindError
        return user


async def update_user(
    qqid: int,
    *,
    friend_code: int | None = None,
    service: ServiceName | None = None,
    token: OAuth2Token | None = None,
    theme: Theme | None = None,
) -> User:
    update_data = {
        "friend_code": friend_code,
        "service": service,
        "access_token": token.access_token if token else None,
        "refresh_token": token.refresh_token if token else None,
        "theme": theme,
    }
    update_data = {k: v for k, v in update_data.items() if v is not None}

    async with AsyncSession(engine) as session:
        statement = select(User).where(User.qqid == qqid)
        result = await session.exec(statement)
        if user := result.first():
            user.sqlmodel_update(update_data)
        else:
            user = User(qqid=qqid)
            session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def delete_user(qqid: int) -> bool:
    async with AsyncSession(engine) as session:
        statement = select(User).where(User.qqid == qqid)
        result = await session.exec(statement)
        if user := result.first():
            await session.delete(user)
            await session.commit()
            return True
        return False
