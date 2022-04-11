#!/usr/bin/env python3

import os.path

import argparse
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("folder_path")
parser.add_argument("--ignore-unnotarized", action='store_true', default=False)
args = parser.parse_args()


if args.ignore_unnotarized is False:
    check_notarization_output = subprocess.run(['spctl', '-a', '-vvv', f'{args.folder_path}/CloudCompare.app'], capture_output=True, ).stderr.decode()
    print(check_notarization_output)
    assert 'accepted' in check_notarization_output, 'App is not notarized by our god Apple'
    dmg_name = ""
else:
    dmg_name = "unotarized-"

version_string = input("Version string: ")

file_output = subprocess.run(['file', f'{args.folder_path}/CloudCompare.app/Contents/MacOs/CloudCompare'], capture_output=True).stdout.decode()

if 'x86_64' in file_output:
    arch = 'x86_64'
elif 'arm64' in file_output:
    arch = 'arm64'
else:
    raise SystemExit(f"Could not determine arch from {file_output}")


dmg_name += f"CloudCompare-{version_string}-{arch}.dmg"

if os.path.exists(dmg_name):
    os.remove(dmg_name)

create_cmd = [
  "create-dmg",
  "--volname", f"CloudCompare {version_string} {arch}",
  '--background', 'cc_background.png',
  '--window-pos','200', '120' ,
  '--window-size', '800', '400' ,
  '--icon-size', '100' ,
  '--icon', "CloudCompare.app", '200', '100' ,
  '--icon', "CHANGELOG.md", '350', '100' ,
  '--icon', "global_shift_list_template.txt" ,'200' ,'260' ,
  '--icon', "license.txt", '350', '260' ,
  '--eula', './GPLv3.txt' ,
  '--app-drop-link', '600' ,'185' ,
  f"{dmg_name}",
  f"{args.folder_path}"
]


subprocess.run(create_cmd)
