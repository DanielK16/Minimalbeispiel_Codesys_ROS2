Übersicht was welche file macht:

tcp_pose.py: Published transformation zwischen base_link(g_flange) und tcp_link(joint6_flange) als neues topic /tcp_pose
status_client.py : Aktelle Positionsinformationen von ros2 -> codesys
command_client.py : Codesys -> ROS2 -> Servo ansteuerung der einzelnen Achsen
action_client.py : Ansteuerung der Action /move_action