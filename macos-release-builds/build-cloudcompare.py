#!/usr/bin/env python3

import argparse
import multiprocessing
from pathlib import Path
from typing import Dict
import subprocess
import os


CMAKE = "cmake"

SCRIPT_DIR = Path(__file__).parent.absolute()

INSTALL_ROOT_FOR_ARCH: Dict[str, Path] = {
    "arm64": SCRIPT_DIR / "arm64-dependencies" / "install",
}


def run_build(args):
    dependencies_dir = INSTALL_ROOT_FOR_ARCH[args.arch]
    source_sir = SCRIPT_DIR.parent
    build_dir = SCRIPT_DIR / f"{args.arch}-build"
    install_dir = SCRIPT_DIR / f"{args.arch}-install"

    build_dir.mkdir(exist_ok=True)

    subprocess.run(
        [
            CMAKE,
            "-S", source_sir,
            "-B", build_dir,
            "-GNinja",
            f"-DCMAKE_FIND_ROOT_PATH={dependencies_dir}",
            f"-DCMAKE_PREFIX_PATH={dependencies_dir / 'lib' / 'cmake'}",
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_INSTALL_PREFIX={install_dir}",
            f"-DCMAKE_OSX_ARCHITECTURES={args.arch}",
            f"-DCMAKE_OSX_DEPLOYMENT_TARGET={args.macos_version}",
            # CloudCompare triggers a bunch of deprecated when built with Qt5.15
            "-DCMAKE_CXX_FLAGS=-Wno-deprecated",
            # CloudCompare CMake options
            f"-DCCCORELIB_USE_CGAL=ON",
        ],
        check=True,
    )

    subprocess.run([CMAKE, "--build", build_dir, f"-j{args.num_jobs}"], check=True)
    subprocess.run([CMAKE, "--install", build_dir], check=True)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("arch", help="The arch for which cloud compare should be build")
    parser.add_argument("macos_version", help="The minimum macOS version targeted", metavar="macos-version")
    parser.add_argument("--num-jobs", help="Number of jobs / threads for the build", default=multiprocessing.cpu_count())

    args = parser.parse_args()
    run_build(args)


if __name__ == '__main__':
    main()