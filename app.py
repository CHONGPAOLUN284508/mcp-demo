from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post("/mcp")
async def mcp_handler(request: Request):
    body = await request.json()
    method = body.get("method")
    req_id = body.get("id")

    # Handle initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {
                    "tools": {"listChanged": True},
                },
                "resources": {}
            },
            "serverInfo": {
                "name": "mcp-demo",
                "version": "1.0.0"
            }
        }

    # Handle tools/list
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "HelloWorld",
                        "description": "Returns a friendly hello message",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"}
                            },
                            "required": ["name"]
                        }
                    }
                ]
            }
        }

    # Handle tools/call (when Copilot tries to use HelloWorld)
    if method == "tools/call":
        params = body.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "HelloWorld":
            user_name = arguments.get("name", "stranger")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "output": f"Hello, {user_name}! 👋"
                }
            }

    # Default if method not recognized
    return JSONResponse(
        content={
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": "Method not found"}
        },
        status_code=200
    )
