import rclpy
from moveit.planning import MoveItPy

def main(args=None):
    rclpy.init(args=args)

    print("--- Starte MoveItPy Test ---")
    
    # 1. Initialisiere MoveItPy (benötigt geladene Parameter!)
    moveit = MoveItPy(node_name="test_moveit_py")
    print("MoveItPy erfolgreich initialisiert!")

    # 2. Roboter-Modell Informationen auslesen
    robot_model = moveit.get_robot_model()
    print(f"Geladener Roboter: {robot_model.name}")
    print(f"Verfügbare Planungsgruppen: {robot_model.joint_model_group_names}")

    # 3. Planungskomponente (MoveGroup) testen
    # Wir nutzen "arm_group" basierend auf deiner MoveIt-Konfiguration
    try:
        arm = moveit.get_planning_component("arm_group")
        print("\nZugriff auf 'arm_group' erfolgreich!")
        
        # 4. Aktuellen Zustand des Roboters abfragen
        current_state = arm.get_start_state()
        print("Aktuelle Gelenkpositionen:")
        for joint, position in current_state.joint_positions.items():
            print(f"  {joint}: {position}")
            
    except Exception as e:
        print(f"\nFehler beim Zugriff auf die Planungsgruppe: {e}")

    print("\n--- Test erfolgreich abgeschlossen! ---")
    
    rclpy.shutdown()

if __name__ == '__main__':
    main()