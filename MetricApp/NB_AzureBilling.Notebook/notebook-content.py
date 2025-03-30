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

#!pip install azure-mgmt-costmanagement --q

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql.functions import lower, col,trim,regexp_replace
import requests
import json
from datetime import datetime,timedelta
from azure.identity import DefaultAzureCredential
from azure.identity import ManagedIdentityCredential
import pytz


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

try:
    df_max = spark.sql(f'''
    SELECT MAX(UsageDate) as MaxDate
    FROM dbo.AzureBillingCost WHERE UsageDate is not null
    '''
    )
    maxdate = df_max.first()['MaxDate']
except:
    maxdate = datetime.today().date() + timedelta(days=-20)
if not maxdate:
    maxdate = datetime.today().date() + timedelta(days=-20)
maxdatefortimeframe = (maxdate + timedelta(days=1))
enddatefortimeframe = (datetime.today().date() + timedelta(days=0))

if maxdatefortimeframe > enddatefortimeframe:
    raise ValueError("No data to pull")

# timezone = pytz.timezone("Asia/Kolkata")
# timezone.utcoffset
# timezone.localize(maxdatefortimeframe)
maxdatefortimeframe_str = maxdatefortimeframe.strftime("%Y-%m-%dT%H:%M:%S")
enddatefortimeframe_str = enddatefortimeframe.strftime("%Y-%m-%dT%H:%M:%S")



# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# from azure.identity import DefaultAzureCredential
# from azure.mgmt.costmanagement import CostManagementClient

# client = CostManagementClient()
# scope = "/subscriptions/709881c1-a52d-4c7b-8476-1c49d6432028"
# client.query.usage(scope,cost_payload)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************


# Azure Credentials
TENANT_ID = "XXXX"
CLIENT_ID = "XXXXX"
CLIENT_SECRET = "XXXXX"
SUBSCRIPTION_ID = "709881c1-a52d-4c7b-8476-1c49d6432028"


# Azure OAuth2 Token Endpoint
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/token"

# Get Access Token
token_payload = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "resource": "https://management.azure.com/"
}

token_response = requests.post(TOKEN_URL, data=token_payload)
token_data = token_response.json()

if "access_token" not in token_data:
    raise Exception("Failed to get access token: " + token_data.get("error_description", "Unknown error"))

ACCESS_TOKEN = token_data["access_token"]

COST_URL = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/providers/Microsoft.CostManagement/query?api-version=2024-08-01"

# API Request Body
cost_payload = {
    "type": "ActualCost",
    "timeframe": "Custom",
    "timePeriod":{
    "from": maxdatefortimeframe_str,  # Replace with your custom start date
    "to": enddatefortimeframe_str    # Replace with your custom end date
    },
    "dataset": {
        "granularity": "Daily",
        
        "filter": {
            "and": [
                {
                    "dimensions": {
                        "name": "SubscriptionId",
                        "operator": "In",
                        "values": [f"{SUBSCRIPTION_ID}"]
                    }
                },
                {
                    "dimensions": {
                        "name": "ResourceType",
                        "operator": "In",
                        "values": ["microsoft.fabric/capacities"]
                    }
                }
            ]
        },
        "aggregation": {
            "CostUSD": {
                "name": "PreTaxCost",
                "function": "Sum"
                },
            "UsageQuantity": {
                "name": "UsageQuantity",
                "function": "Sum"
            }
        },
        "grouping": [
            {
                "type": "Dimension",
                "name": "ResourceId"
            },
            {
                "type": "Dimension",
                "name": "Meter"
            },
            # {
            #     "type": "Dimension",
            #     "name": "UnitOfMeasure"
            # } ,
            {
                "type": "Dimension",
                "name": "ResourceGuid"
            }   ,
            {
                "type": "Dimension",
                "name": "MeterSubCategory"
            }      
            
        ]

    }
}


# Headers
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# Get Cost Data
cost_response = requests.post(COST_URL, headers=headers, json=cost_payload)
cost_response.headers
cost_response.raise_for_status()

cost_data = cost_response.json()



# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql.functions import col, year, month, to_date,split,lit
columns = [col['name'] for col in cost_data['properties']['columns']]
rows = cost_data['properties']['rows']
df =spark.createDataFrame(rows, columns)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

df_cleaned=df.withColumn('UsageDate',to_date(col("UsageDate").cast("string"), "yyyyMMdd"))
df_cleaned=df_cleaned.withColumn("ResourceName", split(col("ResourceId"), "/").getItem(8))
df_cleaned=df_cleaned.withColumn("Meter_cleaned", trim(lower(regexp_replace(col("Meter"), "[^a-zA-Z]", ""))))
df_cleaned=df_cleaned.withColumn("Rate",col('PreTaxCost')/col('UsageQuantity'))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

df_cleaned.write.format('delta').mode('append').option("mergeSchema","true").save('Tables/dbo/AzureBillingCost')

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
