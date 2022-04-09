#!/usr/bin/env python3

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import os
from dataclasses import dataclass
from pathlib import Path
import sys
import logging

import subprocess
import multiprocessing
import shutil
from subprocess import CalledProcessError

# TODO: avoid redoing some steps like extraction, configuration, building if it was already done and
#       shit did not change

# https://cmake.org/cmake/help/latest/manual/cmake-toolchains.7.html
# https://stackoverflow.com/questions/24659753/cmake-find-library-and-cmake-find-root-path
# https://cmake.org/cmake/help/latest/variable/CMAKE_FIND_ROOT_PATH_MODE_LIBRARY.html

SCRIPT_DIR = os.path.dirname(__file__)
# The dir where we put downloaded archives/gits, build files, etc
WORKING_DIR = Path(SCRIPT_DIR) / "stuff"
INSTALL_ROOT = (Path(SCRIPT_DIR) / "install").absolute()
INSTALL_BIN = INSTALL_ROOT /'bin'
INSTALL_LIB = INSTALL_ROOT / 'lib'
INSTALL_INCLUDE = INSTALL_ROOT / 'include'
PKG_CONFIG_PATH = INSTALL_LIB / 'pkgconfig'

NUM_JOBS = multiprocessing.cpu_count() - 1

OUR_ENV_VARS = {
    **os.environ,
    "PKG_CONFIG_PATH": str(PKG_CONFIG_PATH),
}

OUR_ENV_VARS['PATH'] = f"{str(INSTALL_BIN)}:{OUR_ENV_VARS['PATH']}"

CMAKE_DEFAULT_CONFIG_OPTS = {
    "-DCMAKE_BUILD_TYPE": "Release",
    "-DCMAKE_INSTALL_PREFIX": str(INSTALL_ROOT),
    # Otherwise on some Linux some lib would be in /lib and others in /lib64
    "-DCMAKE_INSTALL_LIBDIR": str(INSTALL_LIB),
    "-DCMAKE_PREFIX_PATH": str(INSTALL_LIB / "cmake"),
    "-DCMAKE_INCLUDE_PATH": str(INSTALL_INCLUDE),
    "-DCMAKE_LIBRARY_PATH": str(INSTALL_LIB),
    #"-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM": "NEVER",
    #"-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY": "ONLY", 
    #"-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE": "ONLY", 
    #"-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE": "ONLY",
    "-DCMAKE_FIND_ROOT_PATH": str(INSTALL_ROOT),
}


AUTOTOOLS_DEFAULT_CONFIG_OPTS = [
    f"--prefix={str(INSTALL_ROOT)}"
]

# aka CPPFLAGS
COMPILER_PREPROCESSOR_FLAGS = {
    '-I': [str(INSTALL_INCLUDE)],
    
}

# aka CFLAGS (for C) or CXXFLAGS (for C++)
COMPILER_FLAGS = {
    '-L': [str(INSTALL_LIB)],
}

# Commands
CMAKE = "cmake"
CURL = "curl"
MAKE = "make"
GIT = 'git'

CAPTURE=True

LOGGER = logging.getLogger(__name__)


def run_command(*args, **kwargs):
    if CAPTURE:
        stdout, stderr = subprocess.PIPE, subprocess.STDOUT
    else:
        stdout, stderr = sys.stdout, sys.stderr

    subprocess.run(*args, **kwargs, check=True, stdout=stdout, stderr=stderr, env=OUR_ENV_VARS)

def maybe_log_subprocess_error(exc: subprocess.CalledProcessError):
    if CAPTURE:
        logging.critical(exc.stdout.decode())

class BuildSystem(ABC):
    @abstractmethod
    def configure(self, *args, **kwargs):
        ...

    @abstractmethod
    def build(self, *args, **kwargs):
        ...

    @abstractmethod
    def install(self, *args, **kwargs):
        ...


class SourceDistribution(ABC):
    @abstractmethod
    def download_to(self, output_dir: str) -> str:
        ...

    @abstractmethod
    def verify_checksum(self):
        ...


def extract_archive(archive_path: str, dest_folder):
    if not archive_path.endswith('.tar.gz'):
        raise NotImplementedError

    subprocess.run(['tar', '-xzf', archive_path, '-C', dest_folder])
    return archive_path[:-len('.tar.gz')]


