# Autor: Daniel Körper
# OPC UA Client für Turtlesim Simulation

# Imports ROS2
import rclpy
from rclpy.node import Node
# Import Interfaces
from turtlesim.msg import Pose          
from geometry_msgs.msg import Twist
# Import asyncua
import asyncio
from asyncua import Client, ua  

# ROS2 Knoten
class OPC_UA_Client_Node(Node):

    def __init__(self):
        super().__init__('opc_ua_client_node')
        # IP Adresse Parameter deklarieren -> ros2 run ... --ros-args -p IP_ADRESSE:=IP
        self.declare_parameter('IP_Adresse', '172.25.170.32')

        # Variablendeklaration 
        self.latest_pose = None         # Istwert aus ROS2 -> SPS     
        self.current_linear_x = 0.0     # Sollwert aus SPS -> ROS2
        self.current_angular_z = 0.0

        # Publisher für Sollwerte (Twist)
        self.cmd_vel_publisher = self.create_publisher(Twist,'/turtle1/cmd_vel',10)

        # Subscriber für Istwerte (aktuelle Position)
        self.pose_subscriber = self.create_subscription(Pose,'/turtle1/pose',self.pose_callback,10)

    # Aktuelle Pose speichern
    def pose_callback(self, msg):
        self.latest_pose = msg

    # Twist msg zusammenbauen
    def publish_twist(self):
        twist_msg = Twist()
        twist_msg.linear.x = self.current_linear_x
        twist_msg.angular.z = self.current_angular_z
        self.cmd_vel_publisher.publish(twist_msg)

# Überwacht Änderungen im Adressraum
class SubscriptionHandler:
    def __init__(self,ros_node, opc_knoten):
        self.ros_node = ros_node
        self.opc_knoten = opc_knoten

    def datachange_notification(self, node, val, data):
        # Neuen Sollwert in ROS2 Knoten speichern
        if node == self.opc_knoten["linear_x"]:
            self.ros_node.current_linear_x = float(val)
        elif node == self.opc_knoten["angular_z"]:
            self.ros_node.current_angular_z = float(val)
        
async def async_main(args=None):
    # ROS2 Node Initialisieren
    ros_node = OPC_UA_Client_Node()

    # OPC UA Verbindungsaufbau
    ipaddress = ros_node.get_parameter('IP_Adresse').value
    port = "4840"
    opc_url = f"opc.tcp://{ipaddress}:{port}"
    ros_node.get_logger().info(f"Versuche OPC Verbindung mit {opc_url} herzustellen")
    async with Client(url = opc_url,                    # Netzwerkadresse des Servers
                      timeout = 2.0,                    # Maximaler Zeitraum die Client auf Server Antwort wartet
                      watchdog_intervall = 0.5,         # alle 500ms checken ob Verbindung noch lebt
                      auto_reconnect = True,            # wenn Verbidnung unterbrochen automatisch wiederverbinden
                      reconnect_max_delay = 5.0,        # Wartzezeit zwischen zwei Versuchen beim Verbinden
                      reconnect_request_timeout = 5.0,  # Dauer die die Verbindung zum Server maximal dauern darf 
                        ) as client:
        ros_node.get_logger().info(f"OPC Client verbunden: {opc_url}")
        
        # Variablen aus Adressraum holen über NodeId
        opc_ziel_knoten = {
            "x_pose": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/c1Zp3vJSW28y9njK04S5nsM3Hp"),
            #"x_pose": client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.turtle1_pose.x_pose), 
            "y_pose": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/c1Zp3vJSW28y9njK05S5nsM3Hp"),
            "theta_pose": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/c1Zp3vJSW28y9njK00fIz3IUuZ7DNx6Q=="),
            "linear_x": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/c1Zp3vJSW24C1wtvUleMfvKXqM4jJLkYM="),
            "angular_z": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/c1Zp3vJSW24C1wtvUleMfiLnOc7yFmtvlA")
        }

        # Subscription Handler einrichten                            
        handler = SubscriptionHandler(ros_node, opc_ziel_knoten)
        sub = await client.create_subscription(100,handler) #publishing interval in ms
        await sub.subscribe_data_change([opc_ziel_knoten["linear_x"], opc_ziel_knoten["angular_z"]])

        try:
            while rclpy.ok():
                # Ausführen der ROS2 Callbacks
                rclpy.spin_once(ros_node, timeout_sec=0.0)
                # Aktuelle Sollbewegung veröffentlichen
                ros_node.publish_twist()
                # Aktuelle Position in SPS schreiben
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
