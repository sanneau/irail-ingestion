# Databricks notebook source
# MAGIC %sql
# MAGIC OPTIMIZE workspace.silver.liverboard

# COMMAND ----------

from pyspark.sql import functions as F

silver = spark.table("workspace.silver.liverboard")

(
    silver.withColumn(
        "partition", F.spark_partition_id()
    )  # nouvelle colonne : le n° du morceau de chaque ligne
    .groupBy("partition")
    .count()  # combien de lignes dans chaque morceau
    .show()
)

# COMMAND ----------

silver8 = silver.repartition(8)

(
    silver8.withColumn(
        "partition", F.spark_partition_id()
    )  # même pièce qu'à la cellule 1
    .groupBy("partition")
    .count()
    .show()
)

# COMMAND ----------

silver2 = silver8.coalesce(2)

(
    silver2.withColumn("partition", F.spark_partition_id())
    .groupBy("partition")
    .count()
    .show()
)


# COMMAND ----------

silver20 = silver8.coalesce(20)

(
    silver20.withColumn("partition", F.spark_partition_id())
    .groupBy("partition")
    .count()
    .show()
)

# COMMAND ----------

print("===== PLAN 1 : filter + select =====")
silver8.filter(F.col("canceled") == False).select(
    "departure_station_id", "delay_s"
).explain()

print("===== PLAN 2 : groupBy =====")
silver8.groupBy("departure_station_id").count().explain()

# COMMAND ----------

(
    silver.withColumn(
        "service_date", F.to_date("scheduled_at")
    )  # la date de chaque départ
    .write.mode("overwrite")
    .option("overwriteSchema", "true")
    .partitionBy("service_date")  # la colonne qui donne les dossiers
    .saveAsTable("workspace.silver.liveboard_by_date")
)  # une NOUVELLE table : la silver n'est pas touchée

# COMMAND ----------

# MAGIC %sql
# MAGIC SHOW PARTITIONS workspace.silver.liveboard_by_date

# COMMAND ----------

spark.table("workspace.silver.liveboard_by_date").filter(
    F.col("service_date") == "2026-11-06"
).explain()

# COMMAND ----------

# MAGIC %sql
# MAGIC DESCRIBE DETAIL workspace.silver.liveboard_by_date
