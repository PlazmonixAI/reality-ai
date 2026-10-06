# ASM Teach pricing: a school with 30 digital boards

Worked out on 2026-10-06. Prices exclude 18% GST. ₹88 per US$.

## Usage assumed
- 30 boards × 6 classes a day × 24 school days = **4,320 classes a month** (40 minutes each).
- At peak all 30 boards are in use. Each sends about one engine call every 2 s at ~50 ms CPU, so the peak load is 0.75 vCPU.
- 3 AI questions per class, each about 3,000 input and 500 output tokens with tool calling.
- About 4 MB of engine data and assets per class; 40 teachers with up to 300 MB of files each.

## Monthly cost
| Item | Basis | ₹ / month |
|---|---|---:|
| Servers | 2 vCPU across two instances (headroom and failover) at ~$25 per vCPU-month | 4,400 |
| AI answers | 12,960 questions, 58M input and 10M output tokens (with +50% headroom), Groq 70B at $0.59/$0.79 per M | 3,704 |
| Storage | 42 GB (files, database, two backups): object storage plus a persistent disk with snapshots | 708 |
| Bandwidth | 30 GB at $0.11/GB (+75% headroom) | 286 |
| Tools | monitoring, e-mail, CDN, domain, error tracking (shared) | 528 |
| Support | one engineer at ₹40,000/month per 20 schools | 2,000 |
| Teacher training | ₹15,000 per school, spread over 12 months | 1,250 |
| **Total** | | **12,876** |

## Price
- **₹22,500 a month** (₹2,70,000 a year) for 30 boards, + GST. That is ₹750 per board, or ₹5.21 per class.
- Each board beyond 30: ₹750 a month.
- After the 2% payment-gateway fee, profit is ₹9,174 a month: **71% on cost, 41% of the price**. This clears the 40% minimum on either definition. The floor for 40% on cost alone is ₹18,394.
