#!/bin/bash

docker run -it --gpus all --privileged -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix --ipc host --network host -v `pwd`:/savedir o3d:1.0
