import asyncio
from datetime import UTC, datetime, timedelta

from fastapi import Request

from app.core.auth import AuthContext
from app.core.settings import Settings
from app.schemas.pull_request import WorkerPullRequestPayload
from app.services import worker as worker_service_module
from app.services.worker import WorkerService


def _build_payload() -> WorkerPullRequestPayload:
    now = datetime.now(UTC)
    return WorkerPullRequestPayload(
        repository_full_name="pronunt/pronunt-aggregator-service",
        repository_owner="pronunt",
        repository_name="pronunt-aggregator-service",
        number=7,
        title="Normalize and forward PR",
        author_username="sowrabh0-0",
        base_branch="main",
        head_branch="feat/setup-gitops-workflows",
        labels=["worker"],
        changed_files=4,
        additions=50,
        deletions=10,
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(hours=2),
    )


async def _fake_service_request(*args, **kwargs):
    class FakeResponse:
        def json(self):
            return {"id": "abc123", "pr_uid": "pronunt/pronunt-aggregator-service#7"}

    return FakeResponse()


def test_forward_pull_request_returns_forward_result() -> None:
    original_service_request = worker_service_module.service_request
    worker_service_module.service_request = _fake_service_request
    try:
        service = WorkerService(Settings(_env_file=None, allow_unsafe_dev_auth=True))
        scope = {"type": "http", "headers": [], "state": {}}
        request = Request(scope)
        request.state.request_id = "test-request-id"
        auth_context = AuthContext(subject="dev-user", username="dev-user", roles=["developer"], token="token")

        result = asyncio.run(service.forward_pull_request(_build_payload(), request, auth_context))

        assert result.status == "forwarded"
        assert result.forwarded_to == "http://pronunt-aggregator-service:8000"
        assert result.pr_uid.endswith("#7")
    finally:
        worker_service_module.service_request = original_service_request
