import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

# Change this import if you are using a custom action or Nav2 (e.g., NavigateToPose)
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    MotionPlanRequest, Constraints, PositionConstraint, 
    JointConstraint, BoundingVolume, RobotState
)
from sensor_msgs.msg import JointState
from geometry_msgs.msg import Pose, Point
from moveit_msgs.msg import OrientationConstraint
from geometry_msgs.msg import Quaternion

from moveit.planning import MoveItPy

class MoveActionClient(Node):
    def __init__(self):
        super().__init__('move_action_client')

        self._action_client = ActionClient(self, MoveGroup, 'move_action')

    def send_move_goal(self):
        goal_msg = MoveGroup.Goal()
        req = MotionPlanRequest()

        req.pipeline_id = 'pilz_industrial_motion_planner'
        req.group_name = 'arm_group'
        req.planner_id = 'CIRC'
        req.allowed_planning_time = 2.0
        req.max_velocity_scaling_factor = 0.05
        req.max_acceleration_scaling_factor = 0.05
        req.num_planning_attempts = 10

        goal_msg.request = req

        self.get_logger().info('Waiting for move action server...')
        self._action_client.wait_for_server()

        self.get_logger().info('Sending CIRC goal to action server...')
        
        self._send_goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        
        self._send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Move goal was rejected by the server.')
            return

        self.get_logger().info('Move goal accepted! Executing...')
        
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        result = future.result().result
        status = future.result().status
        
        self.get_logger().info(f'Action completed with status: {status}')
        
        rclpy.shutdown()

    def feedback_callback(self, feedback_msg):

        feedback = feedback_msg.feedback
        self.get_logger().debug(f'Received feedback: {feedback}')


def main(args=None):
    rclpy.init(args=args)
    
    move_client = MoveActionClient()
    move_client.send_move_goal()
    
    try:
        rclpy.spin(move_client)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()