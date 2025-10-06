# System Comparison (Section 4.5)

| Approach              | Graph KB   | Multi-Agent   | Real-time Web   |   Precision@10 |   Cost/Query ($) |
|:----------------------|:-----------|:--------------|:----------------|---------------:|-----------------:|
| Our System            | ✓          | ✓             | ✓               |           0.87 |             0.11 |
| No Graph (Flat JSON)  | ✗          | ✓             | ✓               |           0.72 |             0.11 |
| Monolithic GPT-4      | ✗          | ✗             | ✓               |           0.78 |             0.45 |
| Google CSE + Scraping | ✗          | ✓             | ✓               |           0.68 |             0.15 |