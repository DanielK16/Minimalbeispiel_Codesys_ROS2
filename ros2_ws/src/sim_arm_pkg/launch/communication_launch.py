import os
import yaml
from launch import LaunchDescription

from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder

def load_yaml(package_name, file_path):
    """Hilfsfunktion zum Laden von YAML-Dateien aus einem ROS 2 Paket."""
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)
    with open(absolute_file_path, "r") as file:
        return yaml.safe_load(file)

def generate_launch_description():

    # moveit_config = MoveItConfigsBuilder(
    #     robot_name="firefighter", 
    #     package_name="mycobot_280arduino_moveit2"
    # ).to_moveit_configs()

    # moveit_py_config = load_yaml("mycobot_280arduino_moveit2", "config/moveit_py.yaml")

    return LaunchDescription([

        # Transformation von parent -> child
        Node(
            package = 'sim_arm_pkg',
            executable = 'tcp_pose',
            name = 'tcp_node'
        ),

        Node(
            package = 'sim_arm_pkg',
            executable = 'status_client',
            name = 'status_client_node'
        ),

        Node(
            package = 'sim_arm_pkg',
            executable = 'command_client',
            name = 'command_client_node'
        ),

        # Node(
        #     package = 'sim_arm_pkg',
        #     executable = 'action_client_moveitpy',
        #     name = 'action_client_node',
        #     parameters=[
        #         moveit_config.to_dict(),
        #         moveit_py_config
        #     ],
        #     ros_arguments=['--log-level', 'moveit_ros:=warn', '--log-level', 'moveit_ros_planning:=warn', '--log-level', 'moveit:=warn'],
        # ),

        Node(
            package = 'sim_arm_pkg',
            executable = 'action_client',
            name = 'action_client_node',
        ),
    ])