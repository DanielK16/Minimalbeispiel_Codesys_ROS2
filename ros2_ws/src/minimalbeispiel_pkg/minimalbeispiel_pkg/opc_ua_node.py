import rclpy
from rclpy.node import Node
from turtlesim.msg import Pose
from geometry_msgs.msg import Twist

import asyncio
import logging
from asyncua import Client, ua  

class OPC_UA_Client_Node(Node):

    def __init__(self):
        super().__init__('opc_ua_client_node')
        self.latest_pose = None  

        # Publisher
        self.cmd_vel_publisher = self.create_publisher(
            Twist,
            '/turtle1/cmd_vel',
            10
        )

        # Subscriber
        self.pose_subscriber = self.create_subscription(
            Pose,
            'turtle1/pose',
            self.pose_callback,
            10)

    # topic werte der msg in variable zwischenspeichern
    def pose_callback(self, msg):
        self.latest_pose = msg

    # twist message zusammenbauen
    def publish_twist(self, linear_x, angular_z):
        twist_msg = Twist()
        twist_msg.linear.x = float(linear_x)
        twist_msg.angular.z = float(angular_z)
        self.cmd_vel_publisher.publish(twist_msg)

# Überwacht Änderungen im Adressraum
class SubscriptionHandler:
    def __init__(self,ros_node, opc_knoten):
        self.ros_node = ros_node
        self.opc_knoten = opc_knoten
        self.current_linear_x = 0.0
        self.current_angular_z = 0.0

    def datachange_notification(self, node, val, data):
        if node == self.opc_knoten["linear_x"]:
            self.current_linear_x = float(val)
        elif node == self.opc_knoten["angular_z"]:
            self.current_angular_z = float(val)
        
        

async def async_main(args=None):
    ros_node = OPC_UA_Client_Node()

    # OPC UA Verbindungsaufbau
    ipaddress = "172.25.170.32"
    port = "4840"
    opc_url = f"opc.tcp://{ipaddress}:{port}"
    async with Client(url = opc_url,                    # Netzwerkadresse des Servers
                      timeout = 2.0,                    # Maximaler Zeitraum die Client auf Server Antwort wartet
                      watchdog_intervall = 0.5,         # alle 500ms checken ob Verbindung noch lebt
                      auto_reconnect = True,            # wenn Verbidnung unterbrochen automatisch wiederverbinden
                      reconnect_max_delay = 5.0,        # Wartzezeit zwischen zwei Versuchen beim Verbinden
                      reconnect_request_timeout = 5.0,  # Dauer die die Verbindung zum Server maximal dauern darf 
                        ) as client:
        ros_node.get_logger().info(f"OPC Client verbunden: {opc_url}")
        
        # node holen
        opc_ziel_knoten = {

            "x_pose": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/c1Zp3vJSW28y9njK04S5nsM3Hp"),
            #"x_pose": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.turtle1_pose.x_pose), # funktioniert nicht!

            "y_pose": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/c1Zp3vJSW28y9njK05S5nsM3Hp"),

            "theta_pose": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/c1Zp3vJSW28y9njK00fIz3IUuZ7DNx6Q=="),

            "linear_x": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/c1Zp3vJSW24C1wtvUleMfvKXqM4jJLkYM="),

            "angular_z": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/c1Zp3vJSW24C1wtvUleMfiLnOc7yFmtvlA")
        }
                            
        handler = SubscriptionHandler(ros_node, opc_ziel_knoten)
        sub = await client.create_subscription(100,handler) #publishing interval in ms
        await sub.subscribe_data_change([opc_ziel_knoten["linear_x"], opc_ziel_knoten["angular_z"]])

        try:
            while rclpy.ok():
                rclpy.spin_once(ros_node, timeout_sec=0.0)
                ros_node.publish_twist(handler.current_linear_x,handler.current_angular_z)
                
                if ros_node.latest_pose is not None:
                    await opc_ziel_knoten["x_pose"].write_value(ua.Variant(float(ros_node.latest_pose.x), ua.VariantType.Float))
                    await opc_ziel_knoten["y_pose"].write_value(ua.Variant(float(ros_node.latest_pose.y), ua.VariantType.Float))
                    await opc_ziel_knoten["theta_pose"].write_value(ua.Variant(float(ros_node.latest_pose.theta), ua.VariantType.Float))
                    
                await asyncio.sleep(0.01)
                
        except KeyboardInterrupt:
            pass
        finally:
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