@dataclass
class Dependency:
    name: str
    # version: str
    source: SourceDistribution
    build_system: BuildSystem

    def handle(self) -> None:
        our_dir = WORKING_DIR / self.name
        our_dir.mkdir(exist_ok=True)

        try:
            extrated_dir = self.source.download_to(str(our_dir))
            LOGGER.debug(f"Sources are ready at: {extrated_dir}")
        except CalledProcessError as e:
            # maybe LOGGER.exception ?
            LOGGER.critical("Failed to download sources")
            maybe_log_subprocess_error(e)

       

        build_dir = our_dir / 'build'
        build_dir.mkdir(exist_ok=True)

        LOGGER.debug("Configuring")
        try:
            self.build_system.configure(
                source_dir=str(extrated_dir),
                build_dir=str(build_dir)
            )
        except CalledProcessError as e:
            LOGGER.critical("Failed to configure")
            maybe_log_subprocess_error(e)

        
        LOGGER.debug("Building")
        self.build_system.build(
                build_dir=str(build_dir)
        )
        # try:
        #     self.build_system.build(
        #         build_dir=str(build_dir)
        #     )
        # except CalledProcessError as e:
        #     LOGGER.critical("Failed to build")
        #     maybe_log_subprocess_error(e)
            


        LOGGER.debug("Installing")
        try:
            self.build_system.install(
                build_dir=str(build_dir)
            )
        except CalledProcessError as e:
            LOGGER.critical("Failed to configure")
            maybe_log_subprocess_error(e)


def is_dir_empty(path: str) -> bool:
    iter = Path(path).iterdir()

    try:
        next(iter)
    except StopIteration:
        return True
    else:
        return False


class InternetArchive(SourceDistribution):
    def __init__(self, url: str, expected_hash: Optional[str]) -> None:
        self.url = url
        self.expected_hash = expected_hash

    def download_to(self, output_dir: str) -> str:
        # --location permet de récupérer le fichier même si la page a changé de location
        # subprocess.run(['wget', '-P', output_dir, self.url], check=True)

        archive_name = Path(self.url).name
        local_archive_path = Path(output_dir) / archive_name

        if local_archive_path.exists():
            LOGGER.debug('Sources are already downloaded')
        else:
            LOGGER.debug('Start downloading sources')
            run_command([CURL, '--location', self.url, '-o', local_archive_path])
            LOGGER.debug('Sources succesfully downloaded')

        LOGGER.debug("Extracting sources")
        extracted_dir = extract_archive(str(local_archive_path), output_dir)
        LOGGER.debug(f"Sources extracted to {extracted_dir}")

        return str(extracted_dir)

    def verify_checksum(self):
        if self.expected_hash is not None:
            raise NotImplementedError

class GitRepo(SourceDistribution):
    def __init__(self, url: str, ref: str):
        self.url = url
        self.ref = ref

    def download_to(self, output_dir: str) -> str:
        base_name = Path(self.url).name

        output_dir = Path(output_dir) / base_name
        if output_dir.exists():
            LOGGER.debug('Project already cloned')
        else:
            run_command([GIT, 'clone', self.url, str(output_dir)])

        saved_cwd = os.getcwd()
        os.chdir(str(output_dir))
        run_command(
            [GIT, 'checkout', self.ref],
        )
        os.chdir(saved_cwd)

        return str(output_dir)

    def verify_checksum(self):
        if self.expected_hash is not None:
            raise NotImplementedError

class CMake(BuildSystem):
    def __init__(self, configure_options: Dict[str, str] = None) -> None:
        if configure_options is None:
            self.configure_options = {**CMAKE_DEFAULT_CONFIG_OPTS}
        else:
            self.configure_options = {**CMAKE_DEFAULT_CONFIG_OPTS, **configure_options}

    def configure(self, source_dir: str, build_dir: str):
        options_as_cmd_args = []
        for (key, value) in self.configure_options.items():
            options_as_cmd_args.append(f"{key}={value}")
        run_command([CMAKE, '-S', source_dir, '-B', build_dir] + options_as_cmd_args)

    def build(self, build_dir: str):
        run_command([CMAKE, '--build', build_dir, f'-j{NUM_JOBS}'])

    def install(self, build_dir: str):
        run_command([CMAKE, '--install', build_dir])


