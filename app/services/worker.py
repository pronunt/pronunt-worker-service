import json
from uuid import uuid4

import aio_pika
from fastapi import Request
from aio_pika.abc import AbstractIncomingMessage

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

    async def forward_pull_request_from_queue(
        self,
        payload: WorkerPullRequestPayload,
        request_id: str | None = None,
        authorization: str | None = None,
    ) -> WorkerForwardResult:
        headers = {}
        if request_id:
            headers[self.settings.request_id_header] = request_id
        if authorization:
            headers["Authorization"] = authorization

        response = await service_request(
            "POST",
            f"{self.settings.aggregator_service_url}/api/v1/aggregator/prs",
            headers=headers,
            json=payload.model_dump(mode="json"),
        )
        body = response.json()
        return WorkerForwardResult(
            status="forwarded",
            forwarded_to=self.settings.aggregator_service_url,
            pr_uid=body["pr_uid"],
            aggregator_id=body["id"],
        )


class WorkerConsumer:
    def __init__(self, settings: Settings, worker_service: WorkerService) -> None:
        self.settings = settings
        self.worker_service = worker_service
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: aio_pika.RobustChannel | None = None
        self.queue: aio_pika.RobustQueue | None = None
        self.consume_tag: str | None = None

    async def start(self) -> None:
        self.connection = await aio_pika.connect_robust(self.settings.rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)
        exchange = await self.channel.declare_exchange(
            self.settings.rabbitmq_exchange,
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )
        self.queue = await self.channel.declare_queue(self.settings.rabbitmq_pr_queue, durable=True)
        await self.queue.bind(exchange, routing_key=self.settings.rabbitmq_pr_routing_key)
        self.consume_tag = await self.queue.consume(self.handle_message)

    async def stop(self) -> None:
        if self.queue is not None and self.consume_tag is not None:
            await self.queue.cancel(self.consume_tag)
            self.consume_tag = None
        if self.channel is not None:
            await self.channel.close()
            self.channel = None
        if self.connection is not None:
            await self.connection.close()
            self.connection = None

    async def handle_message(self, message: AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            payload = WorkerPullRequestPayload.model_validate(json.loads(message.body.decode("utf-8")))
            request_id = message.headers.get(self.settings.request_id_header) if message.headers else None
            authorization = message.headers.get("Authorization") if message.headers else None
            if isinstance(request_id, bytes):
                request_id = request_id.decode("utf-8")
            if isinstance(authorization, bytes):
                authorization = authorization.decode("utf-8")
            await self.worker_service.forward_pull_request_from_queue(
                payload,
                request_id=request_id or str(uuid4()),
                authorization=authorization,
            )
