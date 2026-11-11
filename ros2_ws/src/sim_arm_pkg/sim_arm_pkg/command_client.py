# Autor: Daniel Körper
# Manuelle Steuerung des Roboterarms über MoveIt Servo
# Programmm basiert auf Beispielen von:
# Programmen aus Arbeit: Navigation des TurtleBots mit LIDAR und 3D-Kamera von Nele Heinz
# https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Service-And-Client.html

# Imports für ROS2
import rclpy
from rclpy.node import Node

# Import Interfaces für ROS2 Messages
from control_msgs.msg import JointJog       # Gelenkwerte
from geometry_msgs.msg import TwistStamped  # TCP im karteisischen Raum
from std_srvs.srv import Trigger            # Service /start /stop Servo
from std_msgs.msg import Int8               # Status des Servos

# Imports für Asyncua
import asyncio
from asyncua import Client, ua
import logging
import os

logging.basicConfig(level=logging.WARNING)

# Laden der Konfigurationsdatei
import yaml
with open("/home/ros/ros2_ws/src/sim_arm_pkg/config/opc_topic_config.yml", "r") as f:
    config = yaml.safe_load(f)
# Environment Variable von docker run übernehmen
config['OPC_Client']['ipaddress'] = os.environ.get('OPC_IP', config['OPC_Client']['ipaddress'])

class OPC_UA_Client_Node(Node):

    def __init__(self):
        super().__init__('opc_ua_client_node')

        # Service Client für Start Servo
        self.start_servo_client = self.create_client(Trigger, config['servo_node']['start_servo_service'])
        self.get_logger().info("Warte auf Service start_servo")
        self.start_servo_client.wait_for_service()
        self.get_logger().info("Service start_servo gefunden")

        # Service Client für Stop Servo
        self.stop_servo_client = self.create_client(Trigger, config['servo_node']['stop_servo_service'])
        self.get_logger().info("Warte auf Service stop_servo")
        self.stop_servo_client.wait_for_service()
        self.get_logger().info("Service stop_servo gefunden")

        # Publisher erstellen für Achsen
        self.delta_axis_publisher = self.create_publisher(JointJog, config['servo_node']['delta_joint_cmd_topic'], 10)

        # Publisher erstellen für TCP
        self.delta_tcp_publisher = self.create_publisher(TwistStamped, config['servo_node']['delta_tcp_cmd_topic'], 10)

        # Subscriber für Status der Servo Node
        self.status_subscriber = self.create_subscription(Int8, config['servo_node']['status_topic'], self.status_callback, 1)

        # Status der Servo Node
        self.servo_status = None
        self.last_sent_status = None
        self.servo_enabled = False

        # Verbindung zur SPS (wird über Watchdog geprüft)
        self.opc_ok = False

        # Aktueller Modus aus Codesys
        self.mode_tcp = False
        self.mode_axis = False

        # Aktuelle Sollwerte für TCP
        self.tcp_trans_x = 0.0
        self.tcp_trans_y = 0.0
        self.tcp_trans_z = 0.0
        self.tcp_rot_x = 0.0
        self.tcp_rot_y = 0.0
        self.tcp_rot_z = 0.0
        self.tcp_velocity = 0.0

        # Aktuelle Sollwerte für Achsen
        self.axis_0 = 0.0
        self.axis_1 = 0.0
        self.axis_2 = 0.0
        self.axis_3 = 0.0
        self.axis_4 = 0.0
        self.axis_5 = 0.0
        self.axis_velocity = 0.0

        # Namen der Gelenke aus Config
        self.joint_names_list = [
            config['joint_states']['axis_0'],
            config['joint_states']['axis_1'],
            config['joint_states']['axis_2'],
            config['joint_states']['axis_3'],
            config['joint_states']['axis_4'],
            config['joint_states']['axis_5']
        ]

    def status_callback(self, msg):
        self.servo_status = msg

    def start_servo(self):
        """ Startet die Servo Node """
        if not self.servo_enabled:
            self.start_servo_client.call_async(Trigger.Request())
            self.servo_enabled = True
            self.get_logger().info("Servo Node Start-Request gesendet.")

    def stop_servo(self):
        """ Stoppt die Servo Node """
        if self.servo_enabled:
            self.stop_servo_client.call_async(Trigger.Request())
            self.servo_enabled = False
            self.get_logger().info("Servo Node Stop-Request gesendet.")

    def stop_servo_control(self):
        """ Sendet 0.0 damit Roboter steht und Servo Stream aktiv bleibt """
        msg = JointJog()
        msg.header.frame_id = config['servo_node']['servo_base']
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.joint_names = [self.joint_names_list[0]]
        msg.velocities = [0.0]
        self.delta_axis_publisher.publish(msg)

    def servo_control(self):
        """ Publiziert die aktuellen Sollwerte kontinuierlich """
        # Keine Verbindung zur SPS: Roboter stoppen
        if not self.opc_ok:
            self.stop_servo_control()

        # TCP Modus
        elif self.mode_tcp:
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

        # Achs Modus
        elif self.mode_axis:
            directions = [self.axis_0, self.axis_1, self.axis_2, self.axis_3, self.axis_4, self.axis_5]
            active_joints = []
            active_velocities = []
            for i in range(6):
                if directions[i] != 0.0:
                    active_joints.append(self.joint_names_list[i])
                    active_velocities.append(directions[i] * self.axis_velocity)

            # Wenn kein Button gedrückt publishe 0.0 um Servo am Leben zu halten
            if not active_joints:
                self.stop_servo_control()
            else:
                msg = JointJog()
                msg.header.frame_id = config['servo_node']['servo_base']
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.joint_names = active_joints
                msg.velocities = active_velocities
                self.delta_axis_publisher.publish(msg)

        # Kein Modus aktiv
        else:
            self.stop_servo_control()

