#!/usr/bin/env python3
import os.path
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional
import argparse


def list_used_shared_libs(path: str) -> List[str]:
    """ given a path to a binary (either executable or lib) returns a list
    of dylibs this binary depends on as given by otool.

    :param path: path the binary to scan
    :return: list of dylibs used
    """
    otool_output = subprocess.run(['otool', '-L', path], capture_output=True).stdout
    otool_output = otool_output.decode('utf-8')

    needed_libs = otool_output.split('\n\t')
    # First line is the path we gave
    # Second line is our lib
    needed_libs = needed_libs[2:]
    # Now needed_libs is a list of strings that look like this
    # "/usr/lib/libc++.1.dylib (compatibility version 1.0.0, current version 1200.3.0)"
    # We only care about the first part
    needed_libs = [lib.split(' ')[0] for lib in needed_libs]

    return needed_libs


def get_rpath(binary_path: str) -> Optional[str]:
    otool_output = subprocess.run(['otool', '-l', binary_path], capture_output=True).stdout
    otool_output = otool_output.decode('utf-8')

    lines = list(line.strip() for line in otool_output.splitlines())
    for i, line in enumerate(lines):
        if line == 'cmd LC_RPATH':
            return lines[i + 2].split(' ')[1]

    return None


def filter_out_libs_we_should_not_touch(loaded_paths: List[str]) -> List[str]:
    def should_be_ignored(lib_path: str) -> bool:
        if lib_path.startswith('/usr/lib'):
            return True

        if lib_path.startswith("/System"):
            return True

        if lib_path.startswith('@'):
            return True

        if lib_path.startswith('/'):
            return False

        return False

    return [lib for lib in loaded_paths if not should_be_ignored(lib)]

    # return [lib for lib in loaded_paths if
    #         not lib.startswith('/usr/lib') and not lib.startswith('/System') and not lib.startswith(
    #             '@') and lib.startswith('/')]


def handle_qt_frameworks(cc_plugin_path: str, frameworks_path: str) -> None:
    needed_libs = list_used_shared_libs(cc_plugin_path)
    needed_libs = filter_out_libs_we_should_not_touch(needed_libs)

    abs_cc_plugin_dir = os.path.dirname(os.path.abspath(cc_plugin_path))
    abs_frameworks_path = os.path.abspath(frameworks_path)

    # The libs should already have been copied in the frameworks dir by macdeployqt
    for loaded_path in needed_libs:
        if '.framework' not in loaded_path:
            continue

        pos = loaded_path.find("Qt")

        relpath = os.path.relpath(abs_frameworks_path, abs_cc_plugin_dir)
        if relpath != '.':
            new_loaded_path_prefix = f"@loader_path/{relpath}"
        else:
            new_loaded_path_prefix = f"@loader_path"

        if pos != -1:
            new_loaded_path = f"{new_loaded_path_prefix}/{loaded_path[pos:]}"
            subprocess.run(['install_name_tool', '-change', loaded_path, new_loaded_path, cc_plugin_path])
            print(f"\tChanging {loaded_path} to {new_loaded_path}")
            # if args.verbose:
            #     print(f"\tChanging {loaded_path} to {new_loaded_path}")


def list_all_external_libs(paths: List[str]):
    libs_to_analyze = list(paths)
    already_analyzed = set()
    external_libs = []

    while libs_to_analyze:
        current_lib = libs_to_analyze.pop()

        already_analyzed.add(current_lib)

        all_needed_libs = list_used_shared_libs(current_lib)
        needed_libs = filter_out_libs_we_should_not_touch(all_needed_libs)

        current_lib_rpath = get_rpath(current_lib)
        if current_lib_rpath is not None:
            current_lib_rpath = os.path.normpath(
                current_lib_rpath.replace("@loader_path", os.path.dirname(current_lib)))

            needed_libs = [
                os.path.normpath(lib.replace("@rpath", current_lib_rpath))
                for lib in needed_libs if lib.startswith('@rpath')
            ]

        # needed_libs = [os.path.normpath(lib.replace("@rpath", current_lib_rpath)) for lib in all_needed_libs if
        #                lib.startswith('@rpath')]

        # needed_libs = needed_libs + filter_out_libs_we_should_not_touch(all_needed_libs)

        external_libs.append((current_lib, needed_libs))
        for needed_lib in needed_libs:
            if os.path.exists(needed_lib):
                if needed_lib not in already_analyzed:
                    libs_to_analyze.append(needed_lib)
            else:
                raise RuntimeError(f"{needed_lib} does not exist")

    return external_libs


