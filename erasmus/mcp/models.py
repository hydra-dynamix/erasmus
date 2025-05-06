from pydantic import BaseModel, Field, ConfigDict
from io import TextIOWrapper
from typing import Any
import subprocess

class RPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: dict[str, Any]
    id: int

class RPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Any
    id: int


class McpServer(BaseModel):
    name: str
    command: str
    args: list[str]
    env: dict[str, str]

class ServerTransport(BaseModel):
    name: str
    process: subprocess.Popen
    connected: bool
    stdin: TextIOWrapper = Field(..., default_factory=TextIOWrapper)
    stdout: TextIOWrapper = Field(..., default_factory=TextIOWrapper)
    stderr: TextIOWrapper = Field(..., default_factory=TextIOWrapper)
    model_config = ConfigDict(arbitrary_types_allowed=True)
    __pydantic_fields_set__ = True

class RegistryTool(BaseModel):
    name: str
    description: str
    tool_model: type[BaseModel]
    model_config = ConfigDict(arbitrary_types_allowed=True)
    __pydantic_fields_set__ = True

if __name__ == "__main__":
    print(RPCRequest(
        method="",
        params={},
        id=1
    ).model_dump_json())