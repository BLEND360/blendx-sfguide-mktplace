# Snowflake Limitations

This document highlights specific Snowflake limitations relevant for developers working with Snowflake.

---

## 📌 Hybrid Tables & Indexing

Snowflake **does not support traditional indexes on standard table types** — if you need **indexed/row-based access patterns**, you must use **Hybrid Tables**.

- Hybrid tables are a dedicated table type optimized for **low-latency reads and writes with indexes**.  
- They support **PRIMARY KEY and secondary indexes** which are enforced and maintained by the system.  
- Hybrid tables are explicitly used when your workload requires **indexing for high-concurrency or operational lookup patterns**.  
- Note that columns with semi-structured types (`VARIANT`, `OBJECT`, `ARRAY`), geospatial types (`GEOGRAPHY`, `GEOMETRY`), or vector types cannot be indexed.  
➡️ https://docs.snowflake.com/en/user-guide/tables-hybrid-limitations#data-types-not-supported-in-indexes  [oai_citation:0‡Snowflake Documentation](https://docs.snowflake.com/en/user-guide/tables-hybrid-limitations?utm_source=chatgpt.com)

**Reference:**  
https://docs.snowflake.com/en/user-guide/tables-hybrid-limitations#data-types-not-supported-in-indexes  [oai_citation:1‡Snowflake Documentation](https://docs.snowflake.com/en/user-guide/tables-hybrid-limitations?utm_source=chatgpt.com)

---

## 📌 File Writing Limitations

Snowflake’s architecture **does not allow arbitrary file writes directly from SQL or procedural code to persistent storage** in the same way traditional databases or filesystem APIs do.

- By default, Snowflake **cannot write files to arbitrary locations** like local disk paths within the service.  
- The typical pattern for file output is to use **stages** (`CREATE STAGE`) and then commands like `COPY INTO @stage` to unload data to external/internal stages.  
  - This unloads table/query results into cloud storage (e.g., S3/Azure/GCS) or internal Snowflake locations for later use.  
  - Trying to write arbitrary files outside this staging/unloading mechanism is not supported.  
- In **Snowflake Native Apps** and some UDF contexts, there are temporary internal storage mechanisms (e.g., Snowpark UDF internal stage writes), but these are scoped to query results and **not general file system writes**.  
➡️ https://docs.snowflake.com/en/sql-reference/sql/create-stage  [oai_citation:2‡Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/sql/create-stage?utm_source=chatgpt.com)

**Reference:**  
https://docs.snowflake.com/en/sql-reference/sql/create-stage  [oai_citation:3‡Snowflake Documentation](https://docs.snowflake.com/en/sql-reference/sql/create-stage?utm_source=chatgpt.com)

---

## 📌 Notes & Best Practices

- If you need long-term files (CSV/Parquet outputs), use `COPY INTO @my_external_stage/...` to export out of Snowflake.  
- Avoid trying to persist files inside stored procedures or UDFs directly — instead export via stages or external object storage.  

---
