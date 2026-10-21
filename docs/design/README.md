# Design from the lab exercise

Copied from the analysis repository `Rave00/EkteMat-Online-Project` (commit `b86f044`, folder `02_Analysis_and_models/`).
They describe the full Ekte Mat Online system; Oblig 4 builds the subset in plan 0, section 4.

| Diagram | Files | How it is used in Oblig 4 |
|---|---|---|
| Domain class diagram | `02_uml_domain-class.*`, `02_uml_domain-enums.*` | Source of the classes and tables in plan 0 (subset). |
| Use case diagram | `02_uml_use-case.*` | Which actor needs which feature; maps to A1-A4 and C1-C5. |
| Order state machine | `02_uml_state-order.*` | Basis for the order status rules; Oblig 4 uses its simpler status names (plan 0, D10). |
| Sequence: recurring lunch and EHF | `02_uml_sequence-recurring-lunch-ehf.*` | Not in Oblig 4 scope (company accounts, Fiken); kept for later. |
| BPMN AS-IS and TO-BE | `02_bpmn_*` | The TO-BE process is what the customer site and admin panel support. |

When Oblig 4 changes the design (for example the order statuses), the updated diagram is added here with a note.
