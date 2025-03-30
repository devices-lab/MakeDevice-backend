"""
This test script takes all the json files in ./test_data
and spawns a new python process one at a time for each one, 
running `python3 run.py <file_name>` and printing the lines
from its output that contains "PASS:" or "FAIL:".
"""

import os
import subprocess
import sys

def test():
    print("🟢 = OK")
    print("🟡 = WARNING")
    print("🔴 = ERROR")
    print("⚪️ = DEBUG")
    print("🔵 = INFO\n")
    
    # Get all the json files in ./test_data
    test_files = [f for f in os.listdir("./test_data") if f.endswith(".json")]
    passes = 0
    fails = 0

    for file in test_files:
        print(f"🔵 Testing {file}")
        # Remove "data_" and ".json" from the file name
        file = file[5:-5]
        # If there's an error, hide the traceback
        process = subprocess.Popen(["python3", "run.py", file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result_found = False

        # Wait for the process to finish
        while True:
            output = process.stdout.readline()
            if output == b'' and process.poll() is not None:
                if (not result_found):
                    print("🟡\tNo result")
                break
            if output:
                # Print only the line that contains "RESULT:"
                for line in output.decode("utf-8").split("\n"):
                    if "PASS:" in line or "FAIL:" in line:
                        line = line[:1] + "\t" + line[2:]
                        print(line)
                        result_found = True
                        if "PASS:" in line:
                            passes += 1
                        if "FAIL:" in line:
                            fails += 1
                            
    print(f"\n🔵 {len(test_files)} tests run")
    if (passes > 0):
        print(f"🟢\t{passes} tests passed")
    if (fails > 0):
        print(f"🔴\t{fails} tests failed")
    if (passes + fails < len(test_files)):
        print(f"🟡\t{len(test_files) - passes - fails} tests without result")

if __name__ == "__main__":
    test()
