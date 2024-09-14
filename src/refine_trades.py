from pyspark.sql.functions import col

from config import config
from refiners.refine_binance import refine_binance_trades
from refiners.refine_swissborg import refine_swissborg_trades
from utils.spark_utils import get_spark, read_table, write_table_in_postgres

if __name__ == "__main__":

    spark = get_spark("refine - trades")
    print("starting refinement")

    # load raw dataframes
    df_raw_binance = read_table(config.RAW_DB, config.BINANCE_RAW_TABLE)
    df_raw_swissborg = read_table(config.RAW_DB, config.SWISSBORG_RAW_TABLE)
    # df_raw_kucoin = read_table(RAW_DB, KUCOIN_RAW_TABLE)

    #########################
    # REFINE BINANCE TRADES
    #########################
    df_refined_binance_trades = refine_binance_trades(
        df_raw_binance.filter(col("Operation").isin(config.BINANCE_TRADE_OPS)))

    #########################
    # REFINE SWISSBORG TRADES
    #########################
    df_refined_swissborg_trades = refine_swissborg_trades(
        df_raw_swissborg.filter(col("type").isin(config.SWISSBORG_TRADE_OPS))
    )

    # union trades df per exchange
    df_trades = (df_refined_binance_trades
                 .unionByName(df_refined_swissborg_trades, allowMissingColumns=True))
    df_trades.show(100, truncate=False)

    # write output trades df to postgresql database
    write_table_in_postgres(df_trades, config.REFINED_DB, config.REFINED_TRADES)
