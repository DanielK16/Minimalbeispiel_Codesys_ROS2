## Übersicht der Programme

| Datei | Richtung | Beschreibung |
|---|---|---|
| `tcp_pose.py` | ROS2 → ROS2 | Liest die tf2-Transformation zwischen `base_link` (`g_flange`) und `tcp_link` (`joint6_flange`) und veröffentlicht sie als Pose auf dem Topic `/tcp_pose` |
| `status_client.py` | ROS2 → CODESYS | Überträgt die aktuellen Positionsdaten (`/joint_states`, `/tcp_pose`) per OPC UA an die SPS |
| `command_client.py` | CODESYS → ROS2 | Empfängt Handbefehle von der SPS und verfährt die einzelnen Achsen über MoveIt Servo |
| `action_client.py` | CODESYS ↔ ROS2 | Empfängt Fahraufträge von der SPS, sendet sie als Goal an die MoveIt-Action `/move_action` und meldet den Fehlercode zurück |