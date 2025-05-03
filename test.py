import json
from pathlib import Path

path = Path("/mnt/c/Users/richa/.kenv/db/conversations.json")

print(path.exists())

def get_data():
    data = path.read_text().replace("\\\", "\\")
    return json.loads(data)

if __name__ == "__main__":
    data = get_data()
    print(json.dumps(data, indent=4))