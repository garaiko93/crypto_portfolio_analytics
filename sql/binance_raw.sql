select "Coin", sum("Change") as sum from raw.binance_record_history_raw
where "Operation" = 'Transaction Buy'
group by "Coin"
order by sum desc
;
select * from raw.binance_record_history_raw
;
SELECT DISTINCT "Operation" FROM raw.binance_record_history_raw
;
SELECT DISTINCT "Operation", count(*) FROM raw.binance_record_history_raw group by "Operation"
;
select "Coin", sum("Change") from raw.binance_record_history_raw where "Operation" = 'Deposit' group by "Coin"
;
--select * from raw.binance_record_history_raw where "Operation" = 
;
select * from raw.binance_record_history_raw order by "UTC_Time"
