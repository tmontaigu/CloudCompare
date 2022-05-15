#!/usr/bin/env python3
import os.path
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from pprint import pprint
from typing import List, Optional, Union, NamedTuple, Dict, Tuple
import argparse
import itertools
import sys


@dataclass
class Library:
    path: Path
    loaded_libs: List[Path]
    rpaths: List[Path]

    @classmethod
    def from_path(cls, path: Union[str, Path]) -> 'Library':
        otool_output = subprocess.run(['otool', '-l', str(path)], capture_output=True, check=True).stdout
        otool_output = otool_output.decode('utf-8')

        lines_iter = (line.strip() for line in otool_output.splitlines())

        loaded_libs = []
        rpaths = []

        for line in lines_iter:
            if not line.startswith("Load command"):
                continue

            cmd_type = next(lines_iter)
            if cmd_type == 'cmd LC_LOAD_DYLIB':
                _cmd_size = next(lines_iter)
                loaded_libs.append(Path(next(lines_iter).split()[1]))
                _time_stamp = next(lines_iter)
                _current_version = next(lines_iter)
                _compatibility_version = next(lines_iter)
            elif cmd_type == 'cmd LC_RPATH':
                _cmd_size = next(lines_iter)
                rpaths.append(Path(next(lines_iter).split()[1]))
            else:
                continue

        return cls(path=path, loaded_libs=loaded_libs, rpaths=rpaths)


def is_system_lib(lib: Path) -> bool:
    if lib.parents[0] == Path('/usr/lib'):
        return True

    if str(lib).startswith('/System'):
        return True

    return False


def list_sublibs_to_relocate(
        libs: List[Path],
        libs_in_app_rpath: List[str],
) -> List[Path]:
    sublibs_to_relocate = []
    for lib in libs:
        if is_system_lib(lib):
            continue

        if lib.parts[0] == '@rpath':
            # Frameworks are folder, so they have more than 2 parts
            # But we use the folder name to identify them
            lib_name = lib.parts[1]

            if lib_name in libs_in_app_rpath:
                continue

        sublibs_to_relocate.append(lib)

    return sublibs_to_relocate


class RelocationAction:
    pass


@dataclass(unsafe_hash=True, eq=True)
class RemoveAllRpath(RelocationAction):
    lib: Path


@dataclass(unsafe_hash=True, eq=True)
class CopyLib(RelocationAction):
    src: Path
    dst: Path

@dataclass(unsafe_hash=True, eq=True)
class LoadPathChange(RelocationAction):
    lib: Path
    old: Path
    new: Path


def resolve_rpath(rpath: Path, executable_path: Path) -> Path:
    if rpath.parts[0] == '@executable_path':
        rpath =  Path(str(rpath).replace('@executable_path', str(executable_path.parent))).resolve()
    return rpath


class AppBundleInfo:
    def __init__(self, path_to_app: Union[str, Path]) -> None:
        self.lib_info = Library.from_path(path_to_app / 'Contents' / 'MacOS' / 'CloudCompare')
        self.frameworks_path = path_to_app / 'Contents' / 'Frameworks'

        index = self.lib_info.rpaths.index(Path('@executable_path/../Frameworks'))
        self.libs_in_rpath = [lib.name for lib in resolve_rpath(self.lib_info.rpaths[index], self.lib_info.path).iterdir()]

class Node:
    def __init__(self, path: Path, depth: int) -> None:
        self.path = path
        self.depth = depth
        

def resolve_load_path(load_path, app_info: AppBundleInfo) -> Path:
    if load_path.parts[0] == '@executable_path':
        load_path =  Path(str(load_path).replace('@executable_path', str(app_info.lib_info.path.parent))).resolve()
    return load_path

    

