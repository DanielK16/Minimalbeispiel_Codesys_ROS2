# Autor: Daniel Körper 
# Programmm basiert auf Beispielen von:
# Programmen aus Arbeit: Navigation des TurtleBots mit LIDAR und 3D-Kamera von Nele Heinz
# https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Service-And-Client.html

import rclpy
from rclpy.node import Node
# ROS2 Message Interfaces
from control_msgs.msg import JointJog       # Gelenkwerte
from geometry_msgs.msg import TwistStamped  # TCP im karteisischen Raum
from std_srvs.srv import Trigger    # Service /start /stop Servo
from std_msgs.msg import Int8       # Status des Servos

import asyncio
import logging
from asyncua import Client, ua
# Logging etwas reduzieren
logging.basicConfig(level=logging.WARNING)

# Konfigurationsdatei laden
import yaml
with open("/home/ros/ros2_ws/src/sim_arm_pkg/config/opc_topic_config.yml", "r") as f:
    config = yaml.safe_load(f)

class OPC_UA_Client_Node(Node):
    def __init__(self):
        super().__init__('opc_ua_client_node')

        ### Servo Services ###
        # Start Servo Service
        self.start_servo_client = self.create_client(
            Trigger,
            config['servo_node']['start_servo_service']
            )
        max_retries = 10
        retries = 0
        while not self.start_servo_client.wait_for_service(timeout_sec=1.0):
            retries += 1
            self.get_logger().info(f'Service /servo_node/start_servo nicht verfügbar, warte... ({retries}/{max_retries})')
            if retries >= max_retries:
                self.get_logger().error('Konnte keine Verbindung zum Servo-Service start_servo herstellen!')
                return
            
        # Stop Servo Service
        self.stop_servo_client = self.create_client(
            Trigger,
            config['servo_node']['stop_servo_service']
            )
        max_retries = 10
        retries = 0
        while not self.stop_servo_client.wait_for_service(timeout_sec=1.0):
            retries += 1
            self.get_logger().info(f'Service /servo_node/stop_servo nicht verfügbar, warte... ({retries}/{max_retries})')
            if retries >= max_retries:
                self.get_logger().error('Konnte keine Verbindung zum Servo-Service stop_servo herstellen!')
                return

        ## Publisher
        # Servo Axis
        self.delta_axis_publisher = self.create_publisher(
            JointJog,
            config['servo_node']['delta_joint_cmd_topic'],
            10
        )

        # Servo TCP
        self.delta_tcp_publisher = self.create_publisher(
            TwistStamped,
            config['servo_node']['delta_tcp_cmd_topic'],
            10)

        ## Subcsriber
        # Status Codes
        self.status_subscriber = self.create_subscription(
            Int8,
            config['servo_node']['status_topic'],
            self.status_callback,
            1)
        self.status_subscriber  # prevent unused variable warning

        ## Variablen Initialisieren
        # Status 
        self.servo_status = None
        self.last_sent_status = None

        # Mode 
        self.current_mode = "NONE"  # TCP, AXIS oder NONE

        # TCP
        self.tcp_trans_x = 0
        self.tcp_trans_y = 0
        self.tcp_trans_z = 0
        self.tcp_rot_x = 0
        self.tcp_rot_y = 0
        self.tcp_rot_z = 0
        self.tcp_velocity = 0

        # Axis
        self.joint_names_list = [
            config['joint_states']['axis_0'],
            config['joint_states']['axis_1'],
            config['joint_states']['axis_2'],
            config['joint_states']['axis_3'],
            config['joint_states']['axis_4'],
            config['joint_states']['axis_5']
        ]
        self.calculated_joint_velocities = {j: 0.0 for j in self.joint_names_list}

    def update_tcp_values(self,trans_x, trans_y,trans_z,rot_x, rot_y, rot_z, velocity):
        self.current_mode = "TCP"
        self.tcp_trans_x = trans_x
        self.tcp_trans_y = trans_y
        self.tcp_trans_z = trans_z
        self.tcp_rot_x = rot_x
        self.tcp_rot_y = rot_y
        self.tcp_rot_z = rot_z
        self.tcp_velocity = velocity

    def update_axis_values(self, directions_list, speed_value):
        self.current_mode = "AXIS"
        speed = float(speed_value)
        for i, direction in enumerate(directions_list):
            joint_name = self.joint_names_list[i]
            self.calculated_joint_velocities[joint_name] = float(direction) * speed

    def stop_all_motion(self):
        """ Setzt alle Werte zurück und wechselt in Modus None """
        self.current_mode = "NONE"
        self.tcp_trans_x = 0.0
        self.tcp_trans_y = 0.0
        self.tcp_trans_z = 0.0
        self.tcp_rot_x = 0.0
        self.tcp_rot_y = 0.0
        self.tcp_rot_z = 0.0
        self.tcp_velocity = 0.0
        for j in self.joint_names_list:
            self.calculated_joint_velocities[j] = 0.0

    def status_callback(self, msg):
        self.servo_status = msg

    def ServoCallback(self):
        if self.current_mode == "TCP":
            # TCP publishen
            msg = TwistStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = config['servo_node']['servo_base']
            msg.twist.linear.x = self.tcp_trans_x * self.tcp_velocity
            msg.twist.linear.y = self.tcp_trans_y * self.tcp_velocity
            msg.twist.linear.z = self.tcp_trans_z * self.tcp_velocity
            msg.twist.angular.x = self.tcp_rot_x * self.tcp_velocity
            msg.twist.angular.y = self.tcp_rot_y * self.tcp_velocity
            msg.twist.angular.z = self.tcp_rot_z * self.tcp_velocity
            self.delta_tcp_publisher.publish(msg)
            
        elif self.current_mode == "AXIS":
            # Gelenke publishen
            active_joints = []
            active_velocities = []
            for joint, vel in self.calculated_joint_velocities.items():
                if vel != 0.0:
                    active_joints.append(joint)
                    active_velocities.append(vel)

            msg = JointJog()
            msg.header.frame_id = config['servo_node']['servo_base']
            msg.header.stamp = self.get_clock().now().to_msg()
            
            # Wenn kein Button gedrückt publishe 0.0 um Servo am Leben zu halten
            if not active_joints:
                msg.joint_names = [self.joint_names_list[0]]
                msg.velocities = [0.0]
            else:
                msg.joint_names = active_joints
                msg.velocities = active_velocities
                
            self.delta_axis_publisher.publish(msg)
            
        else: # "NONE"
            # Weder TCP noch AXIS: Stopp-Kommando senden, damit Servo Stream aktiv bleibt
            msg = JointJog()
            msg.header.frame_id = config['servo_node']['servo_base']
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.joint_names = [self.joint_names_list[0]]
            msg.velocities = [0.0]
            self.delta_axis_publisher.publish(msg)
        

