# Dockerfile für ROS2 Jazzy und OPC UA Connection Minimalbeispiel
# Quellen:  YT Video: articulated robotics_ Crafting your dockerfile
# - https://docs.docker.com/reference/dockerfile/
# - https://docs.docker.com/engine/containers/run/
# - https://github.com/automaticaddison/mycobot_ros2/blob/lyrical/docker/Dockerfile

########################################
# Basis Image für ros2 jazzy mit desktop anwendungen (rviz2, gazebo ,rqt)
########################################
ARG ROS_DISTRO=jazzy
FROM osrf/ros:${ROS_DISTRO}-desktop-full
# muss nach FROM nochmals deklariert werden da sonst nicht gültig 
ARG ROS_DISTRO

########################################
# Environment Variablen anlegen
########################################
# verhindert Fehlermeldungen bei pip installs
ENV PIP_BREAK_SYSTEM_PACKAGES=1
# verhindert abfragen beim image bau -> Standard Werte werden verwendet
ENV DEBIAN_FRONTEND=noninteractive


########################################
# Anlegen eines non root users
########################################
#  Alten ubuntu-User (UID 1000) entfernen, falls vorhanden
RUN id -u 1000 &>/dev/null && userdel -r $(getent passwd 1000 | cut -d: -f1) || true

# ARG ohne Leerzeichen ausführen
ARG USERNAME=ros  
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd -s /bin/bash --uid $USER_UID --gid $USER_GID -m $USERNAME\
    && mkdir /home/$USERNAME/.config && chown $USER_UID:$USER_GID /home/$USERNAME/.config

# sudo rechte erteilen
RUN echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Alle Instruktionen danach werden als USER ros ausgeführt
USER ros

# Systemweite Packages müssen mit root erstellt werden
# der letzte erwähnte user wird wird als standarmäig gesetzt wenn container startet
# deswegen --user ros bei docker run
USER root

########################################
# Systeminstallation als root
########################################

# System Abhängigkeiten Installieren 
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    sudo \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Python Packages installieren
# --break-system-pacakges erforderlich da sonst error
RUN pip3 install asyncua --ignore-installed cryptography

# ROS2 packages installieren
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y ros-humble-pick-ik
########################################
# USER ros Umgebung einrichten
########################################
USER ros

# Arbeitsverzeichnis festlegen
# wird mit -w im docker run festgelegt
#WORKDIR /Projektarbeit_Koerper

# source ros2 direkt in .bashrc schreiben damit automatisch gesourced
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc


########################################
# Standardmäßiger Start des Containers
########################################
# standardmäßig root als user
# ros user wird über docker run engestellt mit --user ros
USER root

# Standard-Befehl beim Start des Containers welches programm er öffnen soll!
CMD ["bash"]

