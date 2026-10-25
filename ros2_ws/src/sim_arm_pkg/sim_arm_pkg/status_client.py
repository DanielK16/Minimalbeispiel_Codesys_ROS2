# Autor: Daniel Körper 
# Programmm basiert auf Beispielen von:
# Programmen aus Arbeit: Navigation des TurtleBots mit LIDAR und 3D-Kamera von Nele Heinz
# https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html
# https://github.com/FreeOpcUa/opcua-asyncio/issues/1787
# https://docs.python.org/3/library/asyncio-task.html#asyncio.gather

# Imports
import rclpy
from rclpy.node import Node

# Imports für ROS2 Messages
from sensor_msgs.msg import JointState  # /joint_states
from geometry_msgs.msg import Pose      # /tcp_pose

# Imports für Asyncua
import os
import asyncio
from asyncua import Client, ua
import logging
logging.basicConfig(level=logging.WARNING) # reduziert Fehlermeldungen von asyncua  

# Laden der Konfigurations Datei
import yaml
with open("/home/ros/ros2_ws/src/sim_arm_pkg/config/opc_topic_config.yml", "r") as f:
    config = yaml.safe_load(f)
config['OPC_Client']['ipaddress'] = os.environ.get('OPC_IP', config['OPC_Client']['ipaddress'])

class OPC_UA_Client_Node(Node):
    def __init__(self):
        super().__init__('opc_ua_client_node')
        
        # Variablen festlegen
        self.current_joint_states = None
        self.current_tcp_pose = None

        # Subscriber für /joint_states
        self.joint_states_sub = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_states_callback,
            1)

        # Subscriber für /tcp_pose
        self.tcp_pose_sub = self.create_subscription(
            Pose,
            '/tcp_pose',
            self.tcp_pose_callback,
            1)

    # Verarbeiten von Subscriber erhaltene Daten    
    def joint_states_callback(self, msg):
        self.current_joint_states = msg

    def tcp_pose_callback(self, msg):
        self.current_tcp_pose = msg


async def async_main(args=None):
    # Instanzziieren der ROS2 Node Klasse
    ros_node = OPC_UA_Client_Node()
    
    # OPC UA Verbindung
    ipaddress = config['OPC_Client']['ipaddress']
    port = config['OPC_Client']['port']
    opc_url = f"opc.tcp://{ipaddress}:{port}"

    async with Client(url = opc_url,
                      timeout = 2.0,
                      watchdog_intervall = 0.5, 
                      auto_reconnect = True,  
                      reconnect_max_delay = 5.0,    
                      reconnect_request_timeout = 5.0, ) as client:
        ros_node.get_logger().info(f"OPC Client verbunden: {opc_url}")

        # Verbindung zu Knoten im OPC-UA Server herstellen
        # Position der Achsen 
        axis_nodes = {
            "axis_0": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotStatus.Ist_Pos_Axis.axis_0"),
            "axis_1": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotStatus.Ist_Pos_Axis.axis_1"),
            "axis_2": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotStatus.Ist_Pos_Axis.axis_2"),
            "axis_3": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotStatus.Ist_Pos_Axis.axis_3"),
            "axis_4": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotStatus.Ist_Pos_Axis.axis_4"),
            "axis_5": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotStatus.Ist_Pos_Axis.axis_5"),
        }

        # Position des TCP 
        tcp_nodes = {
            "trans_x": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotStatus.Ist_Pos_TCP.trans_x"),
            "trans_y": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotStatus.Ist_Pos_TCP.trans_y"),
            "trans_z": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotStatus.Ist_Pos_TCP.trans_z"),
            "rot_x": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotStatus.Ist_Pos_TCP.rot_x"),
            "rot_y": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotStatus.Ist_Pos_TCP.rot_y"),
            "rot_z": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotStatus.Ist_Pos_TCP.rot_z"),
            "rot_w": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotStatus.Ist_Pos_TCP.rot_w")
        }

        # Watchdog Variable für Verbindungscheck
        watchdog_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.RobotStatus.watchdog_counter")
        watchdog_counter = 0

        try:
            # Hauptschleife
            while rclpy.ok():
                
                # ROS2 Callbacks verarbeiten -> ließt neue msg für Subscriber ein
                rclpy.spin_once(ros_node, timeout_sec=0.0)
                
                # Watchdog Variable aktualisieren und schreiben
                try:
                    watchdog_counter = (watchdog_counter + 1) % 32767  # Zählt von 0 bis 32766 hoch
                    await watchdog_node.set_value(int(watchdog_counter), ua.VariantType.Int16)
                except Exception as e:
                    ros_node.get_logger().warn(f" Watchdog konnte nicht gesendet werden: {e}")

                # aktuelle Joint States via OPC UA schreiben
                if ros_node.current_joint_states is not None:
                    joint_state_msg = ros_node.current_joint_states
                    ros_node.current_joint_states = None  
                    
                    # joint states werden im topic durcheinander gepublished, deswegen namenzuordnung!
                    try:
                        tasks = []  
                        for i, joint_name in enumerate(joint_state_msg.name):
                            pos_val = joint_state_msg.position[i]
                            
                            if joint_name == config['joint_states']['axis_0']:
                                tasks.append(axis_nodes["axis_0"].set_value(pos_val, ua.VariantType.Double))
                            elif joint_name == config['joint_states']['axis_1']:
                                tasks.append(axis_nodes["axis_1"].set_value(pos_val, ua.VariantType.Double))
                            elif joint_name == config['joint_states']['axis_2']:
                                tasks.append(axis_nodes["axis_2"].set_value(pos_val, ua.VariantType.Double))
                            elif joint_name == config['joint_states']['axis_3']:
                                tasks.append(axis_nodes["axis_3"].set_value(pos_val, ua.VariantType.Double))
                            elif joint_name == config['joint_states']['axis_4']:
                                tasks.append(axis_nodes["axis_4"].set_value(pos_val, ua.VariantType.Double))
                            elif joint_name == config['joint_states']['axis_5']:
                                tasks.append(axis_nodes["axis_5"].set_value(pos_val, ua.VariantType.Double))
                        
                        if tasks:
                            # führt alle Schreibbefehle für die Achsen parallel gleichzeitig 
                            await asyncio.gather(*tasks)
                    except Exception as e:
                        ros_node.get_logger().warn(f" Fehler beim Schreiben von /joint_states: {e}")

                # Aktuelle TCP Pose via OPC UA schreiben
                if ros_node.current_tcp_pose is not None:
                    p_msg = ros_node.current_tcp_pose
                    ros_node.current_tcp_pose = None  
                    
                    try:
                        await asyncio.gather(
                            tcp_nodes['trans_x'].set_value(float(p_msg.position.x), ua.VariantType.Double),
                            tcp_nodes['trans_y'].set_value(float(p_msg.position.y), ua.VariantType.Double),
                            tcp_nodes['trans_z'].set_value(float(p_msg.position.z), ua.VariantType.Double),
                            tcp_nodes['rot_x'].set_value(float(p_msg.orientation.x), ua.VariantType.Double),
                            tcp_nodes['rot_y'].set_value(float(p_msg.orientation.y), ua.VariantType.Double),
                            tcp_nodes['rot_z'].set_value(float(p_msg.orientation.z), ua.VariantType.Double),
                            tcp_nodes['rot_w'].set_value(float(p_msg.orientation.w), ua.VariantType.Double)
                        )
                    except Exception as e:
                        ros_node.get_logger().warn(f" Fehler beim Schreiben von /tcp_pose: {e}")
                
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
        # ROS2 sauber herunterfahren
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()