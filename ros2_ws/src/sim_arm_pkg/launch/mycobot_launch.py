import os
import yaml
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_demo_launch

def load_yaml(package_name, file_path):
    """Hilfsfunktion zum Laden von YAML-Dateien aus einem ROS 2 Paket."""
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)
    with open(absolute_file_path, "r") as file:
        return yaml.safe_load(file)

def generate_launch_description():
    # 1. MoveIt Konfiguration laden 
    moveit_config = MoveItConfigsBuilder(
        robot_name="firefighter", 
        package_name="mycobot_280arduino_moveit2"
    ).to_moveit_configs()

    # 2. Die servo.yaml Konfiguration laden
    servo_yaml = load_yaml("sim_arm_pkg", "config/servo.yml")
    servo_params = {"moveit_servo": servo_yaml}

    # 3. Den Servo-Knoten definieren
    servo_node = Node(
        package="moveit_servo",
        executable="servo_node_main",
        parameters=[
            servo_params,
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
        ],
        output="screen",
    )

    # 4. Standard MoveIt Demo-Launch generieren (startet move_group, rviz, robot_state_publisher etc.)
    demo_launch_description = generate_demo_launch(moveit_config)

    # 5. Deinen Servo-Node zur gemeinsamen Launch-Beschreibung hinzufügen
    demo_launch_description.add_action(servo_node)

    return demo_launch_description