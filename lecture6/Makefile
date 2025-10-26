init_topic:
	docker-compose exec kafka kafka-topics \
		--create \
		--topic $(t) \
		--replication-factor $(r) \
		--partitions $(p) \
		--bootstrap-server localhost:29092

list_topics:
	docker-compose exec kafka kafka-topics \
		--list \
		--bootstrap-server localhost:29092

delete_topic:
	docker-compose exec kafka kafka-topics \
		--delete \
		--topic $(t) \
		--bootstrap-server localhost:29092
