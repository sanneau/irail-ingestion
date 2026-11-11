# Databricks notebook source
import zipfile

zipfile.ZipFile("/Volumes/workspace/default/irail/bronze07.zip").extractall(
    "/Volumes/workspace/default/irail/bronze/liveboard/"
)

# COMMAND ----------

from pyspark.sql import functions as F

source = "/Volumes/workspace/default/irail/bronze/liveboard/"
checkpoint = "/Volumes/workspace/default/irail/_checkpoints/bronze_liveboard_stream/"

flux = (
    spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", checkpoint)  # où mémoriser le schéma déduit
    .load(source)
    .select(
        "*",
        F.col("_metadata.file_path").alias("_source_file"),
        F.current_timestamp().alias("_ingested_at"),
    )
)

(
    flux.writeStream.option(
        "checkpointLocation", checkpoint
    )  # où noter les fichiers déjà lus
    .trigger(availableNow=True)
    .toTable("workspace.bronze.liveboard_stream")
    .awaitTermination()
)  # attendre la fin avant la cellule suivante

print(spark.table("workspace.bronze.liveboard_stream").count())

# COMMAND ----------

print(spark.table("workspace.bronze.liveboard_stream").count())
display(
    spark.sql("""
  SELECT _source_file, count(*) AS n
  FROM workspace.bronze.liveboard_stream
  GROUP BY _source_file
  HAVING count(*) > 1
""")
)

# COMMAND ----------

(
    flux.writeStream.option("checkpointLocation", checkpoint)
    .trigger(availableNow=True)
    .toTable("workspace.bronze.liveboard_stream")  # ← guillemets
    .awaitTermination()
)
