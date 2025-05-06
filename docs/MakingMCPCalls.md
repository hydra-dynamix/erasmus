## Making Manual Request
MCP servers work by sending RPCv2.0 commands to it and receiving a RPC JSON response back using the STDIO transport. You can manually make this kind of request to confirm your server is running with this command
`echo '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' | ENV=$ENV_VARIABLE" /path/to/server stdio`
### JSON Request

`'{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'` is the JSON RPC request object with the keys:
- **jsonrpc**: Always set to `"2.0"
- **method**: can be `tools/list` or `tools/call`
- **params**: a dictionary of parameters nested inside of a dictionary with the key `name`  which corresponds to the command you want to run that you would get from `tools/list`
**Example params**:
```json
{
	"name": "my_command",
	"params": {
		"param1": "some_value"
	}
}
```
- **id**: arbitrary request id number for tracking. 

#### Example
So if we have a server in `/home/bakobi/mcp/servers/my_server` with the command `do_thing` that takes the parameters `important_parameter` which is a string we would construct a request like this
```json
{
	"jsonrpc": "2.0",
	"method": "tools/call",
	"params": {
		"name": "do_thing",
		"params": {
		    "important_parameter": "some value"
		}
	},
	"id": 1
}
```