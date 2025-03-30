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

!pip install semantic-link --q
 
import pandas as pd
import sempy.fabric as fabric
from datetime import datetime,date,timedelta
from pyspark.sql.functions import lower, col,trim,regexp_replace,concat_ws

#Update with names from your install of the Fabric Metrics Apps
#Note - This code works with V1.5 of Metrics App (March 2024). Breaking changes possible in later updates.
MetricsWS = "KPMG Microsoft Fabric Capacity Metrics"
MetricsModel = "Fabric Capacity Metrics"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

try:
    df_max = spark.sql(f'''
    SELECT MAX(Date) as MaxDate
    FROM dbo.CapacityUsageByItems;
    '''
    )
    maxdate = df_max.first()['MaxDate']
except:
    maxdate = datetime.today() + timedelta(days=-30)

maxdateforDAX = maxdate.strftime('%Y,%m,%d')

try:
    df_max = spark.sql(f'''
    SELECT MAX(Date) as MaxDate
    FROM dbo.StorageByWorkspaces;
    '''
    )
    st_maxdate = df_max.first()['MaxDate']
except:
    st_maxdate = datetime.today() + timedelta(days=-30)

st_maxdateforDAX = st_maxdate.strftime('%Y,%m,%d')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

metric_dax =f"""
// DAX Query
DEFINE
    VAR __yesterday = TODAY() - 1
	VAR __DS0FilterTable = 
		FILTER(
			KEEPFILTERS(VALUES('MetricsByItemandOperationandDay'[Date])),
			AND(
				'MetricsByItemandOperationandDay'[Date] > DATE({maxdateforDAX}),
				'MetricsByItemandOperationandDay'[Date] <= __yesterday
			)
		)
    
	VAR __DS0Core = 
		SUMMARIZECOLUMNS(
			'Items'[WorkspaceName],
			'Items'[ItemKind],
			'Items'[ItemName],
			'Items'[capacityId],
			'Items'[WorkspaceId],
			'MetricsByItemandOperationandDay'[Date],
			'MetricsByItemandOperationandDay'[OperationName],
			__DS0FilterTable,
			"sum_CU", CALCULATE(SUM('MetricsByItemandOperationandDay'[sum_CU])),
			"sum_duration", CALCULATE(SUM('MetricsByItemandOperationandDay'[sum_duration]))
		)
EVALUATE __DS0Core
"""
storage_dax =f"""
// DAX Query
DEFINE
    VAR __yesterday = TODAY() - 1
	VAR __DS0FilterTable = 
		FILTER(
			KEEPFILTERS(VALUES('StorageByWorkspacesandDay'[Date])),
			AND(
				'StorageByWorkspacesandDay'[Date] > DATE({st_maxdateforDAX}),
				'StorageByWorkspacesandDay'[Date] <= __yesterday
			)
		)
    
	VAR __DS0Core = 
		SUMMARIZECOLUMNS(
			
			'StorageByWorkspacesandDay'[WorkspaceId],
			'Workspaces'[WorkspaceName],
			'StorageByWorkspacesandDay'[PremiumCapacityId],
			'StorageByWorkspacesandDay'[WorkloadKind],
			'StorageByWorkspacesandDay'[WorkloadOperationKey],
			'StorageByWorkspacesandDay'[OperationName],
			'StorageByWorkspacesandDay'[Date],
			__DS0FilterTable,
			"UtilizationInGb", CALCULATE(SUM(StorageByWorkspacesandDay[Utilization (GB)])),
			"StaticStorageInGb", CALCULATE(SUM('StorageByWorkspacesandDay'[StaticStorageInGb]))
		)
EVALUATE __DS0Core
"""

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

pdf_capacity_metrics = fabric.evaluate_dax(workspace=MetricsWS, dataset=MetricsModel, dax_string=metric_dax)
pdf_capacity_storage_metrics = fabric.evaluate_dax(workspace=MetricsWS, dataset=MetricsModel, dax_string=storage_dax)
pdf_capacities = fabric.evaluate_dax(workspace=MetricsWS, dataset=MetricsModel, dax_string='EVALUATE Capacities')
pdf_Workspaces = fabric.evaluate_dax(workspace=MetricsWS, dataset=MetricsModel, dax_string='EVALUATE Workspaces')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

df_capacities=spark.createDataFrame(pdf_capacities)
new_column_names = [col_name.split('[')[-1].replace("]", "").replace(" ","") for col_name in df_capacities.columns]
df_capacities=df_capacities.toDF(*new_column_names)
df_capacities.write.format('delta').mode('overwrite').save('Tables/dbo/Capacities')

df = spark.sql("SELECT * FROM LH_CapacityMetric.dbo.Meter LIMIT 1000")
display(df)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

df_Workspaces=spark.createDataFrame(pdf_Workspaces)
new_column_names = [col_name.split('[')[-1].replace("]", "").replace(" ","") for col_name in df_Workspaces.columns]
df_Workspaces=df_Workspaces.toDF(*new_column_names)
df_Workspaces=df_Workspaces.withColumn("CapacityWorkspaceKey",concat_ws("-",col("PremiumCapacityId"),col("WorkspaceId")))
df_Workspaces.write.format('delta').mode('overwrite').option("overwriteSchema", "true").save('Tables/dbo/Workspaces')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

if len(pdf_capacity_metrics)>0:
    df_capacity_metrics=spark.createDataFrame(pdf_capacity_metrics)
    new_column_names = [col_name.split('[')[-1].replace("]", "") for col_name in df_capacity_metrics.columns]
    df_capacity_metrics=df_capacity_metrics.toDF(*new_column_names)
    df_capacity_metrics=df_capacity_metrics.withColumn("CapacityWorkspaceKey",concat_ws("-",col("capacityId"),col("WorkspaceId")))
    df_capacity_metrics=df_capacity_metrics.withColumn("OperationName_cleaned", trim(lower(regexp_replace(col("OperationName"), "[^a-zA-Z]", ""))))
    df_capacity_metrics.write.format('delta').mode('append').option("mergeSchema","true").save('Tables/dbo/CapacityUsageByItems')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

if len(pdf_capacity_storage_metrics)>0:
    df_capacity_storage_metrics=spark.createDataFrame(pdf_capacity_storage_metrics)
    new_column_names = [col_name.split('[')[-1].replace("]", "") for col_name in df_capacity_storage_metrics.columns]
    df_capacity_storage_metrics=df_capacity_storage_metrics.toDF(*new_column_names)
    df_capacity_storage_metrics=df_capacity_storage_metrics.withColumn("CapacityWorkspaceKey",concat_ws("-",col("PremiumCapacityId"),col("WorkspaceId")))
    df_capacity_storage_metrics=df_capacity_storage_metrics.withColumn("OperationName_cleaned", trim(lower(regexp_replace(col("OperationName"), "[^a-zA-Z]", ""))))
    df_capacity_storage_metrics.write.format('delta').mode('append').option("mergeSchema","true").save('Tables/dbo/StorageByWorkspaces')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
