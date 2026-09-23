#!/usr/bin/env python3
# ==============================================================================
# Quellen & Referenzen:
# - GitHub MoveIt 2: https://github.com/ros-planning/moveit2
# - Deep Wiki: https://wiki.ros.org/moveit 
# - AsyncUA (OPC UA): https://github.com/FreeOpcUa/opcua-asyncio
# ==============================================================================

import time
import rclpy
from rclpy.node import Node

from moveit.planning import MoveItPy, PlanRequestParameters
from moveit.core.robot_state import RobotState
from moveit.core.kinematic_constraints import construct_joint_constraint, construct_link_constraint
from geometry_msgs.msg import Pose
from moveit_msgs.msg import Constraints, PositionConstraint
from shape_msgs.msg import SolidPrimitive


import asyncio
from asyncua import Client, ua
import logging

class ROSNode(Node):
    def __init__(self):
        super().__init__('ros_node')
        self.logger = self.get_logger()

        # Error Code initialisieren 
        self.error_code = 0

        # MoveItPy Instanzen 
        self.myCobot = MoveItPy(node_name="action_client")
        self.myCobotArm = self.myCobot.get_planning_component("arm_group")
        self.planning_scene_monitor = self.myCobot.get_planning_scene_monitor()
        self.logger.info("MoveItPy instance created")

    def plan_and_execute(self, single_plan_parameters=None, sleep_time=0.0):
        """Plan and execute a Motion"""
        self.logger.info("Planning trajectory...")

        # Plan mit Parametern
        if single_plan_parameters is not None:
            plan_result = self.myCobotArm.plan(parameters=single_plan_parameters)
        else:
            plan_result = self.myCobotArm.plan()

        # Plan auswerten und ausführen
        if plan_result:
            self.logger.info("Executing plan...")
            robot_trajectory = plan_result.trajectory
            self.myCobot.execute("arm_group", robot_trajectory)
            
            # Error Code aktualisieren
            self.error_code = plan_result.error_code.val
            self.logger.info(f"Execution finished. Error Code: {self.error_code}")
            
            if sleep_time > 0.0:
                time.sleep(sleep_time)
        else:
            self.error_code = plan_result.error_code.val
            self.logger.error(f"Planning failed! Error Code: {self.error_code}")

        return self.error_code

    def setPlanRequestParameters(self,
                                 planning_pipeline="ompl",
                                 planner_id="",
                                 planning_time=10.0,
                                 num_planning_attempts=10,
                                 max_velocity_scaling_factor=0.2,
                                 max_acceleration_scaling_factor=0.2):
        """Konfiguriert die Planungs-Parameter"""
        self.single_plan_parameters = PlanRequestParameters(self.myCobot)
        self.single_plan_parameters.planning_pipeline = planning_pipeline
        self.single_plan_parameters.planner_id = planner_id
        self.single_plan_parameters.planning_time = planning_time
        self.single_plan_parameters.planning_attempts = num_planning_attempts
        self.single_plan_parameters.max_velocity_scaling_factor = max_velocity_scaling_factor
        self.single_plan_parameters.max_acceleration_scaling_factor = max_acceleration_scaling_factor
        
        return self.single_plan_parameters

    def createJointGoal(self, joint_values: dict, joint_tolerance: float = 0.01):
        """Setzt ein Ziel basierend auf Gelenkwinkeln (Joint Goal)"""
        robot_model = self.myCobot.get_robot_model()
        robot_state = RobotState(robot_model)
        
        # Aktuellen Zustand übernehmen, dann gewünschte Joints überschreiben
        robot_state.joint_positions = joint_values
        
        joint_constraint = construct_joint_constraint(
            robot_state=robot_state,
            joint_model_group=robot_model.get_joint_model_group("arm_group"),
            tolerance=joint_tolerance
        )
        
        self.myCobotArm.set_goal_state(motion_plan_constraints=[joint_constraint])
        self.logger.info("Joint Goal constraint set.")

    def createTCPGoal(self, position: list, orientation: list, position_tolerance: float = 0.01, orientation_tolerance: float = 0.1, link_name="joint6_flange", frame_id="g_base"):
        """Setzt ein Ziel basierend auf kartesischen Koordinaten (TCP Goal)"""
        tcp_constraint = construct_link_constraint(
            link_name=link_name,
            source_frame=frame_id,
            cartesian_position=position,
            cartesian_position_tolerance=position_tolerance,
            orientation=orientation, # Format: [x, y, z, w]
            orientation_tolerance=orientation_tolerance,
        )
        
        self.myCobotArm.set_goal_state(motion_plan_constraints=[tcp_constraint])
        self.logger.info(f"TCP Goal constraint set for {link_name}.")

    def createCIRCGoal(self, position: list, orientation: list, aux_position: list, 
                       aux_type: str = "interim", position_tolerance: float = 0.01, 
                       orientation_tolerance: float = 0.1, link_name="joint6_flange", frame_id="g_base"):
        """Setzt ein Ziel für eine Kreisbahn (CIRC Goal) mit einem Hilfspunkt"""
        try:
            # 1. Das Endziel der Bewegung setzen (identisch zum TCP Goal)
            tcp_constraint = construct_link_constraint(
                link_name=link_name,
                source_frame=frame_id,
                cartesian_position=[float(p) for p in position],
                cartesian_position_tolerance=float(position_tolerance),
                orientation=[float(o) for o in orientation],
                orientation_tolerance=float(orientation_tolerance),
            )
            self.myCobotArm.set_goal_state(motion_plan_constraints=[tcp_constraint])

            # 2. Den Hilfspunkt (Center oder Interim) als Path Constraint setzen
            aux_constraint = Constraints()
            aux_constraint.name = str(aux_type)  # Zwingend "interim" oder "center"
            
            pos_constraint = PositionConstraint()
            pos_constraint.link_name = link_name
            pos_constraint.header.frame_id = frame_id
            
            # Kugel (Sphere) definieren, in der der Hilfspunkt liegen muss
            primitive = SolidPrimitive()
            primitive.type = SolidPrimitive.SPHERE
            primitive.dimensions = [0.001] # 1mm Toleranz für den Durchgangspunkt
            
            # Koordinaten des Hilfspunktes übernehmen
            aux_pose = Pose()
            aux_pose.position.x = float(aux_position[0])
            aux_pose.position.y = float(aux_position[1])
            aux_pose.position.z = float(aux_position[2])
            aux_pose.orientation.w = 1.0 # Orientierung des Zwischenpunktes ist für Pilz zweitrangig
            
            # Alles zusammenbauen
            pos_constraint.constraint_region.primitives.append(primitive)
            pos_constraint.constraint_region.primitive_poses.append(aux_pose)
            aux_constraint.position_constraints.append(pos_constraint)
            
            # 3. Path Constraint in MoveItPy setzen
            self.myCobotArm.set_path_constraints(aux_constraint)
            
            self.logger.info(f"CIRC Goal gesetzt. Typ: {aux_type} bei [{aux_position[0]}, {aux_position[1]}, {aux_position[2]}].")
            return True

        except Exception as e:
            self.logger.error(f"Fehler bei createCIRCGoal: {e}")
            return False

    def create_goal(
        self,
        pipeline_id,
        planner_id,
        Joint_Goal,
        TCP_Goal,
        axis_0, axis_1, axis_2, axis_3, axis_4, axis_5,
        trans_x, trans_y, trans_z,
        rot_x, rot_y, rot_z, rot_w,
        position_tolerance=0.05,
        orientation_tolerance=0.05,
        joint_tolerance = 0.01
    ):
        """
        Interpretiert die Variablen von der SPS und ruft intern die jeweilige Goal-Funktion auf.
        """
        # Joint dictionary für Gelenkwinkel
        joint_values = {
            "joint2_to_joint1": axis_0,
            "joint3_to_joint2": axis_1,
            "joint4_to_joint3": axis_2,
            "joint5_to_joint4": axis_3,
            "joint6_to_joint5": axis_4,
            "joint6output_to_joint6": axis_5
        }
        
        # Positions- und Rotationslisten für kartesische Ziele
        position = [trans_x, trans_y, trans_z]
        orientation = [rot_x, rot_y, rot_z, rot_w]

        # Pipeline Logik auswerten
        if pipeline_id == "pilz_industrial_motion_planner":
            if planner_id == "PTP":
                if Joint_Goal:
                    self.createJointGoal(joint_values=joint_values)
                elif TCP_Goal:
                    self.createTCPGoal(position=position, orientation=orientation, 
                                       position_tolerance=position_tolerance, 
                                       orientation_tolerance=orientation_tolerance)
                else:
                    self.logger.error('Pilz PTP: Weder Joint Goal noch TCP Goal ausgewählt.')
                    
            elif planner_id in ["LIN", "CIRC"]:
                # LIN und CIRC sind typischerweise TCP/Kartesisch
                self.createTCPGoal(position=position, orientation=orientation, 
                                   position_tolerance=position_tolerance, 
                                   orientation_tolerance=orientation_tolerance)
            else:
                self.logger.error(f'Ungültige Planner ID für Pilz: {planner_id}')

        elif pipeline_id == "ompl":
            if Joint_Goal:
                self.createJointGoal(joint_values=joint_values, joint_tolerance= joint_tolerance)
            elif TCP_Goal:
                self.createTCPGoal(position=position, orientation=orientation, 
                                   position_tolerance=position_tolerance, 
                                   orientation_tolerance=orientation_tolerance)
            else:
                self.logger.error('OMPL: Weder Joint Goal noch TCP Goal ausgewählt.')
        else:
            self.logger.error(f'Keine gültige Pipeline ID: {pipeline_id}')


