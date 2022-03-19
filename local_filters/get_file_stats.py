'''
This filter simulates the behavior of Regolith. It creates a JSON file with
the information of the files available in the cache and the files in RP and BP
folders with their SHA.
'''
# Timing the execution of the script
from time import perf_counter
TIME_START = perf_counter()

# The actual script
from pathlib import Path
import hashlib
import json
BP_PATH = Path("BP")
RP_PATH = Path("RP")
CACHE_PATH = Path("data/.cache/files")

# Every filter should have its own "previous_actions.json" file but this is just
# an example.
PREVIOUS_ACTIONS_PATH = Path("data/.cache/previous_actions.json")
FILE_STATS_PATH = Path("data/.cache/file_stats.json")

BUF_SIZE = 65536

def file_sha(path: Path):
    sha1 = hashlib.sha1()
    with path.open('rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()

if __name__ == "__main__":
    print(f"Get file stats: This action would be performed by Regolith.")
    # Dictionary (file path -> SHA) of the files in RP and BP
    project = {}
    # Populate the "project" dictionary
    for root in [BP_PATH, RP_PATH]:
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            sha = file_sha(p)
            project[p.as_posix()] = sha
    # The actions of the filter from previous run
    previous_actions = {}
    if PREVIOUS_ACTIONS_PATH.exists():
        with PREVIOUS_ACTIONS_PATH.open() as f:
            previous_actions = json.load(f)
    FILE_STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FILE_STATS_PATH.open('w') as f:
        json.dump(project, f, indent=4)
    print(f"Get file stats: Finished in {(perf_counter() - TIME_START)*100:.4f} ms")