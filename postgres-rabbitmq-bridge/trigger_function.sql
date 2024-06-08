CREATE OR REPLACE FUNCTION notify_table_change()
    RETURNS trigger AS
$$
BEGIN
    RAISE LOG 'notify_table_change() on table %, operation %, new record %', TG_TABLE_NAME,TG_OP,NEW;
    PERFORM pg_notify(
            'table_changed',
            json_build_object(
                    'table', TG_TABLE_NAME,
                    'operation', TG_OP,
                    'timestamp', current_timestamp(6),
                    'new_record', row_to_json(NEW),
                    'old_record', row_to_json(OLD)
                )::text
        );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;