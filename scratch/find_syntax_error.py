import subprocess

def check_file(filepath):
    res = subprocess.run(["node", "--check", filepath], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ SYNTAX ERROR IN {filepath}:\n{res.stderr}")
    else:
        print(f"✅ {filepath} is syntactically VALID!")

check_file("app.js")
check_file("data/embedded_data.js")
