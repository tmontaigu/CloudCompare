#!/usr/bin/env python3
import os.path
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from pprint import pprint
from typing import List, Optional, Union, NamedTuple, Dict
import argparse
import itertools


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
    lib: Path
    dst_folder: Path

@dataclass(unsafe_hash=True, eq=True)
class LoadPathChange(RelocationAction):
    lib: Path
    old: Path
    new: Path


def resolve_rpath(rpath: Path, executable_path: Path) -> Path:
    return Path(str(rpath).replace('@executable_path', str(executable_path.parent))).resolve()


class AppBundleInfo:
    def __init__(self, path_to_app: Union[str, Path]) -> None:
        self.lib_info = Library.from_path(path_to_app / 'Contents' / 'MacOS' / 'CloudCompare')
        self.frameworks_path = path_to_app / 'Contents' / 'Frameworks'

        index = self.lib_info.rpaths.index(Path('@executable_path/../Frameworks'))
        self.libs_in_rpath = [lib.name for lib in resolve_rpath(self.lib_info.rpaths[index], self.lib_info.path).iterdir()]


def create_relocation_plan(root_lib: Path, app_info: AppBundleInfo) -> List[RelocationAction]:
    relocation_actions: List[RelocationAction] = []

    lib_names_in_rpaths = {}
    libs_to_analyze: List[Path] = [root_lib]
    libs_to_copy: List[Path] = []
    while libs_to_analyze:
        current_lib = Library.from_path(libs_to_analyze.pop())
            # print('\t',  current_lib.path, 'depdends on')
            # pprint(current_lib.loaded_libs, indent=4)

        for rpath in current_lib.rpaths:
            if rpath not in lib_names_in_rpaths:
                rpath = resolve_rpath(rpath, app_info.lib_info.path)
                lib_names_in_rpaths[rpath] = [lib.name for lib in rpath.iterdir()]

        sublibs_to_relocate = list_sublibs_to_relocate(current_lib.loaded_libs, app_info.libs_in_rpath)
        # print('\t', current_lib.path, 'depdends on relocatables')
        pprint(sublibs_to_relocate, indent=4)
        print('Relocation actions')
        pprint(relocation_actions)

        for lib_to_relocate in sublibs_to_relocate:
            print('Investigating relocation of', lib_to_relocate, lib_to_relocate.parts)
            parts = lib_to_relocate.parts
            if parts[0] == '@rpath':
                for rpath, libs_inside in lib_names_in_rpaths.items():
                    if lib_to_relocate.name in libs_inside:
                        print(f'found {lib_to_relocate} in {rpath}')
                        complete_path = str(lib_to_relocate).replace('@rpath', str(rpath))
                        relocation_actions.append(CopyLib(lib=Path(complete_path), dst_folder=app_info.frameworks_path))
                        libs_to_copy.append(Path(complete_path))
                        libs_to_analyze.append(Path(complete_path))
                    break
                else:
                    raise RuntimeError(f'Could not find {lib_to_relocate} in any rpath')

            elif parts[0] == '/':
                relocation_actions.append(CopyLib(lib=lib_to_relocate, dst_folder=app_info.frameworks_path))
                # print(libs_to_copy, current_lib.path)
                # current lib depends on lib_to_relocate with a full path
                # so we have to update that path. there are 2 cases to handle
                # current lib was copied, or it was not
                if current_lib.path in libs_to_copy:
                    print('lib was copied')
                    relocation_actions.append(LoadPathChange(
                        lib=app_info.frameworks_path / current_lib.path.name,
                        old=lib_to_relocate,
                        new=Path(f'@rpath/{lib_to_relocate.name}'),
                    ))
                else:
                    relocation_actions.append(LoadPathChange(
                        lib=current_lib.path,
                        old=lib_to_relocate,
                        new=Path(f'@rpath/{lib_to_relocate.name}'),
                    ))
                libs_to_copy.append(lib_to_relocate)
                libs_to_analyze.append(lib_to_relocate)
            elif parts[0] == '@executable_path':
                # TODO maybe verif it exists
                complete_path = resolve_rpath(lib_to_relocate, app_info.lib_info.path)
                libs_to_analyze.append(complete_path)
            else:
                raise RuntimeError(f'Cannot handle relocation of {lib_to_relocate}')

        if current_lib.rpaths:
            relocation_actions.append(RemoveAllRpath(current_lib.path))

    return relocation_actions



