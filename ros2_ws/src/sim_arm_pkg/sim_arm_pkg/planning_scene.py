import rclpy
from rclpy.node import Node
from moveit_msgs.msg import CollisionObject
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose

class WallPublisher(Node):
    def __init__(self):
        super().__init__('wall_publisher')
        # Publisher für MoveIt Collision Objects
        self.publisher_ = self.create_publisher(CollisionObject, 'collision_object', 10)
        
        # Timer, um sicherzustellen, dass die Verbindung steht
        self.timer = self.create_timer(1.5, self.publish_wall)

    def publish_wall(self):
        co = CollisionObject()
        # Koordinatensystem anpassen (z.B. "world" oder "base_link")
        co.header.frame_id = "world"  
        co.id = "mauer_hindernis"

        # Definition der Form (Box: X, Y, Z Dimensionen in Metern)
        wall = SolidPrimitive()
        wall.type = SolidPrimitive.BOX
        wall.dimensions = [0.5, 0.1, 0.3]  # 10 cm dick, 1 m breit, 80 cm hoch

        # Position und Ausrichtung der Mauer im Raum
        pose = Pose()
        pose.position.x = 0.4  # 40 cm vor dem Roboter
        pose.position.y = 0.0  # Mittig
        pose.position.z = 0.2  # Auf halber Höhe
        pose.orientation.w = 1.0

        co.primitives.append(wall)
        co.primitive_poses.append(pose)
        co.operation = CollisionObject.ADD

        # Senden an MoveIt
        self.publisher_.publish(co)
        self.get_logger().info("Mauer wurde erfolgreich zur Planning Scene hinzugefügt!")
        self.timer.cancel()

def main(args=None):
    rclpy.init(args=args)
    node = WallPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()