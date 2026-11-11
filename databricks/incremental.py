# Databricks notebook source
from pyspark.sql import Window
from pyspark.sql import functions as F

# COMMAND ----------


def to_silver(bronze_df):
    w = Window.partitionBy(
        "departure_station_id", "vehicle_id", "scheduled_at"
    ).orderBy(F.col("snapshot_at").desc())

    dep = bronze_df.select(
        "stationinfo",
        "timestamp",
        "_source_file",
        F.explode("departures.departure").alias("d"),
    )
    return (
        dep.select(
            F.col("stationinfo.id").alias("departure_station_id"),
            F.col("stationinfo.standardname").alias("departure_station_name"),
            F.timestamp_seconds(F.col("timestamp").cast("long")).alias("snapshot_at"),
            F.timestamp_seconds(F.col("d.time").cast("long")).alias("scheduled_at"),
            F.col("d.delay").cast("int").alias("delay_s"),
            F.col("d.canceled").cast("boolean").alias("canceled"),
            F.col("d.isExtra").cast("boolean").alias("is_extra"),
            F.col("d.stationinfo.id").alias("destination_station_id"),
            F.col("d.vehicle").alias("vehicle_id"),
            F.col("d.vehicleinfo.type").alias("train_type"),
            F.col("d.platform").alias("platform"),
            F.col("_source_file"),
        )
        .withColumn("rn", F.row_number().over(w))
        .filter(F.col("rn") == 1)
        .drop("rn")
    )


# COMMAND ----------

import zipfile

zipfile.ZipFile("/Volumes/workspace/default/irail/bronze.zip").extractall(
    "/Volumes/workspace/default/irail/bronze/liveboard/"
)


# COMMAND ----------

bronze = spark.read.json(
    "/Volumes/workspace/default/irail/bronze/liveboard/date=2026-11-05/"
).select(
    "*",
    F.col("_metadata.file_path").alias("_source_file"),
    F.current_timestamp().alias("_ingested_at"),
)

print(spark.table("workspace.bronze.liveboard").count())
print(to_silver(spark.table("workspace.bronze.liveboard")).count())

# COMMAND ----------

bronze06 = spark.read.json(
    "/Volumes/workspace/default/irail/bronze/liveboard/date=2026-11-06/"
).select(
    "*",
    F.col("_metadata.file_path").alias("_source_file"),
    F.current_timestamp().alias("_ingested_at"),
)
bronze06.write.mode("append").saveAsTable("workspace.bronze.liveboard")
silver06 = to_silver(bronze06)
print(spark.table("workspace.bronze.liveboard").count())  # 1 800
silver06 = to_silver(bronze06)
print(silver06.count())  # 1 176
silver06.createOrReplaceTempView("lot")

# COMMAND ----------

spark.sql("""
MERGE INTO workspace.silver.liverboard AS t
USING lot AS s
ON t.departure_station_id = s.departure_station_id
AND t.vehicle_id = s.vehicle_id
AND t.scheduled_at = s.scheduled_at
WHEN MATCHED AND s.snapshot_at > t.snapshot_at THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
""")

# COMMAND ----------

silver = spark.table("workspace.silver.liverboard")

gold = silver.groupBy("departure_station_id", "departure_station_name").agg(
    F.count("*").alias("number_of_departures"),
    F.round(F.avg(F.when(~F.col("canceled"), F.col("delay_s") / 60)), 2).alias(
        "avg_delay_minutes"
    ),
    F.round(
        100
        * F.count(F.when((F.col("delay_s") == 0) & ~F.col("canceled"), 1))
        / F.count(F.when(~F.col("canceled"), 1)),
        2,
    ).alias("on_time_percentage"),
    F.count(F.when(F.col("canceled"), 1)).alias("number_of_cancellations"),
)
gold.show(truncate=False)
gold.write.mode("overwrite").option("mergeSchema", "true").saveAsTable(
    "workspace.gold.punctuality"
)

# COMMAND ----------

bronze = spark.table("workspace.bronze.liveboard")
dernier = bronze.agg(F.max(F.col("timestamp").cast("long"))).first()[
    0
]  # la photo la plus récente (secondes Unix)

lot = to_silver(
    bronze.filter(F.col("timestamp").cast("long") >= dernier - 3 * 24 * 3600)
)
lot.createOrReplaceTempView("lot")

# COMMAND ----------

silver = spark.table("workspace.silver.liverboard")
silver.count()
