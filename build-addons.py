#!/usr/bin/env python3

# Téléchargement, compilation et installation d'outils et bibliothèques C et C++ complémentaires dans le système.

import os
import shutil
import subprocess
import argparse
import multiprocessing


SCRIPT_DIR = os.path.dirname(__file__)

# Répertoire des sources.
SOURCE_DIR = os.path.join(SCRIPT_DIR, 'Source')

# Répertoire d'installation des bibliothèques et outils.
INSTALL_ROOT = '/Users/Shared'
INSTALL_DIR = os.path.join(INSTALL_ROOT, 'local')
INSTALL_BIN = os.path.join(INSTALL_DIR, 'bin')
INSTALL_LIB = os.path.join(INSTALL_DIR, 'lib')
INSTALL_INCLUDE = os.path.join(INSTALL_DIR, 'include')

# SDK courant.
SDK = subprocess.run(['xcrun', '--show-sdk-path'], stdout=subprocess.PIPE, check=True, encoding='utf-8').stdout.splitlines()[0]

os.environ['PATH'] = INSTALL_BIN + ':' + os.environ['PATH']

# Mots clefs pour le téléchargement
# Chaque composant a un nom et est récupéré suivant un des 3 procédés :
# CURL : téléchargement d'un fichier compressé sur le net
# GIT : téléchargement des sources sur un serveur GIT
# COPY : copie à partir du dossier DATA (nécessaire si les sources ont été modifiées par nos besoins)
CURL = 'curl'
GIT  = 'git'
COPY = 'copy'

NAME = 'name'
UNARCHIVED_NAME = 'unarchived_name'

CFLAGS = 'CFLAGS'
CXXFLAGS = 'CXXFLAGS'
DEFAULT_VARS = {'CC' : 'clang', 'CXX' : 'clang++', CFLAGS : '-Os -I' + INSTALL_INCLUDE, CXXFLAGS : '-Os -I' + INSTALL_INCLUDE, 'LDFLAGS' : '-L' + INSTALL_LIB}

# Mots clés pour la configuration.
CONFIG_OPTIONS = 'opts'
CONFIG_VARS = 'vars'
CMAKE_OPTIONS = 'cmakeopts'
COMMANDS = 'cmds'
CUSTOM_CONFIG = 'customconfig'

# Options pour la configuration.
DISABLE_DEPENDENCY_TRACKING = '--disable-dependency-tracking'
ENABLE_STATIC = '--enable-static'
ENABLE_SHARED = '--enable-shared'

