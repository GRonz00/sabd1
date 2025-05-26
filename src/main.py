import csv
import os
import time

from pyspark.sql import SparkSession, DataFrame
from typing import Callable, Dict, Tuple, List

from pyspark.sql.functions import col, year, month, to_date,  avg, lit
from pyspark.sql.functions import min as minspa
from pyspark.sql.functions import max as maxspa

def analysis(formato: str)->List[Tuple[int,str,str,float,float]]:
    #query,tipo,tempo caricamente, tempo esecuzione
    t: List[Tuple[int,str,str,float,float]]=[]
    spark = (
        SparkSession.Builder()
        .appName("sabd")
        .getOrCreate()
    )

    # remove logging
    spark.sparkContext.setLogLevel("OFF")
    start = time.time()
    df = load_dataset(spark, "italy/italy_dataset."+formato)
    df = preProcessamento(df,formato).cache()
    # action on dataset loading (so the first query is not influenced by this)
    df.head()
    load_time = time.time() - start

    #Query2
    start = time.time()
    _,q2_cd, q2_ca, q2_rd, q2_ra = query2_df(df)
    q2_ca.collect()
    q2_cd.collect()
    q2_ra.collect()
    q2_rd.collect()
    t.append((2,"df",formato,load_time,time.time()-start))

    start = time.time()
    _, q2_cd, q2_ca, q2_rd, q2_ra = query2_rdd(df.rdd)
    len(q2_ca)
    t.append((2,"rdd",formato,load_time,time.time()-start))

    #Query1
    df.unpersist()
    start = time.time()
    df_sweden = load_dataset(spark, "sweden/sweden_dataset."+formato)
    df_sweden = preProcessamento(df_sweden, formato)
    df = df.unionByName(df_sweden).cache()
    df.head()
    load_time = load_time+time.time()-start
    start = time.time()
    q1 = query1_df(df)
    q1.collect()
    t.append((1,"df",formato,load_time,time.time()-start))

    start = time.time()
    q1_rdd = query1_rdd(df.rdd)
    q1_rdd.collect()
    t.append((1,"rdd",formato,load_time, time.time()-start))
    spark.stop()
    return t


def save_to_hdfs(df: DataFrame, file: str):
    (
        # write CSV file
        df.write.format("csv")
        # overwrite if it already exists
        .mode("overwrite")
        # include header
        .option("header", True)
        # save to HDFS
        .save(f"hdfs://master:54310{file}")
    )


def save_to_mongo(df: DataFrame, collection: str, mode="overwrite"):
    (
        # write to mongo
        df.write.format("mongodb")
        # overwrite or append
        .mode(mode)
        # to database
        .option("database", "spark")
        # to collection
        .option("collection", collection)
        .save()
    )


def query2_df(df: DataFrame):

    # Step 2: Raggruppamento per (anno, mese) e medie
    df_grouped = (
        df.groupBy("year", "month")
        .agg(
            avg("Carbon intensity gCO₂eq/kWh (direct)").alias("avg_carbon_intensity"),
            avg("Carbon-free energy percentage (CFE%)").alias("avg_cfe")
        )
    )

    # Step 3: Ordinamenti diversi
    top5_carbon_desc = df_grouped.orderBy("avg_carbon_intensity", ascending=False).limit(5)
    top5_carbon_asc = df_grouped.orderBy("avg_carbon_intensity", ascending=True).limit(5)

    top5_cfe_desc = df_grouped.orderBy("avg_cfe", ascending=False).limit(5)
    top5_cfe_asc = df_grouped.orderBy("avg_cfe", ascending=True).limit(5)
    return df_grouped,top5_carbon_desc,top5_carbon_asc,top5_cfe_desc,top5_cfe_asc

def query2_rdd(rdd):
    # Step 1: Mappatura verso ((anno, mese), (carbon, cfe, 1))
    rdd_mapped = rdd.map(lambda row: (
        (row[4], row[5]),  # chiave: (anno, mese)
        (row[2], row[3], 1)           # valori: (carbon, cfe, count)
    ))

    # Step 2: Aggregazione per somma
    rdd_aggregated = rdd_mapped.reduceByKey(lambda a, b: (
        a[0] + b[0],  # somma carbon intensity
        a[1] + b[1],  # somma CFE%
        a[2] + b[2]   # somma count
    ))

    # Step 3: Calcolo delle medie
    rdd_averages = rdd_aggregated.map(lambda kv: (
        kv[0],                          # (anno, mese)
        kv[1][0] / kv[1][2],           # media carbon
        kv[1][1] / kv[1][2]            # media cfe
    ))

    # Step 4: Ordinamento e top 5
    top5_carbon_desc = rdd_averages.sortBy(lambda x: -x[1]).take(5)
    top5_carbon_asc  = rdd_averages.sortBy(lambda x:  x[1]).take(5)
    top5_cfe_desc    = rdd_averages.sortBy(lambda x: -x[2]).take(5)
    top5_cfe_asc     = rdd_averages.sortBy(lambda x:  x[2]).take(5)

    return rdd_averages,top5_carbon_desc, top5_carbon_asc, top5_cfe_desc, top5_cfe_asc


def query1_df(df: DataFrame) -> DataFrame:
    return (
        df
        .groupBy("country","year")
        .agg(
            minspa("Carbon intensity gCO₂eq/kWh (direct)").alias("min_carbon_intensity"),
            maxspa("Carbon intensity gCO₂eq/kWh (direct)").alias("max_carbon_intensity"),
            avg("Carbon intensity gCO₂eq/kWh (direct)").alias("avg_carbon_intensity"),

            minspa("Carbon-free energy percentage (CFE%)").alias("min_cfe"),
            maxspa("Carbon-free energy percentage (CFE%)").alias("max_cfe"),
            avg("Carbon-free energy percentage (CFE%)").alias("avg_cfe")
        )
        .orderBy("country","year")
    )
