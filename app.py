from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from azure.storage.blob import BlobServiceClient
import os

app = FastAPI()

# Connect to Azure Storage
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

@app.post("/mcp")
async def mcp_handler(request: Request):
    body = await request.json()
    method = body.get("method")
    req_id = body.get("id")

    # Initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {"listChanged": True}},
                "resources": {}
            },
            "serverInfo": {"name": "mcp-demo", "version": "1.0.0"}
        }

    # List tools
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "uploadFile",
                        "description": "Upload a file to Azure Blob Storage",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "container": {"type": "string"},
                                "blob_name": {"type": "string"},
                                "content": {"type": "string"}
                            },
                            "required": ["container", "blob_name", "content"]
                        }
                    },
                    {
                        "name": "getFile",
                        "description": "Retrieve a file from Azure Blob Storage",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "container": {"type": "string"},
                                "blob_name": {"type": "string"}
                            },
                            "required": ["container", "blob_name"]
                        }
                    }
                ]
            }
        }

    # Handle tools/call
    if method == "tools/call":
        params = body.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "uploadFile":
            container = arguments["container"]
            blob_name = arguments["blob_name"]
            content = arguments["content"]

            blob_client = blob_service_client.get_blob_client(container, blob_name)
            blob_client.upload_blob(content, overwrite=True)

            return {"jsonrpc": "2.0", "id": req_id, "result": {"output": f"File {blob_name} uploaded to {container}"}}

        if tool_name == "getFile":
            container = arguments["container"]
            blob_name = arguments["blob_name"]

            blob_client = blob_service_client.get_blob_client(container, blob_name)
            content = blob_client.download_blob().readall().decode("utf-8")

            return {"jsonrpc": "2.0", "id": req_id, "result": {"output": content}}

    return JSONResponse(content={"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}, status_code=200)
