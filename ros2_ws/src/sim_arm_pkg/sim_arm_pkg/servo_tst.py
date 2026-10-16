#!/usr/bin/env python3
import sys
import select
import termios
import tty
import time
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from geometry_msgs.msg import TwistStamped
from control_msgs.msg import JointJog

# --- Konfiguration der Tastenbelegung ---
msg = """
MoveIt Servo Interaktive Steuerung
--------------------------------------------------
Twist Steuerung (Kartesisch):
   w / s : +X / -X (Vor / Zurück)
   a / d : +Y / -Y (Links / Rechts)
   q / e : +Z / -Z (Hoch / Runter)

Joint Steuerung (Gelenke):
   1 bis 6 : Wähle das aktive Gelenk (1-6)
   r / f   : Ausgewähltes Gelenk positiv/negativ verfahren

Geschwindigkeit:
   + / -   : Geschwindigkeit erhöhen / verringern (10% Schritte)

Leertaste : Sofortiger Stopp
STRG+C    : Beenden
"""

def get_key(settings, timeout=0.02):
    """Liest einen Tastendruck aus dem Terminal (nicht-blockierend)."""
    tty.setraw(sys.stdin.fileno())
    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
    if rlist:
        key = sys.stdin.read(1)
    else:
        key = ''
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key

class InteractiveServoNode(Node):
    def __init__(self):
        super().__init__("servo_interactive_tester")

        self.joint_pub = self.create_publisher(JointJog, "/servo_node/delta_joint_cmds", 10)
        self.twist_pub = self.create_publisher(TwistStamped, "/servo_node/delta_twist_cmds", 10)
        self.start_client = self.create_client(Trigger, "/servo_node/start_servo")

        self.joint_names = [
            "joint2_to_joint1", "joint3_to_joint2", "joint4_to_joint3",
            "joint5_to_joint4", "joint6_to_joint5", "joint6output_to_joint6",
        ]

        # Interne Status-Variablen
        self.speed_scale = 0.2     # Basis-Geschwindigkeit (m/s oder rad/s)
        self.active_joint_idx = 0  # Welches Gelenk (0-5) wird gerade mit r/f gesteuert?
        
        # Aktuelle Befehlswerte
        self.target_twist = [0.0, 0.0, 0.0] # X, Y, Z
        self.target_joint_vel = 0.0
        self.mode = "TWIST" # "TWIST" oder "JOINT"

    def start_servo(self):
        self.get_logger().info("Warte auf Service /servo_node/start_servo ...")
        while not self.start_client.wait_for_service(timeout_sec=1.0):
            pass
        req = Trigger.Request()
        future = self.start_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        if future.result() is not None and future.result().success:
            self.get_logger().info(f"Servo gestartet: {future.result().message}")
            return True
        return False

    def publish_command(self):
        """Publiziert den aktuell anliegenden Befehl."""
        now = self.get_clock().now().to_msg()
        
        if self.mode == "TWIST":
            t_msg = TwistStamped()
            t_msg.header.stamp = now
            t_msg.header.frame_id = "g_base"
            t_msg.twist.linear.x = self.target_twist[0] * self.speed_scale
            t_msg.twist.linear.y = self.target_twist[1] * self.speed_scale
            t_msg.twist.linear.z = self.target_twist[2] * self.speed_scale
            self.twist_pub.publish(t_msg)
            
        elif self.mode == "JOINT":
            j_msg = JointJog()
            j_msg.header.stamp = now
            j_msg.header.frame_id = "g_base"
            j_msg.joint_names = self.joint_names
            velocities = [0.0] * 6
            velocities[self.active_joint_idx] = self.target_joint_vel * self.speed_scale
            j_msg.velocities = velocities
            self.joint_pub.publish(j_msg)


def main(args=None):
    rclpy.init(args=args)
    settings = termios.tcgetattr(sys.stdin)
    
    node = InteractiveServoNode()
    
    if not node.start_servo():
        print("Konnte Servo nicht starten. Beende.")
        node.destroy_node()
        rclpy.shutdown()
        return

    print(msg)
    print(f"Aktuelle Geschwindigkeit: {node.speed_scale:.2f} | Aktives Gelenk: {node.active_joint_idx + 1}")

    try:
        no_key_counter = 0
        
        # Hauptschleife (läuft mit ca. 50 Hz durch den Timeout in get_key)
        while rclpy.ok():
            key = get_key(settings, timeout=0.02)
            
            if key != '':
                no_key_counter = 0 # Totmannschalter zurücksetzen
                
                # --- Beenden ---
                if key == '\x03': # STRG+C
                    break
                
                # --- Geschwindigkeitskontrolle ---
                elif key == '+':
                    node.speed_scale += 0.05
                    print(f"Geschwindigkeit: {node.speed_scale:.2f}\r")
                elif key == '-':
                    node.speed_scale = max(0.01, node.speed_scale - 0.05)
                    print(f"Geschwindigkeit: {node.speed_scale:.2f}\r")
                
                # --- Gelenk-Auswahl (1-6) ---
                elif key in ['1', '2', '3', '4', '5', '6']:
                    node.active_joint_idx = int(key) - 1
                    print(f"Aktives Gelenk geändert auf: {node.active_joint_idx + 1}\r")
                
                # --- Joint Jogging ---
                elif key == 'r':
                    node.mode = "JOINT"
                    node.target_joint_vel = 1.0
                elif key == 'f':
                    node.mode = "JOINT"
                    node.target_joint_vel = -1.0
                
                # --- Twist (Kartesisch) ---
                elif key == 'w':
                    node.mode = "TWIST"; node.target_twist = [1.0, 0.0, 0.0]
                elif key == 's':
                    node.mode = "TWIST"; node.target_twist = [-1.0, 0.0, 0.0]
                elif key == 'a':
                    node.mode = "TWIST"; node.target_twist = [0.0, 1.0, 0.0]
                elif key == 'd':
                    node.mode = "TWIST"; node.target_twist = [0.0, -1.0, 0.0]
                elif key == 'q':
                    node.mode = "TWIST"; node.target_twist = [0.0, 0.0, 1.0]
                elif key == 'e':
                    node.mode = "TWIST"; node.target_twist = [0.0, 0.0, -1.0]
                
                # --- Stop ---
                elif key == ' ':
                    node.target_twist = [0.0, 0.0, 0.0]
                    node.target_joint_vel = 0.0
            
            else:
                # Totmannschalter: Wenn ~0.1 Sekunden (5 Loops) keine Taste gedrückt wird, stoppen.
                no_key_counter += 1
                if no_key_counter > 5:
                    node.target_twist = [0.0, 0.0, 0.0]
                    node.target_joint_vel = 0.0

            # Befehl immer senden (erhält den Servo am Leben und verhindert Timeout-Fehler)
            node.publish_command()
            rclpy.spin_once(node, timeout_sec=0)

    except Exception as e:
        print(e)
    finally:
        # Terminal-Einstellungen zwingend wiederherstellen!
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        
        # Abschließender Stopp-Befehl
        node.target_twist = [0.0, 0.0, 0.0]
        node.target_joint_vel = 0.0
        node.publish_command()
        
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()