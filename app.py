# app.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from azure.storage.blob import BlobServiceClient
import os

app = FastAPI()


# ---------- Storage helpers ----------
def get_blob_service() -> BlobServiceClient:
    """
    Read the connection string from the environment and create a BlobServiceClient.
    Set this in Azure App Service: AZURE_STORAGE_CONNECTION_STRING
    """
    conn = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not conn:
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING not configured")
    return BlobServiceClient.from_connection_string(conn)


def get_container_name() -> str:
    """
    Default container name (override with env var AZURE_STORAGE_CONTAINER).
    """
    return os.environ.get("AZURE_STORAGE_CONTAINER", "data")


# ---------- MCP endpoint ----------
@app.post("/mcp")
async def mcp_handler(request: Request):
    body = await request.json()
    method = body.get("method")
    req_id = body.get("id")

    # 1) initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {"listChanged": True}},
                "resources": {},
            },
            "serverInfo": {"name": "mcp-demo", "version": "1.0.0"},
        }

    # 2) tools/list
if method == "tools/list":
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "tools": [
                {
                    "name": "HelloWorld",
                    "description": "Returns a friendly hello message",
                    "inputSchema": {              # <-- was input_schema
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                        "required": ["name"],
                    },
                },
                {
                    "name": "echo",
                    "description": "Repeats back the text you provide.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                },
                {
                    "name": "blobList",
                    "description": "List blobs in a container (optional prefix).",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "container": {"type": "string", "description": "Container name (default from env)."},
                            "prefix": {"type": "string", "description": "Optional name prefix filter."},
                        },
                        "required": [],
                    },
                },
                {
                    "name": "blobReadText",
                    "description": "Read a text blob from a container.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "container": {"type": "string"},
                            "blob": {"type": "string"},
                            "encoding": {"type": "string", "description": "e.g. utf-8", "default": "utf-8"},
                        },
                        "required": ["blob"],
                    },
                },
                {
                    "name": "blobWriteText",
                    "description": "Create or overwrite a text blob.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "container": {"type": "string"},
                            "blob": {"type": "string"},
                            "text": {"type": "string"},
                            "encoding": {"type": "string", "default": "utf-8"},
                        },
                        "required": ["blob", "text"],
                    },
                },
                {
                    "name": "blobDelete",
                    "description": "Delete a blob.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "container": {"type": "string"},
                            "blob": {"type": "string"},
                        },
                        "required": ["blob"],
                    },
                },
            ]
        },
    }


    # 3) tools/call
    if method == "tools/call":
        try:
            params = body.get("params", {}) or {}
            tool_name = params.get("name")
            args = params.get("arguments", {}) or {}

            # demo tools
            if tool_name == "HelloWorld":
                user_name = args.get("name", "stranger")
                return {"jsonrpc": "2.0", "id": req_id, "result": {"output": f"Hello, {user_name}! 👋"}}

            if tool_name == "echo":
                return {"jsonrpc": "2.0", "id": req_id, "result": {"output": args.get("text", "")}}

            # blob tools
            bsc = get_blob_service()
            container = args.get("container") or get_container_name()
            container_client = bsc.get_container_client(container)

            if tool_name == "blobList":
                prefix = args.get("prefix")
                names = [b.name for b in container_client.list_blobs(name_starts_with=prefix)]
                return {"jsonrpc": "2.0", "id": req_id, "result": {"blobs": names}}

            if tool_name == "blobReadText":
                blob_name = args["blob"]
                encoding = args.get("encoding", "utf-8")
                data = container_client.download_blob(blob_name).readall()
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"blob": blob_name, "text": data.decode(encoding)},
                }

            if tool_name == "blobWriteText":
                blob_name = args["blob"]
                text = args["text"]
                encoding = args.get("encoding", "utf-8")
                container_client.upload_blob(name=blob_name, data=text.encode(encoding), overwrite=True)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"ok": True, "blob": blob_name}}

            if tool_name == "blobDelete":
                blob_name = args["blob"]
                container_client.delete_blob(blob_name)
                return {"jsonrpc": "2.0", "id": req_id, "result": {"deleted": True, "blob": blob_name}}

            # unknown tool name inside tools/call
            return JSONResponse(
                status_code=200,
                content={
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                },
            )

        except Exception as e:
            # JSON-RPC application error
            return JSONResponse(
                status_code=200,
                content={"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}},
            )

    # 4) unknown method
    return JSONResponse(
        status_code=200,
        content={"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}},
    )

