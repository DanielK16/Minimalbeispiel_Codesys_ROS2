# Quellen:
# -https://github.com/moveit/moveit_tutorials/blob/master/doc/pilz_industrial_motion_planner/pilz_industrial_motion_planner.rst#id3


import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, PositionConstraint, OrientationConstraint
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose

import asyncio
from asyncua import Client, ua
import logging

class ROSNode(Node):
    def __init__(self):
        super().__init__('ros_node')

        # Deklaration error code
        self.error_code = 0

        self._action_client = ActionClient(self, MoveGroup, '/move_action')
        self.create_action_client()


    def create_action_client(self):
        self.get_logger().info('Warte auf Server...')
        self._action_client.wait_for_server()
        self.get_logger().info('Action Server gefunden')

    def create_ompl_joint_goal(self, planning_attempts, planning_time, velocity_scaling, acceleration_scaling, axis_0, axis_1, axis_2, axis_3, axis_4, axis_5, joint_tolerance = 0.01):
        goal_msg = MoveGroup.Goal()

        goal_msg.request.pipeline_id = 'ompl'
        goal_msg.request.group_name = 'arm_group'
        goal_msg.request.num_planning_attempts = planning_attempts
        goal_msg.request.allowed_planning_time = planning_time
        goal_msg.request.max_velocity_scaling_factor = velocity_scaling
        goal_msg.request.max_acceleration_scaling_factor = acceleration_scaling

        goal_msg.planning_options.plan_only = False

        joint_constraints = []

        joint_constraints.append(JointConstraint(
            joint_name='joint2_to_joint1',
            position=axis_0,
            tolerance_above=joint_tolerance,
            tolerance_below=joint_tolerance,
            weight=1.0
        ))

        joint_constraints.append(JointConstraint(
            joint_name='joint3_to_joint2',
            position=axis_1,
            tolerance_above=joint_tolerance,
            tolerance_below=joint_tolerance,
            weight=1.0
        ))

        joint_constraints.append(JointConstraint(
            joint_name='joint4_to_joint3',
            position=axis_2,
            tolerance_above=joint_tolerance,
            tolerance_below=joint_tolerance,
            weight=1.0
        ))

        joint_constraints.append(JointConstraint(
            joint_name='joint5_to_joint4',
            position=axis_3,
            tolerance_above=joint_tolerance,
            tolerance_below=joint_tolerance,
            weight=1.0
        ))

        joint_constraints.append(JointConstraint(
            joint_name='joint6_to_joint5',
            position=axis_4,
            tolerance_above=joint_tolerance,
            tolerance_below=joint_tolerance,
            weight=1.0
        ))

        joint_constraints.append(JointConstraint(
            joint_name='joint6output_to_joint6',
            position=axis_5,
            tolerance_above=joint_tolerance,
            tolerance_below=joint_tolerance,
            weight=1.0
        ))

        goal_msg.request.goal_constraints = [
            Constraints(joint_constraints=joint_constraints)
        ]

        return goal_msg

    def create_ompl_tcp_goal(self, planning_attempts, planning_time, velocity_scaling, acceleration_scaling, trans_x, trans_y, trans_z, rot_x, rot_y, rot_z, rot_w, position_tolerance, orientation_tolerance):
        goal_msg = MoveGroup.Goal()
        goal_msg.request.pipeline_id = 'ompl'   
        goal_msg.request.group_name = 'arm_group'

        goal_msg.request.num_planning_attempts = planning_attempts
        goal_msg.request.allowed_planning_time = planning_time

        goal_msg.request.max_velocity_scaling_factor = velocity_scaling
        goal_msg.request.max_acceleration_scaling_factor = acceleration_scaling
        
        goal_msg.planning_options.plan_only = False

        # Zielposition des TCP
        target_pose = Pose()
        target_pose.position.x = trans_x
        target_pose.position.y = trans_y
        target_pose.position.z = trans_z

        target_pose.orientation.x = rot_x
        target_pose.orientation.y = rot_y
        target_pose.orientation.z = rot_z
        target_pose.orientation.w = rot_w

        position_constraint = PositionConstraint()
        position_constraint.header.frame_id = "g_base"
        position_constraint.link_name = "joint6_flange"
        position_constraint.weight = 1.0
        box = SolidPrimitive()
        box.type = SolidPrimitive.BOX
        box.dimensions = [
            position_tolerance * 2,  # X-Toleranz
            position_tolerance * 2,  # Y-Toleranz
            position_tolerance * 2   # Z-Toleranz
        ]
        position_constraint.constraint_region.primitives.append(box)
        position_constraint.constraint_region.primitive_poses.append(
            target_pose
        )

        orientation_constraint = OrientationConstraint()
        orientation_constraint.header.frame_id = "g_base"       #relativ zu g_base
        orientation_constraint.link_name = "joint6_flange"      # tcp ist joint6_flange
        orientation_constraint.orientation.x = rot_x
        orientation_constraint.orientation.y = rot_y
        orientation_constraint.orientation.z = rot_z
        orientation_constraint.orientation.w = rot_w
        orientation_constraint.absolute_x_axis_tolerance = orientation_tolerance
        orientation_constraint.absolute_y_axis_tolerance = orientation_tolerance
        orientation_constraint.absolute_z_axis_tolerance = orientation_tolerance
        orientation_constraint.weight = 1.0

        constraints = Constraints()
        constraints.position_constraints.append(
            position_constraint
        )
        constraints.orientation_constraints.append(
            orientation_constraint
        )
        goal_msg.request.goal_constraints = [
            constraints
        ]

        return goal_msg

    def create_pilz_ptp_joint_goal(self, planning_attempts, planning_time, velocity_scaling, acceleration_scaling, axis_0, axis_1, axis_2, axis_3, axis_4, axis_5, joint_tolerance):
        goal_msg = MoveGroup.Goal()

        goal_msg.request.pipeline_id = 'pilz_industrial_motion_planner'
        goal_msg.request.planner_id = 'PTP'
        goal_msg.request.group_name = 'arm_group'   # name of the planning group

        goal_msg.request.num_planning_attempts = planning_attempts
        goal_msg.request.allowed_planning_time = planning_time

        goal_msg.request.max_velocity_scaling_factor = velocity_scaling     # scaling factor of maximal joint velocity
        goal_msg.request.max_acceleration_scaling_factor = acceleration_scaling #scaling factor of maximal joint aceleration

        goal_msg.planning_options.plan_only = False

        joint_constraints = []

        joint_constraints.append(JointConstraint(
            joint_name='joint2_to_joint1',
            position=axis_0,
            tolerance_above=joint_tolerance,
            tolerance_below=joint_tolerance,
            weight=1.0
        ))

        joint_constraints.append(JointConstraint(
            joint_name='joint3_to_joint2',
            position=axis_1,
            tolerance_above=joint_tolerance,
            tolerance_below=joint_tolerance,
            weight=1.0
        ))

        joint_constraints.append(JointConstraint(
            joint_name='joint4_to_joint3',
            position=axis_2,
            tolerance_above=joint_tolerance,
            tolerance_below=joint_tolerance,
            weight=1.0
        ))

        joint_constraints.append(JointConstraint(
            joint_name='joint5_to_joint4',
            position=axis_3,
            tolerance_above=joint_tolerance,
            tolerance_below=joint_tolerance,
            weight=1.0
        ))

        joint_constraints.append(JointConstraint(
            joint_name='joint6_to_joint5',
            position=axis_4,
            tolerance_above=joint_tolerance,
            tolerance_below=joint_tolerance,
            weight=1.0
        ))

        joint_constraints.append(JointConstraint(
            joint_name='joint6output_to_joint6',
            position=axis_5,
            tolerance_above=joint_tolerance,
            tolerance_below=joint_tolerance,
            weight=1.0
        ))

        goal_msg.request.goal_constraints = [
            Constraints(joint_constraints=joint_constraints)
        ]

        return goal_msg

    def create_pilz_ptp_tcp_goal(self, planning_attempts, planning_time, velocity_scaling, acceleration_scaling, trans_x, trans_y, trans_z, rot_x, rot_y, rot_z, rot_w, position_tolerance, orientation_tolerance):
        goal_msg = MoveGroup.Goal()

        goal_msg.request.pipeline_id = 'pilz_industrial_motion_planner'
        goal_msg.request.planner_id = 'PTP'
        goal_msg.request.group_name = 'arm_group'

        goal_msg.request.num_planning_attempts = planning_attempts
        goal_msg.request.allowed_planning_time = float(planning_time)

        goal_msg.request.max_velocity_scaling_factor = velocity_scaling
        goal_msg.request.max_acceleration_scaling_factor = acceleration_scaling

        goal_msg.planning_options.plan_only = False

        target_pose = Pose()
        target_pose.position.x = trans_x
        target_pose.position.y = trans_y
        target_pose.position.z = trans_z

        target_pose.orientation.x = rot_x
        target_pose.orientation.y = rot_y
        target_pose.orientation.z = rot_z
        target_pose.orientation.w = rot_w

        position_constraint = PositionConstraint()
        position_constraint.header.frame_id = "g_base"
        position_constraint.link_name = "joint6_flange"
        position_constraint.weight = 1.0

        box = SolidPrimitive()
        box.type = SolidPrimitive.BOX
        box.dimensions = [
            position_tolerance * 2,
            position_tolerance * 2,
            position_tolerance * 2
        ]

        position_constraint.constraint_region.primitives.append(box)
        position_constraint.constraint_region.primitive_poses.append(target_pose)

        orientation_constraint = OrientationConstraint()
        orientation_constraint.header.frame_id = "g_base"
        orientation_constraint.link_name = "joint6_flange"
        orientation_constraint.orientation.x = rot_x
        orientation_constraint.orientation.y = rot_y
        orientation_constraint.orientation.z = rot_z
        orientation_constraint.orientation.w = rot_w
        orientation_constraint.absolute_x_axis_tolerance = orientation_tolerance
        orientation_constraint.absolute_y_axis_tolerance = orientation_tolerance
        orientation_constraint.absolute_z_axis_tolerance = orientation_tolerance
        orientation_constraint.weight = 1.0

        constraints = Constraints()
        constraints.position_constraints.append(position_constraint)
        constraints.orientation_constraints.append(orientation_constraint)

        goal_msg.request.goal_constraints = [constraints]

        return goal_msg
    
    def create_pilz_lin_goal(self, planning_attempts, planning_time, velocity_scaling, acceleration_scaling, trans_x, trans_y, trans_z, rot_x, rot_y, rot_z, rot_w, position_tolerance, orientation_tolerance):
        goal_msg = MoveGroup.Goal()

        goal_msg.request.pipeline_id = 'pilz_industrial_motion_planner'
        goal_msg.request.planner_id = 'LIN'
        goal_msg.request.group_name = 'arm_group'

        goal_msg.request.num_planning_attempts = planning_attempts
        goal_msg.request.allowed_planning_time = planning_time

        goal_msg.request.max_velocity_scaling_factor = velocity_scaling
        goal_msg.request.max_acceleration_scaling_factor = acceleration_scaling

        goal_msg.planning_options.plan_only = False

        target_pose = Pose()
        target_pose.position.x = trans_x
        target_pose.position.y = trans_y
        target_pose.position.z = trans_z

        target_pose.orientation.x = rot_x
        target_pose.orientation.y = rot_y
        target_pose.orientation.z = rot_z
        target_pose.orientation.w = rot_w

        position_constraint = PositionConstraint()
        position_constraint.header.frame_id = "g_base"
        position_constraint.link_name = "joint6_flange"
        position_constraint.weight = 1.0

        box = SolidPrimitive()
        box.type = SolidPrimitive.BOX
        box.dimensions = [
            position_tolerance * 2,
            position_tolerance * 2,
            position_tolerance * 2
        ]

        position_constraint.constraint_region.primitives.append(box)
        position_constraint.constraint_region.primitive_poses.append(target_pose)

        orientation_constraint = OrientationConstraint()
        orientation_constraint.header.frame_id = "g_base"
        orientation_constraint.link_name = "joint6_flange"
        orientation_constraint.orientation.x = rot_x
        orientation_constraint.orientation.y = rot_y
        orientation_constraint.orientation.z = rot_z
        orientation_constraint.orientation.w = rot_w
        orientation_constraint.absolute_x_axis_tolerance = orientation_tolerance
        orientation_constraint.absolute_y_axis_tolerance = orientation_tolerance
        orientation_constraint.absolute_z_axis_tolerance = orientation_tolerance
        orientation_constraint.weight = 1.0

        constraints = Constraints()
        constraints.position_constraints.append(position_constraint)
        constraints.orientation_constraints.append(orientation_constraint)

        goal_msg.request.goal_constraints = [constraints]

        return goal_msg

    def create_pilz_circ_goal(self, planning_attempts, planning_time, velocity_scaling, acceleration_scaling, trans_x, trans_y, trans_z, rot_x, rot_y, rot_z, rot_w, position_tolerance, orientation_tolerance):
        # to do!
        # center punkt definieren für
        pass

    def create_goal(
        self,
        pipeline_id,
        planner_id,
        Joint_Goal,
        TCP_Goal,
        planning_attempts,
        planning_time,
        axis_0,
        axis_1,
        axis_2,
        axis_3,
        axis_4,
        axis_5,
        trans_x=0.0,
        trans_y=0.0,
        trans_z=0.0,
        rot_x=0.0,
        rot_y=0.0,
        rot_z=0.0,
        rot_w=1.0,
        velocity_scaling=0.2,
        acceleration_scaling=0.2,
        position_tolerance=0.05,
        orientation_tolerance=0.05,
        joint_tolerance=0.01
    ):
        if pipeline_id == "pilz_industrial_motion_planner":
            if planner_id == "PTP":
                if Joint_Goal:
                    return self.create_pilz_ptp_joint_goal(planning_attempts,planning_time,velocity_scaling,acceleration_scaling,axis_0,axis_1,axis_2,axis_3,axis_4,axis_5, joint_tolerance)
                elif TCP_Goal:
                    return self.create_pilz_ptp_tcp_goal(planning_attempts,planning_time,velocity_scaling,acceleration_scaling,trans_x,trans_y,trans_z,rot_x,rot_y,rot_z,rot_w,position_tolerance,orientation_tolerance)
                else:
                    self.get_logger().error('Joint Goal oder TCP Goal auswählen')
                    return None

            elif planner_id == "LIN":
                return self.create_pilz_lin_goal(planning_attempts,planning_time,velocity_scaling,acceleration_scaling,trans_x,trans_y,trans_z,rot_x,rot_y,rot_z,rot_w,position_tolerance,orientation_tolerance)

            elif planner_id == "CIRC":
                return self.create_pilz_circ_goal(planning_attempts,planning_time,velocity_scaling,acceleration_scaling,trans_x,trans_y,trans_z,rot_x,rot_y,rot_z,rot_w,position_tolerance,orientation_tolerance)

            else:
                self.get_logger().error(f'Ungültige Planner ID: {planner_id}')
                return None

        elif pipeline_id == "ompl":
            if Joint_Goal:
                return self.create_ompl_joint_goal(planning_attempts,planning_time,velocity_scaling,acceleration_scaling,axis_0,axis_1,axis_2,axis_3,axis_4,axis_5, joint_tolerance)

            elif TCP_Goal:
                return self.create_ompl_tcp_goal(planning_attempts,planning_time,velocity_scaling,acceleration_scaling,trans_x,trans_y,trans_z,rot_x,rot_y,rot_z,rot_w,position_tolerance,orientation_tolerance)

            else:
                self.get_logger().error('Joint Goal oder TCP Goal auswählen')
                return None

        else:
            self.get_logger().error(f'Keine gültige Pipeline ID: {pipeline_id}')
            return None

    def send_goal(self, goal_msg):
        if goal_msg is None:
            self.get_logger().error('Kein gültiges Goal vorhanden')
            return

        self.get_logger().info('Sende Ziel...')
        self.send_goal_future = self._action_client.send_goal_async(goal_msg)
        self.send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().info('Goal rejected')
            return

        self.get_logger().info('Goal accepted')
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        result = future.result().result
        error_code = result.error_code.val
        self.error_code = error_code

        if error_code == 1:
            self.get_logger().info('Bewegung erfolgreich!')
        else:
            self.get_logger().info(f'Fehlgeschlagen mit Fehlercode: {error_code}')