async def async_main(args=None):
    ### OPC UA Verbindung
    ipaddress = "172.25.170.32"
    port = "4840"
    opc_url = f"opc.tcp://{ipaddress}:{port}"

    ros_node = ROSNode()

    async with Client(url = opc_url,
                      timeout = 2.0,
                      watchdog_intervall = 0.5, 
                      auto_reconnect = True,  
                      reconnect_max_delay = 5.0,    
                      reconnect_request_timeout = 5.0) as client:
        
        ros_node.get_logger().info(f"OPC Client verbunden: {opc_url}")

        ## Node IDs holen
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
        
        # Watchdog Variable
        watchdog_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotAction.watchdog_counter")
        watchdog_counter = 0

        # Hauptschleife:
        try:
            while rclpy.ok():
                rclpy.spin_once(ros_node, timeout_sec=0.0)

                # SPS Zustand lesen
                execute = await execute_node.read_value()
                
                # Kontinuierlich den aktuellen Error Code an die SPS übermitteln
                await error_node.write_value(ua.DataValue(ua.Variant(ros_node.error_code, ua.VariantType.Int32)))

                # Watchdog schreiben
                try:
                    watchdog_counter = (watchdog_counter + 1) % 32767  # Zählt von 0 bis 32766 hoch
                    await watchdog_node.write_value(int(watchdog_counter), ua.VariantType.Int16)
                except Exception as e:
                    ros_node.get_logger().warn(f"Watchdog konnte nicht gesendet werden: {e}")       

                if execute:
                    # Ausführung blockiert neues Lesen, starte Sequenz:
                    ros_node.error_code = 0  # Reset Error Code
                    await execute_node.write_value(False) # Bestätigung (Flanke zurücksetzen)
                    ros_node.get_logger().info("Execute erkannt, baue Action Goal...")

                    try:
                        # Variablen via OPC UA einlesen
                        Joint_Goal = await JointGoal_node.read_value()
                        MotionType = await MotionType_node.read_value() # Dient als Pipeline (z.B. ompl, pilz_industrial_motion_planner)
                        PlannerID = await PlannerID_node.read_value() # z.B. PTP, LIN, CIRC
                        TCP_Goal = await TCPGoal_node.read_value()
                        
                        acceleration_scaling = await accelerationscaling_node.read_value()
                        velocity_scaling = await velocityscaling_node.read_value()
                        planning_attempts = await planningattempts_node.read_value()
                        planning_time = await planningtime_node.read_value()
                        
                        axis_0 = await axis_0_node.read_value()
                        axis_1 = await axis_1_node.read_value()
                        axis_2 = await axis_2_node.read_value()
                        axis_3 = await axis_3_node.read_value()
                        axis_4 = await axis_4_node.read_value()
                        axis_5 = await axis_5_node.read_value()
                        
                        orientation_tolerance = await orientationtolerance_node.read_value()
                        position_tolerance = await positiontolerance_node.read_value()
                        joint_tolerance = await jointtolerance_node.read_value()
                        
                        rot_x = await rot_x_node.read_value()
                        rot_y = await rot_y_node.read_value()
                        rot_z = await rot_z_node.read_value()
                        rot_w = await rot_w_node.read_value()
                        
                        trans_x = await trans_x_node.read_value()
                        trans_y = await trans_y_node.read_value()
                        trans_z = await trans_z_node.read_value()
                        
                    except Exception as e:
                        ros_node.get_logger().error(f"Fehler beim Lesen der Action-Daten: {e}")
                        continue # Startet Schleife neu
                    
                    # 1. Startzustand des Roboters updaten! WICHTIG!
                    ros_node.myCobotArm.set_start_state_to_current_state()

                    # 2. PlanRequestParameters mit gelesenen Variablen konfigurieren
                    plan_params = ros_node.setPlanRequestParameters(
                        planning_pipeline=MotionType,
                        planner_id=PlannerID,
                        planning_time=float(planning_time),
                        num_planning_attempts=int(planning_attempts),
                        max_velocity_scaling_factor=float(velocity_scaling),
                        max_acceleration_scaling_factor=float(acceleration_scaling)
                    )

                    # 3. Create Goal aufrufen mit den gelesenen SPS-Daten
                    ros_node.create_goal(
                        pipeline_id=MotionType,
                        planner_id=PlannerID,
                        Joint_Goal=Joint_Goal,
                        TCP_Goal=TCP_Goal,
                        axis_0=axis_0, axis_1=axis_1, axis_2=axis_2, 
                        axis_3=axis_3, axis_4=axis_4, axis_5=axis_5,
                        trans_x=trans_x, trans_y=trans_y, trans_z=trans_z,
                        rot_x=rot_x, rot_y=rot_y, rot_z=rot_z, rot_w=rot_w,
                        position_tolerance=position_tolerance,
                        orientation_tolerance=orientation_tolerance,
                        joint_tolerance= joint_tolerance
                    )
                    
                    # 4. Geplante Sequenz ausführen und Error Code abspeichern
                    ros_node.plan_and_execute(single_plan_parameters=plan_params, sleep_time=0.5)

                # Kleine Pause für die CPU
                await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            ros_node.get_logger().info("OPC UA Loop beendet.")
        finally:
            # Aufräumen
            ros_node.destroy_node()

def main(args=None):
    rclpy.init(args=args)
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()