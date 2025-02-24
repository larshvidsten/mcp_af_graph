from typing import Any, Optional
from mcp.server.fastmcp import FastMCP
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError

# Initialize FastMCP server
mcp = FastMCP("graphql-explorer")

class GraphQLClient:
    def __init__(self, endpoint_url: str, headers: Optional[dict] = None):
        self.endpoint_url = endpoint_url
        self.headers = headers
        self.transport = None
        self.client = None
        
    async def initialize(self):
        """Initialize the async client."""
        if not self.client:
            self.transport = AIOHTTPTransport(
                url=self.endpoint_url,
                headers=self.headers
            )
            self.client = Client(
                transport=self.transport,
                fetch_schema_from_transport=True
            )
            # Fetch schema to validate connection
            async with self.client as session:
                await session.fetch_schema()

    async def execute_query(self, query: str, variables: Optional[dict] = None) -> dict:
        """Execute a GraphQL query and return the results."""
        if not self.client:
            await self.initialize()
            
        try:
            parsed_query = gql(query)
            async with self.client as session:
                result = await session.execute(parsed_query, variable_values=variables)
                return result
        except TransportQueryError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    async def get_schema(self) -> str:
        """Get the GraphQL schema as a string."""
        if not self.client:
            await self.initialize()
        return str(self.client.schema)

# Initialize GraphQL client (will be set in setup)
graphql_client = None

@mcp.tool()
async def setup_connection(endpoint_url: str, auth_token: Optional[str] = None) -> str:
    """Set up the GraphQL client connection.
    
    Args:
        endpoint_url: The GraphQL endpoint URL
        auth_token: Optional authentication token
    """
    global graphql_client
    
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else None
    try:
        graphql_client = GraphQLClient(endpoint_url, headers)
        await graphql_client.initialize()
        return "Successfully connected to GraphQL endpoint"
    except Exception as e:
        return f"Failed to connect: {str(e)}"

@mcp.tool()
async def execute_query(query: str, variables: Optional[dict] = None) -> str:
    """Execute a GraphQL query.
    
    Args:
        query: The GraphQL query string
        variables: Optional variables for the query
    """
    if not graphql_client:
        return "Error: Please set up connection first using setup_connection"
    
    # Check for mutations
    if "mutation" in query.lower():
        return "Error: Mutations are not allowed"
    
    result = await graphql_client.execute_query(query, variables)
    return str(result)

@mcp.resource("schema://graphql")
async def get_schema() -> str:
    """Get the GraphQL schema as a resource."""
    if not graphql_client:
        return "Error: Please set up connection first using setup_connection"
    
    return await graphql_client.get_schema()

@mcp.tool()
async def get_type_info(type_name: str) -> str:
    """Get detailed information about a specific GraphQL type.
    
    Args:
        type_name: Name of the GraphQL type
    """
    if not graphql_client:
        return "Error: Please set up connection first using setup_connection"
    
    await graphql_client.initialize()  # Ensure we have schema
    schema = graphql_client.client.schema
    type_def = schema.get_type(type_name)
    
    if not type_def:
        return f"Type '{type_name}' not found in schema"
    
    return str(type_def)

@mcp.tool()
async def list_types() -> str:
    """List all available types in the GraphQL schema."""
    if not graphql_client:
        return "Error: Please set up connection first using setup_connection"
    
    await graphql_client.initialize()  # Ensure we have schema
    schema = graphql_client.client.schema
    types = schema.type_map.keys()
    return "\n".join(sorted(types))

if __name__ == "__main__":
    mcp.run()