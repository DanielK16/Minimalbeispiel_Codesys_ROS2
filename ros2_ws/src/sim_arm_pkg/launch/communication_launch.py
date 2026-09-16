from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([

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

        Node(
            package = 'sim_arm_pkg',
            executable = 'action_client',
            name = 'action_client_node'
        ),
    ])