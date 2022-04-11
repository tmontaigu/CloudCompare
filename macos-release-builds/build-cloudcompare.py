#!/usr/bin/env python3

import argparse
import multiprocessing
from pathlib import Path
from typing import Dict
import subprocess
import os

CMAKE = "cmake"

SCRIPT_DIR = Path(__file__).parent.absolute()


def run_build(args):
    dependencies_dir = SCRIPT_DIR / args.arch / "install"
    source_sir = SCRIPT_DIR.parent
    build_dir = SCRIPT_DIR / f"{args.arch}" / "builds" / "CloudCompare"
    install_dir = SCRIPT_DIR / f"{args.arch}"

    EIGEN_ROOT_DIR = str(dependencies_dir / 'include' / 'eigen3')

    build_dir.mkdir(exist_ok=True)
    subprocess.run(
        [
            CMAKE,
            "-S", source_sir,
            "-B", build_dir,
            "-GNinja",
            f"-DCMAKE_FIND_ROOT_PATH={dependencies_dir}",
            f"-DCMAKE_PREFIX_PATH={dependencies_dir / 'lib' / 'cmake'}",
            f"-DCMAKE_INCLUDE_PATH={dependencies_dir / 'include'}",
            "-DCMAKE_IGNORE_PATH=/opt/homebrew/lib/",
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_INSTALL_PREFIX={install_dir}",
            # macOS special things
            f"-DCMAKE_OSX_ARCHITECTURES={args.arch}",
            f"-DCMAKE_OSX_DEPLOYMENT_TARGET={args.macos_version}",
            # CloudCompare triggers a bunch of deprecated when built with Qt5.15
            "-DCMAKE_CXX_FLAGS=-Wno-deprecated -DDLIB_NO_GUI_SUPPORT",
            f"-DEIGEN_ROOT_DIR={EIGEN_ROOT_DIR}",
            # CloudCompare CMake options
            '-DOPTION_BUILD_CCVIEWER=OFF',
            f"-DCCCORELIB_USE_CGAL=ON",
            "-DOPTION_USE_DXF_LIB=ON",
            "-DOPTION_USE_SHAPE_LIB=ON",
            "-DOPTION_USE_GDAL=ON",
            # GL Plugins
            "-DPLUGIN_GL_QEDL=ON",
            "-DPLUGIN_GL_QSSAO=ON",
            # Standard Plugins
            "-DPLUGIN_STANDARD_QANIMATION=ON",
            "-DPLUGIN_STANDARD_QBROOM=ON",
            '-DPLUGIN_STANDARD_QCANUPO=ON',
            '-DPLUGIN_STANDARD_QCOLORIMETRIC_SEGMENTER=ON',
            '-DPLUGIN_STANDARD_QCOMPASS=ON',
            '-DPLUGIN_STANDARD_QCSF=ON',
            '-DPLUGIN_STANDARD_QFACETS=ON',
            '-DPLUGIN_STANDARD_QHOUGH_NORMALS=ON',
            "-DPLUGIN_STANDARD_QHPR=ON",
            "-DPLUGIN_STANDARD_QM3C2=ON",
            "-DPLUGIN_STANDARD_QMPLANE=ON",
            "-DPLUGIN_STANDARD_QPCL=OFF",  # TODO
            "-DPLUGIN_STANDARD_QPCV=ON",
            "-DPLUGIN_STANDARD_QPOISSON_RECON=ON",
            "-DPLUGIN_STANDARD_QRANSAC_SD=ON",
            "-DPLUGIN_STANDARD_QSRA=ON",
            "-DPLUGIN_STANDARD_MASONRY_QAUTO_SEG=OFF",  # TODO (not as important)
            "-DPLUGIN_STANDARD_MASONRY_QMANUAL_SEG=OFF",  # TODO (not as important)
            "-DPLUGIN_STANDARD_QCLOUDLAYERS=ON",
            # IO Plugins
            "-DPLUGIN_IO_QCORE=ON",
            "-DPLUGIN_IO_QADDITIONAL=ON",
            "-DPLUGIN_IO_QCSV_MATRIX=ON",
            "-DPLUGIN_IO_QE57=OFF",  # TODO
            "-DPLUGIN_IO_QPDAL=ON", # TODO lazperf missing
            "-DPLUGIN_IO_QPHOTOSCAN=ON",
        ],
        check=True,
    )

    subprocess.run([CMAKE, "--build", str(build_dir), f"-j{args.num_jobs}"], check=True)
    subprocess.run([CMAKE, "--install", str(build_dir)], check=True)


def main():
    parser = argparse.ArgumentParser(description="Builds the macOS CloudCompare app using the dependencies built"
                                                 "by the build-dependencies script")

    parser.add_argument("arch", help="The arch for which cloud compare should be build")
    parser.add_argument("macos_version", help="The minimum macOS version targeted", metavar="macos-version")
    parser.add_argument("--num-jobs", help="Number of jobs / threads for the build",
                        default=multiprocessing.cpu_count())

    args = parser.parse_args()
    run_build(args)


if __name__ == '__main__':
    main()
