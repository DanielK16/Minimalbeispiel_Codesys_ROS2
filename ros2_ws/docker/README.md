# Übersicht: Docker-Images bauen und Container starten
Für jeden Roboter gibt es ein eigenes Dockerfile. Der Quellcode wird beim Build aus GitHub geladen. Nach dem Bauen des Images muss nur noch der Container gestartet werden.

| Roboter | Dockerfile | Image | Container | Branch |
|---|---|---|---|---|
| myCobot280 | `mycobot_dockerfile` | `mycobot280` | `mycobot280` | `main` |
| xArm6 | `xarm6_dockerfile` | `xarm6` | `xarm6` | `xArm6` |


## myCobot280 
### Image bauen
```
docker build -t mycobot280 --no-cache -f mycobot_dockerfile .
```

### Container starten
```
docker run -it \
  --name mycobot280 \
  --network host \
  -e OPC_IP=<IP der SPS> \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  mycobot280
```

## xArm6 
### Image bauen
```
docker build -t xarm6 --no-cache -f xarm6_dockerfile .
```

### Container starten
```
docker run -it \
  --name xarm6 \
  --network host \
  -e OPC_IP=<IP der SPS> \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  xarm6
```

## Hilfreiche Befehle für Docker
| Aufgabe | Befehl |
|---|---|
| Zweites Terminal im laufenden Container | `docker exec -it <container> bash` |
| Container löschen| `docker rm <container>` |
| Image neu bauen und dabei den aktuellen GitHub-Stand holen | `docker build --no-cache -t <image> -f <dockerfile> .` |
