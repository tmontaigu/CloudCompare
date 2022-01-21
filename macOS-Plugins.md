## Optional features and plugins

The optional features are:

|     CMake Option      | Default Value | Description 
|-----------------------|---------------|-------------
| OPTION_BUILD_CCVIEWER |      ON       | Whether or not to build the ccViewer side project.
| OPTION_USE_SHAPE_LIB  |      ON       | Use the vendored shapelib to add support for SHP files.
| OPTION_USE_DXF_LIB    |      ON       | Use the vendored dxflib to add support for DXF files.
| OPTION_USE_GDAL       |      ON       | Add support for a lot of raster files in CloudCompare/ccViewer with **GDAL** library.

The available plugins are

## GL Plugins

|       Plugin Name       |         CMake Option                     | Default Value | Description
|-------------------------|------------------------------------------|---------------|-------------
| qEDL                    | PLUGIN_GL_QEDL                           | ON            |
| qSSAO                   | PLUGIN_GL_QSSAO                          | ON            |

## IO Plugins

|       Plugin Name       |         CMake Option                     | Default Value | Description
|-------------------------|------------------------------------------|---------------|-------------
| qCoreIO                 | PLUGIN_IO_QCORE                          | ON            |
| qAdditionalIO           | PLUGIN_IO_QADDITIONAL                    | ON            |
| qCSVMatrixIO            | PLUGIN_IO_QCSV_MATRIX                    | ON            | Add support for CSV matrix files.
| qDraco                  | PLUGIN_IO_QDRACO                         | OFF           | Add support force draco files
| qE57IO                  | PLUGIN_IO_QE57                           | ON            | Add support for e57 files using **libE57**.
| qFBXIO                  | PLUGIN_IO_QFBX                           | OFF           | Add support for AutoDesk FBX files using the official **FBX SDK**
| qLASFWIO                | PLUGIN_IO_QLAS_FWF                       | OFF           | Windows only. Support for LAS/LAZ with and without waveform.
| qPDALIO                 | PLUGIN_IO_QPDAL                          | ON           | Add support for LAS/LAZ files using **PDAL**.
| qPhotoscanIO            | PLUGIN_IO_QPHOTOSCAN                     | ON           | 
| qRDBIO                  | PLUGIN_IO_QRDB                           | OFF           | Add support for RDB.
| qStepCADImport          | PLUGIN_IO_QSTEP                          | OFF           | Add support for STEP files.

## Standard Plugins

|       Plugin Name       |         CMake Option                     | Default Value | Description
|-------------------------|------------------------------------------|---------------|-------------
| qAnimation              | PLUGIN_STANDARD_QANIMATION               | ON            | Plugin to create videos.
| qBroom                  | PLUGIN_STANDARD_QBROOM                   | ON            |
| qCanupo                 | PLUGIN_STANDARD_QCANUPO                  | ON           |
| qColorimetricSegmenter  | PLUGIN_STANDARD_QCOLORIMETRIC_SEGMENTER  | ON            |
| qCompass                | PLUGIN_STANDARD_QCOMPASS                 | ON            |
| qCork                   | PLUGIN_STANDARD_QCORK                    | OFF           |
| qCSF                    | PLUGIN_STANDARD_QCSF                     | ON            |
| qFacets                 | PLUGIN_STANDARD_QFACETS                  | ON            |
| qHoughNormals           | PLUGIN_STANDARD_QHOUGH_NORMALS           | ON            |
| qHPR                    | PLUGIN_STANDARD_QHPR                     | ON            |
| qJSonRPCPlugin          | PLUGIN_STANDARD_QJSONRPC                 | OFF           |
| qM3C2                   | PLUGIN_STANDARD_QM3C2                    | ON            |
| qMPlane                 | PLUGIN_STANDARD_QMPLANE                  | ON            |
| qPCL                    | PLUGIN_STANDARD_QPCL                     | ON            |
| qPCV                    | PLUGIN_STANDARD_QPCV                     | ON            |
| qPoissonRecon           | PLUGIN_STANDARD_QPOISSON_RECON           | ON            |
| qRANSAC_SD              | PLUGIN_STANDARD_QRANSAC_SD               | ON            |
| qSRA                    | PLUGIN_STANDARD_QSRA                     | ON            |
| qAutoSeg                | PLUGIN_STANDARD_MASONRY_QAUTO_SEG        | OFF           |
| qManualSeg              | PLUGIN_STANDARD_MASONRY_QMANUAL_SEG      | OFF           |

## Additional Instructions

Some plugins do not have their dependencies vendored in CloudCompare's repo, thus they require additional steps
to install them. This section aims to document the steps for these plugins.

### qAnimation

The qAnimation plugin has an additional option `QANIMATION_WITH_FFMPEG_SUPPORT` to be able to create
movies with FFMPEG.

### qE57IO

If you want to compile CloudCompare (and ccViewer) with LibE57 files support, you'll need:

