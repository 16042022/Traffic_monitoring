# models/repositories/base_repository.py
from typing import TypeVar, Generic, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from dal.database import Base, db_manager

T = TypeVar('T', bound=Base)


class BaseRepository(Generic[T]):
    """
    Generic base repository providing CRUD operations
    """
    
    def __init__(self, model_class: type[T]):
        self.model_class = model_class
        self.logger = logging.getLogger(f"{__name__}.{model_class.__name__}")
    
    @property
    def session(self) -> Session:
        """Get current session"""
        return db_manager.session
    
    def create(self, **kwargs) -> T:
        """
        Create new entity
        
        Args:
            **kwargs: Model attributes
            
        Returns:
            Created entity
        """
        try:
            entity = self.model_class(**kwargs)
            self.session.add(entity)
            self.session.commit()
            self.session.refresh(entity)
            self.logger.info(f"Created {self.model_class.__name__} with id {entity.id}")
            return entity
        except SQLAlchemyError as e:
            self.session.rollback()
            self.logger.error(f"Error creating {self.model_class.__name__}: {e}")
            raise
    
    def get_by_id(self, id: int) -> Optional[T]:
        """
        Get entity by ID
        
        Args:
            id: Entity ID
            
        Returns:
            Entity or None
        """
        try:
            return self.session.query(self.model_class).filter_by(id=id).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Error getting {self.model_class.__name__} by id {id}: {e}")
            raise
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """
        Get all entities
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of entities
        """
        try:
            query = self.session.query(self.model_class)
            if limit:
                query = query.limit(limit).offset(offset)
            return query.all()
        except SQLAlchemyError as e:
            self.logger.error(f"Error getting all {self.model_class.__name__}: {e}")
            raise
    
    def update(self, id: int, **kwargs) -> Optional[T]:
        """
        Update entity
        
        Args:
            id: Entity ID
            **kwargs: Attributes to update
            
        Returns:
            Updated entity or None
        """
        try:
            entity = self.get_by_id(id)
            if entity:
                for key, value in kwargs.items():
                    if hasattr(entity, key):
                        setattr(entity, key, value)
                self.session.commit()
                self.session.refresh(entity)
                self.logger.info(f"Updated {self.model_class.__name__} with id {id}")
            return entity
        except SQLAlchemyError as e:
            self.session.rollback()
            self.logger.error(f"Error updating {self.model_class.__name__} with id {id}: {e}")
            raise
    
    def delete(self, id: int) -> bool:
        """
        Delete entity
        
        Args:
            id: Entity ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            entity = self.get_by_id(id)
            if entity:
                self.session.delete(entity)
                self.session.commit()
                self.logger.info(f"Deleted {self.model_class.__name__} with id {id}")
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            self.logger.error(f"Error deleting {self.model_class.__name__} with id {id}: {e}")
            raise
    
    def filter_by(self, **kwargs) -> List[T]:
        """
        Filter entities by attributes
        
        Args:
            **kwargs: Filter conditions
            
        Returns:
            List of matching entities
        """
        try:
            return self.session.query(self.model_class).filter_by(**kwargs).all()
        except SQLAlchemyError as e:
            self.logger.error(f"Error filtering {self.model_class.__name__}: {e}")
            raise
    
    def count(self, **kwargs) -> int:
        """
        Count entities
        
        Args:
            **kwargs: Filter conditions
            
        Returns:
            Number of matching entities
        """
        try:
            query = self.session.query(self.model_class)
            if kwargs:
                query = query.filter_by(**kwargs)
            return query.count()
        except SQLAlchemyError as e:
            self.logger.error(f"Error counting {self.model_class.__name__}: {e}")
            raise
    
    def exists(self, **kwargs) -> bool:
        """
        Check if entity exists
        
        Args:
            **kwargs: Filter conditions
            
        Returns:
            True if exists
        """
        return self.count(**kwargs) > 0
    
    def bulk_create(self, entities: List[Dict[str, Any]]) -> List[T]:
        """
        Bulk create entities
        
        Args:
            entities: List of entity data dictionaries
            
        Returns:
            List of created entities
        """
        try:
            objects = [self.model_class(**data) for data in entities]
            self.session.bulk_save_objects(objects, return_defaults=True)
            self.session.commit()
            self.logger.info(f"Bulk created {len(objects)} {self.model_class.__name__} entities")
            return objects
        except SQLAlchemyError as e:
            self.session.rollback()
            self.logger.error(f"Error bulk creating {self.model_class.__name__}: {e}")
            raise