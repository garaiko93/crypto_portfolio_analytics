from pyspark.sql import DataFrame
from pyspark.sql.functions import col, lit, collect_list, udf, sum
from pyspark.sql.types import DoubleType, StringType, StructField, StructType

from config import config
from utils.convert_coins import convert_coin
from utils.spark_utils import read_table, get_spark, write_table_in_postgres


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


def process_transactions(operations, coins, changes):
    sent_coin = None
    sent_amount = None
    fee_coin = None
    fee_amount = None
    received_coin = None
    received_amount = None
    for op, coin, change in zip(operations, coins, changes):
        change = abs(change)
        if op == "Transaction Spend":
            sent_coin = coin
            sent_amount = change
        elif op == "Transaction Fee":
            fee_coin = coin
            fee_amount = change
        elif op == "Transaction Buy":
            received_coin = coin
            received_amount = change
        elif op == "Transaction Sold":
            sent_coin = coin
            sent_amount = change
        elif op == "Transaction Revenue":
            received_coin = coin
            received_amount = change

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


def refine_binance_trades(df: DataFrame) -> DataFrame:
    # this avoids a trade that has been split between different operations at the same time
    summary_df = (df.groupBy("User_Id", "UTC_Time", "Account", "Operation", "Coin", "year_month", "date_key")
                  .agg(sum("Change").alias("Change")))

    grouped_df = summary_df.groupBy("User_Id", "UTC_Time", "Account", "year_month", "date_key").agg(
        collect_list("Operation").alias("Operations"),
        collect_list("Coin").alias("Coins"),
        collect_list("Change").alias("Changes")
    )

    # Register UDF
    process_transactions_udf = udf(process_transactions, schema)

    # Apply UDF to DataFrame
    processed_df = (grouped_df
                    .withColumn("processed_transactions",
                                process_transactions_udf(col("Operations"), col("Coins"), col("Changes"))))

    # Expand struct columns into separate columns
    final_df = processed_df.select(
        col("UTC_Time").alias("timestamp"),
        col("User_Id").alias("user_id"),
        col("Account").alias("account"),
        col("processed_transactions.*"),
        lit(config.BINANCE_EXCHANGE_NAME).alias("exchange"),
        col("date_key"),
        col("year_month")
    )

    print(f"table has {final_df.count()} records.")

    # final_df = convert_coin(final_df, "sent_coin", "sent_amount", "sent_amount_in_usd")
    # final_df = convert_coin(final_df, "received_coin", "received_amount", "received_amount_in_usd")
    final_df = convert_coin(final_df, "fee_coin", "fee_amount", "fee_amount_in_usd")

    # write_table_in_postgres(final_df, REFINED_DB, REFINED_TRADES)

    return final_df


def refine_binance_rewards(df: DataFrame) -> DataFrame:
    summary_df = df.groupBy("User_Id", "UTC_Time", "Account", "Coin", "year_month", "date_key").agg(sum("Change").alias("Change"))

    # Expand struct columns into separate columns
    final_df = summary_df.select(
        col("UTC_Time").alias("timestamp"),
        col("User_Id").alias("user_id"),
        col("Account").alias("account"),
        col("year_month"),
        col("date_key"),
        col("Coin").alias("received_coin"),
        col("Change").alias("received_amount"),
        lit(config.BINANCE_EXCHANGE_NAME).alias("exchange"))

    print(f"table has {final_df.count()} records.")

    final_df = convert_coin(final_df, "received_coin", "received_amount", "received_amount_in_usd")

    # write_table_in_postgres(final_df, config.REFINED_DB, config.REFINED_STAKING_REWARDS)

    return final_df


if __name__ == "__main__":

    spark = get_spark("binance - refine")
    print("starting refinement")
    
    # load raw dataframes
    df_raw_binance = read_table(config.RAW_DB, config.BINANCE_RAW_TABLE)

    # refine raw transactions into trades and rewards separately
    # process trades - buy and sells
    df_refined_binance_trades = refine_binance_trades(
        df_raw_binance.filter(col("Operation").isin(config.BINANCE_TRADE_OPS))
    )
    df_refined_binance_trades.show(truncate=False)

    # process staking rewards
    df_refined_staking_rewards = refine_binance_rewards(
        df_raw_binance.filter(col("Operation").isin(config.BINANCE_STAKING_REWARDS_OPS))
    )
    df_refined_staking_rewards.show(truncate=False)





