# Source data audit

No models were trained or evaluated in this audit.

| Dataset | Rows | Districts | Years |
|---|---:|---:|---|
| Apportioned/Crops_Area Production Yield.csv | 16,146 | 311 | 1966–2017 |
| Unapportioned/Crops_Area Production Yield.csv | 18,060 | 602 | 1990–2019 |
| Unapportioned/Environment_Evapotranspiration.csv | 36,890 | 602 | 1958–2023 |
| Unapportioned/Environment_Precipitation.csv | 36,890 | 602 | 1958–2023 |
| Unapportioned/Environment_Temperature Maximum.csv | 36,890 | 602 | 1958–2023 |
| Unapportioned/Environment_Temperature Minimum.csv | 36,890 | 602 | 1958–2023 |

## Andhra Pradesh and Telangana: unapportioned crop records

Counts require positive area, production and reported yield; they are provisional eligibility counts.

| Crop | Eligible rows | Districts | Matching keys in four weather files |
|---|---:|---:|---:|
| Rice | 752 | 46 | 752 |
| Wheat | 255 | 22 | 255 |
| Maize | 717 | 45 | 717 |
| Cotton | 671 | 43 | 671 |
| Sugarcane | 632 | 38 | 632 |
| Groundnut | 742 | 44 | 742 |

## Required investigation

- No seasons provided for the six selected crops. Do not manufacture season labels from annual records.
- Matching district IDs and names does not establish matching historical boundaries.
- Weather monthly dates must be aligned to the documented agricultural-year convention.
- Negative crop entries (including -1) require documented missing-value interpretation.
- No soil measurements or independent external test set identified by this CSV inventory.
- Do not use same-year production and area as predictors of the corresponding yield.
- No model fitting, tuning, or evaluation performed.

The apportioned crop table and unapportioned weather table must not be joined merely because codes match. Review the archive's apportionment workbook and documentation first.

Archive and member SHA-256 checksums, schemas and per-crop year counts are recorded in source_audit.json. Original files remain unchanged.