# Composants
COMPONENTS = [
    {
        NAME : 'autoconf',
        #CURL : 'https://ftp.gnu.org/gnu/autoconf/autoconf-2.69.tar.xz',
        CURL : 'https://ftp.gnu.org/gnu/autoconf/autoconf-2.71.tar.xz',
    },
    {
        NAME : 'automake',
        #CURL : 'https://ftp.gnu.org/gnu/automake/automake-1.16.2.tar.xz',
        CURL : 'https://ftp.gnu.org/gnu/automake/automake-1.16.4.tar.xz',
    },
    {
        NAME : "pkg-config",
        CURL : "https://pkg-config.freedesktop.org/releases/pkg-config-0.29.2.tar.gz",
        CONFIG_OPTIONS : ["--with-internal-glib"]
    },
    {
        NAME : 'gawk',
        CURL : 'https://ftp.gnu.org/gnu/gawk/gawk-5.1.0.tar.xz',
        CONFIG_OPTIONS : [DISABLE_DEPENDENCY_TRACKING],
    },
    {
        NAME : 'spatialindex',
        #CURL : 'http://download.osgeo.org/libspatialindex/spatialindex-src-1.8.5.tar.bz2',
       #CONFIG_OPTIONS : [DISABLE_DEPENDENCY_TRACKING],
        CURL : 'https://github.com/libspatialindex/libspatialindex/releases/download/1.9.3/spatialindex-src-1.9.3.tar.bz2',
        CMAKE_OPTIONS : []
    },
    {
        NAME : 'openssl',
        CURL : 'https://www.openssl.org/source/openssl-1.1.1k.tar.gz',
        CUSTOM_CONFIG : ['./config', '--prefix=' + INSTALL_DIR, '--openssldir=' + os.path.join(INSTALL_DIR, 'ssl'), 'CFLAGS=-Os -I' + INSTALL_INCLUDE, 'CXXFLAGS=-Os -I' + INSTALL_INCLUDE, 'LDFLAGS=-L' + INSTALL_LIB]
    },
#    {
#        NAME : 'openssl',
#        COMMANDS : [['ln', '-sf', '/usr/lib/libssl.dylib', os.path.join(INSTALL_LIB, 'libssl.dylib')]]
#    },
#    {
#        NAME : 'crypto',
#        COMMANDS : [['ln', '-sf', '/usr/lib/libcrypto.dylib', os.path.join(INSTALL_LIB, 'libcrypto.dylib')]]
#    },
    {
        NAME : 'fftw',
        #CURL : 'ftp://ftp.fftw.org/pub/fftw/fftw-3.3.8.tar.gz',
        CURL : 'ftp://ftp.fftw.org/pub/fftw/fftw-3.3.9.tar.gz',
        CONFIG_OPTIONS : [ENABLE_STATIC, ENABLE_SHARED, DISABLE_DEPENDENCY_TRACKING],
    },
    {
        NAME : 'sqlite',
        CURL : 'https://sqlite.org/2021/sqlite-autoconf-3360000.tar.gz',
        CONFIG_OPTIONS : [DISABLE_DEPENDENCY_TRACKING]
    },
    {
        NAME : 'jpeg',
        CURL : 'http://ijg.org/files/jpegsrc.v9d.tar.gz',
        UNARCHIVED_NAME : 'jpeg-9d',
        CONFIG_OPTIONS : [DISABLE_DEPENDENCY_TRACKING]
    },
    {
        NAME : 'tiff',
        #CURL : 'http://download.osgeo.org/libtiff/tiff-4.1.0.tar.gz',
        #CONFIG_VARS : {'--with-jpeg-lib-dir' : INSTALL_LIB, '--with-jpeg-include-dir' : INSTALL_INCLUDE, CFLAGS : DEFAULT_VARS[CFLAGS] + ' -DHAVE_APPLE_OPENGL_FRAMEWORK', CXXFLAGS : DEFAULT_VARS[CXXFLAGS] + ' -DHAVE_APPLE_OPENGL_FRAMEWORK'},
        #CONFIG_OPTIONS : [DISABLE_DEPENDENCY_TRACKING],
        CURL : 'http://download.osgeo.org/libtiff/tiff-4.3.0.tar.gz',
        CONFIG_VARS : {CFLAGS : DEFAULT_VARS[CFLAGS] + ' -DHAVE_APPLE_OPENGL_FRAMEWORK', CXXFLAGS : DEFAULT_VARS[CXXFLAGS] + ' -DHAVE_APPLE_OPENGL_FRAMEWORK'},
        CMAKE_OPTIONS : ['-DCMAKE_INSTALL_NAME_DIR=' + INSTALL_LIB]
    },
    {
        NAME : 'proj',
        #CURL : 'https://download.osgeo.org/proj/proj-4.9.3.tar.gz',
        CURL : 'http://download.osgeo.org/proj/proj-8.1.0.tar.gz',
        CONFIG_VARS : {'SQLITE3_CFLAGS' : '-I' + INSTALL_INCLUDE, 'SQLITE3_LIBS' : '-L' + INSTALL_LIB + ' -lsqlite3', 'TIFF_CFLAGS' : '-I' + INSTALL_INCLUDE, 'TIFF_LIBS' : '-L' + INSTALL_LIB + ' -ltiff'},  # pour Proj 8 et suivants
        CONFIG_OPTIONS : [DISABLE_DEPENDENCY_TRACKING]
    },
    {
        NAME : 'geotiff',
        #CURL : 'http://download.osgeo.org/geotiff/libgeotiff/libgeotiff-1.4.3.tar.gz',
        #CURL : 'http://download.osgeo.org/geotiff/libgeotiff/libgeotiff-1.6.0.tar.gz', # nécessite Proj 6 minimum
        CURL : 'http://download.osgeo.org/geotiff/libgeotiff/libgeotiff-1.7.0.tar.gz',
        CONFIG_VARS : {'--includedir' : os.path.join(INSTALL_INCLUDE, 'geotiff'), '--with-libtiff' : INSTALL_INCLUDE},
        CONFIG_OPTIONS : [DISABLE_DEPENDENCY_TRACKING]
    },
    {
        NAME : 'png',
        CURL : 'http://prdownloads.sourceforge.net/libpng/libpng-1.6.37.tar.xz',
        CONFIG_OPTIONS : [DISABLE_DEPENDENCY_TRACKING]
    },
    {
        NAME : 'kakadu',
        COPY : os.path.join(SCRIPT_DIR, 'kakadu-6.4.1.zip'),
        COMMANDS : [
            [os.path.join(SCRIPT_DIR, 'build-kakadu.py'), '--sourcedir', os.path.join(SOURCE_DIR, 'kakadu-6.4.1'), '--libdir', INSTALL_LIB, '--bindir', INSTALL_BIN, '--includedir', os.path.join(INSTALL_INCLUDE, 'kakadu')]
        ]
    },
    {
        NAME : 'geos',
        #CURL : 'http://download.osgeo.org/geos/geos-3.8.2.tar.bz2',
        CURL : 'http://download.osgeo.org/geos/geos-3.9.1.tar.bz2',
        CONFIG_OPTIONS : [DISABLE_DEPENDENCY_TRACKING]
    },
    {
        NAME : 'shapelib',
        CURL : 'http://download.osgeo.org/shapelib/shapelib-1.5.0.tar.gz',
        CONFIG_OPTIONS : [DISABLE_DEPENDENCY_TRACKING]
    },
    {
        NAME : 'postgresql',
        #CURL : 'http://ftp.postgresql.org/pub/source/v12.2/postgresql-12.2.tar.bz2'
        CURL : 'https://ftp.postgresql.org/pub/source/v13.3/postgresql-13.3.tar.bz2'
    },
    {
        NAME : 'gdal',
        #CURL : 'http://download.osgeo.org/gdal/2.4.4/gdal-2.4.4.tar.xz',
        #CURL : 'http://download.osgeo.org/gdal/3.0.4/gdal-3.0.4.tar.xz', # nécessite Proj 6 minimum
        #CURL : 'https://github.com/OSGeo/gdal/releases/download/v3.1.3/gdal-3.1.3.tar.gz',
        CURL : 'https://github.com/OSGeo/gdal/releases/download/v3.3.1/gdal-3.3.1.tar.gz',
        CONFIG_VARS : {
            '--with-libtiff' : INSTALL_DIR,
            '--with-geotiff' : INSTALL_DIR,
            #'--with-pg' : os.path.join(INSTALL_BIN, 'pg_config'),
            '--with-pg' : 'yes',
            '--with-geos' : 'yes',
            '--with-python' : 'no',
            '--with-kakadu' : os.path.join(SOURCE_DIR, 'kakadu-6.4.1'),
            #'--with-xml2' : os.path.join(SDK, 'usr', 'bin', 'xml2-config'),
            '--with-xml2' : 'yes',
            CXXFLAGS : DEFAULT_VARS[CXXFLAGS] + ' -I' + os.path.join(INSTALL_INCLUDE, 'geotiff') + ' -DKDU_MAJOR_VERSION=6 -DKDU_MINOR_VERSION=4 -DKDU_PATCH_VERSION=1',
            'PQ_CFLAGS' : '-I' + INSTALL_INCLUDE,
            'PQ_LIBS' : '-L' + INSTALL_LIB + ' -lpq',
            'LIBXML2_CFLAGS' : subprocess.run([os.path.join(SDK, 'usr', 'bin', 'xml2-config'), '--cflags'], stdout=subprocess.PIPE, check=True, encoding='utf-8').stdout.splitlines()[0],
            'LIBXML2_LIBS' : subprocess.run([os.path.join(SDK, 'usr', 'bin', 'xml2-config'), '--libs'], stdout=subprocess.PIPE, check=True, encoding='utf-8').stdout.splitlines()[0]
        }
    }
]


