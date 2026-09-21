# Inhaltsverzeichnis
<details>
<summary><b>Klicke hier, um das Inhaltsverzeichnis aufzuklappen</b></summary>

* [0. Einrichtung der Entwicklungsumgebung](#0-einrichtung-der-entwicklungsumgebung)
  * [a. Übersicht Entwicklungsumgebung](#a-übersicht-der-entwicklungsumgebung)
  * [b. Installation der Entwicklungsumgebung](#b-installation-der-entwicklungsumgebung)
* [1. Minimalbeispiel für Datenaustausch zwischen ROS 2 und CODESYS via OPC UA](#1-minimalbeispiel-für-datenaustausch-zwischen-ros-2-und-codesys-via-opc-ua)
  * [a. Aufbau des OPC UA Adressraums](#a-aufbau-des-opc-ua-adressraums)
  * [b. Datenaustausch ROS 2 und CODESYS](#b-datenaustausch-ros-2-und-codesys)
  * [c. Start des Minimalbeispiels](#c-start-des-minimalbeispiels)
  * [d. Übersicht des Minimalbeispiels](#d-übersicht-des-minimalbeispiels)
* [2. Setup des OPC UA Servers](#2-setup-des-opc-ua-servers)
  * [a. Setup für CODESYS Virtual Control for Linux SL](#a-setup-für-codesys-virtual-control-for-linux-sl)
* [3. Simulation MyCobot 280](#3-simulation-mycobot-280)

</details>

# 0. Einrichtung der Entwicklungsumgebung:
<details>
<summary><b>Klicke hier, um Kapitel 0 aufzuklappen</b></summary>  

## a: Entwicklungsumgebung
|Tool|Version|Befehl zum Prüfen|
|---|---|---|
|Host Betriebssystem|WIN11|winver|
|Subsystem|WSL2: Ubuntu-24.04 | wsl -l -v|	
|Container Plattform|Docker Desktop 4.88.1|docker version|	
|SPS Entwicklungsumgebung|Codesys Development V3.5 SP22 Patch 2|Codesys Installer |
|SPS Runtime| CODESYS Virtual Runtime for Linux SL|Codesys Installer|
|ROS Distribution	|ROS2 Jazzy| echo $ROS_DISTRO|
|Versionsverwaltung|git 2.43.0| git --version|

![Entwicklungsumgebung Aufbau](/doc/img/Aufbau_Entwicklungsumgebung.png)

## b: Installation der Entwicklungsumgebung
0. WSL2 einrichten
In Windows Power Shell:
```
wsl --install -d Ubuntu-24.04
```
Anschließend Benutzer und Passwort festlegen.  
wsl kann gestartet werden mit: ``` wsl ```  
Für OPC UA wird später SSH benötigt:
```
sudo apt update && sudo apt install -y openssh-server
service ssh start
```

1. Github in WSL Workspace clonen
In WSL:  
```
git clone https://github.com/DanielK16/Minimalbeispiel_Codesys_ROS2.git
```
2. Dockerfile -> Image
Im Github liegt ein Dockerfile ab unter /Minimalbeispiel_Codesys_ROS2
Passe `--build-arg` an, ob ROS 2 **Humble** oder **Jazzy** benötigt wird:
```
docker build -t <image_name> --build-arg ROS_DISTRO=humble .
```

3. Image -> Container
eventuell -v anpassen je nachdem wohin github gecloned wurde!  
**auf Pfad achten -v!**  
```
docker run -it \
  --name minimalbsp_ros2_codesys \
  --user ros \
  --hostname ros_container \
  --network=host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v ~/Minimalbeispiel_Codesys_ROS2/ros2_ws:/home/ros/ros2_ws \
  -w /home/ros/ros2_ws \
  <image_name> \
  /bin/bash
```
4. Container starten mit:
```
docker start <container_name>
docker exec -it <container_name> bash
```

4. Codesys Projekt öffnen und mit Deploy Tool Container einrichten
Die Einrichtung mit dem Deploy Tool ist weiter unten ausführlich erklärt

5. ROS2 Projekt bauen
```
sudo apt update
sudo apt upgrade -y
cd ~/ros2_ws
rosdep init
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build
source install/setup.bash
```
</details>

# 1. Minimalbeispiel für Datenaustausch zwischen ROS2 und Codesys via OPC UA
<details>
<summary><b>Klicke hier, um Kapitel 1 aufzuklappen</b></summary>  

Das Ziel ist es mithilfe von **turlesim** den Datenaustausch zwischen ROS2 und Codesys darzustellen und zu erlernen wie OPC UA dafür eingebaut und genutzt werden kann.
turtlesim ist ein Einsteigertool um ROS2 Konzepte zu erlernen.
Das Gesamtsystem besteht aus:
* ROS2 Simulation turtlesim
* OPC UA Brücke(asyncua)
* Codesys VSPS und Visualisierung

## a: Aufbau des OPC UA Adressraums
Der Adressraum ist folgendermaßen aufgebaut:
![Adressraum Minimalbeispiel](/doc/img/Adressraum_Minimalbeispiel.png)

## b: Datenaustausch ROS2 Codesys
Für Datenaustausch zwischen ROS2 und Codesys gibt es generell 3 Möglichkeiten:
- Shared Memory (IPC) -> z.B: ROBIN Projekt
- Feldbusse (ModbusTCP, EtherCAT, ...)
- Netzwerkprotokolle (OPC UA, MQTT, rosbridge)
Entschieden für OPC UA, da industrieller Standard.

![Datenaustausch ROS2 und Codesys](/doc/img/Datenaustausch_Codesys_ROS2.png)
Die Topics aus ROS2 werden auf Structs in Codesys gemapped mit diesen dann der Adressraum aufgebaut wird.
Für die OPC UA Kommunikation wird das [opcua-asyncio](https://github.com/FreeOpcUa/opcua-asyncio) verwendet.

# c: Start des Minimalbeispiels
1. Stelle sicher das der ros2_ws korrekt gebaut wurde mit:
mit symlink install lassen sich python projekte ohne erneut bauen zu müssen ausführen!
```
cd ros2_ws
colcon build --packages-select minimalbeispiel_pkg --symlink-install
source install/setup.bash
```
2. Starten des OPC Servers in Codesys und Einloggen + Starten

3. Starten der turtlesim node und der kommunikations node in zwei separaten terminals
```
ros2 run turtlesim turtlesim_node
ros2 run minimalbeispiel_pkg opc_node 
```

# d: Übersicht des Minimalbeispiels
Beispielsvideo:  
![Beispielsdarstellung](/doc/vid/codesys_ros2_minimalbeispiel.gif)

In diesem Beispiel wird der Datenaustausch wird der Datenaustausch in beide Richtungen getestet:
Einmal von ROS2 -> Codesys: In diesem Fall wird die Position der Schildkröte übertragen und in Codesys angezeigt.
Dabei wird zunächst auf das topic /tutle1_pose subscribed und dann die variablen in die Itemliste geschrieben.
Codesys -> ROS2: Steuerung der Schildkröte mit Tastern
Dafür werden die Items in Variablenlsite beschrieben und bei Datenänderung dann von mit einer ros2 node gepublished.

</details>  

# 2. Setup für OPC UA Verbindung
<details>
<summary><b>Klicke hier, um Kapitel 2 aufzuklappen</b></summary>  

## a: Setup für CODESYS Virtual Control for Linux SL

### 1. Deploy Tool installieren 
Folgende Tools sind mit dem **Codesys Install Manager** zu installieren:
* 'CODESYS Virtual Control for Linux SL'
* 'CODESYS Control SL Deploy Tool'

### 2. Verbindung zu WSL herstellen (SSH)
SSH muss installiert und aktiviert sein unter WSL:
```bash
sudo apt update && sudo apt install -y openssh-server
sudo service ssh start
sudo service ssh status
``` 
![Einloggen in Codesys](/doc/img/einloggen_ssh_codesys.png)

### 3. Im Reiter **Bereitstellung** Images installieren
Folgende Images sind zu installieren:
* 'CODESYS Virtual Control for Linux SL Version 4.22.0(amd64)'
*  'CODESYS Virtual Edge Gateway for Linux Version 4.22.0(amd64)'
![Images installieren](/doc/img/images_v_sps_Codesys.png)

### 4. Im Reiter **Operation** Container starten
![Container VSPS starten](/doc/img/container_codesys_starten_v_sps.png)
![Container Edge Gateway starten](/doc/img//container_codesys_starten_edge.png)

### 5. Codesys Laufzeit Sicherheitsrichtlinie anpassen um anonymes einloggen zu erlauben
![Laufzeit Sicherheitsrichtlinie in Codesys anpassen!](/doc/img/cod_laufzeit_sicherheitsrichtlinie.png)

### 6. Verbindung Device herstellen
![Verbindung zum Device herstellen!](/doc/img/device_verbiindung_codesys.png)

</details>  

# 3. Simulation MyCobot280
<details>
<summary><b>Klicke hier, um Kapitel 3 aufzuklappen</b></summary>  

## a: Aufbau des transformations tree mycobot280
Um den Aufbau des Transformationen Baums zu sehen kann man folgendes tool verwenden:
tf2 übernimmt für uns die Arbeit der Transformationen!
```
ros2 run tf2_tools view_frames
```
![tf2_baum für mycobot280](/doc/img/tf2_Transformation.png)

## b: Aufbau OPC UA Clients
Aufteilung der OPC UA Kommunikation in drei OPC Clients.

![OPC Clients](/doc/img/ClientAufbau.png)

**RobotStatus Client**:
- ist für den Datenaustausch ROS2 -> Codesys verantworlich. Client subscribed auf die Daten /joint_states und /tcp_pose und Daten werden dann an Codesys übertragen. Die Orientierung des TCP wird in ROS2 üblicherweise in Quaternions ausgegeben. Die Umrechnung von Quaternions -> Euler Winkel findet dann in Codesys statt.
**RobotCommand Client**:
ist für den Datenaustausch Codesys -> ROS2 verantwortlich. Dabei soll der Roboter manuell angesteuert werden. 
**RobotAction Client**:
ist für den Datenaustauch ROS2<->Codesys verantwortlich. Steuert RVIZ über MoveIt an! Dafür wird ein Action Client erstellt auf die /move_action.  

## c: Variablentypen ROS2 und IEC 61131-3
|**ROS2**|**IEC 66131-3**|
|---|---|
|Bool|BOOL|
|float64|LREAL|
|float32|REAL|
|int32|DINT|
|int16|INT|
|string|STRING|

## Launch der ros2 Dateien
Zuerst in Codesys einloggen, dann ros2 launch!
```
cd ~/ros2_ws
source install/setup.bash
 ros2 launch sim_arm_pkg mycobot_launch.py 
ros2 launch sim_arm_pkg communication_launch.py 
```

## Aufbau des OPC UA Adressraums für mycobot Visualisierung  

<table>
  <tr>
    <td align="center">
      <img src="/doc/img/uaE_Base.png" width="100%"><br>
      <sub><b>Base</b></sub>
    </td>
    <td align="center">
      <img src="/doc/img/uaE_Status.png" width="100%"><br>
      <sub><b>Status</b></sub>
    </td>
    <td align="center">
      <img src="/doc/img/uaE_Command.png" width="100%"><br>
      <sub><b>Command</b></sub>
    </td>
    <td align="center">
      <img src="/doc/img/uaE_Action.png" width="100%"><br>
      <sub><b>Action</b></sub>
    </td>
  </tr>
</table>  

# Beispielsvideo zur Steuerung der Visualisierung
![Visualisierung Codesys](/doc/img/Visualisierung_Codesys.png)
## Manuelle Steuerung
![mycobot manuelle Steuerung](/doc/vid/mycobot_manuelle_steuerung.gif)

## Automatik Steuerung mit Bahnplanung durch MoveIt
Im Rahmen der aktuellen Projektumsetzung können vier verschiedene Ansätze bzw. Konfigurationen für die Bahnplanung realisiert werden:

* **OMPL (Open Motion Planning Library):**
  * Standardmäßig wird hierbei der Algorithmus *RRT (Rapidly-exploring Random Tree)* verwendet
  * Die Planung kann wahlweise im Gelenkraum (*Joint Space*) oder im kartesischen Raum (*Cartesian Space*) erfolgen.

* **Pilz Industrial Motion Planner:**
  * Ermöglicht die Bahnplanung ebenfalls wahlweise im Gelenk- oder im kartesischen Raum.
  * Unterstützt die standardisierten PTP (*Point-to-Point*), LIN (*Linear*) und CIR (*Circular*).
  * *Hinweis zum Implementierungsstatus:* PTP Bewegungen funktionieren oft fehlerfrei. LIN Bewegungen erfordern noch nicht zu komplett. CIRC muss noch implementiert werden
  * LIN schlägt häufiger fehl da mit 6 achsen nicht jede position linear angefahren werden kann! Orientierung muss übereinstimmen!


</details>  