def main():
    parser = argparse.ArgumentParser(description="Script that will copy third dependencies into the App Bundle "
                                                 "and update load paths so that the .app is self contained")
    parser.add_argument("app_path", help="Path the the .app")
    parser.add_argument("--verbose", action='store_true', default=False)
    parser.add_argument("--sign", action='store_true', default=False)

    args = parser.parse_args()
    app_path = args.app_path

    if not app_path.endswith(".app"):
        raise SystemExit("The path you gave does not look likes its a .app bundle")

    frameworks_path = f"{app_path}/Contents/Frameworks"
    plugins_path = Path(f"{app_path}/Contents/PlugIns/ccPlugins")
    executable_path = list((Path(app_path) / "Contents" / "MacOs").iterdir())[0]

    app_rpath = os.path.normpath(
        get_rpath(str(executable_path)).replace("@executable_path", str(executable_path.parent)))
    assert app_rpath == frameworks_path, 'This script relies on the executable rpath pointing to frameworks path'

    # TODO install_name_tool -i should be used somewehere (i think on the libs we copied)

    all_external_libs = []
    libs_to_update = []

    plugins = list(plugins_path.iterdir())
    for i, plugin_path in enumerate(plugins, start=1):
        print(f'[{i} / {len(plugins)}] Plugin: {plugin_path.name}')

        handle_qt_frameworks(str(plugin_path), frameworks_path)

        # Now handle external dependencies
        needed_libs = list_used_shared_libs(str(plugin_path))
        needed_libs = filter_out_libs_we_should_not_touch(needed_libs)
        plugin_needed_libs = needed_libs

        all_plugin_external_libs = list_all_external_libs(plugin_needed_libs)
        all_external_libs.extend(all_plugin_external_libs)
        libs_to_update.append((plugin_path, needed_libs))

        if args.verbose:
            print(f"\tNum direct external dependencies: {len(plugin_needed_libs)}")
            print(f"\tNum pulled external dependencies: {len(all_plugin_external_libs)}")

    for external_lib_path, loaded_paths in all_external_libs:
        dst_path = Path(frameworks_path) / Path(external_lib_path).name
        shutil.copyfile(external_lib_path, dst_path)
        libs_to_update.append((dst_path, loaded_paths))

        if args.verbose:
            print(f'Copying external dylib {external_lib_path} to {dst_path}')

    if args.verbose:
        print(f"Copied {len(all_external_libs)} dylibs")

    # print('')
    for lib, loaded_paths in libs_to_update:
        if not loaded_paths:
            continue

        # print(f'\t{lib}')
        abs_lib = os.path.dirname(os.path.abspath(lib))
        for loaded_path in loaded_paths:
            assert str(lib).startswith(app_path)  # Its critical not to modify libs outside the bundle
            assert loaded_path.startswith('/')

            relpath = os.path.relpath(frameworks_path, abs_lib)
            if relpath != '.':
                new_loaded_path = f"@loader_path/{relpath}/{Path(loaded_path).name}"
            else:
                new_loaded_path = f"@loader_path/{Path(loaded_path).name}"
            subprocess.run(['install_name_tool', '-change', loaded_path, new_loaded_path, lib])

            if args.verbose:
                print(f"Changing {loaded_path} to {new_loaded_path}")

    if args.sign:
        print()
        signing_id = input('Signing ID: ')
        subprocess.run(['codesign', '--verify', '--force', '--options=runtime', '--timestamp', '--deep',
                        '--sign', signing_id, args.app_path], capture_output=False)

        subprocess.run(['codesign', '-vvv', '--deep', args.app_path])


if __name__ == '__main__':
    main()
