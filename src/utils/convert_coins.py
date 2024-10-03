from pyspark.sql import DataFrame
from pyspark.sql.functions import col, desc

from config import config
from utils.spark_utils import read_table



def convert_coin(df: DataFrame, coin_col: str, amount_col: str, converted_col: str, date_col: str="date_key"):

    # load price dataframes for a set of coins
    # cache price dataframes
    df_prices = (read_table(config.REFINED_DB, config.USD_CRYPTO_PRICES_UNION)
                 .withColumnRenamed("symbol", coin_col))

    # join left input df with prices
    result = (df
              .join(df_prices, [coin_col, date_col], "left")
              .withColumn(converted_col, col(amount_col) * col("closing_price"))
              .drop("closing_price", "symbol"))

    from pyspark.sql.functions import count
    result.filter(col(converted_col).isNotNull()).show(truncate=False)
    result.filter(col(converted_col).isNotNull()).sort(desc(converted_col)).show(truncate=False)
    result.filter(col(converted_col).isNull() & col(coin_col).isNotNull()).show(truncate=False)
    result.filter(col(converted_col).isNull()).select(coin_col, date_col).distinct().sort(date_col).show(truncate=False)
    result.filter(col(converted_col).isNull()).select(coin_col).groupby(coin_col).agg(count("*").alias("count")).sort("count").show(100, truncate=False)

    # todo: add mappings of coins that changed of name
    # todo: create lookup, substitute name by an id
    # luna -> lunac: luna prices has a problem in yahoofinance
    # bttc -> btt
    # miota -> iota
    # matic -> pol ?



    count = result.filter(col(converted_col).isNull()).count()
    print(f"result has: {count}/{result.count()} null values of amounts")

    return result

# if __name__ == "__main__":