async def async_main(args=None):

    ros_node = ROSNode()

    # OPC UA Verbindung
    ipaddress = "172.25.170.32"
    port = "4840"
    opc_url = f"opc.tcp://{ipaddress}:{port}"

    try:

        # Verbindungsaufbau OPC UA
        ros_node.get_logger().info(f"Stelle Verbindung mit OPC Client her: {opc_url}")
        async with Client(
            url=opc_url,
            timeout=2.0,                    # Each request sent to the server expects an answer within this time
            watchdog_intervall=0.5,         # The time between checking if the server is still allive in seconds 
            auto_reconnect=True,            # Reestablish Connection on loss
            reconnect_max_delay=5.0,        # Exponential backoff cap for reconnect attempts (seconds)
            reconnect_request_timeout=5.0   # how long requests block waiting for the connection to become ready while the supervisor is connecting
        ) as client:
            ros_node.get_logger().info(f"OPC Client verbunden: {opc_url}")

            #NodeIds einlesen
            execute_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.Execute")
            error_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.Error_Code")
            JointGoal_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.Joint_Goal")
            MotionType_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.Motion_Type")
            PlannerID_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.Planner_ID")
            TCPGoal_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.TCP_GOAL")
            accelerationscaling_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.max_acceleration_scaling")
            axis_0_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.axis_0")
            axis_1_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.axis_1")
            axis_2_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.axis_2")
            axis_3_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.axis_3")
            axis_4_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.axis_4")
            axis_5_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.axis_5")
            orientationtolerance_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.orientation_tolerance")
            planningattempts_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.num_planning_attempts")
            planningtime_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.allowed_planning_time")
            positiontolerance_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.position_tolerance")
            jointtolerance_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.joint_tolerance")
            rot_x_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.rot_x")
            rot_y_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.rot_y")
            rot_z_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.rot_z")
            rot_w_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.rot_w")
            trans_x_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.trans_x")
            trans_y_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.trans_y")
            trans_z_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.trans_z")
            velocityscaling_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.max_velocity_scaling")

            # # Watchdog Variable erhöhren
            watchdog_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.watchdog_counter")
            watchdog_counter = 0

            while rclpy.ok():
                rclpy.spin_once(ros_node,timeout_sec=0.0)

                # Wert von SPS lesen
                execute = await execute_node.read_value()

                # Error Code schreiben
                await error_node.write_value(ua.DataValue(ua.Variant(ros_node.error_code, ua.VariantType.Int32)))

                # Watchdog schreiben
                try:
                    watchdog_counter = (watchdog_counter + 1) % 32767  # Zählt von 0 bis 32766 hoch
                    await watchdog_node.write_value(int(watchdog_counter), ua.VariantType.Int16)
                except Exception as e:
                    ros_node.get_logger().warn(f"Watchdog konnte nicht gesendet werden: {e}")       

                if execute:
                    ros_node.error_code = 0
                    await execute_node.write_value(False)
                    ros_node.get_logger().info("execute erkannt, baue action goal...")

                    try:
                        Joint_Goal = await JointGoal_node.read_value()
                        MotionType = await MotionType_node.read_value()
                        PlannerID = await PlannerID_node.read_value()
                        TCP_Goal = await TCPGoal_node.read_value()
                        acceleration_scaling = await accelerationscaling_node.read_value()
                        axis_0 = await axis_0_node.read_value()
                        axis_1 = await axis_1_node.read_value()
                        axis_2 = await axis_2_node.read_value()
                        axis_3 = await axis_3_node.read_value()
                        axis_4 = await axis_4_node.read_value()
                        axis_5 = await axis_5_node.read_value()
                        orientation_tolerance = await orientationtolerance_node.read_value()
                        planning_attempts = await planningattempts_node.read_value()
                        planning_time = await planningtime_node.read_value()
                        position_tolerance = await positiontolerance_node.read_value()
                        joint_tolerance = await jointtolerance_node.read_value()
                        rot_x = await rot_x_node.read_value()
                        rot_y = await rot_y_node.read_value()
                        rot_z = await rot_z_node.read_value()
                        rot_w = await rot_w_node.read_value()
                        trans_x = await trans_x_node.read_value()
                        trans_y = await trans_y_node.read_value()
                        trans_z = await trans_z_node.read_value()
                        velocity_scaling = await velocityscaling_node.read_value()

                    except Exception as e:
                        ros_node.get_logger().error(f"Fehler beim Lesen der Action-Daten: {e}")
                        continue

                    goal_msg = ros_node.create_goal(
                        pipeline_id=MotionType,
                        planner_id=PlannerID,

                        Joint_Goal=Joint_Goal,
                        TCP_Goal=TCP_Goal,

                        planning_attempts=planning_attempts,
                        planning_time=planning_time,

                        velocity_scaling=velocity_scaling,
                        acceleration_scaling=acceleration_scaling,

                        axis_0=axis_0,
                        axis_1=axis_1,
                        axis_2=axis_2,
                        axis_3=axis_3,
                        axis_4=axis_4,
                        axis_5=axis_5,

                        trans_x=trans_x,
                        trans_y=trans_y,
                        trans_z=trans_z,

                        rot_x=rot_x,
                        rot_y=rot_y,
                        rot_z=rot_z,
                        rot_w=rot_w,

                        position_tolerance=position_tolerance,
                        orientation_tolerance=orientation_tolerance,
                        joint_tolerance = joint_tolerance
                    )

                    ros_node.send_goal(goal_msg)


                await asyncio.sleep(0.01)

    except asyncio.TimeoutError:
        ros_node.get_logger().error(f"OPC UA Server nicht erreichbar: {opc_url}")

    except Exception as e:
        ros_node.get_logger().error(f"OPC UA Verbindungsfehler: {e}")

    finally:
        ros_node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

def main(args=None):
    rclpy.init(args=args)
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()