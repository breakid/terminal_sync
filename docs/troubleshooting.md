# Troubleshooting

The following is a list of potential errors identified during testing and recommended methods for resolving them.

---

## Test Environments

Development and testing were performed using the configurations listed below. If you encounter any problems attributable to a different environment, please [submit a GitHub issue](https://github.com/breakid/terminal_sync/issues); be sure to include a detailed description of the problem and relevant information about your environment. We can't fix what we can't replicate.

- Windows 11 (terminal_sync server and PowerShell hooks)
      - Docker 20.10.24, build 297e128
      - Docker Compose v2.17.2
      - PowerShell 5.1.22621.963
      - Python 3.11
- Debian 11 (terminal_sync server and Bash hooks)
      - Docker version 23.0.4, build f480fb1
      - Docker Compose version v2.17.2
      - Python 3.11.3
- Debian 11 (Bash hooks)
      - Python 3.9.2
- GhostWriter running over HTTPS

---

## Server Problems

### No GhostWriter API key specified

**Problem**: Neither a GraphQL nor a REST API key were provided

**Solution**: Make sure to enter a valid API key for at least one of these settings in the `config.yaml` file or set the `GW_API_KEY_GRAPHQL` or `GW_API_KEY_REST` environment variables.

### A `config.yaml` or `terminal_sync.log` directory gets created

**Problem**: You didn't create the necessary file(s) before running the server with Docker Compose

**Solution**:

1. Stop the server (`docker-compose down`)
2. Delete the `config.yaml` and/or `terminal_sync.log` directory
3. Initalize the `config.yaml` and/or `terminal_sync.log` files (see [Setup: Configure the Server](setup.md#2-configure-the-server))
4. Restart the server (`docker-compose up -d`)

---

## Client Problems

### Cannot connect to host <GHOSTWRITER_SERVER> ssl:False [getaddrinfo failed]

**Problem**: terminal_sync is unable to resolve the hostname of your GhostWriter server

**Solution**:

1. Verify the `gw_url` setting contains the correct hostname
2. Verify connectivity to your GhostWriter server (e.g., check any VPNs, SSH tunnels, etc.)
3. Check your DNS settings

---

### Cannot connect to host <GHOSTWRITER_SERVER> ssl:False [The remote computer refused the network connection]

**Problem**: terminal_sync can reach the GhostWriter server, but the port is blocked

**Solution**:

1. Verify the `gw_url` setting contains any applicable port numbers
2. Check the firewall settings on your GhostWriter server

---

### Authentication hook unauthorized this request

**Problem**: Your GraphQL token is invalid

**Solution**:

1. Verify your token hasn't expired
2. Verify the token you specified is correct and complete
3. Generate a new GraphQL token key

---

### check constraint of an insert/update permission has failed

**Problem**: You're using the GraphQL API, and either the Oplog ID you're trying to write to doesn't exist, or you don't have permission to write to it

**Solution**:

1. Verify an Oplog with the specified ID exists
2. Verify your user account is assigned to the project to which the specified Oplog belongs

---

### Authentication credentials were not provided

**Problem**: You're using the REST API and provided an API key, but your `gw_url` is using `http://` rather than `https://`

**Solution**: Modify your `gw_url` to use `https://`

---

### 404, message='Not Found', url=URL('https://<GHOSTWRITER_SERVER>/v1/graphql')

**Problem**: While there are likely many causes for this generic issue, this was observed when using the GraphQL API and a `gw_url` containing `http://` rather than `https://`

**Solution**: Modify your `gw_url` to use `https://`
