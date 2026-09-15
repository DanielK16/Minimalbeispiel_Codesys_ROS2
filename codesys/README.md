## CODESYS-Projekte

Dieses Repository enthält zwei verschiedene CODESYS-Projekte, die unterschiedliche Ausbaustufen der Schnittstelle demonstrieren:

* **Minimalbeispiel (Turtlesim)**
  Dieses Projekt dient als *Proof of Concept*. Hier wird die grundsätzliche OPC UA Kommunikation zwischen ROS 2 und der CODESYS-SPS isoliert und vereinfacht anhand des `turtlesim`-Simulators getestet. Ideal, um das grundlegende Setup und den Datenaustausch zu verifizieren.

* **Simulation Roboterarm**
  Das Hauptprojekt für die industrielle Anwendung. Hier wird die OPC UA-Brücke genutzt, um komplexe Roboterkinematik (MoveIt 2 & RViz) mit der SPS zu verbinden. 
  