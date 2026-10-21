"""所有 ORM 模型的基类。

SQLAlchemy 2.0 风格：继承 DeclarativeBase 类，而不是旧的 declarative_base() 函数。
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """模型基类。M1-2 的知识条目模型会继承它。"""