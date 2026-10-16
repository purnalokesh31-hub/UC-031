# CropGuard workspace features

## Start and open

Run `./start_all.ps1` from the project folder. Open http://127.0.0.1:5173/.
The backend listens at http://127.0.0.1:8000/. Launch logs are in `logs/`.

## Suggested workflow

1. **My fields:** choose **Add a field** and enter a name and area. Location is optional. Expand **Growing dates & weather** only if needed. **Save & estimate yield** takes you straight to the crop inputs.
   Coordinates are optional. Select **Estimate yield** to open its analysis inputs.
2. **Yield analysis:** choose the crop and enter measurements. Expand **Record sources & measurement dates** to distinguish sample defaults, entered values and measured
   records. Measured records require a date on or before today. Select **Save
   measurements to field** to reuse this scenario later.
3. Select **Analyze yield**. Both model results, inputs, field context, source
   labels and release ID are saved automatically after a successful response.
4. Change an input and analyze again. In **History**, select **Compare** on up to
   three analyses of the same crop. The table compares each model family and
   its interval. Differences between scenarios are not evidence of causation.
5. Use **Record actual harvest** on the matching analysis to enter harvested
   quantity, area, date and notes. Kilograms, quintals, tonnes, hectares and acres
   are supported. Recorded outcomes show normalized yield, absolute error and
   interval inclusion. Records are user-reported and do not automatically train
   the models. Same-day or earlier outcomes are marked retrospective.
6. Expand **Explore how the quantum model produced this estimate** below a new
   result. Its four steps use the active model's scaler, circuit state,
   similarities and kernel regression. A release mismatch requires a new analysis.
7. Open **Research** for deployed synthetic metrics and saved real-source rice
   development results, feature ablations, weather contrasts and district/year
   error breakdowns. Reserved final cohorts remain unscored.

## Historical weather

The browser requests device location when the app opens. If permission is
granted, its coordinates prefill a **new** field; saved field coordinates are
preserved. The detected position is approximate, so check that it matches the
field. The **Use current location** control can replace coordinates while
editing. If location is denied, unsupported or unavailable, enter latitude and
longitude manually. The detected position is held in memory; coordinates are
stored with a field only when that field is saved.

In **My fields**, check the detected coordinates or enter them manually, add a
historical growing period, then select **Look up past weather**. This sends the
coordinates and dates through the backend to NASA POWER. Review the returned
temperature, total rainfall and humidity, then **Save field** to retain them.

The backend accepts 1–366 days from 1981 onward, ending before today. It checks
completeness, units and UTC dates, and retains retrieval metadata and a response
hash. Validated historical summaries are cached locally. A provider failure or
incomplete series is reported without fabricating weather.

Weather is gridded historical context, not an on-farm measurement or forecast.
It is not automatically substituted into model inputs: the deployed synthetic
model has no validated mapping from growing-period aggregates to its features.

## Storage and offline use

- Field profiles, analyses, harvest records, cached metrics and the current
  analysis draft live in this browser's local storage. There is no cloud account
  or cross-device sync. Keep the same host and port: `localhost` and `127.0.0.1`
  have separate browser storage.
- Use **Export backup** regularly. Individual analyses and harvest/history
  records can also be exported as JSON. Backup import is not provided yet.
- Input drafts save as you edit, including while offline. Predictions, weather
  retrieval, research loading and circuit calculations require the backend.
- The service worker caches the application shell and visited assets. Previously
  visited screens can reopen offline once their assets are cached. A first visit
  still needs the server. Reconnect and explicitly select **Analyze yield**;
  requests are not silently queued or submitted.
- Storage failures show a visible warning. Export in-memory work before closing
  if storage is unavailable or full. Browser data clearing removes local records.
- Use one editing tab per field. Other tabs receive saved record updates, but
  simultaneous draft edits are not a collaborative editing system.

## Model and research scope

These features do not retrain models or establish improved accuracy. Deployed
models still use synthetic training records. Real-source research is a separate,
retrospective district-level development study. It is not a validated farm
forecast. R² is not percentage accuracy. The quantum-kernel model is simulated
classically; no quantum-computing advantage is claimed.

## New backend routes

- `POST /workspace/weather`: validated historical weather context.
- `GET /research/evidence`: summaries of fixed saved development artifacts only.
- `POST /quantum/walkthrough`: calculation trace for a validated prediction input.

## Implementation checks

The production frontend build passed. Manual browser checks covered saving and
reusing a demo field, running both models, automatically saving two analyses,
comparing their input snapshots and intervals, reproducing the quantum result in
the walkthrough, and displaying research results at a 390px mobile width without
page overflow. A live weather-import command was blocked by the execution policy;
that provider round trip and a complete offline reload were not verified in this
session. No real harvest outcomes were fabricated for these checks.

Telugu and Hindi translation was excluded as requested.

## Dashboard usability update

The input form shows crop choice and all eight conditions together. A sample
estimate can run immediately. Optional saved field links and measurement records
expand below the conditions. Crop changes offer to retain entered measurements
or load new samples. Previous results stay visible with an explicit update notice
when inputs change. Each value identifies sample defaults or user entries, and
analysis errors appear beside the action. The mobile estimate action stays
available while moving through the form.
The mobile header keeps Yield analysis, My fields and History visible, with
Research, Leaf scan and Method & data under More. Location and backup controls
expand from the device status strip. Optional source recording follows the
main action. Reset to sample offers Undo reset
until a new edit, crop or field selection. The result opens with the yield and
field total; expand Compare classical & quantum estimates for model details.
Numeric inputs and mobile actions have larger touch targets.
