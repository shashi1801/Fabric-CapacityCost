# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "035b7f16-90b8-42a1-8af2-2d2c78f4a5ee",
# META       "default_lakehouse_name": "LH_CapacityMetric",
# META       "default_lakehouse_workspace_id": "a584c2c5-fdf7-4833-a5da-83feb8f2fe59"
# META     }
# META   }
# META }

# CELL ********************

from pyspark.sql.functions import col, year, month, expr
date_range = spark.range(0, 365).selectExpr("date_add('2025-01-01', cast(id as int)) as Date")

# Add Year and Month columns
date_table = date_range.withColumn("Year", year(col("Date"))).withColumn("Month", month(col("Date")))


date_table.write.format('delta').mode('overwrite').save('Tables/dbo/Date')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