class SubscriptionHandler:

    def __init__(self, ros_node):
        self.ros_node = ros_node

    def datachange_notification(self, node, val, data):
        """Aktualisiert Sollwerte bei OPC-UA-Wertänderungen"""
        print(f"datachange_notification {node} = {val}")

        # Vegleicht Wertänderung und übergibt aktuellen Wert an die ROS Node
        # --- ENABLE ---
        if str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.enable":
            if val is not None:
                if val:
                    self.ros_node.start_servo()
                else:
                    self.ros_node.stop_servo()

        # --- MODUS ---
        elif str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Mode_TCP":
            if val is not None:
                self.ros_node.mode_tcp = bool(val)
        elif str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Mode_Axis":
            if val is not None:
                self.ros_node.mode_axis = bool(val)

        # --- TCP ---
        elif str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Velocity":
            if val is not None:
                self.ros_node.tcp_velocity = float(val)
        elif str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.trans_x":
            if val is not None:
                self.ros_node.tcp_trans_x = float(val)
        elif str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.trans_y":
            if val is not None:
                self.ros_node.tcp_trans_y = float(val)
        elif str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.trans_z":
            if val is not None:
                self.ros_node.tcp_trans_z = float(val)
        elif str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.rot_x":
            if val is not None:
                self.ros_node.tcp_rot_x = float(val)
        elif str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.rot_y":
            if val is not None:
                self.ros_node.tcp_rot_y = float(val)
        elif str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.rot_z":
            if val is not None:
                self.ros_node.tcp_rot_z = float(val)

        # --- ACHSEN ---
        elif str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Velocity":
            if val is not None:
                self.ros_node.axis_velocity = float(val)
        elif str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_0":
            if val is not None:
                self.ros_node.axis_0 = float(val)
        elif str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_1":
            if val is not None:
                self.ros_node.axis_1 = float(val)
        elif str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_2":
            if val is not None:
                self.ros_node.axis_2 = float(val)
        elif str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_3":
            if val is not None:
                self.ros_node.axis_3 = float(val)
        elif str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_4":
            if val is not None:
                self.ros_node.axis_4 = float(val)
        elif str(node) == "ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_5":
            if val is not None:
                self.ros_node.axis_5 = float(val)
        else:
            return

