# Input data dictionary

The `date`, `group`, `period`, `revenue`, `ad_spend`, and `campaign_flag` fields are **required**.

| Field | Required? | Expected form | Notes |
|---|---|---|---|
| `date` | Yes | Parseable date | E.g. `2026-06-15` |
| `group` | Yes | `treatment` / `control` | Case-insensitive; whitespace trimmed |
| `period` | Yes | `pre` / `post` | Must contain all four group-period cells |
| `revenue` | Yes | Numeric | Observed revenue for the record |
| `ad_spend` | Yes | Numeric | Spend only counted for active campaign rows in treated post-period |
| `campaign_flag` | Yes | Boolean-like | Supports `1`, `true`, `yes`, `y`, `active`, `on` |
| `product_category` | No | Text | Descriptive context |
| `segment` | No | Text | Descriptive context |
| `sessions` | No | Numeric | Used for one traffic-imbalance warning |
| `conversion_rate` | No | Numeric | Displayed in preview, not used for uplift |
| `channel` | No | Text | Used to detect multi-channel activation |
| `discount_flag` | No | Boolean-like | Raises warning if discount active after campaign |
| `stock_status` | No | Text | Values containing `low` / `stockout` raise warning |
| `notes` | No | Text | Context field |

Use the two example datasets under `data/` for a working input schema. They are **simulated and seeded**; no customer data is included.

**Data-grain caveat:** The current PoC computes mean revenue over rows, assumes those rows are comparable across treatment/control and pre/post, and counts unique treated post-period dates. It does not automatically reconcile multiple product/segment rows per date to a coherent store-level revenue series. Use one comparable daily observation per group in the current demo or explicitly aggregate and validate data first.
