"""
Base CRUD operations with SQLAlchemy 2.x patterns.
Contract: Use only 2.x syntax - select(), insert(), update(), delete()
"""
from sqlalchemy import select, insert, update, delete
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError
from sqlalchemy.orm import Session
import logging
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from app.database import Base

logger = logging.getLogger(__name__)
ModelType = TypeVar("ModelType", bound=Base)

class CRUDBase(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """Get record by ID using SQLAlchemy 2.x select()"""
        try:
            stmt = select(self.model).where(self.model.id == id)
            result = db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model.__name__} {id}: {e}")
            return None
    
    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get multiple records using SQLAlchemy 2.x select()"""
        try:
            stmt = select(self.model).offset(skip).limit(limit)
            result = db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting multiple {self.model.__name__}: {e}")
            return []
    
    def create(self, db: Session, *, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        """Create record using SQLAlchemy 2.x insert()"""
        try:
            stmt = insert(self.model).values(**obj_in).returning(self.model)
            result = db.execute(stmt)
            db.commit()
            return result.scalar_one()
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error creating {self.model.__name__}: {e}")
            # Contract: IntegrityError audit-logged
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            return None
    
    def update(self, db: Session, *, id: int, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        """Update record using SQLAlchemy 2.x update()"""
        try:
            stmt = (
                update(self.model)
                .where(self.model.id == id)
                .values(**obj_in)
                .returning(self.model)
            )
            result = db.execute(stmt)
            db.commit()
            return result.scalar_one()
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error updating {self.model.__name__} {id}: {e}")
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error updating {self.model.__name__} {id}: {e}")
            return None
    
    def remove(self, db: Session, *, id: int) -> Optional[ModelType]:
        """Delete record using SQLAlchemy 2.x delete()"""
        try:
            # Contract: No silent deletes - get first for audit
            stmt_select = select(self.model).where(self.model.id == id)
            result_select = db.execute(stmt_select)
            obj = result_select.scalar_one_or_none()
            
            if not obj:
                return None
            
            stmt_delete = delete(self.model).where(self.model.id == id)
            db.execute(stmt_delete)
            db.commit()
            return obj
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error deleting {self.model.__name__} {id}: {e}")
            return None
    
    def retry_on_operational_error(self, db: Session, operation, max_retries: int = 2):
        """
        Retry decorator for OperationalError.
        Contract: Retry max 2 times on OperationalError.
        """
        for attempt in range(max_retries + 1):
            try:
                return operation()
            except OperationalError as e:
                if attempt == max_retries:
                    logger.error(f"Operation failed after {max_retries + 1} attempts: {e}")
                    raise
                logger.warning(f"OperationalError on attempt {attempt + 1}, retrying...")
                db.rollback()
