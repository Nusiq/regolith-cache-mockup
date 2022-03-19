'''
This filter simulates the behavior of Regolith. It copies files to cache, the
names of the copied files are based on SHA of their content. It uses
`data/.cache` as cache directory but Regolith would store the files in
actual cache directory.
'''
# Timing the execution of the script
from time import perf_counter
TIME_START = perf_counter()

# The actual script
from pathlib import Path
import shutil
import hashlib
import json
import re

# 'postprocessing' is a file with a list of postprocessing actions from the
# filter
POSTPROCESSING_PATH = Path("data/.cache/postprocessing")

# 'actions_log.json' is a file with a list of actions performed by the filter
# it has two properties:
# - 'deletions' - the list of deleted files
# - 'transformations' - a dictionary with pairs of
#   (source file path -> list of destination file paths). Note that the source
#   file path refers to a file before running the filter and the destination
#   file paths are the files after running the filter.
ACTIONS_LOG_PATH = Path("data/.cache/actions_log.json")

# 'previous_actions.json" is an output file of this script. It's very similar
# to "actions_log.json" but it contains additional information about the
# SHA. It has the same structure but all of the paths are replaced with strings
# created with pattern: <file path>:<SHA>.
PREVIOUS_ACTIONS_PATH = Path("data/.cache/previous_actions.json")

# This file is created before running the filter. It contains a dictionary with
# pairs of (file path -> SHA) loaded from RP and BP folders.
FILE_STATS_PATH = Path("data/.cache/file_stats.json")

CACHE_PATH = Path("data/.cache/files")
DELETE_POSTPROCESSING_COMMAND = re.compile("delete (.+)")
LOAD_POSTPROCESSING_COMMAND =  re.compile("load (.+) (.+)")

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
    print(f"Filter postprocessing: This action would be performed by Regolith.")
    # 1. Perform the actions from the "postprocessing" file
    CACHE_PATH.mkdir(parents=True, exist_ok=True)
    with POSTPROCESSING_PATH.open("r") as f:
        postprocessing_commands = f.readlines()
    for cmd in postprocessing_commands:
        if match := DELETE_POSTPROCESSING_COMMAND.match(cmd):
            p = Path(match.group(1))
            if p.exists():
                p.unlink()
        elif match := LOAD_POSTPROCESSING_COMMAND.match(cmd):
            target = Path(match.group(1))
            source = CACHE_PATH / match.group(2)
            if not source.exists():
                raise ValueError(f"Unable to load file {source}")
            if target.exists():
                target.unlink()
            shutil.copy(source, target)
        else:
            raise ValueError(f"Unknown command: {cmd}")
    try:
        with FILE_STATS_PATH.open("r") as f:
            file_stats = json.load(f)
    except:
        file_stats = {}

    # 2. Create "previous_actions.json" file based on the "actions_log.json"
    previous_actions = {
        # List of <file path>:<SHA>
        "deletions": [],
        # Dictionary (<file path>:<SHA> -> List[<file path>:<SHA>])
        "transformations": {}
    }
    def actions_log_to_previous_action_path(path: str):
        '''
        Transforms the path from "actions_log.json" file to a format used in
        the "previous_actions.json file (<file path> ==> <file path>:<sha>)
        '''
        # This could be lazily evalueted for better performance but it's just
        # an example and it would be executed by Regolith anyway.
        path: Path = Path(path)
        if not path.exists():
            raise ValueError(f"File {path} doesn't exist")
        if not path.is_file():
            raise ValueError(f"File {path} is not a file")
        path_sha = file_sha(path)
        return f"{path.as_posix()}:{path_sha}"

    try:
        with ACTIONS_LOG_PATH.open("r") as f:
            actions_log = json.load(f)
    except:
        actions_log = {
            "deletions": [],       # List of file paths
            "transformations": {}  # Dictionary (file path -> List[file path])
        }
    for d in actions_log["deletions"]:
        previous_actions["deletions"].append(f"{d}:{file_stats[d]}")
    for k, v_list in actions_log["transformations"].items():
        new_k = f'{k}:{file_stats[k]}'
        new_v_list = []
        previous_actions["transformations"][new_k] = new_v_list
        for v in v_list:
            v_sha = actions_log_to_previous_action_path(v)
            new_v_list.append(v_sha)
            # Copy the file to the cache
            shutil.copy(v , CACHE_PATH / v_sha.split(":")[1])
    with open(PREVIOUS_ACTIONS_PATH, "w") as f:
        json.dump(previous_actions, f, indent='\t')
    print(f"Filter postprocessing: Finished in {(perf_counter() - TIME_START)*100:.4f} ms")