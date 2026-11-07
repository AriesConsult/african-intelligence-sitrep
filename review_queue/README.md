[README.md](https://github.com/user-attachments/files/34526195/README.md)
# Review queue

This folder receives JSON source-table transcriptions only after GitHub Actions runs.
Each filename contains the report number and first 12 characters of the SHA-256.
The original source PDF is linked in each record; the full downloaded PDF is also
stored in the run's artifacts for 30 days. These tables are **not approved data**.

For a reviewer-approved value, use `reviewed/approved_observations.csv` and ensure
its report number, full SHA, observation date, table ID, page, column header,
row label and raw value exactly match the candidate transcription. Always consult
the original PDF for ambiguous cells before approving. The pipeline refuses rows
that cannot be reproduced from this queue.