def create_relocation_plan(
        root_lib: Path,
        app_info: AppBundleInfo
) -> Tuple[
    List[CopyLib],
    List[LoadPathChange],
    List[RemoveAllRpath],
]:

    min_depth_for_copy = 1
    lib_names_in_rpaths = {}
    libs_to_analyze: List[Node] = [Node(path=root_lib, depth=0)]
    
    copy_actions = []
    load_path_updates = []
    rpath_removals = []

    while libs_to_analyze:
        current_node = libs_to_analyze.pop()
        current_lib = Library.from_path(current_node.path)
        # print('\t',  current_lib.path, 'depdends on')
        # pprint(current_lib.loaded_libs, indent=4)

        for rpath in current_lib.rpaths:
            if rpath not in lib_names_in_rpaths:
                rpath = resolve_rpath(rpath, app_info.lib_info.path)
                if rpath.exists():
                    lib_names_in_rpaths[str(rpath)] = [lib.name for lib in rpath.iterdir()]
                    

        # pprint(lib_names_in_rpaths)

        sublibs_to_relocate = list_sublibs_to_relocate(current_lib.loaded_libs, app_info.libs_in_rpath)
        # print('\t', current_lib.path, 'depdends on relocatables')
        # pprint(sublibs_to_relocate, indent=4)
        
        for sublib in sublibs_to_relocate:
            if sublib.parts[0] == '@rpath':
                for rpath, libs_inside in lib_names_in_rpaths.items():
                    assert len(sublib.parts) == 2
                    if sublib.parts[1] in libs_inside:
                        # Here we don't use the `Path.resolve` method as it follow 
                        # potential symlinks, creating an incoherence between the 
                        # sublib load path and the path we want to copy.
                        # symlinks are handled when actually copying
                        resolved_path = Path(str(sublib).replace('@rpath', rpath))
                        break
                else:
                    raise RuntimeError(f"Failed to find {sublib} in any rpath")
            else:
                resolved_path = resolve_load_path(sublib, app_info)

            # If resolbed path does not exists, we won't be able to copy it
            assert resolved_path.exists(), f"{resolved_path} does not exists"
            # print(str(sublib), "resolved to", str(resolved_path))

            subnode = Node(resolved_path, depth=current_node.depth + 1)
            if subnode.depth >= min_depth_for_copy:
                copy_action = CopyLib(
                        src=resolved_path,
                        dst=Path(app_info.frameworks_path) / resolved_path.name,
                    )
                # since we will be copying the sublib, to the frameworks_path,
                # we need to update the load path of dependent lib
                # which here, is the current_node, which, may get copied
                update_load_path = LoadPathChange(
                    lib=Path(app_info.frameworks_path) / current_node.path.name if current_node.depth >= min_depth_for_copy else current_node.path,
                    old=sublib,
                    new=f"@rpath/{sublib.name}",
                )

                remove_rpath_action = RemoveAllRpath(copy_action.dst)

                copy_actions.append(copy_action)
                load_path_updates.append(update_load_path)
                rpath_removals.append(remove_rpath_action)

                libs_to_analyze.append(subnode)


    return copy_actions, load_path_updates, rpath_removals



if __name__ == '__main__':

    app_bundle_path = Path(sys.argv[1]).absolute()
    assert app_bundle_path.suffix == ".app"
    executable_path = app_bundle_path / 'Contents' / 'MacOS' / 'CloudCompare'
    plugins_folder_path = app_bundle_path / 'Contents' / 'Plugins' / 'ccPlugins'

    info = AppBundleInfo(app_bundle_path)

    all_copy_actions = []
    all_update_actions = []
    all_rpath_removals = []

    copy_actions, update_actions, rpah_actions = create_relocation_plan(executable_path, app_info=info)
    # print("copy actions")
    # pprint(copy_actions)
    # print("update_load_path")
    # pprint(update_actions)
    all_copy_actions.extend(copy_actions)
    all_update_actions.extend(update_actions)
    all_rpath_removals.extend(rpah_actions)

    for plugin in plugins_folder_path.iterdir():
        # if not str(plugin.name).startswith('libQPDAL'):
        #     continue
        print()
        print(plugin.name)
        copy_actions, update_actions, rpah_actions = create_relocation_plan(plugin, app_info=info)
        print("copy actions")
        pprint(copy_actions)
        print("update_load_path")
        pprint(update_actions)
        all_copy_actions.extend(copy_actions)
        all_update_actions.extend(update_actions)
    all_rpath_removals.extend(rpah_actions)

    for action in all_copy_actions:
        if action.src == action.dst:
            assert str(action.src).startswith(str(info.frameworks_path))
            continue
        shutil.copy2(src=action.src, dst=action.dst)

    for action in all_update_actions:
        subprocess.run([
            'install_name_tool',
            '-change',
            str(action.old),
            str(action.new),
            str(action.lib),
        ])

    for action in all_rpath_removals:
        lib = Library.from_path(action.lib)
        for rpath in lib.rpaths:
            subprocess.run([
                'install_name_tool',
                '-delete_rpath',
                str(rpath),
                str(action.lib),
            ],
                check=True
            )


    if True:
        print()
        signing_id = input('Signing ID: ')
        subprocess.run(['codesign', '--verify', '--force', '--options=runtime', '--timestamp', '--deep',
                        '--sign', signing_id, app_bundle_path], capture_output=False)

        print()
        subprocess.run(['codesign', '-vvv', '--deep', app_bundle_path])

