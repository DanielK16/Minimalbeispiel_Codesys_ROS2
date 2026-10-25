# Diese file wurde mit Künstlicher Intelligenz (Gemini) erstellt aufgrund von Zeitgründen
# Kombinierter Launch für xArm6: MoveIt 2 Bahnplanung & MoveIt Servo (Fake Hardware)

import os
import yaml
from ament_index_python import get_package_share_directory
from launch import LaunchDescription
from launch.actions import OpaqueFunction, IncludeLaunchDescription, RegisterEventHandler
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from launch.event_handlers import OnProcessExit
from uf_ros_lib.moveit_configs_builder import MoveItConfigsBuilder
from uf_ros_lib.uf_robot_utils import load_yaml, generate_ros2_control_params_temp_file

def launch_setup(context, *args, **kwargs):
    # Basis-Konfigurationen
    dof = LaunchConfiguration('dof', default=6)
    robot_type = LaunchConfiguration('robot_type', default='xarm')
    prefix = LaunchConfiguration('prefix', default='')
    hw_ns = LaunchConfiguration('hw_ns', default='xarm')
    limited = LaunchConfiguration('limited', default=True)
    effort_control = LaunchConfiguration('effort_control', default=False)
    velocity_control = LaunchConfiguration('velocity_control', default=False)
    model1300 = LaunchConfiguration('model1300', default=False)
    robot_sn = LaunchConfiguration('robot_sn', default='')
    attach_to = LaunchConfiguration('attach_to', default='world')
    attach_xyz = LaunchConfiguration('attach_xyz', default='"0 0 0"')
    attach_rpy = LaunchConfiguration('attach_rpy', default='"0 0 0"')
    mesh_suffix = LaunchConfiguration('mesh_suffix', default='stl')
    kinematics_suffix = LaunchConfiguration('kinematics_suffix', default='')
    gripper_version = LaunchConfiguration('gripper_version', default='G1')
    
    add_gripper = LaunchConfiguration('add_gripper', default=False)
    add_vacuum_gripper = LaunchConfiguration('add_vacuum_gripper', default=False)
    add_bio_gripper = LaunchConfiguration('add_bio_gripper', default=False)
    add_realsense_d435i = LaunchConfiguration('add_realsense_d435i', default=False)
    add_d435i_links = LaunchConfiguration('add_d435i_links', default=True)
    add_other_geometry = LaunchConfiguration('add_other_geometry', default=False)
    geometry_type = LaunchConfiguration('geometry_type', default='box')
    geometry_mass = LaunchConfiguration('geometry_mass', default=0.1)
    geometry_height = LaunchConfiguration('geometry_height', default=0.1)
    geometry_radius = LaunchConfiguration('geometry_radius', default=0.1)
    geometry_length = LaunchConfiguration('geometry_length', default=0.1)
    geometry_width = LaunchConfiguration('geometry_width', default=0.1)
    geometry_mesh_filename = LaunchConfiguration('geometry_mesh_filename', default='')
    geometry_mesh_origin_xyz = LaunchConfiguration('geometry_mesh_origin_xyz', default='"0 0 0"')
    geometry_mesh_origin_rpy = LaunchConfiguration('geometry_mesh_origin_rpy', default='"0 0 0"')
    geometry_mesh_tcp_xyz = LaunchConfiguration('geometry_mesh_tcp_xyz', default='"0 0 0"')
    geometry_mesh_tcp_rpy = LaunchConfiguration('geometry_mesh_tcp_rpy', default='"0 0 0"')

    joystick_type = LaunchConfiguration('joystick_type', default=1)
    ros_namespace = LaunchConfiguration('ros_namespace', default='').perform(context)

    ros2_control_plugin = 'uf_robot_hardware/UFRobotFakeSystemHardware'
    controllers_name = 'fake_controllers'
    xarm_type = '{}{}'.format(robot_type.perform(context), dof.perform(context))

    ros2_control_params = generate_ros2_control_params_temp_file(
        os.path.join(get_package_share_directory('xarm_controller'), 'config', '{}_controllers.yaml'.format(xarm_type)),
        prefix=prefix.perform(context), 
        add_gripper=add_gripper.perform(context) in ('True', 'true'),
        add_bio_gripper=add_bio_gripper.perform(context) in ('True', 'true'),
        ros_namespace=ros_namespace,
        robot_type=robot_type.perform(context)
    )

    # Gemeinsame MoveIt Config für Planning & Servo
    moveit_config = MoveItConfigsBuilder(
        context=context,
        controllers_name=controllers_name,
        dof=dof,
        robot_type=robot_type,
        prefix=prefix,
        hw_ns=hw_ns,
        limited=limited,
        effort_control=effort_control,
        velocity_control=velocity_control,
        model1300=model1300,
        robot_sn=robot_sn,
        attach_to=attach_to,
        attach_xyz=attach_xyz,
        attach_rpy=attach_rpy,
        mesh_suffix=mesh_suffix,
        kinematics_suffix=kinematics_suffix,
        ros2_control_plugin=ros2_control_plugin,
        ros2_control_params=ros2_control_params,
        gripper_version=gripper_version,
        add_gripper=add_gripper,
        add_vacuum_gripper=add_vacuum_gripper,
        add_bio_gripper=add_bio_gripper,
        add_realsense_d435i=add_realsense_d435i,
        add_d435i_links=add_d435i_links,
        add_other_geometry=add_other_geometry,
        geometry_type=geometry_type,
        geometry_mass=geometry_mass,
        geometry_height=geometry_height,
        geometry_radius=geometry_radius,
        geometry_length=geometry_length,
        geometry_width=geometry_width,
        geometry_mesh_filename=geometry_mesh_filename,
        geometry_mesh_origin_xyz=geometry_mesh_origin_xyz,
        geometry_mesh_origin_rpy=geometry_mesh_origin_rpy,
        geometry_mesh_tcp_xyz=geometry_mesh_tcp_xyz,
        geometry_mesh_tcp_rpy=geometry_mesh_tcp_rpy,
    ).to_moveit_configs()

    # 1. Robot Description (Startet robot_state_publisher)
    robot_description_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([FindPackageShare('xarm_description'), 'launch', '_robot_description.launch.py'])),
        launch_arguments={'robot_description': yaml.dump(moveit_config.robot_description)}.items(),
    )

    # 2. MoveIt 2 Common (Startet MoveGroup für Bahnplanung & RViz mit Planning-Plugin)
    robot_moveit_common_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([FindPackageShare('xarm_moveit_config'), 'launch', '_robot_moveit_common2.launch.py'])),
        launch_arguments={
            'prefix': prefix,
            'attach_to': attach_to,
            'attach_xyz': attach_xyz,
            'attach_rpy': attach_rpy,
            # CRITICAL FIX: no_gui_ctrl MUSS 'true' sein, sonst startet ein joint_state_publisher_gui,
            # der permanent Null-Werte publiziert und die korrekten Fake-Hardware-States überschreibt!
            'no_gui_ctrl': 'true', 
            'use_sim_time': 'false',
            'moveit_config_dump': yaml.dump(moveit_config.to_dict()),
        }.items(),
    )

    # 3. ROS 2 Control (Fake Hardware Interface)
    ros2_control_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([FindPackageShare('xarm_controller'), 'launch', '_ros2_control.launch.py'])),
        launch_arguments={
            'robot_description': yaml.dump(moveit_config.robot_description),
            'ros2_control_params': ros2_control_params,
        }.items(),
    )

    # 4. Spawner für Broadcaster und Trajectory Controller
    joint_state_broadcaster = Node(
        package='controller_manager',
        executable='spawner',
        output='screen',
        arguments=['joint_state_broadcaster', '--controller-manager', '{}/controller_manager'.format(ros_namespace)],
    )

    xarm_traj_controller = '{}{}_traj_controller'.format(prefix.perform(context), xarm_type)
    traj_controller_node = Node(
        package='controller_manager',
        executable='spawner',
        output='screen',
        arguments=[xarm_traj_controller, '--controller-manager', '{}/controller_manager'.format(ros_namespace)],
    )

    # Zusätzliche Greifer-Controller (falls konfiguriert)
    controllers = []
    if add_gripper.perform(context) in ('True', 'true'):
        controllers.append('{}{}_gripper_traj_controller'.format(prefix.perform(context), robot_type.perform(context)))
    elif add_bio_gripper.perform(context) in ('True', 'true') and robot_type.perform(context) != 'lite':
        controllers.append('{}bio_gripper_traj_controller'.format(prefix.perform(context)))

    controller_nodes = []
    for controller in controllers:
        controller_nodes.append(Node(
            package='controller_manager',
            executable='spawner',
            output='screen',
            arguments=[controller, '--controller-manager', '{}/controller_manager'.format(ros_namespace)],
        ))

    # 5. MoveIt Servo Parameter
    robot_description_parameters = {}
    robot_description_parameters.update(moveit_config.robot_description)
    robot_description_parameters.update(moveit_config.robot_description_semantic)
    robot_description_parameters.update(moveit_config.robot_description_kinematics)
    robot_description_parameters.update(moveit_config.joint_limits)
    robot_description_parameters.update(moveit_config.planning_pipelines)

    servo_yaml = load_yaml('xarm_moveit_servo', "config/xarm_moveit_servo_config.yaml")
    servo_yaml['move_group_name'] = xarm_type
    servo_yaml['command_out_topic'] = '/{}/joint_trajectory'.format(xarm_traj_controller)
    servo_params = {"moveit_servo": servo_yaml}

    # 6. Servo Component Container
    servo_container = ComposableNodeContainer(
        name='xarm_moveit_servo_container',
        namespace='/',
        package='rclcpp_components',
        executable='component_container',
        composable_node_descriptions=[
            ComposableNode(
                package='moveit_servo',
                plugin='moveit_servo::ServoNode',
                name='servo_server',
                parameters=[servo_params, robot_description_parameters],
            ),
            ComposableNode(
                package='xarm_moveit_servo',
                plugin='xarm_moveit_servo::JoyToServoPub',
                name='joy_to_servo_node',
                parameters=[
                    servo_params,
                    {'dof': dof, 'ros_queue_size': 10, 'joystick_type': joystick_type},
                ],
            ),
            ComposableNode(
                package='joy',
                plugin='joy::Joy',
                name='joy_node',
            ),
        ],
        output='screen',
    )

    return [
        robot_description_launch,
        robot_moveit_common_launch,
        joint_state_broadcaster,
        ros2_control_launch,
        traj_controller_node,
        # Startet den Servo-Container erst, wenn der Trajectory-Controller erfolgreich gespawnt wurde!
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=traj_controller_node,
                on_exit=servo_container,
            )
        ),
    ] + controller_nodes

def generate_launch_description():
    return LaunchDescription([
        OpaqueFunction(function=launch_setup)
    ])