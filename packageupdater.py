import subprocess
import requests
from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import json
from datetime import date

@dataclass
class PIOPackage:
    name: str
    download_urls: dict[str, str]
    package_template: str
    extra_cmds : dict[str, str]

WCHISP_PKG = PIOPackage(
    "tool-wchisp",
    {
        "windows_amd64": "https://github.com/ch32-rs/wchisp/releases/download/nightly/wchisp-win-x64.zip",
        #"windows_x86": "",
        # No Windows ARM64 or ARM32 builds.
        # Linux
        "linux_x86_64": "https://github.com/ch32-rs/wchisp/releases/download/nightly/wchisp-linux-x64.tar.gz",
        #"linux_i686": "",
        "linux_aarch64": "https://github.com/ch32-rs/wchisp/releases/download/nightly/wchisp-linux-aarch64.tar.gz",
        #"linux_armv7l": "",
        #"linux_armv6l": "",
        # Mac (Intel and ARM are separate)
        "darwin_x86_64": "https://github.com/ch32-rs/wchisp/releases/download/nightly/wchisp-macos-x64.tar.gz",
        "darwin_arm64": "https://github.com/ch32-rs/wchisp/releases/download/nightly/wchisp-macos-arm64.tar.gz"
    },
    package_template="""{
  "name": "tool-wchisp",
  "version": "0.23.230228",
  "description": "WCH ISP Tool in Rust",
  "keywords": [
    "tools",
    "uploader",
    "risc-v"
  ],
  "homepage": "https://ch32-rs.github.io/wchisp/",
  "license": " GPL-2.0-only",
  "system": [
    "windows_x86",
    "windows_amd64"
  ],
  "repository": {
    "type": "git",
    "url": "https://github.com/ch32-rs/wchisp"
  }
}""",
    extra_cmds= {
        "linux_x86_64": "chmod +x wchisp",
        "linux_aarch64": "chmod +x wchisp",
        "darwin_x86_64": "chmod +x wchisp",
        "darwin_arm64": "chmod +x wchisp && rm -rf wchisp-macos-arm64"
    }
)

THIS_DIR = Path(__file__).resolve().parent

def build_package(package: PIOPackage):
    base_dir = THIS_DIR / package.name
    print(f"Downloading {package.name} into {base_dir}")
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir()
    for systype in package.download_urls.keys():
        url = package.download_urls[systype]
        print("Key: " + systype +  " URL: " + url)
        local_filename = base_dir / os.path.split(url)[1]
        # Download
        with requests.get(url, stream=True) as r:
            with open(local_filename, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
        # Unpack
        unpacked_dir = Path(str(local_filename) + "_unpacked")
        shutil.unpack_archive(local_filename, extract_dir=unpacked_dir)
        # if the unpack directory only contains one directory, then move all of the files out there
        do_move = False
        for _, dirnames, filenames in os.walk(str(unpacked_dir)):
            #print("In " + str(unpacked_dir) + " got files and dirs")
            #print(str(dirnames))
            #print(str(filenames))
            if len(dirnames) == 1 and len(filenames) == 0:
                do_move = True
            break
        if do_move:
            source = list(unpacked_dir.glob("*"))[0]
            for filename in os.listdir(source):
                shutil.move(os.path.join(str(source), filename), os.path.join(str(unpacked_dir), filename))
            os.rmdir(source)
        # Put package.json into it
        package_json = json.loads(package.package_template)
        major, minor, patch = str(package_json["version"]).split(".")
        datecode = date.today().strftime("%y%m%d")
        package_json["version"] = f"{major}.{minor}.{datecode}"
        # only one systype currently
        package_json["system"] = [ 
            systype
        ]
        (unpacked_dir / "package.json").write_text(json.dumps(package_json, indent=2))
        # execute any extra commands
        if systype in package.extra_cmds:
            cmd = package.extra_cmds[systype]
            try:
                subprocess.check_call(cmd, shell=True, cwd=str(unpacked_dir))
            except Exception as exc:
                print("Failed to execute command: " + str(cmd))
                print(repr(exc))            
        # create PIO package from directory
        try:
            subprocess.check_call(f"pio pkg pack \"{str(unpacked_dir)}\"", shell=True)
        except Exception as exc:
            print("Failed to package pack directory " + str(unpacked_dir))
            print(repr(exc))
            continue
    print("=== Done generating packages === ")
    for genned_file in THIS_DIR.glob(f"{package.name}-*.tar.gz"):
        print("pio pkg publish --type tool --owner \"community-ch32v\" --notify \"" + str(genned_file) + "\"")
def main():
    build_package(WCHISP_PKG)

if __name__ == '__main__':
    main()
