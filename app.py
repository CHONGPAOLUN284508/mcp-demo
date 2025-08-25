from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/")
def health():
    return {"ok": True}


@app.post("/mcp")
async def mcp_handler(request: Request):
    body = await request.json()
    method = body.get("method")
    req_id = body.get("id")

    # ---- tiny helper for consistent replies ----
    def ok(result: dict):
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def err(code: int, message: str):
        # JSON-RPC error object
        return JSONResponse(
            content={"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}},
            status_code=200,
        )

    # --------- initialize ----------
    if method == "initialize":
        return ok({
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {"listChanged": True}},
            "resources": {}
        }) | {"serverInfo": {"name": "mcp-demo", "version": "1.0.0"}}

    # --------- tools/list ----------
    if method == "tools/list":
        return ok({
            "tools": [
                {
                    "name": "HelloWorld",
                    "description": "Returns a friendly hello message",
                    "inputSchema": {                    # camelCase
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Name to greet"}
                        },
                        "required": ["name"]
                    }
                },
                {
                    "name": "echo",
                    "description": "Repeats back the text you provide.",
                    "inputSchema": {                    # camelCase
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "The text to echo back"}
                        },
                        "required": ["text"]
                    }
                }
            ]
        })

    # --------- tools/call ----------
    if method == "tools/call":
        params = body.get("params", {}) or {}
        tool_name_raw = params.get("name") or ""
        arguments = params.get("arguments", {}) or {}

        # normalize name to be lenient
        tool_name = tool_name_raw.strip().lower()

        # HelloWorld
        if tool_name == "helloworld":
            user_name = str(arguments.get("name", "stranger"))
            return ok({"output": f"Hello, {user_name}! 👋"})

        # echo
        if tool_name == "echo":
            text = str(arguments.get("text", ""))
            return ok({"output": text})

        # known method, unknown tool
        return err(-32602, f"Unknown tool '{tool_name_raw}'. Try 'HelloWorld' or 'echo'.")

    # --------- anything else ----------
    return err(-32601, "Method not found")
