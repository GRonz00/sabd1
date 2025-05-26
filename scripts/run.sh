#!/usr/bin/env bash

docker exec spark-master sh -c \
  "/opt/spark/bin/spark-submit \
    --master spark://spark-master:7077 \
    --py-files /app/main.py \
    --conf \"spark.cores.max=3\" \
    --conf \"spark.executor.cores=1\" \
    --conf spark.driver.extraJavaOptions=\"-Divy.cache.dir=/tmp -Divy.home=/tmp\" \
    --packages org.apache.spark:spark-avro_2.12:3.5.5,org.mongodb.spark:mongo-spark-connector_2.12:10.5.0 \
    /app/main.py"

echo "HDFS: copy results into local fs"
docker exec namenode sh -c \
  "hdfs dfs -get /results/query_1/*.csv /app/results/query_1.csv"
docker exec namenode sh -c \
  "hdfs dfs -get /results/query_2_classifiche/cfea/*.csv /app/results/query_2/cfea.csv"
docker exec namenode sh -c \
  "hdfs dfs -get /results/query_2_classifiche/cfed/*.csv /app/results/query_2/cfed.csv"
docker exec namenode sh -c \
  "hdfs dfs -get /results/query_2_classifiche/cd/*.csv /app/results/query_2/cd.csv"
docker exec namenode sh -c \
  "hdfs dfs -get /results/query_2_classifiche/ca/*.csv /app/results/query_2/ca.csv"
docker exec namenode sh -c \
   "hdfs dfs -get /results/times/*.csv /app/results/times.csv"