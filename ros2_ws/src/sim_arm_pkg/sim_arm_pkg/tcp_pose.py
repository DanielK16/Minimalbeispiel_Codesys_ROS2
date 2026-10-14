# Autor: Daniel Körper
# Code basiert auf Beispiel von:
# https://docs.ros.org/en/humble/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Listener-Py.html

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Pose

from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener
from tf2_ros import TransformException

# Laden der Config File
import yaml
with open("/home/ros/ros2_ws/src/sim_arm_pkg/config/opc_topic_config.yml", "r") as f:
    config = yaml.safe_load(f)

class ROS_Node(Node):
    def __init__(self):
        super().__init__('ros_node')
        
        self.parent_frame = config['tcp_pose']['parent_frame']
        self.child_frame =  config['tcp_pose']['child_frame']

        # Buffer erhält tf2 Transformation und buffert diese
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer,self)

        # Publisher für /tcp_pose
        self.tcp_publisher = self.create_publisher(
            Pose,
            '/tcp_pose',
            10
        )

        # alle 0.5 sekunden veröffentlichen
        self.tf_timer = self.create_timer(0.5, self.tf_tcp_timer)

    def tf_tcp_timer(self):

        # transformation "nachschauen"
        try: 
            t = self.tf_buffer.lookup_transform(
                self.parent_frame,
                self.child_frame,
                rclpy.time.Time()   #um aktuellsten Transform zu bekommen
                )
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
    try:
        rclpy.spin(ros_node)    # Spin in Endlosschleife
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            ros_node.destroy_node() 
            rclpy.shutdown()
    
if __name__ == "__main__":
    main()

