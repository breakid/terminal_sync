"""Defines a GhostWriter client class"""

# Standard Libraries
import logging
from collections.abc import Callable

# Third-party Libraries
import aiohttp
from gql import Client
from gql import gql
from gql.client import DocumentNode
from gql.transport.aiohttp import AIOHTTPTransport

# Internal Libraries
from terminal_sync import __version__ as termsync_version
from terminal_sync.log_entry import Entry

logger = logging.getLogger("terminal_sync")

# Suppress overly verbose logging
logging.getLogger("gql.transport.aiohttp").setLevel(logging.WARNING)


class GhostWriterClient:
    """Defines a GhostWriter client

    Attributes:
        base_url (str): The base URL where GhostWriter is hosted (e.g., "https://ghostwriter.example.com")
        oplog_id (int): The ID of the GhostWriter Oplog where entries will be written
        headers (dict[str, str]): A dictionary of HTTP headers used to communicate with GhostWriter
        rest_url (str): The base URL for REST API communications
    """

    # Query inserting a new log entry
    _insert_query: DocumentNode = gql(
        """
        mutation InsertTerminalSyncLog (
            $oplog_id: bigint!, $start_date: timestamptz, $end_date: timestamptz, $source_ip: String,
            $dest_ip: String, $tool: String, $user_context: String, $command: String, $description: String,
            $output: String, $comments: String, $operator_name: String
        ) {
            insert_oplogEntry(objects: {
                oplog: $oplog_id,
                startDate: $start_date,
                endDate: $end_date,
                sourceIp: $source_ip,
                destIp: $dest_ip,
                tool: $tool,
                userContext: $user_context,
                command: $command,
                description: $description,
                output: $output,
                comments: $comments,
                operatorName: $operator_name,
            }) {
                returning { id }
            }
        }
        """
    )

    # Query for updating an existing log entry
    _update_query: DocumentNode = gql(
        """
        mutation UpdateTerminalSyncLog (
            $id: bigint!, $oplog_id: bigint!, $start_date: timestamptz, $end_date: timestamptz, $source_ip: String,
            $dest_ip: String, $tool: String, $user_context: String, $command: String, $description: String,
            $output: String, $comments: String, $operator_name: String
        ) {
            update_oplogEntry(where: {
                id: {_eq: $id}
            }, _set: {
                oplog: $oplog_id,
                startDate: $start_date,
                endDate: $end_date,
                sourceIp: $source_ip,
                destIp: $dest_ip,
                tool: $tool,
                userContext: $user_context,
                command: $command,
                description: $description,
                output: $output,
                comments: $comments,
                operatorName: $operator_name,
            }) {
                returning { id }
            }
        }
        """
    )

    def __init__(self, url: str, graphql_api_key: str = "", rest_api_key: str = "", timeout_seconds: int = 10) -> None:
        """Initializes a GhostWriter client

        Args:
            url (str): The base URL where GhostWriter is hosted (e.g., "https://ghostwriter.example.com")
            graphql_api_key (str, optional): A GhostWriter GraphQL API key. Defaults to "".
            rest_api_key (str, optional): A GhostWriter REST API key. Defaults to "".
            timeout_seconds (int, optional): Seconds the client will wait for a response. Defaults to 10.

        Raises:
            ValueError: If an invald neither API key was specified
        """
        # Validate arguments
        if not url.startswith("http"):
            raise ValueError("Invalid GhostWriter URL")

        if not graphql_api_key and not rest_api_key:
            raise ValueError("No GhostWriter API key specified")

        self.base_url: str = url.rstrip("/")

        self.headers: dict[str, str] = {
            "User-Agent": f"terminal_sync/{termsync_version}",
            "Authorization": f"Bearer {graphql_api_key}" if graphql_api_key else f"Api-Key {rest_api_key}",
            "Content-Type": "application/json",
        }

        # Set create_log() and update_log() functions to call the GraphQL implementation
        self.create_log: Callable = self._create_entry_graphql
        self.update_log: Callable = self._update_entry_graphql

        if graphql_api_key:
            logger.info("Using the GraphQL API")
            url = f"{self.base_url}/v1/graphql"
            # WORKAROUND: When running Docker on a Windows host, the application will always hang waiting for the SSL
            # connection to terminate. The ssl_close_timeout is therefore set to 0 to avoid a negative user experience
            self._transport: AIOHTTPTransport = AIOHTTPTransport(
                url=url, headers=self.headers, ssl_close_timeout=0, timeout=timeout_seconds
            )
        else:
            logger.info("Using the REST API")
            # Important: If you leave off the trailing "/" on oplog/api/entries/ then this POST will return "200 OK"
            # without actually doing anything
            self.rest_url: str = f"{self.base_url}/oplog/api/entries/"

            # Redirect create_log() and update_log() function calls to the REST implementation
            self.create_log = self._create_entry_rest
            self.update_log = self._update_entry_rest

    # =========================================================================
    # ******                       Helper Functions                       *****
    # =========================================================================

    async def log(self, entry: Entry) -> int | None:
        """Convenience function that calls either create or update depending on whether entry.gw_id is populated

        Args:
            entry (Entry): The entry object to be recorded

        Returns:
            int | None: The ID of the GhostWriter entry if successful, otherwise None
        """
        if entry.gw_id is None:
            return await self._create_log(entry)

        return await self._update_log(entry)

    # =========================================================================
    # ******                        REST function                         *****
    # =========================================================================

    async def _create_entry_rest(self, entry: Entry) -> int | None:
        """Create an entry in Ghostwriter's Oplog (POST) using the REST API

        Args:
            entry (Entry): The entry object to be recorded

        Returns:
            int | None: The ID of the GhostWriter log entry

        Raises:
            Exception: If an error occurred while communicating with GhostWriter
        """
        logger.debug(f"[REST] Creating entry for: {entry}")

        data: dict[str, int | str] = entry.gw_fields()

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.post(self.rest_url, json=data) as resp:
                resp = await resp.json()
                logger.debug(f"Response: {resp}")

                if resp.get("detail"):
                    raise Exception(resp.get("detail"))

                logger.info(f'Logged "{entry.command}" to GhostWriter as ID: {resp.get("id")}')
                return resp.get("id")

    async def _update_entry_rest(self, entry: Entry) -> int | None:
        """Update an entry in Ghostwriter's Oplog (PUT) using the REST API

        Args:
            entry (Entry): The entry object to be recorded

        Returns:
            int | None: The ID of the GhostWriter log entry

        Raises:
            Exception: If an error occurred while communicating with GhostWriter
        """
        logger.debug(f"[REST] Updating entry: {entry}")

        url: str = f"{self.rest_url}{entry.gw_id}/?format=json"

        data: dict[str, int | str] = entry.gw_fields()

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.put(url, json=data) as resp:
                resp = await resp.json()
                logger.debug(f"Response: {resp}")

                if resp.get("detail"):
                    raise Exception(resp.get("detail"))

                logger.info(f"Updated GhostWriter entry with ID: {entry.gw_id}")
                return resp.get("id")

    # =========================================================================
    # ******                      GraphQL functions                       *****
    # =========================================================================

    async def _execute_query(self, query: DocumentNode, values: dict) -> dict:
        """Execute a GraphQL query against the Ghostwriter server

        Args:
            query (DocumentNode): The GraphQL query to execute
            values (dict): The parameters to pass to the query

        Returns:
            A dictionary containing the server's response

        Raises:
            Exception: If an error occurred while communicating with GhostWriter
        """
        logger.debug(f"variable_values: {values}")

        async with Client(transport=self._transport, fetch_schema_from_transport=True) as session:
            return await session.execute(query, variable_values=values)

    async def _create_entry_graphql(self, entry: Entry) -> int | None:
        """Create an entry in Ghostwriter's Oplog using the GraphQL API

        Args:
            entry (Entry): The entry object to be recorded

        Returns:
            int | None: The ID of the GhostWriter log entry

        Raises:
            Exception: If an error occurred while communicating with GhostWriter
        """
        logger.debug(f"[GraphQL] Creating entry for: {entry}")

        resp: dict = await self._execute_query(self._insert_query, entry.gw_fields())
        logger.debug(f"Response: {resp}")
        # Example response: `{'insert_oplogEntry': {'returning': [{'id': 192}]}}`

        entry_id: int = resp.get("insert_oplogEntry", {}).get("returning", [{"id": None}])[0].get("id")

        if entry_id:
            logger.info(f"Logged to GhostWriter with ID: {entry_id}")
            return entry_id
        else:
            logger.error(f"Did not receive a response with data from Ghostwriter's GraphQL API! Response: {resp}")

        return None

    async def _update_entry_graphql(self, entry: Entry) -> int | None:
        """Update an entry in Ghostwriter's Oplog using the GraphQL API

        Args:
            entry (Entry): The entry object to be recorded

        Returns:
            int | None: The ID of the GhostWriter log entry

        Raises:
            Exception: If an error occurred while communicating with GhostWriter
        """
        logger.debug(f"[GraphQL] Updating log entry: {entry}")

        resp: dict = await self._execute_query(self._update_query, {"id": entry.gw_id, **entry.gw_fields()})
        logger.debug(f"Response: {resp}")
        # Example response: `{'update_oplogEntry': {'returning': [{'id': 192}]}}`

        entry_id: int = resp.get("update_oplogEntry", {}).get("returning", [{"id": None}])[0].get("id")

        if entry_id:
            logger.info(f"Updated GhostWriter entry with ID: {entry_id}")
            return entry_id
        else:
            logger.error(f"Did not receive a response with data from Ghostwriter's GraphQL API! Response: {resp}")

        return None
