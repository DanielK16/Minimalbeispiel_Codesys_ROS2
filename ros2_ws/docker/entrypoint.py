# Startet den OPCUA Client um die Softkeys aus Codesys zu verwenden!
import subprocess
import os
import signal

import asyncio
from asyncua import Client

# Verhindern, dass nicht doppelt gestartet wird!
RViz2_is_running = False
Communication_Clients_are_running = False
# Zu startende Prozesse
RViz2_process = None
Communication_process = None

def starte_RViz2_launch():
    global RViz2_is_running
    global RViz2_process
    # Verhindern, dass der Launch doppelt gestartet wird
    if RViz2_is_running is True and RViz2_process.poll() is None:
        print("RViz2 Launch läuft bereits!")
        return

    arbeitsverzeichnis = os.path.expanduser("~/ros2_ws")
    bash_command = "source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 launch sim_arm_pkg mycobot_launch.py"
    RViz2_process = subprocess.Popen(
        ["/bin/bash", "-c", bash_command],
        cwd=arbeitsverzeichnis,
        start_new_session=True
    )
    print("ROS 2 Launch gestartet.")
    RViz2_is_running = True

def stoppe_RViz2_launch():
    global RViz2_is_running
    global RViz2_process

    if RViz2_is_running is True:
        print("Sende Stopp-Signal an RViz2...")
        try:
            # Nur terminate beendet nicht alle ROS2 Prozess nicht!
            #RViz2_process.terminate() -> beendet nur PID des launches
            # alle zur Process Group gehörenden Programme killen! (PGID)
            os.killpg(os.getpgid(RViz2_process.pid), signal.SIGINT)
            RViz2_process.wait(timeout=5)
            print(f"RViz2 Launch erfolgreich beendet.")
            
        except Exception as e:
            print(f"Fehler beim Beenden: {e}")
        finally:
            RViz2_is_running = False
    else:
        print("Kein Prozess da zum stoppen!")

def start_communication_launch():
    global Communication_Clients_are_running
    global Communication_process
    if Communication_Clients_are_running is True and Communication_process.poll() is None:
            print("ROS 2 Launch läuft bereits!")
            return
    
    arbeitsverzeichnis = os.path.expanduser("~/ros2_ws")
    bash_command = "source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 launch sim_arm_pkg communication_launch.py"
        
    Communication_process = subprocess.Popen(
        ["/bin/bash", "-c", bash_command],
        cwd=arbeitsverzeichnis,
        start_new_session=True
    )
    print("ROS 2 Communication Launch gestartet.")
    Communication_Clients_are_running = True


def stoppe_communication_launch():
    global Communication_Clients_are_running
    global Communication_process

    if Communication_Clients_are_running is True:
        print("Sende Stopp-Signal an Communication Client...")
        try:
            os.killpg(os.getpgid(Communication_process.pid), signal.SIGINT)
            
            Communication_process.wait(timeout=5)
            print("ROS 2 Communication Launch erfolgreich beendet.")
            
        except Exception as e:
            print(f"Fehler beim Beenden: {e}")
        finally:
            Communication_Clients_are_running = False
    else:
        print("Kein Prozess da zum stoppen!")

class SubscriptionHandler:
    def datachange_notification(self, node, val, data):
        try:
            # Nur Ausführen wenn Wert auf True gesetzt wird
            if val == True:
                # Prüfen ob Name in NodeId vorkommt
                if "Start_RViz2" in str(node.nodeid):
                    starte_RViz2_launch()
                    
                elif "Stop_RViz2" in str(node.nodeid):
                    stoppe_RViz2_launch()
                    
                elif "Start_OPCClients" in str(node.nodeid):
                    start_communication_launch()
                    
                elif "Stop_OPC_Clients" in str(node.nodeid):
                    stoppe_communication_launch()
        except Exception as e:
            print(f"Fehler im Subscription Handler: {e}")

async def async_main():
    # Endlosschleife um sicher gegen Abstürze zu machen
    while True:
        try:
            # OPC UA Verbindung
            ipaddress = "172.25.170.32"
            port = "4840"
            opc_url = f"opc.tcp://{ipaddress}:{port}"
            async with Client(url = opc_url,
                            timeout = 2.0,
                            watchdog_intervall = 0.5, 
                            auto_reconnect = True,  
                            reconnect_max_delay = 5.0,    
                            reconnect_request_timeout = 5.0, ) as client:
                print(f"OPC Client verbunden: {opc_url}")

                Start_RViz2_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.Start_RViz2")
                Start_OPCClients_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.Start_OPCClients")
                Stop_OPCClients_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.Stop_OPC_Clients")
                Stop_RViz2_node = client.get_node("ns=4;s=|var|CODESYS Virtual Control for Linux SL.Application.GVL_OPCUA.Stop_RViz2")

                nodes = [
                    Start_RViz2_node,
                    Start_OPCClients_node,
                    Stop_OPCClients_node,
                    Stop_RViz2_node
                ]

                # create Subscription
                handler = SubscriptionHandler()
                subscription = await client.create_subscription(500, handler)
                await subscription.subscribe_data_change(nodes)

                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"Verbindungsabbruch: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("Str + C gedrückt: Beende alle ROS2 Prozesse")
        stoppe_communication_launch()
        stoppe_RViz2_launch()

        # beende alle übriggebliebenen ros2 nodes (nciht nötig da durch PGID terminiert)
        #subprocess.run(["pkill", "-9", "-f" "ros|rviz|spawner"])

        print("Alle Prozesse beendet!")