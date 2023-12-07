"""Test the GhostwriterClient class"""

# Standard Libraries
import json
from os import environ
from os import getenv
from pathlib import Path
from typing import Any
from typing import Generator

# Third-party Libraries
import pytest
import pytest_asyncio
from gql.transport.aiohttp import AIOHTTPTransport
from pytest import fixture
from pytest import raises
from pytest_httpx import HTTPXMock

# Internal Libraries
from terminal_sync.ghostwriter import GhostwriterClient


# Constants
GW_API_KEY_GRAPHQL: str = getenv("GW_API_KEY_GRAPHQL")
GW_API_KEY_REST: str = getenv("GW_API_KEY_REST")
GW_URL: str = getenv("GW_URL")
BASE_URL: str = GW_URL.rstrip("/")

EXPECTED_RESPONSE_REST: dict[int | str | None] = {
  "id": 42,
  "start_date": "2023-10-15T01:59:45Z",
  "end_date": "2023-10-15T01:59:45Z",
  "source_ip": "Normandy (192.168.1.100)",
  "dest_ip": "",
  "tool": "smbclient",
  "user_context": None,
  "command": "proxychains4 -q smbclient -U username",
  "description": "Connect to SMB share over SOCKS proxy",
  "output": "Success",
  "comments": "Test comment",
  "operator_name": "dbreakiron",
  "oplog_id": 1
}


@fixture
def ghostwriter_rest_client() -> GhostwriterClient:
    return GhostwriterClient(url=GW_URL, rest_api_key=GW_API_KEY_REST)


@fixture
def ghostwriter_graphql_client() -> GhostwriterClient:
    return GhostwriterClient(url=GW_URL, graphql_api_key=GW_API_KEY_GRAPHQL, rest_api_key=GW_API_KEY_REST)


def test_client_init_graphql(ghostwriter_graphql_client):
    user_agent: str = "Ghostwriter Python Client"

    client: GhostwriterClient = GhostwriterClient(
        url=GW_URL, graphql_api_key=GW_API_KEY_GRAPHQL, rest_api_key=GW_API_KEY_REST
    )

    assert client.base_url == BASE_URL, f"Expected base_url to be '{BASE_URL}' but was '{client.base_url}'"

    assert isinstance(client.headers, dict), f"Expected headers to be 'dict' but was: '{type(client.headers)}'"
    assert len(client.headers) == 3, f"Expected 'headers' to have 3 entries but has: {len(client.headers)}"

    assert (
        client.headers.get("User-Agent") == user_agent
    ), f"Expected 'User-Agent' header to be '{user_agent}' but was '{client.headers.get('User-Agent')}'"
    assert (
        client.headers.get("Authorization") == f"Bearer {GW_API_KEY_GRAPHQL}"
    ), f"Expected 'Authorization' header to be 'Bearer {GW_API_KEY_GRAPHQL}' but was '{client.headers.get('Authorization')}'"
    assert (
        client.headers.get("Content-Type") == "application/json"
    ), f"Expected 'Content-Type' header to be 'application/json' but was '{client.headers.get('Content-Type')}'"

    assert (
        hasattr(client, "_transport") is True
    ), "Client should have a '_transport' attribute because the GraphQL key is specified and takes precedence over REST"
    assert isinstance(
        client._transport, AIOHTTPTransport
    ), f"Expected 'client._transport' to be '{type(AIOHTTPTransport)}' but was '{type(client._transport)}'"

    assert (
        hasattr(client, "rest_url") is False
    ), "Client should NOT have a 'rest_url' attribute because the GraphQL key is specified and takes precedence over REST"


def test_client_init_rest(ghostwriter_rest_client):
    client: GhostwriterClient = ghostwriter_rest_client

    assert isinstance(client.headers, dict), f"Expected headers to be 'dict' but was: '{type(client.headers)}'"
    assert len(client.headers) == 3, f"Expected 'headers' to have 3 entries but has: {len(client.headers)}"

    assert (
        client.headers.get("Authorization") == f"Api-Key {GW_API_KEY_REST}"
    ), f"Expected 'Authorization' header to be 'Api-Key {GW_API_KEY_REST}' but was '{client.headers.get('Authorization')}'"

    assert (
        hasattr(client, "_transport") is False
    ), "Client should NOT have a '_transport' attribute because the GraphQL key was not specified"

    assert (
        client.rest_url == f"{GW_URL}/oplog/api/entries/"
    ), "Client should have a 'rest_url' attribute because the GraphQL key was not specified, and it should fallback to REST"


def test_client_log():
    # TODO: Figure out how to mock REST and GraphQL requests
    pass


@pytest.mark.asyncio
async def test_graphql_create_rest(httpx_mock: HTTPXMock, basic_entry):
    expected_log_id: int = 123

    httpx_mock.add_response(json={"id": expected_log_id})

    client: GhostwriterClient = GhostwriterClient(url=GW_URL, rest_api_key=GW_API_KEY_REST)

    gw_log_id = await client.log(basic_entry)

    assert (
        gw_log_id == expected_log_id
    ), f"Expected client.log() to return '{expected_log_id}' but returned '{gw_log_id}' instead"
