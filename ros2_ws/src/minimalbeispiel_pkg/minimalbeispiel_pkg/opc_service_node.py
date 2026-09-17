import sys
import rclpy
from rclpy.node import Node
from turtlesim.srv import Spawn

import asyncio
import logging
from asyncua import Client, ua

class OPC_Service_Node(Node):
    def __init__(self):
        super().__init__("opc_service_node")
        # Service Client erstellen
        self.service_client = self.create_client(Spawn,'spawn')
        while not self.service_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not availablle, waiting...')
        self.req=Spawn.Request()

    def send_request(self, req_x, req_y, req_theta, req_name):
        self.req.x = req_x
        self.req.y = req_y
        self.req.theta = req_theta
        self.req.name = req_name
        return self.service_client.call_async(self.req)

class SubscriptionHandler:
    """ Handelt Kommunikation SPS -> ROS2 """
    def __init__(self, opc_knoten):
        self.opc_knoten = opc_knoten
        self.execute_service = False
        self.current_req_x = 0.0
        self.current_req_y = 0.0
        self.current_req_theta = 0.0
        self.current_req_name = ""

    def datachange_notification(self, node, val, data):
        if val != None: #wird benötigt weil sonst Fehlermeldung (es wird zuerst kurz None übertragen bevor val)
            if node == self.opc_knoten["req_x"]:
                self.current_req_x = float(val)
            elif node == self.opc_knoten["req_y"]:
                self.current_req_y = float(val)
            elif node == self.opc_knoten["req_theta"]:
                self.current_req_theta = float(val)
            elif node == self.opc_knoten["req_name"]:
                self.current_req_name = str(val)
            elif node == self.opc_knoten["xExecute"]:
                self.execute_service = bool(val)
        

async def async_main(args=None):

    # ROS2 Node starten
    ros_node = OPC_Service_Node()

    # OPC UA Verbindungsaufbau
    ipaddress = "172.25.170.32"
    port = "4840"
    opc_url = f"opc.tcp://{ipaddress}:{port}"

    async with Client(opc_url) as client:
        print(f"OPC Client: {opc_url} verbunden")
        
        # node holen
        opc_ziel_knoten = {
            # Request
            "req_x": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/AwdZ7tbmaM8h9s6Q=="),

            "req_y": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/AwdZ7tbmaM8h9t6Q=="),

            "req_theta": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/AwdZ7tbmaM8h9ggeY0dek="),

            "req_name": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/AwdZ7tbmaM8h96iO4lFA=="),

            "xExecute": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/AwdZ7tbmys+yV3nPclFA=="),
            # --- Response
            "xDone": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/AwdZ7tbmyt7C5x6Q=="),

            "resp_name": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/AwdZ7tbmaM8DBLh+Itcek="),

            "xError": client.get_node("ns=5;s=AQAAAKbhKnGK9zM6uvotdobvJ2ac8zBxx/AwdZ7tbmys8TJ7m4M=")
        }

        # OPC UA Subscription
        handler = SubscriptionHandler(opc_ziel_knoten)
        sub = await client.create_subscription(100,handler)         
        await sub.subscribe_data_change([
            opc_ziel_knoten["req_x"],
            opc_ziel_knoten["req_y"],
            opc_ziel_knoten["req_theta"],
            opc_ziel_knoten["req_name"],
            opc_ziel_knoten["xExecute"]
            ])

        # ROS2 Request senden
        active_future = None
        try:
            while rclpy.ok():
                rclpy.spin_once(ros_node, timeout_sec=0.0)
                # Service request an Server senden wenn anfrage von sps
                if handler.execute_service and active_future is None:
                    active_future = ros_node.send_request(
                        handler.current_req_x, 
                        handler.current_req_y, 
                        handler.current_req_theta, 
                        handler.current_req_name
                    )
                    handler.execute_service = False

                # Response vom Server abfragen und in SPS schreiben
                if active_future is not None and active_future.done():
                    if active_future.exception() != None:
                        await opc_ziel_knoten["xError"].write_value(True)
                        active_future=None
                        continue
                    response = active_future.result()
                    current_resp_name = response.name
                    await opc_ziel_knoten["resp_name"].write_value(str(current_resp_name))
                    await opc_ziel_knoten["xDone"].write_value(True)
                    active_future=None
                    
                await asyncio.sleep(0.01)
                
        except KeyboardInterrupt:
            pass
        finally:
            ros_node.destroy_node()

def main(args=None):
    rclpy.init(args=args)
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
