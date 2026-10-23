# Übersicht um Docker Container und Images zu bauen/starten
## My Cobot 280 Simulation
### myCobot Image
```
docker build -t mycobot_sim_img --build-arg ROS_DISTRO=humble .
```

### myCobot Container
```
docker run -it \
  --name mycobot_sim \
  --user ros \
  --hostname ros_container \
  --network=host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v ~/Minimalbeispiel_Codesys_ROS2/ros2_ws:/home/ros/ros2_ws \
  -w /home/ros/ros2_ws \
  my_cobot_sim_img:latest \
```

## TB4 Real
### TB4 Real Image
```
docker build -t tb4_real_img --build-arg ROS_DISTRO=humble -f tb4_dockerfile_real .
```
### TB4 Real Container
```
docker run -it \
    --name tb4_real \
    --user ros \
    --hostname ros_container \
    --network=host \
    --ipc=host \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -w /home/ros/ros2_ws \
    tb4_real_img:latest
```

### Zenoh Container
```
docker run -d \
    --name zenoh_client \
    --network=host \
    eclipse/zenoh:latest \
    --listener tcp/192.168.2.189:7447
```

## TB4 Simulation
### TB4 Simulation Image
```
docker build -t tb4_sim_img --build-arg ROS_DISTRO=jazzy -f tb4_dockerfile_sim .
```
### TB4 Simulation Container
```
docker run -it \
    --name tb4_sim \
    --user ros \
    --hostname ros_container \
    --network=host \
    --ipc=host \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -w /home/ros/ros2_ws \
    tb4_sim_img:latest
```