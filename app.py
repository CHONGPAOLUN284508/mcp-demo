from fastapi import FastAPI

app = FastAPI()

@app.post("/mcp")
async def mcp_endpoint(request: dict):
    # handle MCP JSON-RPC requests here
    return {"jsonrpc": "2.0", "result": "ok"}
