# Sample.Basic

This is Essbase's canonical demo cube, re-expressed as a Lakecube spec. It's the
parity target for every phase of Lakecube development — if Sample.Basic works
end-to-end, a real customer cube will too.

## What's here

- [`cube.yaml`](cube.yaml) — the cube spec (dimensions, measures, scenarios, security).

## What should work

- **P0**: `lakecube compile cube.yaml` validates the spec and prints the emission plan.
- **P1**: `lakecube deploy --catalog main` produces a queryable Unity Catalog Metric View; AI/BI + Genie work against it; Workbench Analyze mode supports ad-hoc with zoom/keep-only/pivot.
- **P2**: calcs (Margin, Profit, Variance) match Essbase within tolerance; Excel plugin offers Smart-View-parity gestures.
- **P3**: `lakecube scenario new budget-fy26` creates a Delta branch; write-back via Workbench Forms and Excel works; approval workflow completes a budget cycle.

## Essbase reference

Oracle's Sample.Basic docs: see any Essbase Administration Services install or the
[Oracle Essbase tutorial](https://docs.oracle.com/en/database/other-databases/essbase/21/). The member
structure here follows the standard demo cube — Colas/Root Beer/Cream Soda/Fruit Soda
across East/West/South/Central, with Actual/Budget/Variance scenarios.
