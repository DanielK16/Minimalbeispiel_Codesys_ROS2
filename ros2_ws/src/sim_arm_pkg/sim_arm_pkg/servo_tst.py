#!/usr/bin/env python3
import sys, select, termios, tty
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from std_srvs.srv import Trigger  # NEU: Import für den Service

class SimpleTeleop(Node):
    def __init__(self):
        super().__init__('keyboard_teleop')
        
        # Publisher für MoveIt Servo
        self.pub = self.create_publisher(TwistStamped, '/servo_node/delta_twist_cmds', 1)
        self.command_frame = 'g_base'  
        
        self.timer = self.create_timer(0.05, self.publish_twist)
        self.cmd = [0.0] * 6
        
        # Tastenbelegung
        self.keys = {
            'w': ( 1, 0, 0, 0, 0, 0), 's': (-1, 0, 0, 0, 0, 0),
            'a': ( 0, 1, 0, 0, 0, 0), 'd': ( 0,-1, 0, 0, 0, 0),
            'q': ( 0, 0, 1, 0, 0, 0), 'e': ( 0, 0,-1, 0, 0, 0),
            'u': ( 0, 0, 0, 1, 0, 0), 'o': ( 0, 0, 0,-1, 0, 0),
            'i': ( 0, 0, 0, 0, 1, 0), 'k': ( 0, 0, 0, 0,-1, 0),
            'j': ( 0, 0, 0, 0, 0, 1), 'l': ( 0, 0, 0, 0, 0,-1),
            ' ': ( 0, 0, 0, 0, 0, 0) # Leertaste = Stopp
        }

    def publish_twist(self):
        # Lese Taste ohne das Terminal zu blockieren
        if select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1)
            if key in self.keys:
                self.cmd = list(self.keys[key])
                
                # Terminal-Rückmeldung (mit Leerzeichen zum Überschreiben alter Zeilen)
                if key == ' ':
                    print("\r[STOPP] Bewegung angehalten.                  ", end="")
                else:
                    print(f"\r[AKTIV] Taste '{key}' gedrückt...             ", end="")
                
        # Twist-Nachricht aufbauen und senden
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.command_frame
        
        msg.twist.linear.x = self.cmd[0] * 0.05
        msg.twist.linear.y = self.cmd[1] * 0.05
        msg.twist.linear.z = self.cmd[2] * 0.05
        msg.twist.angular.x = self.cmd[3] * 0.1
        msg.twist.angular.y = self.cmd[4] * 0.1
        msg.twist.angular.z = self.cmd[5] * 0.1
        
        self.pub.publish(msg)

def main():
    rclpy.init()
    node = SimpleTeleop()
    
    # --- NEU: MoveIt Servo Service automatisch starten ---
    cli = node.create_client(Trigger, '/servo_node/start_servo')
    print("Warte auf Service '/servo_node/start_servo' (max 3 Sekunden)...")
    if cli.wait_for_service(timeout_sec=3.0):
        req = Trigger.Request()
        future = cli.call_async(req)
        # Wir warten kurz, bis der Service geantwortet hat
        rclpy.spin_until_future_complete(node, future)
        if future.result() is not None:
            print(f"[ERFOLG] Servo Node gestartet. Rückmeldung: {future.result().message}")
        else:
            print("[FEHLER] Service-Aufruf fehlgeschlagen.")
    else:
        print("[WARNUNG] Service nicht gefunden! Läuft der Servo Node?")
    # -----------------------------------------------------

    print("\nMinimaler Teleop gestartet.")
    print("Tasten: w/s/a/d/q/e für XYZ | u/o/i/k/j/l für Rotation | Leertaste für Stopp\n")
    
    # Terminal-Settings für rohes Einlesen erst NACH den ganzen print-Befehlen aktivieren
    old_attr = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Terminal wiederherstellen
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_attr)
        rclpy.shutdown()
        print("\nBeendet.")

if __name__ == '__main__':
    main()