if __name__ == '__main__':

    app_bundle_path = Path('/Users/thomas/Projects/CloudCompare/macos-release-builds/x86_64/CloudCompare/CloudCompare.app')
    executable_path = app_bundle_path / 'Contents' / 'MacOS' / 'CloudCompare'
    plugins_folder_path = app_bundle_path / 'Contents' / 'Plugins' / 'ccPlugins'

    info = AppBundleInfo(app_bundle_path)

    # all_actions = create_relocation_plan(executable_path, app_info=info)
    # # For the main executable, we actually don't want to remove the rpaths !
    # all_actions = [action for action in all_actions if not isinstance(action, RemoveAllRpath)]
    all_actions = []
    for plugin in plugins_folder_path.iterdir():
        print(plugin.name)
        all_actions.extend(create_relocation_plan(plugin, app_info=info))


    # p = Path('/Users/thomas/Projects/CloudCompare/macos-release-builds/x86_64/CloudCompare/CloudCompare.app/Contents/PlugIns/ccPlugins/libQPDAL_IO_PLUGIN.dylib')
    # all_actions = create_relocation_plan(p, app_info=info)

    all_actions = set(all_actions)
    pprint(all_actions)

    for action in all_actions:
        if isinstance(action, CopyLib):
            # TODO unhardcode
            shutil.copy2(src=action.lib, dst=action.dst_folder)
        elif isinstance(action, RemoveAllRpath):
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
        elif isinstance(action, LoadPathChange):
            pprint(action)
            subprocess.run([
                'install_name_tool',
                '-change',
                str(action.old),
                str(action.new),
                str(action.lib),
            ])


    if True:
        print()
        signing_id = input('Signing ID: ')
        subprocess.run(['codesign', '--verify', '--force', '--options=runtime', '--timestamp', '--deep',
                        '--sign', signing_id, app_bundle_path], capture_output=False)

        print()
        subprocess.run(['codesign', '-vvv', '--deep', app_bundle_path])

    # pdal_plugin = Library.from_path('/Users/thomas/Projects/CloudCompare/macos-release-builds/x86_64/CloudCompare/CloudCompare.app/Contents/PlugIns/ccPlugins/libQPDAL_IO_PLUGIN.dylib')
    # pdal_plugin.loaded_libs = [lib for lib in pdal_plugin.loaded_libs if should_be_relocated(lib)]
    #
    # # pprint(pdal_plugin.loaded_libs)
    # # pprint(pdal_plugin.rpaths)
    # # pprint(libs_in_app_rpaths)
    #
    # libs_to_handle = []
    # for lib in pdal_plugin.loaded_libs:
    #     lib_str = str(lib)
    #     if lib_str.startswith('@rpath/'):
    #         lib_name = lib_str[len('@rpath/'):].split('/')[0]
    #         if lib_name not in libs_in_app_rpaths:
    #             libs_to_handle.append(lib)
    # pdal_plugin.loaded_libs = libs_to_handle
    # print("PATH TO CHANGE")
    # # pprint(pdal_plugin.loaded_libs)
    #
    # lib_names_in_rpaths = {}
    # for rpath in pdal_plugin.rpaths:
    #     lib_names_in_rpaths[rpath] = [lib.name for lib in rpath.iterdir()]
    # # pprint(lib_names_in_rpaths)
    #
    # for lib_to_relocate in pdal_plugin.loaded_libs:
    #     parts = lib_to_relocate.parts
    #     if parts[0] == '@rpath':
    #         for rpath, libs_inside in lib_names_in_rpaths.items():
    #             if lib_to_relocate.name in libs_inside:
    #                 print(f'found {lib_to_relocate} in {rpath}')
    #                 # TODO COPY to framework dir
    #                 break
    #         else:
    #             raise RuntimeError(f'Could not find {lib_to_relocate} in any rpath')
    #
    #     elif parts[0] == '/':
    #         # TODO COPY to framwework dir
    #         pass
    #     else:
    #         raise RuntimeError(f'Cannot handle relocation of {lib_to_relocate}')
    #
    # # TODO Delete rpaths from lib
    # # TODO hadnle sub depdendencies
