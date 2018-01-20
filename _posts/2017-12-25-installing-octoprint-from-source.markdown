---
layout: post
title: Installing OctoPrint from source
date: 2017-12-25 20:23:59 -0800
categories: 3D-Printing Servers
---


## Adding & locking new user account


    sudo su
    Var_user='octosrv'
    adduser ${Var_user}
    usermod -L ${Var_user}


Append groups `tty` & `dialout` to the new user account


    usermod -a -G tty ${Var_user}
    usermod -a -G dialout ${Var_user}


Install dependencies via `apt-get`


    apt-get update
    apt-get install python-pip python-dev python-setuptools python-virtualenv git libyaml-dev build-essential


## Login to locked user account for source install operations


    su - ${Var_user}
    git clone https://github.com/foosel/OctoPrint.git
    cd OctoPrint
    virtualenv venv
    ./venv/bin/pip install pip --upgrade
    ./venv/bin/python setup.py install
    mkdir ${HOME}/.octoprint


Start the server from within locked user account with the following line


    ${HOME}/OctoPrint/venv/bin/octoprint serve


Or from root via


    su - ${Var_user} '${HOME}/OctoPrint/venv/bin/octoprint serve'


## Updating & re-installing


    su - ${Var_user}
    cd ${HOME}/OctoPrint
    git pull
    ./venv/bin/python setup.py clean
    ./venv/bin/python setup.py install


## Resources

- [Setup-on-a-Raspberry-Pi-running-Raspbian](https://github.com/foosel/OctoPrint/wiki/Setup-on-a-Raspberry-Pi-running-Raspbian)
