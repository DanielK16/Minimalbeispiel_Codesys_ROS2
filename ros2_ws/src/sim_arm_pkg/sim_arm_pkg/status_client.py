# Quellen
# - https://docs.ros.org/en/rolling/ROS-Framework/nodes/Working-with-nodes/Writing-An-Async-Node-With-Asyncio-Python.html

import asyncio
import logging

import rclpy
from rclpy.node import Node

# imports für ROS2 Messages
from sensor_msgs.msg import JointState
from geometry_msgs.msg import Pose

from asyncua import Client, ua

logging.basicConfig(level=logging.WARNING)

class OPC_UA_Client_Node(Node):
    def __init__(self):
        super().__init__('opc_ua_client_node')
        self.current_joint_states = None
        self.current_tcp_pose = None

        # Subscriber für /joint_states
        self.joint_states_sub = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_states_callback,
            10)

        # Subscriber für /tcp_pose
        self.tcp_pose_sub = self.create_subscription(
            Pose,
            '/tcp_pose',
            self.tcp_pose_callback,
            10)
        
    def joint_states_callback(self, msg):
        self.current_joint_states = msg

    def tcp_pose_callback(self, msg):
        self.current_tcp_pose = msg


async def async_main(args=None):
    # OPC UA Verbindung
    ipaddress = "172.25.170.32"
    port = "4840"
    opc_url = f"opc.tcp://{ipaddress}:{port}"

    ros_node = OPC_UA_Client_Node()

    async with Client(url = opc_url,
                      timeout = 2.0,
                      watchdog_intervall = 0.5, 
                      auto_reconnect = True,  
                      reconnect_max_delay = 5.0,    
                      reconnect_request_timeout = 5.0, ) as client:
        ros_node.get_logger().info(f"OPC Client verbunden: {opc_url}")

        # Pos_Axis 
        axis_nodes = {
            "axis_0": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3E2CI9zVnx9MvZ7bCOH2arSFsgPAfJOk="),
            "axis_1": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3E2CI9zVnx9MvZ7bCOH2arSFsgPAfJek="),
            "axis_2": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3E2CI9zVnx9MvZ7bCOH2arSFsgPAfJuk="),
            "axis_3": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3E2CI9zVnx9MvZ7bCOH2arSFsgPAfJ+k="),
            "axis_4": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3E2CI9zVnx9MvZ7bCOH2arSFsgPAfIOk="),
            "axis_5": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3E2CI9zVnx9MvZ7bCOH2arSFsgPAfIek="),
        }

        # Pos_TCP
        tcp_nodes = {
            "trans_x": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3E2CI9zVnx9MvZ7bXA0TH9zJ1h/AfbOk="),
            "trans_y": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3E2CI9zVnx9MvZ7bXA0TH9zJ1h/Afbek="),
            "trans_z": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3E2CI9zVnx9MvZ7bXA0TH9zJ1h/Afbuk="),
            "rot_x": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3E2CI9zVnx9MvZ7bXA0TH8S9gtvtA"),
            "rot_y": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3E2CI9zVnx9MvZ7bXA0TH8S9gtvpA"),
            "rot_z": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3E2CI9zVnx9MvZ7bXA0TH8S9gtvlA"),
            "rot_w": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3E2CI9zVnx9MvZ7bXA0TH8S9gtvRA")
        }

        # Watchdog Variable erhöhren
        watchdog_node = client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3E2CI9zVnx/QhYIrrJHuO3CN7nO00cZuD")
        watchdog_counter = 0

        try:
            # Die asynchrone Hauptschleife
            while rclpy.ok():
                
                # ROS Callbacks verarbeiten
                rclpy.spin_once(ros_node, timeout_sec=0.0)
                
                # Watchdog schreiben
                try:
                    watchdog_counter = (watchdog_counter + 1) % 32767  # Zählt von 0 bis 32766 hoch
                    await watchdog_node.set_value(int(watchdog_counter), ua.VariantType.Int16)
                except Exception as e:
                    ros_node.get_logger().warn(f"⚠️ Watchdog konnte nicht gesendet werden: {e}")

                # Joint States schreiben
                if ros_node.current_joint_states is not None:
                    joint_state_msg = ros_node.current_joint_states
                    ros_node.current_joint_states = None  
                    # joint states werden durcheinander gepublished, deswegen namenzuordnung!

                try:
                    for i, joint_name in enumerate(joint_state_msg.name):
                        pos_val = joint_state_msg.position[i]
                        
                        if joint_name == "joint2_to_joint1":
                            await axis_nodes["axis_0"].set_value(float(pos_val), ua.VariantType.Double)
                        elif joint_name == "joint3_to_joint2":
                            await axis_nodes["axis_1"].set_value(float(pos_val), ua.VariantType.Double)
                        elif joint_name == "joint4_to_joint3":
                            await axis_nodes["axis_2"].set_value(float(pos_val), ua.VariantType.Double)
                        elif joint_name == "joint5_to_joint4":
                            await axis_nodes["axis_3"].set_value(float(pos_val), ua.VariantType.Double)
                        elif joint_name == "joint6_to_joint5":
                            await axis_nodes["axis_4"].set_value(float(pos_val), ua.VariantType.Double)
                        elif joint_name == "joint6output_to_joint6":
                            await axis_nodes["axis_5"].set_value(float(pos_val), ua.VariantType.Double)

                except Exception as e:
                    ros_node.get_logger().warn(f"⚠️ Fehler beim Schreiben von /joint_states: {e}")

                # ---- TCP POSE SCHREIBEN ----
                if ros_node.current_tcp_pose is not None:
                    p_msg = ros_node.current_tcp_pose
                    ros_node.current_tcp_pose = None  
                    
                    try:
                        await tcp_nodes['trans_x'].set_value(float(p_msg.position.x), ua.VariantType.Double)
                        await tcp_nodes['trans_y'].set_value(float(p_msg.position.y), ua.VariantType.Double)
                        await tcp_nodes['trans_z'].set_value(float(p_msg.position.z), ua.VariantType.Double)
                        await tcp_nodes['rot_x'].set_value(float(p_msg.orientation.x), ua.VariantType.Double)
                        await tcp_nodes['rot_y'].set_value(float(p_msg.orientation.y), ua.VariantType.Double)
                        await tcp_nodes['rot_z'].set_value(float(p_msg.orientation.z), ua.VariantType.Double)
                        await tcp_nodes['rot_w'].set_value(float(p_msg.orientation.w), ua.VariantType.Double)
                    except Exception as e:
                        ros_node.get_logger().warn(f"⚠️ Fehler beim Schreiben von /tcp_pose: {e}")
                
                # Kurze Pause für die CPU (bestimmt auch den Takt des Watchdogs)
                await asyncio.sleep(0.1)
                
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