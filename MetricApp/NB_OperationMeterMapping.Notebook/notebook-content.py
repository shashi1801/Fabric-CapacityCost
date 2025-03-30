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

pip install html-table-parser-python3

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import urllib.request
from pprint import pprint
from html_table_parser.parser import HTMLTableParser
import pandas as pd
from pyspark.sql.functions import lower, col,trim,regexp_replace

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Opens a website and read its
# binary contents (HTTP Response Body)
def url_get_contents(url):

    # Opens a website and read its
    # binary contents (HTTP Response Body)

    #making request to the website
    req = urllib.request.Request(url=url)
    f = urllib.request.urlopen(req)

    #reading contents of the website
    return f.read()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# defining the html contents of a URL.
xhtml = url_get_contents('https://learn.microsoft.com/en-us/fabric/enterprise/fabric-operations').decode('utf-8')

# Defining the HTMLTableParser object
p = HTMLTableParser()

# feeding the html contents in the
# HTMLTableParser object
p.feed(xhtml)

# Now finally obtaining the data of
# the table required
pdf_list =[]
for table in p.tables:
    pdf=pd.DataFrame(table)
    pdf.columns = pdf.iloc[0]
    pdf.columns = pdf.columns.str.lower().str.replace(' ', '_')
    pdf=pdf[1:]
    pdf.reset_index(drop=True,inplace=True)
    pdf_list.append(pdf)
union_pdf=pd.concat(pdf_list)
mapping_df=spark.createDataFrame(union_pdf)


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

mapping_df=mapping_df.withColumn("azure_billing_meter",regexp_replace(col("azure_billing_meter"),"Operations via API","Operations via Proxy"))
mapping_df=mapping_df.withColumn("operation_cleaned", trim(lower(regexp_replace(col("operation"), "[^a-zA-Z]", ""))))
mapping_df=mapping_df.withColumn("azure_billing_meter_cleaned", trim(lower(regexp_replace(col("azure_billing_meter"), "[^a-zA-Z]", ""))))

mapping_df.select('operation','azure_billing_meter','operation_cleaned','azure_billing_meter_cleaned').distinct().write.format('delta').mode('overwrite').option("mergeSchema","true").save('Tables/dbo/OperationAzureMeterMapping')


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

#mapping_df.select('azure_billing_meter_cleaned','azure_billing_meter').distinct().write.format('delta').mode('overwrite').option("mergeSchema","true").save('Tables/dbo/Meter')


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

data=[
    {"operation":"OneLake Storage" , "azure_billing_meter":"OneLake Storage Data Stored"}
    ,{"operation":"Eventhouse Standard Storage" , "azure_billing_meter":"OneLake Storage Data Stored"}
    ,{"operation":"Eventhouse Cache Storage" , "azure_billing_meter":"OneLake Cache Data Stored"}
    ,{"operation":"XMLA Read Operation" , "azure_billing_meter":"Power BI Capacity Usage CU"}
    ,{"operation":"XMLA Write Operation" , "azure_billing_meter":"Power BI Capacity Usage CU"}
    ,{"operation":"Web Modeling Read Operation" , "azure_billing_meter":"Power BI Capacity Usage CU"}
    ,{"operation":"Web Modeling Write Operation" , "azure_billing_meter":"Power BI Capacity Usage CU"}
    ,{"operation":"Notebook HC run" , "azure_billing_meter":"Spark Memory Optimized Capacity Usage CU"}
    ,{"operation":"Eventstream Connector Per vCore-hour" , "azure_billing_meter":"Eventstream Connector Capacity Usage CU"}
    ,{"operation":"Dataset Scheduled Refresh" , "azure_billing_meter":"Power BI Capacity Usage CU"}
    ,{"operation":"Dataset On-Demand Refresh" , "azure_billing_meter":"Power BI Capacity Usage CU"}
    ,{"operation":"Notebook HC Pipeline Run" , "azure_billing_meter":"Spark Memory Optimized Capacity Usage CU"}
    
]
df=spark.createDataFrame(data)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

mapping_df=df.withColumn("operation_cleaned", trim(lower(regexp_replace(col("operation"), "[^a-zA-Z]", ""))))
mapping_df=mapping_df.withColumn("azure_billing_meter_cleaned", trim(lower(regexp_replace(col("azure_billing_meter"), "[^a-zA-Z]", ""))))
mapping_df=mapping_df.select('operation','azure_billing_meter','operation_cleaned','azure_billing_meter_cleaned').distinct()
#.write.format('delta').mode('overwrite').option("mergeSchema","true").save('Tables/dbo/OperationAzureMeterMapping')


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from delta import DeltaTable

table = DeltaTable.forPath(spark,"Tables/dbo/OperationAzureMeterMapping")
table.alias("T").merge(
    mapping_df.alias("S")
    ,"""T.operation_cleaned = S.operation_cleaned
    """
).whenMatchedUpdateAll(
).whenNotMatchedInsertAll(
).execute()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

table = DeltaTable.forPath(spark,"Tables/dbo/OperationAzureMeterMapping")
meter_df= table.toDF()
meter_df.select('azure_billing_meter_cleaned','azure_billing_meter').distinct().write.format('delta').mode('overwrite').option("mergeSchema","true").save('Tables/dbo/Meter')


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
