from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.resource import Resource, ResourceTypeEnum
from app.models.user import User
from app.repositories.resource_repo import ResourceRepository
from app.schemas.resource import ResourceCreate, ResourceUpdate
from app.services.audit_service import AuditService


class ResourceService:
    def __init__(self, db: Session):
        self.repo = ResourceRepository(db)
        self.audit = AuditService(db)

    def list_resources(self, only_active: bool = True, type_filter: Optional[ResourceTypeEnum] = None) -> List[Resource]:
        return self.repo.list_all(only_active=only_active, type_filter=type_filter)

    def get(self, resource_id: int) -> Resource:
        resource = self.repo.get_by_id(resource_id)
        if not resource:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Resource not found")
        return resource

    def create(self, data: ResourceCreate, acting_user: User) -> Resource:
        resource = Resource(**data.model_dump())
        resource = self.repo.create(resource)
        self.audit.log(acting_user.id, "resource.create", "Resource", resource.id, data.model_dump(mode="json"))
        return resource

    def update(self, resource_id: int, data: ResourceUpdate, acting_user: User) -> Resource:
        resource = self.get(resource_id)
        updates = data.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(resource, key, value)
        resource = self.repo.update(resource)
        self.audit.log(acting_user.id, "resource.update", "Resource", resource.id, updates)
        return resource

    def deactivate(self, resource_id: int, acting_user: User) -> None:
        resource = self.get(resource_id)
        self.repo.delete(resource)
        self.audit.log(acting_user.id, "resource.deactivate", "Resource", resource.id)
