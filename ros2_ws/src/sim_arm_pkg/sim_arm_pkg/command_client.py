# Autor: Daniel Körper 
# Programmm basiert auf Beispielen von:
# Programmen aus Arbeit: Navigation des TurtleBots mit LIDAR und 3D-Kamera von Nele Heinz
# https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Service-And-Client.html

import asyncio
import logging

import rclpy
from rclpy.node import Node
from control_msgs.msg import JointJog
from std_srvs.srv import Trigger

from asyncua import Client, ua

# Logging etwas reduzieren
logging.basicConfig(level=logging.WARNING)

# für config file
import yaml
with open("/home/ros/ros2_ws/src/sim_arm_pkg/config/opc_topic_config.yml", "r") as f:
    config = yaml.safe_load(f)

class OPC_UA_Client_Node(Node):
    def __init__(self):
        super().__init__('opc_ua_client_node')

####################################
# Service Call zum Start des Services
#####################################
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

####################################
# Service Call zum Stop des Services Servo
#####################################
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


#######################################
# Publisher für MoveIt Servo JointJog
#######################################
        self.delta_axis_publisher = self.create_publisher(
            JointJog,
            config['servo_node']['delta_joint_cmd_topic'],
            10
        )
        
        # Mapping der myCobot Gelenke
        self.joint_names_list = [
            config['joint_states']['axis_0'],
            config['joint_states']['axis_1'],
            config['joint_states']['axis_2'],
            config['joint_states']['axis_3'],
            config['joint_states']['axis_4'],
            config['joint_states']['axis_5']
        ]

        # aktuellen Geschwindigkeiten pro Gelenk
        self.calculated_joint_velocities = {j: 0.0 for j in self.joint_names_list}

        # Alle 0.05 sekunden publishen von MoveIt Servo
        self.tf_timer = self.create_timer(0.05, self.JointJogCallback)

    def update_jog_velocity(self, axis_index, direction, speed_value):
        """Verrechnet Richtung (+1, -1, 0) und die Schieberegler-Geschwindigkeit"""
        if 0 <= axis_index < len(self.joint_names_list):
            joint_name = self.joint_names_list[axis_index]
            self.calculated_joint_velocities[joint_name] = float(direction * speed_value)

    def JointJogCallback(self):
        """ Sendet alle 0.05s die verrechneten Geschwindigkeiten an MoveIt Servo """
        """ Hier nicht über SubscriptionHandler da regelmäßig an MoveIt Servo gepublished werden muss da sonst auf Stop Status automatisch geht"""
        active_joints = []
        active_velocities = []

        for joint, vel in self.calculated_joint_velocities.items():
            if vel != 0.0:
                active_joints.append(joint)
                active_velocities.append(vel)

        msg = JointJog()
        msg.header.frame_id = "g_base"
        msg.header.stamp = self.get_clock().now().to_msg()
        
        # Wenn nichts verfahren wird, 0.0 für Gelenk 1 senden damit servo stream nicht abbricht!
        if not active_joints:
            msg.joint_names = [self.joint_names_list[0]]
            msg.velocities = [0.0]
        else:
            msg.joint_names = active_joints
            msg.velocities = active_velocities

        self.delta_axis_publisher.publish(msg)


async def async_main(args=None):
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

        # Variablen aus Adressraum holen über Node IDs
        # erwartet 0 1 oder -1
        axis_direction_nodes = {
            "axis_0": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_0"),
            "axis_1": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_1"),
            "axis_2": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_2"),
            "axis_3": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_3"),
            "axis_4": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_4"),
            "axis_5": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Servo.axis_5"),
        }

        # Velocity
        global_velocity_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.Soll_Axis_Velocity")

        #Watchdog Node für CODESYS
        watchdog_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.watchdog_counter")
        watchdog_counter = 0

        # Enable Node zum Start oder Stop des Servo Nodes
        enable_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotCommand.enable")
        current_enable_status = False

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

                # Watchdog hochzählen und senden
                try:
                    watchdog_counter = (watchdog_counter + 1) % 32767
                    await watchdog_node.set_value(int(watchdog_counter), ua.VariantType.Int16)
                except Exception as e:
                    ros_node.get_logger().warn(f" Watchdog Fehler: {e}")

                # Globale Geschwindigkeit und Richtungen auslesen und verrechnen
                try:
                    speed = await global_velocity_node.get_value()

                    for i in range(6):
                        direction = await axis_direction_nodes[f"axis_{i}"].get_value()
                        ros_node.update_jog_velocity(i, int(direction), float(speed))
                except Exception as e:
                    pass
                
                # Kurze Pause
                await asyncio.sleep(0.05)
                
        except KeyboardInterrupt:
            pass
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