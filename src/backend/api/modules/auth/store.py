from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from typing import Any

import boto3
from botocore.exceptions import ClientError


class DynamoDBAuthStore:
    def __init__(
        self,
        table_name: str | None = None,
        *,
        dynamodb_resource: Any | None = None,
    ) -> None:
        self._table_name = table_name or os.environ["AUTH_TABLE_NAME"]
        dynamodb = dynamodb_resource or boto3.resource(
            "dynamodb",
            region_name=os.getenv("AWS_REGION"),
        )
        self._table = dynamodb.Table(self._table_name)

    # Static "formatting" methods that do not need instance state
    @staticmethod
    def _client_key(client_id: str) -> str:
        return f"CLIENT#{client_id}"

    @staticmethod
    def _code_key(code: str) -> str:
        return f"CODE#{code}"

    @staticmethod
    def _token_key(token: str) -> str:
        return f"TOKEN#{token}"

    async def put_client(self, client: Mapping[str, Any]) -> None:
        client_id = client["client_id"]
        item = dict(client)
        item.update(
            {
                "pk": self._client_key(client_id),
                "entity_type": "client",
            }
        )
        await asyncio.to_thread(self._table.put_item, Item=item)

    async def get_client(self, client_id) -> dict[str, Any] | None:
        return await self._get_item(self._client_key(client_id), "client")

    async def put_authorization_code(
        self,
        code: str,
        authorization_code: Mapping[str, Any],
    ) -> None:
        item = dict(authorization_code)
        item.update(
            {
                "pk": self._code_key(code),
                "entity_type": "authorization_code",
                # DynamoDB TTL requires epoch seconds as an integer
                "expires_at": int(item["expires_at"]),
            }
        )
        await asyncio.to_thread(self._table.put_item, Item=item)

    async def get_authorization_code(self, code: str) -> dict[str, Any] | None:
        return await self._get_item(self._code_key(code), "authorization_code")

    async def consume_authorization_code(self, code: str) -> bool:
        """Delete a code exactly once. False means it was already consumed"""
        try:
            await asyncio.to_thread(
                self._table.delete_item,
                Key={"pk": self._code_key(code)},
                ConditionExpression="attribute_exists(pk)",
            )
        except ClientError as error:
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

        return True

    async def put_access_token(
        self,
        token: str,
        access_token: Mapping[str, Any],
    ) -> None:
        item = dict(access_token)
        item.update(
            {
                "pk": self._token_key(token),
                "entity_type": "access_token",
                "expires_at": int(item["expires_at"]),
            }
        )
        await asyncio.to_thread(self._table.put_item, Item=item)

    async def get_access_token(self, token: str) -> dict[str, Any] | None:
        return await self._get_item(self._token_key(token), "access_token")

    async def _get_item(
        self,
        key: str,
        expected_type: str,
    ) -> dict[str, Any] | None:
        response = await asyncio.to_thread(
            self._table.get_item,
            Key={"pk": key},
            ConsistentRead=True,
        )
        item = response.get("Item")

        if item is None or item.get("entity_type") != expected_type:
            return None

        return item
