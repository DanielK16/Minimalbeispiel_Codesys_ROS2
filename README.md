# Minimalbeispiel für Datenaustausch zwischen ROS2 und Codesys via OPC UA
Das Ziel ist es mithilfe von **turlesim** den Datenaustausch zwischen ROS2 und Codesys darzustellen und zu erlernen wie OPC UA dafür eingebaut und genutzt werden kann.
turtlesim ist ein Einsteigertool um ROS2 Konzepte zu erlernen.
Das Gesamtsystem besteht aus:
* ROS2 Simulation turtlesim
* OPC UA Brücke(asyncua)
* Codesys VSPS und Visualisierung


# Einrichtung der Entwicklungsumgebung:
0. WSL2 einrichten
In Windows Power Shell:
```
wsl --install -d Ubuntu-24.04
```
Anschließend Benutzer und Passwort festlegen
wsl kann gestartet werden mit: ``` wsl ```

1. Github in WSL Workspace clonen
In WSL:
```
git clone https://github.com/DanielK16/Minimalbeispiel_Codesys_ROS2.git
```
2. Dockerfile -> Image
Im Github liegt ein Dockerfile ab unter /Minimalbeispiel_Codesys_ROS2
Passe `--build-arg` an, ob ROS 2 **Humble** oder **Jazzy** benötigt wird:
```
docker build -t --build-arg ROS_DISTRO=humble <image_name> .
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
docker exec -it <image_name> bash
```

4. Codesys Projekt öffnen und mit Deploy Tool Container einrichten
Die Einrichtung mit dem Deploy Tool ist weiter unten ausführlich erklärt

5. ROS2 Projekt bauen mit apt-get update, rosdep update, rosdep install..., colcon build
```
sudo apt update
sudo apt upgrade -y
cd ros2_ws
rosdep init
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build
cd src
source install/setup.bash
```


# Entwicklungsumgebung
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

# Datenaustausch ROS2 und Codesys
Für Datenaustausch zwischen ROS2 und Codesys gibt es generell 3 Möglichkeiten:
- Shared Memory (IPC) -> z.B: ROBIN Projekt
- Feldbusse (ModbusTCP, EtherCAT, ...)
- Netzwerkprotokolle (OPC UA, MQTT, rosbridge)

Entschieden für OPC UA, da industrieller Standard und "einfach" zu implementieren.
![Datenaustausch ROS2 und Codesys](/doc/img/Datenaustausch_Codesys_ROS2.png)

Für die OPC UA Kommunikation wird das [opcua-asyncio](https://github.com/FreeOpcUa/opcua-asyncio) verwendet.

https://github.com/FreeOpcUa/opcua-asyncio

# Beispiel
![Beispielsdarstellung](/doc/vid/codesys_ros2_minimalbeispiel.gif)

In diesem Beispiel wird der Datenaustausch wird der Datenaustausch in beide Richtungen getestet:
Einmal von ROS2 -> Codesys: In diesem Fall wird die Position der Schildkröte übertragen und in Codesys angezeigt.
Dabei wird zunächst auf das topic /tutle1_pose subscribed und dann die variablen in die Itemliste geschrieben.
Codesys -> ROS2: Steuerung der Schildkröte mit Tastern
Dafür werden die Items in Variablenlsite beschrieben und bei Datenänderung dann von mit einer ros2 node gepublished.

# Setup für OPC UA Verbindung

# Setup für CODESYS Virtual Control for Linux SL
### 1. Deploy Tool installieren 
Folgende Tools sind mit dem **Codesys Install Manager** zu installieren:
* 'CODESYS Virtual Control for Linux SL'
* 'CODESYS Control SL Deploy Tool'

### 2. Verbindung zu WSL herstellen (SSH)
SSH muss installiert und aktiviert sein unter WSL:
```bash
sudo apt update && sudo apt install -y openssh-server
service ssh start
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


# Aufbau tf transformations mycobot280
Um den Aufbau des Transformationen Baums zu sehen kann man folgendes tool verwenden:
tf2 übernimmt für uns die Arbeit der Transformationen!
```
ros2 run tf2_tools view_frames
```
![tf2_baum für mycobot280](/doc/img/tf2_Transformation.png)



# Simulation des mycobot280 arm mit RVIZ2




## Aufbau OPC UA Clients
Aufteilung der OPC UA Kommunikation in drei OPC Clients.

**RobotStatus Client**:
- ist für den Datenaustausch ROS2 -> Codesys verantworlich. Client subscribed auf die Daten /joint_states und /tcp_pose und Daten werden dann an Codesys übertragen. Die Orientierung des TCP wird in ROS2 üblicherweise in Quaternions ausgegeben. Die Umrechnung von Quaternions -> Euler Winkel findet dann in Codesys statt.
**RobotCommand Client**:
ist für den Datenaustausch Codesys -> ROS2 verantwortlich. Dabei soll der Roboter manuell angesteuert werden. 
**RobotAction Client**:
ist für den Datenaustauch ROS2<->Codesys verantwortlich. Steuert RVIZ über MoveIt an!  

## Variablentypen ROS2 und IEC 61131-3
|**ROS2**|**IEC 66131-3**|
|---|---|
|Bool|BOOL|
|float64|LREAL|
|float32|REAL|
|int32|DINT|
|int16|INT|
|string|STRING|

## Aufbau des OPC UA Adressraums

## Aufbau der Codesys Visualisierung
