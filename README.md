# Bridge PostgreSQL and RabbitMQ using a Python script

The `postgres-rabbitmq-bridge` folder contains the relevant scripts.
The `djangostub` folder contains a simple script inserting and updating data in a PostgreSQL table. Each of those accesses triggers a notification that is received and acted upon by the bridge script.

This solution uses Docker (compose).