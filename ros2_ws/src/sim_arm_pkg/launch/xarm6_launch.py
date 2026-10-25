#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Basis-Parameter
    dof = LaunchConfiguration('dof', default='6')
    robot_type = LaunchConfiguration('robot_type', default='xarm')
    hw_ns = LaunchConfiguration('hw_ns', default='xarm')

    # 1. BASIS: Der normale Fake Launch
    # Startet die simulierte Hardware, den 'move_group' (Motion Planner) und RViz2.
    # Dadurch ist das MotionPlanning Plugin in RViz sofort voll einsatzbereit.
    robot_moveit_fake_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('xarm_moveit_config'), 'launch', '_robot_moveit_fake.launch.py'
        ])),
        launch_arguments={
            'dof': dof,
            'robot_type': robot_type,
            'hw_ns': hw_ns,
            'no_gui_ctrl': 'true',
        }.items(),
    )

    # 2. ERWEITERUNG: Nur den Servo Node hinzufügen
    # xArm bündelt den reinen Servo-Algorithmus (ohne Hardware/RViz) in '_robot_moveit_servo.launch.py'.
    # Wir fügen diesen in die bereits laufende Fake-Umgebung ein.
    robot_servo_node_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('xarm_moveit_servo'), 'launch', '_robot_moveit_servo.launch.py'
        ])),
        launch_arguments={
            'dof': dof,
            'robot_type': robot_type,
            'hw_ns': hw_ns,
        }.items(),
    )
    
    return LaunchDescription([
        robot_moveit_fake_launch,
        robot_servo_node_launch,
    ])