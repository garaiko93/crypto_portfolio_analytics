from pyspark.sql import DataFrame
from pyspark.sql.functions import col, collect_list, udf, lit, sum
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

from config import ConfigClass, config

# from config import SWISSBORG_STAKING_REWARDS_OPS, SWISSBORG_TRADE_OPS, SWISSBORG_EXCHANGE_NAME, STABLE_COINS, \
#     STABLE_COINS_AND_FIAT, RAW_DB, SWISSBORG_RAW_TABLE
from utils.spark_utils import read_table


def process_transactions(operations, coins, changes, fees):
    sent_coin = None
    sent_amount = None
    fee_coin = None
    fee_amount = None
    received_coin = None
    received_amount = None
    for op, coin, change, fee in zip(operations, coins, changes, fees):
        change = abs(change)
        if op == "Sell":
            sent_coin = coin
            sent_amount = change
        elif op == "Buy":
            received_coin = coin
            received_amount = change
            fee_coin = coin
            fee_amount = fee
        # elif op == "Transaction Sold":
        #     sent_coin = coin
        #     sent_amount = change
        # elif op == "Transaction Revenue":
        #     received_coin = coin
        #     received_amount = change


        if sent_coin in config.STABLE_COINS_AND_FIAT:
            action = "buy"
        elif received_coin in config.STABLE_COINS_AND_FIAT:
            action = "sell"
        else:
            action = "exchange"

    if action == "buy":
        price = sent_amount / received_amount
    else:
        price = received_amount / sent_amount

    return sent_coin, sent_amount, fee_coin, fee_amount, received_coin, received_amount, price, action

schema = StructType([
    StructField("sent_coin", StringType(), True),
    StructField("sent_amount", DoubleType(), True),
    StructField("fee_coin", StringType(), True),
    StructField("fee_amount", DoubleType(), True),
    StructField("received_coin", StringType(), True),
    StructField("received_amount", DoubleType(), True),
    StructField("price", DoubleType(), True),
    StructField("action", StringType(), True)
])


def refine_swissborg_trades(df) -> DataFrame:
    # this avoids a trade that has been splitted between different operations at the same time
    summary_df = (df.groupBy("time_utc", "type", "currency", "year_month", "date_key")
                  .agg(
        sum("net_amount").alias("net_amount"),
        sum("fee").alias("fee")
        # sum("fee_usd").alias("fee_usd")
    )).sort("time_utc")
    # summary_df.show()

    grouped_df = summary_df.groupBy("time_utc", "year_month", "date_key").agg(
        collect_list("type").alias("type"),
        collect_list("fee").alias("fee"),
        collect_list("currency").alias("currency"),
        collect_list("net_amount").alias("net_amount")
    ).sort("time_utc")
    # grouped_df.show()

    # Register UDF
    process_transactions_udf = udf(process_transactions, schema)

    # Apply UDF to DataFrame
    processed_df = (grouped_df
                    .withColumn("processed_transactions",
                                process_transactions_udf(col("type"), col("currency"), col("net_amount"), col("fee"))))

    # Expand struct columns into separate columns
    final_df = processed_df.select(
        col("time_utc").alias("timestamp"),
        col("processed_transactions.*"),
        lit(config.SWISSBORG_EXCHANGE_NAME).alias("exchange"),
        col("date_key"),
        col("year_month")
    )
    final_df.show(100, truncate=False)

    print(f"table has {final_df.count()} records.")

    # write_table_in_postgres(final_df, REFINED_DB, REFINED_TRADES)

    return final_df


def refine_swissborg_rewards(df):
    summary_df = df.groupBy("time_utc", "currency", "year_month", "date_key").agg(sum("net_amount").alias("net_amount"))

    # Expand struct columns into separate columns
    final_df = summary_df.select(
        col("time_utc").alias("timestamp"),
        col("year_month"),
        col("date_key"),
        col("currency").alias("received_coin"),
        col("net_amount").alias("received_amount"),
        lit(config.SWISSBORG_EXCHANGE_NAME).alias("exchange"))

    print(f"table has {final_df.count()} records.")

    # write_table_in_postgres(final_df, config.REFINED_DB, config.REFINED_STAKING_REWARDS)

    return final_df


if __name__ == "__main__":
    df_raw_swissborg = read_table(config.RAW_DB, config.SWISSBORG_RAW_TABLE)
    df_raw_swissborg.show()

    # process trades - buy and sells
    # df_refined_swissborg_trades = refine_swissborg_trades(
    #     df_raw_swissborg.filter(col("type").isin(config.SWISSBORG_TRADE_OPS))
    # )
    # df_refined_swissborg_trades.show(truncate=False)

    # process staking rewards
    df_refined_rewards = refine_swissborg_rewards(
        df_raw_swissborg.filter(col("type").isin(config.SWISSBORG_STAKING_REWARDS_OPS))
    )
    df_refined_rewards.show(truncate=False)

