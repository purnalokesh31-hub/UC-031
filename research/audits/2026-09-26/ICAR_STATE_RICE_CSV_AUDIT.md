# ICAR-IIRR state-level rice CSV audit

Audit date: 2026-09-26  
Scope: file structure, basic internal consistency, source documentation, and suitability for the existing district-level study. No outcomes were joined to the pilot, and no model was fitted, tuned, or scored.

## Input identity

- File received: `Rice_Data_2026-09-24.csv`
- SHA-256: `3a4dc6b0820ac77f9d7cd25ca19ca0588f4e06cc485b0c17713cc35a1f2eaa10`
- Size: 66,181 bytes
- The file starts with the HTML comment `<!-- FILE: config.php -->`; remove or skip that line in a documented parser. The source file was left unchanged.
- No data dictionary, license statement, query/filter record, source-version identifier, or boundary-vintage field is embedded in the file.

## Structural checks

| Check | Finding |
|---|---|
| Records | 1,844 |
| State/territory labels | 35 |
| Year range | 1966–2025 |
| Duplicate state-year keys | 0 |
| Missing values in the five columns | 0 |
| Numeric parse failures or nonpositive area, production, or yield | 0 |
| 2024 rows | 34 |
| 2025 rows | 20 |
| Andhra Pradesh rows | 60 (1966–2025) |
| Telangana rows | 16 (2010–2025) |

Columns are `State`, `Year`, `Area (Ha)`, `Production (Tonnes)`, and `Yield (Kg/ha)`. The reported yield is broadly consistent with `production × 1000 / area`; the maximum absolute difference in this file is 3 kg/ha, consistent with a rounded reported field but requiring confirmation from the source documentation. State labels include spelling and boundary-vintage issues that need a canonical crosswalk before geographic aggregation.

## Provenance and study suitability

The file's stated context is the [ICAR-IIRR Rice APY Dashboard](https://icar-iirr.org/Rice_APY_Dashboard/). ICAR-IIRR's linked database description says its state-level rice APY series was created for 1997–2023 and its all-India series for 1966–2023 ([database description](https://icar-iirr.org/index.php/en/component/content/article/39-iirr-databases/214-rice-area-production-and-productivity-database?Itemid=258)). This CSV instead contains state-labeled records back to 1966 and through 2025. That may reflect an updated export, but the discrepancy must be resolved with a versioned source export or data dictionary before publication use. The dashboard fetch could not be independently retrieved during this audit.

This is state-level area, production, and yield only. It has no district outcomes, weather, soil, or management measurements. State-year coverage overlaps the Andhra Pradesh/Telangana geography and years in the existing district pilot; state aggregates may include districts reserved by the frozen protocol. The Telangana series also starts in 2010 alongside Andhra Pradesh, so historical boundary definitions must be documented before interpreting or combining the rows.

**Decision:** keep this file outside the modeling panel and reserved evaluation. It is not an independent external test set for a district-level model and cannot establish external validation. It could support contextual state-level descriptions after its version, provenance, license, target definitions, and boundary history are verified. Do not sum the Andhra Pradesh and Telangana rows in overlapping years without explicit historical-boundary documentation. No lockbox outcomes were compared in this audit.

## Next research action

The most relevant data-access lead found is the official General Crop Estimation Survey / crop-cutting experiment (GCES/CCE) system. The National Statistical Commission describes plot-level harvest measurements and district/state yield estimation; Telangana DES says its survey collects plot yield, inputs, and irrigation details. These are method descriptions, not a public microdata download. Because official APY yields are themselves based on crop-cutting estimates, CCE records may underlie the existing labels and cannot be called independent until the agency confirms source lineage and overlap. [NSC methodology](https://nsc.mospi.gov.in/43-crop-production), [Telangana DES survey and forms](https://ecostat.telangana.gov.in/crop_estimation_survey.html).

Request anonymized rice CCE records or estimates from the Andhra Pradesh and Telangana Directorates of Economics & Statistics, including district/mandal, season and agricultural year, yield/measurement units, sampling weights and experiment counts, boundary definitions, source lineage relative to DES APY, availability dates, and publication/reuse terms. In parallel, request the ICAR-IIRR export documentation/version and license for this exact file. After receipt, audit overlap before considering any record for external validation. Keep the existing reserved cohort unscored until that design is frozen.
