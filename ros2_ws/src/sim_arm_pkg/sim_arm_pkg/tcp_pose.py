# Transformation vom base_link zum tcp_link
# diese Information wird auf ein neues topic /tcp_pose gepubished
# da kann ich schreiben wie transforms funktionieren entlang der kette. 
# theorie vom unterricht mit Matrizenmultiplikation!
import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Pose
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener
from tf2_ros import TransformException

class ROS_Node(Node):
    def __init__(self):
        super().__init__('ros_node')

        # declare parent and child frame -> auslesen aus tf baum
        self.parent_frame = "g_base"
        self.child_frame =  "joint6_flange"

        # receive tf2 transformmations and buffer them for up to 10 seconds
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer,self)

        # create publisher for /tcp_pose
        self.tcp_publisher = self.create_publisher(
            Pose,
            '/tcp_pose',
            10
        )

        # Call tf_timer function every 0.5 seconds
        self.tf_timer = self.create_timer(0.5, self.tf_tcp_timer)

    def tf_tcp_timer(self):

        # transformation "nachschauen"
        try: 
            t = self.tf_buffer.lookup_transform(
                self.parent_frame,
                self.child_frame,
                rclpy.time.Time())
        except TransformException as ex:
            self.get_logger().info(f"Could not transform {self.child_frame} to {self.parent_frame}: {ex}")
            return

        # Pose msg zusammenbauen
        msg = Pose()
        msg.position.x = t.transform.translation.x
        msg.position.y = t.transform.translation.y
        msg.position.z = t.transform.translation.z
        msg.orientation.x = t.transform.rotation.x
        msg.orientation.y = t.transform.rotation.y
        msg.orientation.z = t.transform.rotation.z
        msg.orientation.w = t.transform.rotation.w

        self.tcp_publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    ros_node = ROS_Node()
    rclpy.spin(ros_node)
    ros_node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()

