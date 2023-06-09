# ----------------------------------------------------------------------------
# -                        Open3D: www.open3d.org                            -
# ----------------------------------------------------------------------------
# The MIT License (MIT)
#
# Copyright (c) 2018-2021 www.open3d.org
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
# ----------------------------------------------------------------------------

# examples/python/reconstruction_system/sensors/realsense_pcd_openvino_pointpillar_visualizer.py

# pyrealsense2 is required.
# Please see instructions in https://github.com/IntelRealSense/librealsense/tree/master/wrappers/python
import pyrealsense2 as rs
import numpy as np
from enum import IntEnum

from datetime import datetime
import open3d as o3d

from os.path import abspath
import sys
sys.path.append(abspath(__file__))
from realsense_helper import get_profiles

import os

# OpenML/OpenVINO for 3D OD (starting w/ Point Pillar)
import open3d.ml.torch as ml3d
import torch
from open3d.ml.utils import Config
#

class Preset(IntEnum):
    Custom = 0
    Default = 1
    Hand = 2
    HighAccuracy = 3
    HighDensity = 4
    MediumDensity = 5


def get_intrinsic_matrix(frame):
    intrinsics = frame.profile.as_video_stream_profile().intrinsics
    out = o3d.camera.PinholeCameraIntrinsic(640, 480, intrinsics.fx,
                                            intrinsics.fy, intrinsics.ppx,
                                            intrinsics.ppy)
    return out


if __name__ == "__main__":

    # Point Pillar 3D OD download 
    ckpt_folder = "./3dmodels/"
    os.makedirs(ckpt_folder, exist_ok=True)
    ckpt_path = ckpt_folder +  "pointpillars_kitti_202012221652utc.pth"
    pointpillar_url = "https://storage.googleapis.com/open3d-releases/model-zoo/pointpillars_kitti_202012221652utc.pth"
    
    if not os.path.exists(ckpt_path):
        cmd = "wget {} -O {}".format(pointpillar_url, ckpt_path)
        os.system(cmd)

    # Create a pipeline
    pipeline = rs.pipeline()

    #Create a config and configure the pipeline to stream
    #  different resolutions of color and depth streams
    config = rs.config()

    color_profiles, depth_profiles = get_profiles()

    print("----")
    i = 0
    for p in color_profiles:     
     print(str(i) + " " + str(p))
     i = i + 1
    print("")
    i = 0
    for p in depth_profiles:
        print(str(i) + str(p))  
        i = i + 1  
    print("----")

    # http://www.open3d.org/docs/release/tutorial/sensor/realsense.html : States 
    # "Open3D only supports synchronized color and depth capture (color_fps = depth_fps)." 
    # so using 640x480@60 for now...
    print('Using the color == depth profiles: \n  color:{}, depth:{}'.format(
        color_profiles[84], depth_profiles[11]))
    w, h, fps, fmt = depth_profiles[11]
    config.enable_stream(rs.stream.depth, w, h, fmt, fps)
    w, h, fps, fmt = color_profiles[84]
    config.enable_stream(rs.stream.color, w, h, fmt, fps)
    #quit()

    # Start streaming
    profile = pipeline.start(config)
    depth_sensor = profile.get_device().first_depth_sensor()

    # Using preset HighAccuracy for recording
    depth_sensor.set_option(rs.option.visual_preset, Preset.HighAccuracy)

    # Getting the depth sensor's depth scale (see rs-align example for explanation)
    depth_scale = depth_sensor.get_depth_scale()
    print("Depth scale is: " + str(depth_scale))

    # We will not display the background of objects more than
    #  clipping_distance_in_meters meters away
    clipping_distance_in_meters = 3  # 3 meter
    clipping_distance = clipping_distance_in_meters / depth_scale
    print("Clip distance in meter: " + str(clipping_distance))
    #quit()


    # Create an align object
    # rs.align allows us to perform alignment of depth frames to others frames
    # The "align_to" is the stream type to which we plan to align depth frames.
    align_to = rs.stream.color
    align = rs.align(align_to)

    vis = o3d.visualization.Visualizer()
    vis.create_window()

    pcd = o3d.geometry.PointCloud()
    
    # uncomment to view render results
    #flip_transform = [[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 0], [0, 0, 0, 1]]

    # Streaming loop
    frame_count = 0
    try:
        while True:

            dt0 = datetime.now()

            # Get frameset of color and depth
            frames = pipeline.wait_for_frames()

            # Align the depth frame to color frame
            aligned_frames = align.process(frames)

            # Get aligned frames
            aligned_depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()
            intrinsic = o3d.camera.PinholeCameraIntrinsic(
                get_intrinsic_matrix(color_frame))

            # Validate that both frames are valid
            if not aligned_depth_frame or not color_frame:
                continue

            depth_image = o3d.geometry.Image(np.array(aligned_depth_frame.get_data()))
            color_image = o3d.geometry.Image(np.asarray(color_frame.get_data()))

            rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(
                color_image,
                depth_image,
                depth_scale=1.0 / depth_scale,
                depth_trunc=clipping_distance_in_meters,
                convert_rgb_to_intensity=False)
            
            temp = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd_image, intrinsic)
            
            # Uncomment to render right-side up 
            #temp.transform(flip_transform)

            pcd.points = temp.points
            pcd.colors = temp.colors

            #################3D Point Pillar Inference Using OpenVINO ##############
            xpu_device = 'cpu'
            cfg_path = '3dmodels/pointpillars_kitti.yml'
            cfg = Config.load_from_file(cfg_path)
            net =  ml3d.models.PointPillars(**cfg.model, device=xpu_device)
            net = ml3d.models.OpenVINOModel(net)
            # TODO: Needs clDNNPlugin.so for GPU
            #net.to("gpu")
            
            npy_pcd = np.asarray(pcd.points)            
            #print(npy_pcd.shape)
            shp = np.shape(npy_pcd)
            tmp = np.ones((shp[0],4))
            tmp[:,:-1] = npy_pcd
            #print(tmp)
            
            data = {
                'point': tmp,
                'calib': None,
                'bounding_boxes': [],
            }
            
            
            batcher = ml3d.dataloaders.ConcatBatcher('cpu', model='PointPillars')
            #print("preprocess")
            data = net.preprocess(data, {'split': 'val'})
            #data = net.preprocess(data, {'split': 'test'})
            #print(data)
            #print("transform")
            data = net.transform(data, {'split': 'val'})
            #data = net.transform(data, {'split': 'test'})
            #print(data)
            #print("Batcher")
            data = batcher.collate_fn([{'data': data, 'attr': {'split': 'val'}}])
            #print(data.point)
            net.eval()
            #print("------------->Data sent for infer: " + str(data.point))

            #with torch.no_grad():
            #results = net(data)
            #boxes = net.inference_end(results, data)
            #assert type(boxes) == list
            #print("Bounding Boxes (results): " + str(boxes))

            # uncomment to show render 
            #if frame_count == 0:
            #    vis.add_geometry(pcd)

            # uncomment to show render
            #vis.update_geometry(pcd)
            vis.poll_events()
            # uncomment to show render
            #vis.update_renderer()

            process_time = datetime.now() - dt0
            print("\rFPS: " + str(1 / process_time.total_seconds()), end='')
            frame_count += 1

    finally:
        pipeline.stop()
    vis.destroy_window()
