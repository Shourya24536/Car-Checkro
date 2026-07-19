import urllib.request
import subprocess
import os

url = "https://github.com/mmozeiko/build-mesa/releases/download/26.1.4/mesa-llvmpipe-x64-26.1.4.7z"
archive = "mesa-llvmpipe-x64-26.1.4.7z"

print("Downloading Mesa software OpenGL DLL (x64)...")
try:
    urllib.request.urlretrieve(url, archive)
    print("Download complete.")
except Exception as e:
    print(f"Error downloading: {e}")
    exit(1)

print("Extracting opengl32.dll...")
try:
    subprocess.run(["tar", "-xf", archive, "opengl32.dll"], check=True)
    print("Extraction complete.")
except Exception as e:
    print(f"Error extracting with tar: {e}")
    exit(1)

# Move opengl32.dll to .venv/Scripts/
project_root = os.path.dirname(os.path.abspath(__file__))
venv_scripts = os.path.join(project_root, ".venv", "Scripts")
dest = os.path.join(venv_scripts, "opengl32.dll")

if os.path.exists("opengl32.dll"):
    try:
        if os.path.exists(dest):
            os.remove(dest)
        os.rename("opengl32.dll", dest)
        print(f"[+] opengl32.dll successfully copied to {dest}")
    except Exception as e:
        print(f"Error moving opengl32.dll: {e}")
else:
    # If tar failed to find it directly, maybe it's in a subdirectory
    print("Warning: opengl32.dll not found in current directory. Scanning folder...")
    # Let's list files to see if it extracted somewhere else
    found = False
    for root, dirs, files in os.walk("."):
        if "opengl32.dll" in files:
            src_path = os.path.join(root, "opengl32.dll")
            if os.path.exists(dest):
                os.remove(dest)
            os.rename(src_path, dest)
            print(f"[+] Found and copied opengl32.dll from {src_path} to {dest}")
            found = True
            break
    if not found:
        print("Error: opengl32.dll could not be found.")

# Clean up archive
if os.path.exists(archive):
    os.remove(archive)
print("Done!")