1. [Xerces-C++](http://xerces.apache.org/xerces-c) multi-thread **static** libraries
    - On Ubuntu install the package `libxerces-c-dev`
    - On Visual C++ (Windows):
        1. select the `Static Debug` or `Static Release` configurations
        2. you'll have to manually modify the `XercesLib` project options so that
           the `C/C++ > Code Generation > Runtime Library` are of DLL type in both release and debug modes (i.e. `/MD`
           in release or `/MDd` in debug)
        3. for 64 bits version be sure to select the right platform (x64 instead of Win32). If you use Visual Studio
           Express 2010, be sure also that the `toolset` (in the project properties) is set to something
           like `Windows7.1SDK`
    - only the XercesLib project neet to be compiled
    - eventually, CMake will look for the resulting files in `/include` (instead of `/src`) and `/lib` (without the
      Release or Debug subfolders). By default the visual project will put them in `/Build/WinXX/VCXX/StaticXXX`.
      Therefore you should create a custom folder with the right organization and copy the files there.

2. [LibE57](https://github.com/asmaloney/libE57Format) (*last tested version: 2.0.1 on Windows*)
    - Checkout the submodule in `plugins/core/IO/qE57IO/extern/libE57Format` or download and extract the
      latest [libE57Format](https://github.com/asmaloney/libE57Format) release

### qPCL

qPCL relies on the PCL library. Follow the instructions from their website [PCL](http://pointclouds.org/).

### qFBXIO

If you want to compile CloudCompare (and ccViewer) with FBX files support, you'll need: The
official [Autodesk's FBX SDK](http://usa.autodesk.com/adsk/servlet/pc/item?siteID=123112&id=10775847) (last tested
version: 2015.1 on Windows)

Then, the CloudCompare CMake project will request that you set the 3 following variables:

1. `FBX_SDK_INCLUDE_DIR`: FBX SDK include directory (pretty straightforward ;)
2. `FBX_SDK_LIBRARY_FILE`: main FBX SDK library (e.g. `libfbxsdk-md.lib`)
3. `FBX_SDK_LIBRARY_FILE_DEBUG`: main FBX SDK library for debug mode (if any)

### qPDALIO

If you want to compile CloudCompare (and ccViewer) with LAS/LAZ files support,
you'll need [PDAL](https://pdal.io/).


### GDAL support

If you want to compile CloudCompare (and ccViewer) with GDAL (raster) files support, you'll need a compiled version of
the [GDAL library](http://www.gdal.org/) (last tested version: 1.10 on Windows, 2.0.2 on Mac OS X)

Then, the CloudCompare CMake project will request that you set the 2 following variables:

1. `GDAL_INCLUDE_DIR`: GDAL include directory (pretty straightforward ;)
2. `GDAL_LIBRARY`: the static library (e.g. `gdal_i.lib`)

### qCork + MPIR support

If you want to compile the qCork plugin (**on Windows only for now**), you'll need:

1. [MPIR 2.6.0](http://www.mpir.org/)
2. the forked version of the Cork library for
   CC: [<https://github.com/cloudcompare/cork>](https://github.com/cloudcompare/cork)
    - on Windows see the Visual project shipped with this fork and corresponding to your version (if any ;)
    - for VS2013 just edit the `mpir` property sheet (in the Properties manager) and update the MPIR macro (in
      the `User macros` tab)

Then, the CloudCompare CMake project will request that you set the following variables:

1. `CORK_INCLUDE_DIR` and `MPIR_INCLUDE_DIR`: both libraries include directories (pretty straightforward ;)
2. `CORK_RELEASE_LIBRARY_FILE` and `MPIR_RELEASE_LIBRARY_FILE`: both main library files
3. and optionally `CORK_DEBUG_LIBRARY_FILE` and `MPIR_DEBUG_LIBRARY_FILE`: both main library files (for debug mode)

4. Make sure you have a C++11 compliant compiler (gcc 4.7+ / clang / Visual 2013 and newer)

*To compile the project with older versions of Qt (from 4.8 to 5.4) or with a non C++11 compliant compiler, you'll have to stick with the https://github.com/cloudcompare/CloudCompare/releases/tag/v2.6.3.1 version*


5.  Last but not least, the `CMAKE` group contains a `CMAKE_INSTALL_PREFIX` variable which is where CloudCompare and ccViewer will be installed (when you compile the `INSTALL` project)
  - On Linux, default install dir is `/usr/local` (be sure to have administrative rights if you want to install CloudCompare there: once configured, you can call `# make install` from the sources directory)
  - On Windows 7/8/10 CMake doesn't have the rights to 'install' files in the `Program Files` folder (even though it's CMake's default installation destination!)


# Other things 

## macOs

If you are compiling and running locally, add `-DCC_MAC_DEV_PATHS` to the `CMAKE_CXX_FLAGS` in the `CMAKE` group. This
will look for the plugins in your build directory rather than the application bundle. If you need the shaders as well,
you will have to create a `shaders` folder in the build directory and copy the shaders you need into it.

## Working with Visual Studio on Windows

As all the files (executables, plugins and other DLLs) are copied in the `CMAKE_INSTALL_PREFIX` directory, the standard project launch/debug mechanism is broken.
Therefore, by default you won't be able to 'run' the CloudCompare or ccViewer projects as is (with F5 or Ctrl + F5 for instance).
See [this post](http://www.danielgm.net/cc/forum/viewtopic.php?t=992) on the forum to setup Visual correctly.

## Debugging plugins

If you want to use or debug plugins in DEBUG mode while using a single configuration compiler/IDE (gcc, etc.) the you'll have to comment the automatic definition of the `QT_NO_DEBUG` macro in '/plugins/CMakePluginTpl.cmake' (see http://www.cloudcompare.org/forum/viewtopic.php?t=2070).
