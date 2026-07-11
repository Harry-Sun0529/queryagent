-- Static init: read-only account for the agent. Defence in depth — even if
-- the SQL safety layer were bypassed, this account cannot write.
-- Schema + data live in the generated 10_demo_shop.sql (run `make demo-data`).
CREATE USER IF NOT EXISTS 'queryagent_ro'@'%'
  IDENTIFIED WITH mysql_native_password BY 'demo_ro_password';
GRANT SELECT ON demo_shop.* TO 'queryagent_ro'@'%';
FLUSH PRIVILEGES;