def query1_rdd(rdd):
    # Step 1: Mappatura verso ((country, year), (carbon, cfe, carbon, cfe, carbon, cfe, 1))
    rdd_mapped = rdd.map(lambda row: (
        (row[1], row[4]),  # chiave: (country, year)
        (
            float(row[2]), float(row[3]),   # min
            float(row[2]), float(row[3]),   # max
            float(row[2]), float(row[3]),   # sum
            1                # count
        )
    ))

    # Step 2: Aggregazione per chiave
    rdd_aggregated = rdd_mapped.reduceByKey(lambda a, b: (
        min(a[0], b[0]), min(a[1], b[1]),   # min carbon, min cfe
        max(a[2], b[2]), max(a[3], b[3]),   # max carbon, max cfe
        a[4] + b[4], a[5] + b[5],           # somma carbon, somma cfe
        a[6] + b[6]                         # count
    ))

    # Step 3: Calcolo medie
    rdd_result = rdd_aggregated.map(lambda kv: (
        kv[0],                              # (country, year)
        kv[1][0], kv[1][2], kv[1][4] / kv[1][6],  # min, max, avg carbon
        kv[1][1], kv[1][3], kv[1][5] / kv[1][6]   # min, max, avg cfe
    ))

    return rdd_result

def load_dataset(spark: SparkSession, filename: str) -> DataFrame:
    # assign each file format into the corresponding reading function
    format_map: Dict[str, Callable[..., DataFrame]] = {
        "csv": spark.read.option("inferSchema", True).option("header", True).csv,
        "avro": spark.read.format("avro").load,
        "parquet": spark.read.parquet,
    }
    # get the file format
    format = filename.split(".")[-1]
    # call the read function for the file format
    return format_map[format](f"hdfs://master:54310/data/{filename}")
def preProcessamento(df: DataFrame, formato: str) -> DataFrame:
    if formato == "csv":
        return (
            df.select(
                col("Datetime (UTC)").alias("Datetime (UTC)"),
                col("Country"),
                col("Carbon intensity gCO₂eq/kWh (direct)").cast("float").alias("Carbon intensity gCO₂eq/kWh (direct)"),
                col("Carbon-free energy percentage (CFE%)").cast("float").alias("Carbon-free energy percentage (CFE%)")
            )
            .withColumn("year", year(to_date("Datetime (UTC)")))
            .withColumn("month", month(to_date("Datetime (UTC)")))
        )

    elif formato == "avro" or formato == "parquet":
        return (
            df.select(
                col("Datetime__UTC_").alias("Datetime (UTC)"),
                col("Country"),
                col("Carbon_intensity_gCO_eq_kWh__direct_").alias("Carbon intensity gCO₂eq/kWh (direct)"),
                col("Carbon_free_energy_percentage__CFE__").alias("Carbon-free energy percentage (CFE%)")
            )
            .withColumn("year", year(to_date("Datetime (UTC)")))
            .withColumn("month", month(to_date("Datetime (UTC)")))
        )

    else:
        raise ValueError("Formato non supportato")

def graphic():
    username = os.environ.get("MONGO_USERNAME")
    password = os.environ.get("MONGO_PASSWORD")
    # mongo connection uri
    uri = f"mongodb://{username}:{password}@mongo:27017/"
    spark = (
        # create new session builder
        SparkSession.Builder()
        # set session name
        .appName("sabd")
        # config mongo
        .config("spark.mongodb.write.connection.uri", uri)
        # create session
        .getOrCreate()
    )
    # load dataset
    df_italy = load_dataset(spark, "italy/italy_dataset.csv")
    df1 = preProcessamento(df_italy, "csv")
    df_sweden = load_dataset(spark, "sweden/sweden_dataset.csv")
    df = df_italy.unionByName(df_sweden)
    df = preProcessamento(df, "csv")
    q1 = query1_df(df)
    q1.show()
    save_to_hdfs(q1, "/results/query_1/")
    save_to_mongo(q1, "query_1")
    q2,top5_carbon_desc, top5_carbon_asc, top5_cfe_desc, top5_cfe_asc= query2_df(df1)
    save_to_hdfs(top5_carbon_asc, "/results/query_2_classifiche/ca/")
    save_to_hdfs(top5_carbon_desc, "/results/query_2_classifiche/cd/")
    save_to_hdfs(top5_cfe_asc, "/results/query_2_classifiche/cfea/")
    save_to_hdfs(top5_cfe_desc, "/results/query_2_classifiche/cfed/")
    save_to_hdfs(q2, "/results/query_2/")
    save_to_mongo(q2, "query_2")
    spark.stop()


def get_time():
    all_data: List[Tuple[int, str, str, float, float]] = []


    for _ in range(40):
        all_data.extend(analysis("avro"))
        all_data.extend(analysis("parquet"))
        all_data.extend(analysis("csv"))
    spark1 = (
        SparkSession.Builder()
        .appName("sabd")
        .getOrCreate()
    )

    # Crea DataFrame Spark da lista di tuple
    df = spark1.createDataFrame(
        all_data,
        schema=["Query", "Tipo", "Formato", "Load_time", "Exec_Time"]
    )
    df.show()

    df.coalesce(1).write.format("csv") \
        .mode("overwrite") \
        .option("header", True) \
        .save("hdfs://master:54310/results/times/")

    spark1.stop()
if __name__ == "__main__":
    get_time()