async def async_main(args=None):
    # Instanziieren der ROS2 Node Klasse
    ros_node = OPC_UA_Client_Node()

    # OPC-UA-Verbindung herstellen
    ipaddress = config["OPC_Client"]["ipaddress"]
    port = config["OPC_Client"]["port"]
    opc_url = f"opc.tcp://{ipaddress}:{port}"

    try:
        async with Client(
                        url=opc_url,
                        timeout=2.0,
                        watchdog_intervall=0.5,
                        auto_reconnect=True,
                        reconnect_max_delay=5.0,
                        reconnect_request_timeout=5.0
                    ) as client:
            ros_node.get_logger().info(f"OPC Client verbunden: {opc_url}")

            # Verbindung zu den OPC-UA-Knoten herstellen
            mode_node = {
                "enable": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.enable"),
                "mode_tcp": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Mode_TCP"),
                "mode_axis": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Mode_Axis"),
            }

            tcp_node = {
                "velocity": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Velocity"),
                "trans_x": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.trans_x"),
                "trans_y": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.trans_y"),
                "trans_z": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.trans_z"),
                "rot_x": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.rot_x"),
                "rot_y": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.rot_y"),
                "rot_z": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_TCP_Servo.rot_z"),
            }

            axis_node = {
                "velocity": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Velocity"),
                "axis_0": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_0"),
                "axis_1": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_1"),
                "axis_2": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_2"),
                "axis_3": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_3"),
                "axis_4": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_4"),
                "axis_5": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_5"),
            }

            status_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Status_Code")

            watchdog_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.watchdog_counter")
            watchdog_counter = 0

            # Subscription Handler
            handler = SubscriptionHandler(ros_node)
            subscription = await client.create_subscription(50, handler)
            await subscription.subscribe_data_change([
                mode_node["enable"],
                mode_node["mode_tcp"],
                mode_node["mode_axis"],
                tcp_node["velocity"],
                tcp_node["trans_x"],
                tcp_node["trans_y"],
                tcp_node["trans_z"],
                tcp_node["rot_x"],
                tcp_node["rot_y"],
                tcp_node["rot_z"],
                axis_node["velocity"],
                axis_node["axis_0"],
                axis_node["axis_1"],
                axis_node["axis_2"],
                axis_node["axis_3"],
                axis_node["axis_4"],
                axis_node["axis_5"]
                ])

            # Hauptschleife:
            while rclpy.ok():
                rclpy.spin_once(ros_node, timeout_sec=0.0)

                # Watchdog Variable erhöhen und schreiben
                # Wenn Schreiben fehlschlägt ist Verbindung zur SPS weg -> Roboter stoppen
                try:
                    watchdog_counter = (watchdog_counter +1) % 32767
                    await watchdog_node.set_value(int(watchdog_counter), ua.VariantType.Int16)
                    ros_node.opc_ok = True
                except Exception as e:
                    ros_node.opc_ok = False
                    ros_node.get_logger().warn(f"Watchdog konnte nicht gesendet werden: {e}")

                # Status der Servo Node schreiben (99 = Servo aus)
                status_code = 99
                if ros_node.servo_enabled and ros_node.servo_status is not None:
                    status_code = int(ros_node.servo_status.data)
                if status_code != ros_node.last_sent_status:
                    try:
                        await status_node.set_value(status_code, ua.VariantType.SByte)
                        ros_node.last_sent_status = status_code
                    except Exception as e:
                        ros_node.get_logger().warn(f"Status konnte nicht gesendet werden: {e}")

                # Sollwerte an Servo Node publishen
                ros_node.servo_control()

                await asyncio.sleep(0.05)

    except Exception as e:
        ros_node.get_logger().error(f"OPC-UA-Fehler: {e}")
    finally:
        if rclpy.ok():
            # Beim Beenden des Programms sichergehen dass Roboter gestoppt ist!
            ros_node.get_logger().info("Sende Stopp-Signal an Roboter...")
            ros_node.stop_servo_control()
            ros_node.destroy_node()


def main(args=None):

    rclpy.init(args=args)
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        print("Strg + C gedrückt: Programm wird beendet.")
    finally:
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()
