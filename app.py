import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from azure.storage.blob import BlobServiceClient

app = FastAPI()

# --- Storage client (use either connection string or SAS) ---
# Prefer using a Managed Identity in production, but this keeps it simple:
CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
if not CONN_STR:
    raise RuntimeError("Set AZURE_STORAGE_CONNECTION_STRING for the app.")

blob_service = BlobServiceClient.from_connection_string(CONN_STR)

# ---------------- MCP CONTRACT ----------------
# POST /mcp accepts JSON-RPC 2.0 messages. We present a single "AzureStorage" tool
# but ALSO expose a more AI-friendly "action" | "container" | "blob" | "content".

@app.post("/mcp")
async def mcp_handler(req: Request):
    body = await req.json()
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
                "resources": {}
            },
            "serverInfo": {"name": "azure-storage-mcp", "version": "1.0.0"}
        }

    # 2) tools/list
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "AzureStorage",
                        "description": "Create, read, update and delete blobs in Azure Storage.",
                        # IMPORTANT: use inputSchema with clear properties so Copilot can map inputs
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": ["uploadBlob", "getBlob", "deleteBlob", "updateBlob"],
                                    "description": "Which operation to perform."
                                },
                                "container": {"type": "string", "description": "Container name."},
                                "blob": {"type": "string", "description": "Blob name (path)."},
                                "content": {
                                    "type": "string",
                                    "description": "Text content for upload/update."
                                }
                            },
                            "required": ["action", "container", "blob"]
                        }
                    }
                ]
            }
        }

    # 3) tools/call
    if method == "tools/call":
        params = body.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name != "AzureStorage":
            return _rpc_error(req_id, -32601, "Unknown tool")

        action = (args.get("action") or "").lower()
        container = args.get("container")
        blob = args.get("blob")
        content = args.get("content", "")

        if not (action and container and blob):
            return _rpc_error(req_id, -32602, "Missing required fields.")

        try:
            container_client = blob_service.get_container_client(container)

            if action == "uploadBlob":
                container_client.upload_blob(name=blob, data=content.encode("utf-8"), overwrite=False)
                return _ok(req_id, {"message": f"Uploaded '{blob}' to '{container}'."})

            if action == "getBlob":
                downloader = container_client.download_blob(blob)
                text = downloader.readall().decode("utf-8")
                return _ok(req_id, {"content": text})

            if action == "deleteBlob":
                container_client.delete_blob(blob)
                return _ok(req_id, {"message": f"Deleted '{blob}'."})

            if action == "updateBlob":
                # overwrite existing
                container_client.upload_blob(name=blob, data=content.encode("utf-8"), overwrite=True)
                return _ok(req_id, {"message": f"Updated '{blob}'."})

            return _rpc_error(req_id, -32602, "Unsupported action.")

        except Exception as e:
            return _rpc_error(req_id, 500, f"Storage error: {e}")

    # Default
    return _rpc_error(req_id, -32601, "Method not found")


def _ok(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}

def _rpc_error(req_id, code, msg):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": msg}}
