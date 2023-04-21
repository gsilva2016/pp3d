# Open3d Object Detection (Point Pillars) 


This sample chooses a Realsense color and depth profile which are equal (resolution+fps) and converts the color and depth frames to RGBD. The PCD is then created from RGBD image and a 4th column (harcoded to value equal to 1) is appended to satisfy inference input need. The inference is performed using OpenVINO backend (presumably).

Note: Remove all references to "uncomment" to view render results in Visualizer. Several lines were commented out to understand if Visualizer was taking significant time to render 3D scene. Note that this code does not show significant difference with/without render at least on KBL.
