from pyspark.sql.functions import col

from config import config
from refiners.refine_binance import refine_binance_trades, refine_binance_rewards
from refiners.refine_swissborg import refine_swissborg_trades, refine_swissborg_rewards
from utils.spark_utils import get_spark, read_table, write_table_in_postgres

if __name__ == "__main__":

    spark = get_spark("refine - rewards")
    print("starting refinement")

    # load raw dataframes
    df_raw_binance = read_table(config.RAW_DB, config.BINANCE_RAW_TABLE)
    df_raw_swissborg = read_table(config.RAW_DB, config.SWISSBORG_RAW_TABLE)
    # df_raw_kucoin = read_table(RAW_DB, KUCOIN_RAW_TABLE)

    # process trades - buy and sells
    df_refined_binance_rewards = refine_binance_rewards(
        df_raw_binance.filter(col("Operation").isin(config.BINANCE_STAKING_REWARDS_OPS)))

    # refined_binance_trades, refined_binance_rewards = refine_binance(df_raw_binance)
    df_refined_swissborg_rewards = refine_swissborg_rewards(
        df_raw_swissborg.filter(col("type").isin(config.SWISSBORG_STAKING_REWARDS_OPS))
    )

    # union trades df per exchange
    df_rewards = (df_refined_binance_rewards
                 .unionByName(df_refined_swissborg_rewards, allowMissingColumns=True))
    df_rewards.show(100, truncate=False)

    # write output trades df to postgresql database
    write_table_in_postgres(df_rewards, config.REFINED_DB, config.REFINED_STAKING_REWARDS)
