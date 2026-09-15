import asyncio
import logging

import rclpy
from rclpy.node import Node
from control_msgs.msg import JointJog
from std_srvs.srv import Trigger

from asyncua import Client, ua

# Logging etwas reduzieren
logging.basicConfig(level=logging.WARNING)

class OPC_UA_Client_Node(Node):
    def __init__(self):
        super().__init__('opc_ua_client_node')

####################################
# Service Call zum Start des Services
#####################################
        self.start_servo_client = self.create_client(
            Trigger,
            '/servo_node/start_servo'
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
# Service Call zum Start des Services
#####################################
        self.stop_servo_client = self.create_client(
            Trigger,
            '/servo_node/stop_servo'
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
            '/servo_node/delta_joint_cmds',
            10
        )
        
        # Mapping der myCobot Gelenke
        self.joint_names_list = [
            "joint2_to_joint1",
            "joint3_to_joint2",
            "joint4_to_joint3",
            "joint5_to_joint4",
            "joint6_to_joint5",
            "joint6output_to_joint6"
        ]

        # Hier speichern wir die aktuellen Geschwindigkeiten pro Gelenk
        self.calculated_joint_velocities = {j: 0.0 for j in self.joint_names_list}

        # Alle 0.05 sekunden publishen von MoveIt Servo
        self.tf_timer = self.create_timer(0.05, self.JointJogCallback)

    def update_jog_velocity(self, axis_index, direction, speed_value):
        """Verrechnet Richtung (+1, -1, 0) und die globale Schieberegler-Geschwindigkeit"""
        if 0 <= axis_index < len(self.joint_names_list):
            joint_name = self.joint_names_list[axis_index]
            self.calculated_joint_velocities[joint_name] = float(direction * speed_value)

    def JointJogCallback(self):
        """Sendet alle 0.05s die verrechneten Geschwindigkeiten an MoveIt Servo"""
        active_joints = []
        active_velocities = []

        for joint, vel in self.calculated_joint_velocities.items():
            if vel != 0.0:
                active_joints.append(joint)
                active_velocities.append(vel)

        msg = JointJog()
        msg.header.frame_id = "g_base"
        msg.header.stamp = self.get_clock().now().to_msg()
        
        # Wenn nichts verfahren wird, 0.0 für Gelenk 1 senden (Hält den Servo-Stream aktiv)
        if not active_joints:
            msg.joint_names = [self.joint_names_list[0]]
            msg.velocities = [0.0]
        else:
            msg.joint_names = active_joints
            msg.velocities = active_velocities

        self.delta_axis_publisher.publish(msg)


async def async_main(args=None):
    ipaddress = "172.25.170.32"
    port = "4840"
    opc_url = f"opc.tcp://{ipaddress}:{port}"

    ros_node = OPC_UA_Client_Node()

    async with Client(url = opc_url,
                      timeout = 2.0,
                      watchdog_intervall = 0.5, 
                      auto_reconnect = True,  
                      reconnect_max_delay = 5.0,    
                      reconnect_request_timeout = 5.0) as client:
        ros_node.get_logger().info(f"OPC Client verbunden: {opc_url}")

        # --- OPC UA KNOTEN FÜR STEUERUNG ---
        # 1. Achsen-Richtungs-Nodes (Erwartet -1, 0 oder +1 aus CODESYS pro Achse)
        axis_direction_nodes = {
            0: client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3A3uE7iF6ja0hbIDwH2eM8TZ7x+I4fZrccBQ="),
            1: client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3A3uE7iF6ja0hbIDwH2eM8TZ7x+I4fZrccRQ="),
            2: client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3A3uE7iF6ja0hbIDwH2eM8TZ7x+I4fZrcchQ="),
            3: client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3A3uE7iF6ja0hbIDwH2eM8TZ7x+I4fZrccxQ="),
            4: client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3A3uE7iF6ja0hbIDwH2eM8TZ7x+I4fZrcdBQ="),
            5: client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3A3uE7iF6ja0hbIDwH2eM8TZ7x+I4fZrcdRQ="),
        }

        # 2. EINZIGER Velocity-Node für den globalen Schieberegler
        global_velocity_node = client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3A3uE7iF6ja0hbIDwH2eM8TZ7x/UleIbgKWCQgw==")

        # 3. Watchdog Node für CODESYS
        watchdog_node = client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3A3uE7iF6ja03dZ3gKHCG5B93hvYuYIzxQA==")
        watchdog_counter = 0

        # Enable Node
        enable_node = client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx9Evdob3A3uE7iF6ja0leojhLHHp")
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
                    ros_node.get_logger().warn(f"⚠️ Watchdog Fehler: {e}")

                # Globale Geschwindigkeit und Richtungen auslesen und verrechnen
                try:
                    speed = await global_velocity_node.get_value()
                    
                    for i in range(6):
                        direction = await axis_direction_nodes[i].get_value()
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