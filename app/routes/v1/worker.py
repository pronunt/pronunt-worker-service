from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.core.auth import AuthContext, require_roles
from app.core.settings import Settings, get_settings
from app.schemas.pull_request import WorkerForwardResult, WorkerHealthDependencyResponse, WorkerPullRequestPayload
from app.services.worker import WorkerService

router = APIRouter(tags=["worker"])
WorkerAccessDependency = Annotated[
    AuthContext,
    Depends(require_roles("developer", "reviewer", "release")),
]


def get_worker_service(settings: Annotated[Settings, Depends(get_settings)]) -> WorkerService:
    return WorkerService(settings)


WorkerServiceDependency = Annotated[WorkerService, Depends(get_worker_service)]


@router.post("/prs/forward", status_code=status.HTTP_202_ACCEPTED)
async def forward_pull_request(
    payload: WorkerPullRequestPayload,
    request: Request,
    auth_context: WorkerAccessDependency,
    service: WorkerServiceDependency,
) -> WorkerForwardResult:
    return await service.forward_pull_request(payload, request, auth_context)


@router.get("/dependencies/aggregator")
def aggregator_dependency(
    settings: Annotated[Settings, Depends(get_settings)],
    _: WorkerAccessDependency,
) -> WorkerHealthDependencyResponse:
    return WorkerHealthDependencyResponse(
        status="configured",
        aggregator_url=settings.aggregator_service_url,
    )