class Autotools(BuildSystem):
    def __init__(self, configure_options: List[str] = None, supports_out_of_tree_build=True) -> None:
        if configure_options is not None:
            self.configure_options = [*AUTOTOOLS_DEFAULT_CONFIG_OPTS, *configure_options]
        else:
            self.configure_options = [*AUTOTOOLS_DEFAULT_CONFIG_OPTS]
        self.supports_out_of_tree_build = supports_out_of_tree_build

    def configure(self, source_dir: str, build_dir: str):
        cpp_flags_value = ""
        for key, value in COMPILER_PREPROCESSOR_FLAGS.items():
            if isinstance(value, list):
                for v in value:
                    cpp_flags_value += f"{key}{v} "
            else:
                cpp_flags_value += f"{key}{value} "

        cxx_flags_value = ""
        for key, value in COMPILER_FLAGS.items():
            if isinstance(value, list):
                for v in value:
                    cxx_flags_value += f"{key}{v} "
            else:
                cxx_flags_value += f"{key}{value} "

        if self.supports_out_of_tree_build:
            saved_cwd = os.getcwd()
            os.chdir(build_dir)
            run_command(
                [f"{source_dir}/configure", f"CPPFLAGS={cpp_flags_value}", f"CXXFLAGS={cxx_flags_value}", f"CFLAGS={cxx_flags_value}"] + self.configure_options,
            )
            os.chdir(saved_cwd)
        else:
            if is_dir_empty(build_dir): 
                LOGGER.debug("Out of tree build not supported, copying sources to build dir")
                shutil.copytree(src=source_dir, dst=build_dir, dirs_exist_ok=True)
            saved_cwd = os.getcwd()
            os.chdir(build_dir)
            run_command(
                [f"./configure", f"CPPFLAGS={cpp_flags_value}", f"CXXFLAGS={cxx_flags_value}", f"CFLAGS={cxx_flags_value}"] + self.configure_options,
            )
            os.chdir(saved_cwd)


    def build(self, build_dir: str):
        saved_cwd = os.getcwd()
        os.chdir(build_dir)
        run_command([MAKE, f'-j{NUM_JOBS}'])
        os.chdir(saved_cwd)  

    def install(self, build_dir: str):
        saved_cwd = os.getcwd()
        os.chdir(build_dir)
        run_command([MAKE, 'install'])
        os.chdir(saved_cwd)



DEPENDENCIES: List[Dependency] = [
    Dependency(
        name="libtiff",
        source=InternetArchive(
            url="http://download.osgeo.org/libtiff/tiff-4.3.0.tar.gz",
            expected_hash=None
        ),
        build_system=CMake()
    ),
    Dependency(
        name='sqlite',
        source=InternetArchive(
            url='https://sqlite.org/2021/sqlite-autoconf-3360000.tar.gz',
            expected_hash=None,
        ),
        build_system=Autotools(),
    ),
    Dependency(
        name='proj',
        source=InternetArchive(
            url="http://download.osgeo.org/proj/proj-8.1.0.tar.gz",
            expected_hash=None,
        ),
        build_system=Autotools(
            configure_options=['--without-curl']
        ),
    ),
    Dependency(
   	    name='libgeotiff',
    	  source=InternetArchive(
    		  url="http://download.osgeo.org/geotiff/libgeotiff/libgeotiff-1.7.0.tar.gz",
    		  expected_hash=None,
    	  ),
    	  build_system=Autotools(),
    ),
    Dependency(
        name='gdal',
        source=InternetArchive(
            url='https://github.com/OSGeo/gdal/releases/download/v3.3.1/gdal-3.3.1.tar.gz',
            expected_hash=None,
        ),
        build_system=Autotools(
            configure_options=['--with-python=no'],
            supports_out_of_tree_build=False,
        )
    ),
    Dependency(
        name='laz-perf',
        source=GitRepo(
            url="https://github.com/hobu/laz-perf",
            ref="3.0.0",
        ),
        build_system=CMake(
          configure_options={
            "-DWITH_TESTS": "FALSE",
          }
        )
    ),
    Dependency(
      name='pdal',
      source=InternetArchive(
        url='https://github.com/PDAL/PDAL/releases/download/2.3.0/PDAL-2.3.0-src.tar.gz',
        expected_hash=None,
      ),
      build_system=CMake()
    )
]


def main():
    logging.basicConfig(
        level=logging.DEBUG
    )
    
    WORKING_DIR.mkdir(exist_ok=True)
    
    for dependency in DEPENDENCIES:
        LOGGER.info(f"Handling dependency named '{dependency.name}'")
        dependency.handle()


if __name__ == '__main__':
    main()
    
    
    
    
    
    
    
    
    
'''
    If you ever happen to want to link against installed libraries
in a given directory, LIBDIR, you must either use libtool, and
specify the full pathname of the library, or use the '-LLIBDIR'
flag during linking and do at least one of the following:
   - add LIBDIR to the 'LD_LIBRARY_PATH' environment variable
     during execution
   - add LIBDIR to the 'LD_RUN_PATH' environment variable
     during linking
   - use the '-Wl,-rpath -Wl,LIBDIR' linker flag
   - have your system administrator add LIBDIR to '/etc/ld.so.conf'

See any operating system documentation about shared libraries for
more information, such as the ld(1) and ld.so(8) manual pages.
'''
