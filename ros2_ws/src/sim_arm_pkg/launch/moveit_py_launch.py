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
    # 1. MoveIt-Konfiguration für den Roboter laden
    moveit_config = MoveItConfigsBuilder(
        robot_name="firefighter", 
        package_name="mycobot_280arduino_moveit2"
    ).to_moveit_configs()

    # 2. Spezifische MoveItPy-YAML laden
    moveit_py_config = load_yaml("mycobot_280arduino_moveit2", "config/moveit_py.yaml")

    return LaunchDescription([
        # Der Action-Client, der OPC UA liest und ÜBER MOVEIT_PY steuert!
        # Er bekommt hier die vollen MoveIt- und MoveItPy-Parameter übergeben.
        Node(
            package='sim_arm_pkg',
            executable='action_client_moveitpy',
            name='action_client_moveitpy',
            parameters=[
                moveit_config.to_dict(),
                moveit_py_config
            ],
            output='screen'
        ),
    ])