async def async_main(args=None):
    # Instanzziieren der ROS2 Node Klasse
    ros_node = OPC_UA_Client_Node()

    # OPC UA Verbindungsaufbau
    ipaddress = config['OPC_Client']['ipaddress']
    port = config['OPC_Client']['port']
    opc_url = f"opc.tcp://{ipaddress}:{port}"
    async with Client(url = opc_url,
                      timeout = 2.0,
                      watchdog_intervall = 0.5, 
                      auto_reconnect = True,  
                      reconnect_max_delay = 5.0,    
                      reconnect_request_timeout = 5.0) as client:
        ros_node.get_logger().info(f"OPC Client verbunden: {opc_url}")

        # Verbindung zu Knoten im OPC-UA Server herstellen
        # Richtung der Achsen (erwartet 0, 1 oder -1)
        axis_direction_nodes = {
            "axis_0": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_0"),
            "axis_1": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_1"),
            "axis_2": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_2"),
            "axis_3": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_3"),
            "axis_4": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_4"),
            "axis_5": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_5"),
        }

        # Geschwindigkeit der Achsen
        global_velocity_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Velocity")

        # Richtung im kartesischen Raum (erwartet 0, 1 oder 1-)
        tcp_direction_nodes = {
            "trans_x": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.trans_x"),
            "trans_y": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.trans_y"),
            "trans_z": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.trans_z"),
            "rot_x": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.rot_x"),
            "rot_y": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.rot_y"),
            "rot_z": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.rot_z"),
        }

        # Geschwindigkeit im kartesischen Raum
        tcp_velocity_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Velocity")

        #Watchdog Node 
        watchdog_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.watchdog_counter")
        watchdog_counter = 0

        # Enable Node zum Start (true) oder Stop (false) des Servo Nodes
        enable_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.enable")
        current_enable_status = False

        # aktueller Modus: ob TCP Werte oder Joint Werte gepublished werden
        mode_nodes = {
            "mode_axis": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Mode_Axis"),
            "mode_tcp": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Mode_TCP"),
        }

        # Status Node /servo_node/status
        status_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Status_Code")

        try:
            while rclpy.ok():
                # ROS Callbacks abarbeiten
                rclpy.spin_once(ros_node, timeout_sec=0.0)

                # Starten und Stopen der servo node
                enable = await enable_node.get_value()
                if enable and not current_enable_status:
                    ros_node.req = Trigger.Request()
                    ros_node.future = ros_node.start_servo_client.call_async(ros_node.req)
                    ros_node.get_logger().info('Servo Node Start-Request gesendet.')
                    current_enable_status = True
                elif not enable and current_enable_status:
                    ros_node.req = Trigger.Request()
                    ros_node.future = ros_node.stop_servo_client.call_async(ros_node.req)
                    ros_node.get_logger().info('Servo Node Stop-Request gesendet.')
                    current_enable_status = False

                # Schreiben des aktuellen Status
                current_status_val = 99  # Standardwert: Servo aus
                if current_enable_status and ros_node.servo_status is not None:
                    current_status_val = int(ros_node.servo_status.data)
                if current_status_val != ros_node.last_sent_status:
                    try:
                        await status_node.set_value(current_status_val, ua.VariantType.SByte)
                        ros_node.last_sent_status = current_status_val
                    except Exception as e:
                        ros_node.get_logger().warn(f"Status Node Fehler: {e}")

                # Watchdog hochzählen und senden
                try:
                    watchdog_counter = (watchdog_counter + 1) % 32767
                    await watchdog_node.set_value(int(watchdog_counter), ua.VariantType.Int16)
                except Exception as e:
                    ros_node.get_logger().warn(f" Watchdog Fehler: {e}")

                # TCP Jogging und Joint Jogging Werte einlesen
                try: 
                    # Modus auslesen
                    tcp_mode = await mode_nodes["mode_tcp"].get_value()
                    axis_mode = await mode_nodes["mode_axis"].get_value()

                    if tcp_mode:
                        # Lese nur TCP Werte
                        tcp_vel = await tcp_velocity_node.get_value()
                        tx = await tcp_direction_nodes["trans_x"].get_value()
                        ty = await tcp_direction_nodes["trans_y"].get_value()
                        tz = await tcp_direction_nodes["trans_z"].get_value()
                        rx = await tcp_direction_nodes["rot_x"].get_value()
                        ry = await tcp_direction_nodes["rot_y"].get_value()
                        rz = await tcp_direction_nodes["rot_z"].get_value()
                        ros_node.update_tcp_values(tx, ty, tz,rx,ry,rz, tcp_vel)

                    elif axis_mode:
                        # Lese nur Joint Werte
                        joint_vel = await global_velocity_node.get_value()
                        directions = [await axis_direction_nodes[f"axis_{i}"].get_value() for i in range(6)]
                        ros_node.update_axis_values(directions, joint_vel)

                    else: 
                        # Kein Modus aktiv
                        ros_node.stop_all_motion()

                except Exception as e:
                    ros_node.get_logger().error(f"Fehler beim Jogging: {e}")
                    ros_node.stop_all_motion()

                # Aufruf des ServoCallbacks
                ros_node.ServoCallback()
                
                # Kurze Pause
                await asyncio.sleep(0.05)
                
        except KeyboardInterrupt:
            ros_node.get_logger().info("Strg + C gedrückt: Programm wird beendet...")
        finally:
            await client.disconnect()
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

if __name__ == '__main__':
    main()