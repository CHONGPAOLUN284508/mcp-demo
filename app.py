from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()


def ok(id_, result):
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def err(id_, code=-32601, message="Method not found"):
    # -32601 is the JSON-RPC "Method not found" error
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


@app.get("/")
async def health():
    return {"status": "ok"}


@app.post("/mcp")
async def mcp_handler(request: Request):
    body = await request.json()
    method = body.get("method")
    req_id = body.get("id")

    # 1) Handshake / capability negotiation
    if method == "initialize":
        return ok(req_id, {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                # tells the client you can list tools dynamically
                "tools": {"listChanged": True},
            },
            "resources": {}
        })

    # 2) List the tools you support
    if method == "tools/list":
        return ok(req_id, {
            "tools": [
                {
                    "name": "echo",
                    "title": "Echo Tool",
                    "description": "Repeats back the text you provide.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The text to echo back"
                            }
                        },
                        "required": ["text"]
                    }
                },
                {
                    "name": "helloWorld",  # NOTE: exact case; must match in tools/call
                    "title": "Hello World Tool",
                    "description": "Greets the user by name.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Name of the person to greet"
                            }
                        },
                        "required": ["name"]
                    }
                }
            ]
        })

    # 3) Execute a specific tool
    if method == "tools/call":
        params = body.get("params", {}) or {}
        tool_name = params.get("name")
        args = params.get("arguments", {}) or {}

        if tool_name == "echo":
            text = args.get("text", "")
            return ok(req_id, f"You said: {text}")

        if tool_name == "helloWorld":
            name = args.get("name", "stranger")
            return ok(req_id, f"Hello, {name}! 👋 Welcome to MCP on Azure 🚀")

        # Unknown tool
        return err(req_id)

    # 4) Fallback for any other/unknown JSON-RPC methods
    return JSONResponse(content=err(req_id), status_code=200)
