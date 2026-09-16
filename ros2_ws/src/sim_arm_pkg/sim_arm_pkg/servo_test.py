import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped

class ServoTestNode(Node):
    def __init__(self):
        super().__init__('servo_test_node')
        self.pub = self.create_publisher(TwistStamped, '/servo_node/delta_twist_cmds', 10)
        # 0.1 Sekunden = 10 Hz
        self.timer = self.create_timer(0.1, self.publish_twist)

    def publish_twist(self):
        msg = TwistStamped()
        # Hier passiert die Magie: Frischer Zeitstempel für jede Nachricht!
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'g_base' # Ggf. an den Basis-Link des myCobot anpassen
        
        # 5 cm/s in X-Richtung
        msg.twist.linear.x = 0.05
        msg.twist.linear.y = 0.0
        msg.twist.linear.z = 0.0
        msg.twist.angular.x = 0.0
        msg.twist.angular.y = 0.0
        msg.twist.angular.z = 0.0
        
        self.pub.publish(msg)

def main():
    rclpy.init()
    node = ServoTestNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    rclpy.shutdown()

if __name__ == '__main__':
    main()