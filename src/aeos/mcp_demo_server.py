"""A tiny MCP server for demos and tests — run as a module:
`python -m aeos.mcp_demo_server`. Newline-delimited JSON-RPC 2.0."""
import json
import sys

TOOLS = [{"name": "echo", "description": "echo the text back",
          "inputSchema": {"type": "object",
                          "properties": {"text": {"type": "string"}}}}]


def handle(msg: dict) -> dict | None:
    if "id" not in msg:
        return None                       # notification — no response
    method, mid = msg.get("method"), msg["id"]
    if method == "initialize":
        result = {"protocolVersion": "2025-06-18",
                  "capabilities": {"tools": {}},
                  "serverInfo": {"name": "aeos-demo-server", "version": "1.0"}}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        args = (msg.get("params") or {}).get("arguments") or {}
        result = {"content": [{"type": "text",
                               "text": f"echo: {args.get('text', '')}"}],
                  "isError": False}
    else:
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": f"no such method: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
