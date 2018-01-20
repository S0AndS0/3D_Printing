---
layout: post
title: OctoPrint Webcam Setup
date: 2018-01-08 05:04:25 -0800
categories: 3D-Printing Servers Webcams
---


Install some dependencies via `apt-get`


    sudo apt-get install subversion libjpeg62-turbo-dev imagemagick libav-tools libv4l-dev cmake


Add the user you wish server streaming services under to the video group


    sudo usermod -a -G video user-name


Make a directory for GitHub sources (if necessary) & `cd` there


    mkdir -p ${HOME}/GitHub
    cd ${HOME}/GitHub


Download source files for `mjpg-streamer` & `cd` to the project root directory


    git clone https://github.com/jacksonliam/mjpg-streamer.git
    cd mjpg-streamer/mjpg-streamer-experimental/


Install via `make` with a prefixing environment variable


    LD_LIBRARY_PATH=. make -j$(nproc)


Provided there where no errors, the server maybe started via the following


    # From the current directory
    ./mjpg_streamer -i "./input_uvc.so" -o "./output_http.so"
    # From any directory, eg a script
    #${HOME}/GitHub/mjpg-streamer/mjpg-streamer.git-esperimental\
    # -i "${HOME}/GitHub/mjpg-streamer/mjpg-streamer.git-esperimental/input_uvc.so"
    # -o "${HOME}/GitHub/mjpg-streamer/mjpg-streamer.git-esperimental/output_http.so"


To define a listen address & port


    ./mjpg_streamer -i './input_uvc.so' -o './output_http.so -p 8090 -l localhost'


Pointing a web browser at `http://localhost:8080/?action=stream` substitute `localhost`
 for the server's IP or domain address *should* result in a low frame rate stream
 of what that device's webcam is capable of seeing


## Adding webcam view within OctoPrint web user interface


Append the following to `${HOME}/.octoprint/config.yml`


    webcam:
        stream: http://192.168.96.107:8080/?action=stream
        snapshot: http://192.168.96.107:8080/?action=snapshot
        ffmpeg: /usr/bin/ffmpeg


## Sources of information


- [Wiki - Setup on a Raspberry Pi running Raspbian](https://github.com/foosel/OctoPrint/wiki/Setup-on-a-Raspberry-Pi-running-Raspbian)
