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
                },
                {
                    "name": "echo",
                    "description": "Repeats back the text you provide.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"}
                        },
                        "required": ["text"]
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

    if tool_name == "HelloWorld":
        user_name = arguments.get("name", "stranger")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"output": f"Hello, {user_name}! 👋"}
        }

    if tool_name == "echo":
        text = arguments.get("text", "")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"output": text}
        }
