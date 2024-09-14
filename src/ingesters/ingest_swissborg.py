import os

from pyspark.sql import Window
from pyspark.sql.functions import date_format, col, row_number, current_timestamp

from config import EXCHANGES_RAW_FILES, SWISSBORG_CSV_PATH, SCHEMAS_PATH, RAW_DB, SWISSBORG_RAW_TABLE, \
    SWISSBORG_EXCHANGE_NAME
from utils.spark_utils import get_spark, read_csv_to_df, write_table_in_postgres


def read_excel_to_csv(path: str, file: str) -> None:
    if file.__contains__(".xlsx"):
        print(f"its an excel file, extracting {file}")
        year = file[-9:-5]
        extract_path = f"{SWISSBORG_CSV_PATH}/{year}"
        df = spark.read \
            .format("com.crealytics.spark.excel") \
            .option("header", "true") \
            .option("inferSchema", "true") \
            .option("skipFirstRows", 14) \
            .option("treatEmptyValuesAsNulls", "true") \
            .option("timestampFormat", "yyyy-MM-dd HH:mm:ss") \
            .option("dateFormat", "yyyy-MM-dd") \
            .option("dataAddress", "'Transactions'!A14") \
            .option("sheetName", "Transactions") \
            .load(f"{path}/{file}")
        print(df.schema.json())
        df.coalesce(1).write.mode("overwrite").csv(extract_path)

        print(f"extracted file at: {extract_path}")

def preprocess_raw_files(exchange):
    originals_path = f"{EXCHANGES_RAW_FILES}/{exchange}/originals"
    print(os.listdir(originals_path))
    if os.path.exists(originals_path):
        for file in os.listdir(originals_path):
            read_excel_to_csv(originals_path, file)
    else:
        print(f"path {originals_path} does not exist")


if __name__ == "__main__":

    spark = get_spark()
    print("starting ingestion for SWISSBORG")

    # this extracts .zip files into different folders as csv
    preprocess_raw_files(SWISSBORG_EXCHANGE_NAME)

    # load files per year/month or all at once with spark
    schema_path = f"{SCHEMAS_PATH}/swissborg/transactions.json"
    df = (read_csv_to_df(SWISSBORG_CSV_PATH, schema_path=schema_path)
          .distinct()
          .withColumn("year_month", date_format(col("time_utc"), "yyyyMM"))
          .withColumn("date_key", date_format(col("time_utc"), "yyyyMMdd"))
          .withColumn("ingestion_timestamp", current_timestamp())
          .sort("time_utc"))

    w = Window().orderBy("time_utc").partitionBy("year_month")

    df_trans = df.withColumn("row_number", row_number().over(w))

    print(f"table has {df_trans.count()} records.")

    write_table_in_postgres(df_trans, RAW_DB, SWISSBORG_RAW_TABLE)



