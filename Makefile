.PHONY: up down status silver gold query-oracle clean

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
	docker exec -i lakehouse-oracle sqlplus system/oracle@//localhost:1521/XEPDB1 <<< "SET PAGESIZE 50; SET LINESIZE 200; COLUMN PRODUCT_ID FORMAT A12; COLUMN PRODUCT_TITLE FORMAT A40; SELECT * FROM GOLD_BOOK_REVIEWS; EXIT;"
