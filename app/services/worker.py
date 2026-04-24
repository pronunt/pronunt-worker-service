from fastapi import Request

from app.core.auth import AuthContext
from app.core.http import service_request
from app.core.settings import Settings
from app.schemas.pull_request import WorkerForwardResult, WorkerPullRequestPayload


class WorkerService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def forward_pull_request(
        self,
        payload: WorkerPullRequestPayload,
        request: Request,
        auth_context: AuthContext,
    ) -> WorkerForwardResult:
        response = await service_request(
            "POST",
            f"{self.settings.aggregator_service_url}/api/v1/aggregator/prs",
            request=request,
            auth_context=auth_context,
            json=payload.model_dump(mode="json"),
        )
        body = response.json()
        return WorkerForwardResult(
            status="forwarded",
            forwarded_to=self.settings.aggregator_service_url,
            pr_uid=body["pr_uid"],
            aggregator_id=body["id"],
        )
