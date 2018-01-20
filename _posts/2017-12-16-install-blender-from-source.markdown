---
layout: post
title: Install Blender from Source
date: 2017-12-16 21:45:08 -0800
categories: 3D Modeling
credits:
  title: Blender Wiki general Linux distro installation instructions
  link: https://wiki.blender.org/index.php/Dev:Doc/Building_Blender/Linux/Generic_Distro/CMake
  title:
  link: https://askubuntu.com/a/568813
---

Make a directory for git downloads and change current working directory there


    mkdir ${HOME}/blender-git
    cd ${HOME}/blender-git


Download updated sources from Blender Git repo


    git clone https://git.blender.org/blender.git
    cd blender
    git submodule update --init --recursive
    git submodule foreach git checkout master
    git submodule foreach git pull --rebase origin master


To update sources in the future, issue the following from the source code root
 directory


    make update


Install or update dependencies


    cd ${HOME}/blender-git
    ./blender/build_files/build_enviroment/install_deps.sh


Compile with CMake


    cd ${HOME}/blender-git/blender
    make -j$(nproc)
    ## make -j2 BUILD_CMAKE_ARGS="-U *SNDFILE* -U *PYTHON* -U *BOOST* -U *Boost* -U *OPENCOLORIO* -U *OPENEXR* -U *OPENIMAGEIO* -U *LLVM* -U *CYCLES* -U *OPENSUBDIV* -U *OPENVDB* -U *COLLADA* -U *FFMPEG* -U *ALEMBIC* -D WITH_CODEC_SNDFILE=ON -D PYTHON_VERSION=3.6 -D PYTHON_ROOT_DIR=/opt/lib/python-3.6 -D WITH_OPENCOLORIO=ON -D OPENCOLORIO_ROOT_DIR=/opt/lib/ocio -D OPENEXR_ROOT_DIR=/opt/lib/openexr -D WITH_OPENIMAGEIO=ON -D OPENIMAGEIO_ROOT_DIR=/opt/lib/oiio -D WITH_CYCLES_OSL=ON -D WITH_LLVM=ON -D LLVM_VERSION=3.4 -D OSL_ROOT_DIR=/opt/lib/osl -D WITH_OPENSUBDIV=ON -D OPENSUBDIV_ROOT_DIR=/opt/lib/osd -D WITH_OPENVDB=ON -D WITH_OPENVDB_BLOSC=ON -D OPENVDB_ROOT_DIR=/opt/lib/openvdb -D WITH_ALEMBIC=ON -D ALEMBIC_ROOT_DIR=/opt/lib/alembic -D WITH_CODEC_FFMPEG=ON -D FFMPEG_LIBRARIES='avformat;avcodec;avutil;avdevice;swscale;swresample;lzma;rt;theora;theoradec;theoraenc;vorbisenc;vorbis;vorbisfile;ogg;x264;openjpeg;openjpeg_JPWL' -D FFMPEG=/opt/lib/ffmpeg"


Create applications short-cut


    sudo cat > /usr/share/applications/blender.desktop <<EOF
    [Desktop Entry]
    Name=Blender-2.79
    GenericName=3D modeller
    Comment=Create and edit 3D models and animations
    Exec=${HOME}/blender-git/build_linux/bin/blender %F
    Icon=${HOME}/blender-git/build_linux/bin/blender.svg
    Terminal=false
    Type=Application
    Categories=Graphics;3DGraphics;
    StartupNotify=False
    MimeType=application/x-blender;
    EOF


In the future to update run the following


    cd ${HOME}/blender-git/blender
    make update
    make


> Note if errors arise try re-running the install_deps.sh script again and
> re-run the above three commands again.


    cd ${HOME}/blender-git
    ./blender/build_files/build_enviroment/install_deps.sh


To run the built software


    ${HOME}/blender-git/build_linux/bin/blender


    #
    #	Adding plug-ins
    #

    ## [File] -> [User Preferences] (Ctrl Alt U)
    ##  [Add-ons]
    ##   Search; "3D Print Toolbox"
    ##   or any other key word, and check the check-box to enable
    ##  [Save User Settings]
