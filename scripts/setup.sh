#!/bin/bash

echo "Cleaning up"
docker compose stop
docker compose rm -f

echo "Starting Docker Compose"
docker compose up -d

echo "HDFS: mesg ttyname failed fix"
docker exec namenode sh -c \
  "echo '#!/bin/sh' > /usr/bin/mesg && chmod 755 /usr/bin/mesg"

echo "HDFS: formatting"
docker exec namenode sh -c \
  "hdfs namenode -format"

echo "HDFS: starting"
docker exec namenode sh -c \
  "/usr/local/hadoop/sbin/start-dfs.sh"

echo "HDFS: creating folders"
docker exec namenode sh -c \
  "hdfs dfs -mkdir /data"
docker exec namenode sh -c \
  "hdfs dfs -mkdir /results"

echo "HDFS: chown folders"
docker exec namenode sh -c \
  "hdfs dfs -chown nifi /data"
docker exec namenode sh -c \
  "hdfs dfs -chown spark /results"

echo "Spark: launching master"
docker exec spark-master sh -c \
  "/opt/spark/sbin/start-master.sh"

echo "Spark: launching workers"
docker exec spark-worker-1 sh -c \
  "/opt/spark/sbin/start-worker.sh spark://spark-master:7077"
docker exec spark-worker-2 sh -c \
  "/opt/spark/sbin/start-worker.sh spark://spark-master:7077"
docker exec spark-worker-3 sh -c \
  "/opt/spark/sbin/start-worker.sh spark://spark-master:7077"

echo "NiFi: running flow"
python -m venv .venv &> /dev/null
source .venv/bin/activate &> /dev/null
pip install -r requirements.txt &> /dev/null
python3 nifi/main.py
deactivate