import sys
import os
import subprocess

if __name__ == "__main__":
    vision_script = os.path.join(os.path.dirname(__file__), "fetch_and_calc_vision.py")
    res = subprocess.run([sys.executable, vision_script] + sys.argv[1:])
    sys.exit(res.returncode)
