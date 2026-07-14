from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.resource import Resource, ResourceTypeEnum


class ResourceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, resource_id: int) -> Optional[Resource]:
        return self.db.query(Resource).filter(Resource.id == resource_id).first()

    def list_all(self, only_active: bool = True, type_filter: Optional[ResourceTypeEnum] = None) -> List[Resource]:
        q = self.db.query(Resource)
        if only_active:
            q = q.filter(Resource.is_active.is_(True))
        if type_filter:
            q = q.filter(Resource.type == type_filter)
        return q.order_by(Resource.name.asc()).all()

    def create(self, resource: Resource) -> Resource:
        self.db.add(resource)
        self.db.commit()
        self.db.refresh(resource)
        return resource

    def update(self, resource: Resource) -> Resource:
        self.db.commit()
        self.db.refresh(resource)
        return resource

    def delete(self, resource: Resource) -> None:
        # Soft delete: keep historical bookings intact.
        resource.is_active = False
        self.db.commit()
