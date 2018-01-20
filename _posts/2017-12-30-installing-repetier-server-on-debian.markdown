---
layout: post
title: Installing Repetier Server on Debian
date: 2017-12-30 16:37:21 -0800
categories: 3D Printing Server
---

Download the [Repetier Server][Repetier-Server-Download]

Issue the following `dpkg` command, substituting the file path and version for
 the one downloaded


    sudo dpkg -i ${HOME}/Downloads/Repetier-Server-0.86.2-Linux.deb


Provided that there where no errors during install the following commands maybe
 issued to start or star the server


    sudo service RepetierServer start
    sudo service RepetierServer stop


To disable auto-starting of service at boot time


    sudo systemctl enable RepetierServer.service
    sudo systemctl disable RepetierServer.service


See the very well written [Repetier Server Manuals][Repetier-Server-Manuals]
 from the server software's development team for steps on configuration steps.


[Repetier-Server-Download]: https://www.repetier-server.com/download-repetier-server/
[Repetier-Server-Manuals]: https://www.repetier-server.com/documentation/
