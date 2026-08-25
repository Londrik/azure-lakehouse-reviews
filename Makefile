.PHONY: up down status silver gold query-oracle view-powerbi clean

up:
	docker compose up -d

down:
	docker compose down

status:
	docker ps

silver:
	docker exec -it lakehouse-spark spark-submit --packages org.apache.hadoop:hadoop-aws:3.3.4 /home/jovyan/work/process_silver.py

gold:
	docker exec -it lakehouse-spark spark-submit --packages org.apache.hadoop:hadoop-aws:3.3.4,com.oracle.database.jdbc:ojdbc8:21.9.0.0 /home/jovyan/work/process_gold.py

query-oracle:
	printf "SET PAGESIZE 50;\nSET LINESIZE 200;\nCOLUMN PRODUCT_ID FORMAT A12;\nCOLUMN PRODUCT_TITLE FORMAT A40;\nSELECT * FROM GOLD_BOOK_REVIEWS;\nEXIT;\n" | docker exec -i lakehouse-oracle sqlplus system/oracle@//localhost:1521/XEPDB1

view-powerbi:
	printf "SELECT * FROM VW_POWERBI_GOLD_REVIEWS;\nEXIT;\n" | docker exec -i lakehouse-oracle sqlplus system/oracle@//localhost:1521/XEPDB1
