#FROM nvcr.io/nvidia/deepstream:6.1.1-devel
#FROM nvidia/cuda:11.7.1-cudnn8-devel-ubuntu20.04
#FROM nvidia/cuda:10.1-cudnn8-devel-ubuntu18.04
#FROM ros:noetic-ros-core-focal
FROM tensorflow/tensorflow:latest-gpu

COPY src/ /3dsrc

RUN apt update -y || true; DEBIAN_FRONTEND=noninteractive apt install -y wget python3 python3-dev python3-pip curl vim gpg-agent \
    lsb-release \
    build-essential \
    autoconf \
    git \
    libssl-dev \
    libusb-1.0-0-dev \
    libudev-dev \
    pkg-config \
    libgtk-3-dev \
    libglfw3-dev \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    libgl1-mesa-glx \
    nasm \
    ninja-build \
    cmake  \
    python3  \
    python3-pip  \
    python3-dev \
    meson \
    flex \
    bison && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Upgrade meson as the gstreamer needs later version
RUN python3 -m pip install --upgrade pip
RUN echo "upgrading meson to the latest version..." && pip3 install --user meson --upgrade
RUN pip3 install \
	opencv-python \
   	numpy \
        scipy \
        matplotlib \
        Cython setuptools pybind11 \
        scikit-image numba pillow \
	open3d 

RUN mkdir -p /o3d; cd o3d; git clone https://github.com/isl-org/Open3D-ML.git; git clone https://github.com/isl-org/Open3D.git
RUN cd /o3d/Open3D-ML; pip3 install -r requirements-tensorflow.txt; pip3 install -r requirements-torch.txt; pip3 install -r requirements-torch-cuda.txt

RUN pip3 install pyrealsense2
RUN mkdir -p /rs && cd /rs && git clone https://github.com/IntelRealSense/librealsense.git

RUN cd /rs/librealsense && mkdir build && \
    cd build/ && \
    cmake ../ \
        -DBUILD_SHARED_LIBS=true \
        -DBUILD_WITH_JPEGTURBO=true \
        -DBUILD_PYTHON_BINDINGS:bool=true \
        -DBUILD_WITH_CUDA=false \
        -DFORCE_RSUSB_BACKEND=false \
        -DPYTHON_EXECUTABLE=/usr/bin/python3 \
        -DBUILD_GLSL_EXTENSIONS=true \
        -DBUILD_WITH_CPU_EXTENSIONS=true \
        -DBUILD_UNIT_TESTS=false \
        -DBUILD_GRAPHICAL_EXAMPLES=true \
        -DBUILD_NETWORK_DEVICE=true \
        -DCMAKE_BUILD_TYPE=Release && \
    make -j$(cat /proc/cpuinfo |grep -c proc) && \
    make install && \
    export PYTHONPATH="$PYTHONPATH":/usr/lib/python3/dist-packages/pyrealsense2 && \
    python3 -c "import pyrealsense2 as rs; print(rs)"

COPY src/realsense_pcd_openvino_pointpillar.py /o3d/Open3D/examples/python/reconstruction_system/sensors/

SHELL ["/bin/bash", "-c"] 
WORKDIR /o3d/Open3D/examples/python/reconstruction_system/sensors/