def unarchive(archive_dir, archive_name, destination_dir, unarchived_name=None):
    """Décompactage d'une archive"""
    archive_root, archive_ext = os.path.splitext(archive_name)
    archive_root_split = os.path.splitext(archive_root)
    if archive_root_split[1] == '.tar':
        archive_root = archive_root_split[0]
        archive_ext = archive_root_split[1] + archive_ext
    unarchived_dir = os.path.join(destination_dir, unarchived_name if unarchived_name != None else archive_root)
    if os.path.isdir(unarchived_dir):
        shutil.rmtree(unarchived_dir)
    archive_path = os.path.join(archive_dir, archive_name)
    if archive_ext in ['.tar.gz', '.tar.bz2', '.tar.xz']:
        subprocess.run(['tar', '-C', destination_dir, '-xvf', archive_path], check=True)
    elif archive_ext == '.zip':
        subprocess.run(['unzip', '-o', archive_path, '-d', destination_dir], check=True)
    if os.path.isdir(unarchived_dir):
        os.utime(unarchived_dir, None)
    macosx_dir = os.path.join(destination_dir, '__MACOSX')
    if os.path.isdir(macosx_dir):
        shutil.rmtree(macosx_dir)
    return unarchived_dir


def build_component(component):

    # On se place dans le répertoire racine des sources.
    os.chdir(SOURCE_DIR)

    # Téléchargement et décompactage des sources du composant.
    if CURL in component:
        # On ne télécharge que si nécessaire.
        if not os.path.isfile(os.path.join(SOURCE_DIR, os.path.basename(component[CURL]))):
            # --location permet de récupérer le fichier même si la page a changé de location
            subprocess.run(['curl', '--location', component[CURL], '--remote-name'], check=True)
        # Décompactage de l'archive du composant.
        component_source_dir = unarchive(SOURCE_DIR, os.path.basename(component[CURL]), SOURCE_DIR, component.get(UNARCHIVED_NAME))
    
    # Décompactage d'une archive locale.
    elif COPY in component:
        archive_path_split = os.path.split(component[COPY])
        component_source_dir = unarchive(archive_path_split[0], archive_path_split[1], SOURCE_DIR)

    if CURL in component:
        # On se place dans le répertoire des sources du composant.
        if os.path.isdir(component_source_dir):
            os.chdir(component_source_dir)

    if COMMANDS not in component:

        # Composition de la commande de configuration du composant.

        # CMake : commande de base.
        if CMAKE_OPTIONS in component:
            component_build_dir = os.path.join(component_source_dir, 'cmake_build')
            os.makedirs(component_build_dir)
            os.chdir(component_build_dir)
            cmd = ['cmake', '-GUnix Makefiles', '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_INSTALL_PREFIX=' + INSTALL_DIR]

        elif CUSTOM_CONFIG in component:
            cmd = component[CUSTOM_CONFIG]

        # configure : commande de base
        else:
            cmd = [os.path.join('.', 'configure'), '--prefix', INSTALL_DIR]

        component_has_vars = CONFIG_VARS in component
        # Ajout des variables par défaut.
        for var_key in DEFAULT_VARS.keys():
            if (not component_has_vars) or (var_key not in component[CONFIG_VARS]):
                cmd.append('%s=%s' % (var_key, DEFAULT_VARS[var_key]))
        # Ajout des variables du composant.
        if component_has_vars:
            for var_key in component[CONFIG_VARS]:
                cmd.append('%s=%s' % (var_key, component[CONFIG_VARS][var_key]))

        # CMake : ajout du chemin du source
        if CMAKE_OPTIONS in component:
            cmd += component[CMAKE_OPTIONS]
            cmd.append(component_source_dir)

        # configure : ajout des options de configuration du composant.
        elif CONFIG_OPTIONS in component:
            cmd += component[CONFIG_OPTIONS]

        subprocess.run(cmd, check=True)

        # Compilation et installation.
        subprocess.run(['make', '-j{0:d}'.format(multiprocessing.cpu_count() // 2)], check=True)
        subprocess.run(['make', 'install'], check=True)

    else:
        # Compilation et installation avec les commandes définies spécifiquement dans le composant.
        for cmd in component[COMMANDS]:
            subprocess.run(cmd, check=True)


def main():

    # Récupération des arguments éventuels.
    parser = argparse.ArgumentParser(description="Construction de bibliothèques et d'outils.")
    parser.add_argument('components', metavar='component', nargs='*', help="Composant à compiler. Ne rien préciser pour tout compiler")
    options = parser.parse_args()

    # Création du répertoire des sources si nécessaire.
    if not os.path.isdir(SOURCE_DIR):
        os.makedirs(SOURCE_DIR)

    # Création du répertoire d'installation si nécessaire.
    if not os.path.isdir(INSTALL_DIR):
        os.makedirs(INSTALL_DIR)

    all_components = (len(options.components) == 0)

    # Traitement de tous les composants.
    for component in COMPONENTS:
        if all_components or (component[NAME] in options.components):
            build_component(component)


if __name__ == '__main__':
    main()
