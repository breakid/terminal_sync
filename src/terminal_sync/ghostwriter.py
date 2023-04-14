# Standard Libraries
import asyncio
import logging
import os
import time
import sys
from asyncio.exceptions import TimeoutError
from collections.abc import Callable
from datetime import datetime
from importlib import metadata
from pathlib import Path
from typing import Optional

# Third-party Libraries
import aiohttp
from gql import Client, gql
from gql.client import DocumentNode
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError
from graphql.error.graphql_error import GraphQLError

# Internal Libraries
from terminal_sync.log_entry import Entry


logger = logging.getLogger("terminal_sync")

# Suppress overly verbose logging
logging.getLogger("gql.transport.aiohttp").setLevel(logging.WARNING)


class GhostWriterClient:
    # Query inserting a new log entry
    insert_query: DocumentNode = gql(
        """
        mutation InsertTerminalSyncLog (
            $oplog_id: bigint!, $start_time: timestamptz, $end_time: timestamptz, $source_host: String, $destination_host: String, $tool: String, $user_context: String, $command: String, $description: String, $output: String, $comments: String, $operator: String
        ) {
            insert_oplogEntry(objects: {
                oplog: $oplog_id,
                startDate: $start_time,
                endDate: $end_time,
                sourceIp: $source_host,
                destIp: $destination_host,
                tool: $tool,
                userContext: $user_context,
                command: $command,
                description: $description,
                output: $output,
                comments: $comments,
                operatorName: $operator,
            }) {
                returning { id }
            }
        }
        """
    )

    # Query for updating an existing log entry
    update_query: DocumentNode = gql(
        """
        mutation UpdateTerminalSyncLog (
            $gw_id: bigint!, $oplog_id: bigint!, $start_time: timestamptz, $end_time: timestamptz, $source_host: String, $destination_host: String, $tool: String, $user_context: String, $command: String, $description: String, $output: String, $comments: String, $operator: String,
        ) {
            update_oplogEntry(where: {
                id: {_eq: $gw_id}
            }, _set: {
                oplog: $oplog_id,
                startDate: $start_time,
                endDate: $end_time,
                sourceIp: $source_host,
                destIp: $destination_host,
                tool: $tool,
                userContext: $user_context,
                command: $command,
                description: $description,
                output: $output,
                comments: $comments,
                operatorName: $operator,
            }) {
                returning { id }
            }
        }
        """
    )

    def __init__(
        self, url: str, api_key: str, oplog_id: int, api_type: str = "graphql", timeout_seconds: int = 10
    ) -> None:
        self.base_url: str = url.rstrip("/")
        self.oplog_id: str = oplog_id
        api_type = api_type.lower()
        auth_header: str = f"Api-Key {api_key}" if api_type == "rest" else f"Bearer {api_key}"

        self.headers: dict[str, str] = {
            "User-Agent": f"terminal_sync/{metadata.version('terminal_sync')}",
            "Authorization": auth_header,
            "Content-Type": "application/json",
        }

        # Use REST if explicitly specified, otherwise default to GraphQL
        if api_type == "rest":
            # Important: If you leave off the trailing "/" on oplog/api/entries/ then this POST will return "200 OK"
            # without actually doing anything
            self.rest_url: str = f"{self.base_url}/oplog/api/entries/"

            # Redirect create_log() and update_log() function calls to the REST implementation
            self._create_log: Callable = self._create_entry_rest
            self._update_log: Callable = self._update_entry_rest
        else:
            url: str = f"{self.base_url}/v1/graphql"
            self.transport: AIOHTTPTransport = AIOHTTPTransport(url=url, timeout=timeout_seconds, headers=self.headers)

            # Redirect create_log() and update_log() function calls to the GraphQL implementation
            self._create_log: Callable = self._create_entry_graphql
            self._update_log: Callable = self._update_entry_graphql

    # =========================================================================
    # ******                       Helper Functions                       *****
    # =========================================================================

    async def log(self, entry: Entry) -> Entry:
        if entry.gw_id is None:
            entry.gw_id = await self._create_log(entry)
        else:
            entry.gw_id = await self._update_log(entry)

        return entry

    # =========================================================================
    # ******                        REST function                         *****
    # =========================================================================

    async def _create_entry_rest(self, entry: Entry) -> Optional[int]:
        """Create entry in Ghostwriter's Oplog (POST)"""
        try:
            logger.debug(f"[REST] Creating entry for: {entry}")

            message: dict[str, datetime | int | str] = entry.to_rest()

            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.post(self.rest_url, json=message) as resp:
                    resp: dict[str, int | Optional[str]] = await resp.json()
                    logger.debug(f"Response: {resp}")
                    logger.info(f'Logged "{entry.command}" to GhostWriter as ID: {resp.get("id")}')
                    return resp.get("id")
        except Exception as e:
            logger.exception(f"Error posting to GhostWriter ({e})")

        return None

    async def _update_entry_rest(self, entry: Entry) -> Optional[int]:
        """Create entry in Ghostwriter's Oplog (POST)"""
        try:
            logger.debug(f"[REST] Updating entry: {entry}")

            url: str = f"{self.rest_url}{entry.gw_id}/?format=json"

            message: dict[str, datetime | int | str] = entry.to_rest()

            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.put(url, json=message) as resp:
                    resp: dict[str, int | Optional[str]] = await resp.json()
                    logger.debug(f"Response: {resp}")
                    logger.info(f"Updated GhostWriter entry with ID: {entry.gw_id}")
                    return resp.get("id")
        except Exception as e:
            logger.exception(f"Error posting to GhostWriter ({e})")

        return None

    # =========================================================================
    # ******                      GraphQL functions                       *****
    # =========================================================================

    async def _execute_query(self, query: DocumentNode, values: dict) -> dict:
        """
        Execute a GraphQL query against the Ghostwriter server.

        Args:
            query (DocumentNode): The GraphQL query to execute
            values (dict): The parameters to pass to the query

        Returns:
            A dictionary with the server's response

        """
        resp: dict = {}
        # Add oplog_id to and remove uuid from values to pass to GraphQL
        values["oplog_id"] = self.oplog_id

        logger.debug(f"variable_values: {values}")

        try:
            async with Client(transport=self.transport, fetch_schema_from_transport=True) as session:
                try:
                    resp = await session.execute(query, variable_values=values)
                    # logger.debug("Successfully executed query with response: %s", resp)
                except TimeoutError:
                    logger.error("Timeout occurred while trying to connect to Ghostwriter at %s", self.base_url)
                except TransportQueryError as e:
                    logger.error("Error encountered while fetching GraphQL schema: %s", e)
                except GraphQLError as e:
                    logger.error("Error with GraphQL query: %s", e)
        except Exception:
            logger.exception("Exception occurred while trying to post the query to Ghostwriter!")

        return resp

    async def _create_entry_graphql(self, entry: Entry) -> Optional[int]:
        """
        Create an entry for the proxychains command in Ghostwriter's ``OplogEntry`` model. Uses the
        ``insert_query`` template and the operation name ``InsertTerminalSyncLog``.

        Args:
            entry (Entry): An object representing a GhostWriter log entry
        """
        try:
            logger.debug(f"[GraphQL] Creating entry for: {entry}")

            data: dict[str, str] = entry.fields()

            resp: dict = await self._execute_query(self.insert_query, data)
            logger.debug(f"Response: {resp}")
            # Example response: `{'insert_oplogEntry': {'returning': [{'id': 192}]}}`

            entry_id: int = resp.get("insert_oplogEntry", {}).get("returning", [{"id": None}])[0].get("id")

            if entry_id:
                logger.info(f"Logged to GhostWriter with ID: {entry_id}")
                return entry_id
            else:
                logger.error(f"Did not receive a response with data from Ghostwriter's GraphQL API! Response: {resp}")
        except Exception as e:
            logger.exception(
                f"Exception occurred while trying to create a new log entry! Response from Ghostwriter: {e}"
            )

        return None

    async def _update_entry_graphql(self, entry: Entry) -> dict:
        """
        Update an existing Ghostwriter ``OplogEntry`` entry for a task with more details from Mythic.
        Uses the ``update_query`` template and the operation name ``UpdateTerminalSyncLog``.

        Args:
            entry (Entry): An object representing a GhostWriter log entry
            entry_id (str): The ID of the log entry to be updated
        """
        logger.debug(f"[GraphQL] Updating log entry: {entry}")

        try:
            resp: dict = await self._execute_query(self.update_query, entry.fields())
            logger.debug(f"Response: {resp}")
            # Example response: `{'update_oplogEntry': {'returning': [{'id': 192}]}}`

            entry_id: int = resp.get("update_oplogEntry", {}).get("returning", [{"id": None}])[0].get("id")

            if entry_id:
                logger.info(f"Updated GhostWriter entry with ID: {entry_id}")
                return entry_id
            else:
                logger.error(f"Did not receive a response with data from Ghostwriter's GraphQL API! Response: {resp}")
        except Exception as e:
            logger.exception(f"Exception occurred while trying to update log entry in Ghostwriter: {e}")

        return None
