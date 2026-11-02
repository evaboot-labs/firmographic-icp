# Which accounts to list

The ICP is only as good as the deals behind it.

## Where they come from

- **Won:** closed-won deals of the last 12 to 24 months. Leave out customers who churned within 6 months: they bought, but they did not fit.
- **Lost:** closed-lost deals of the same period, after at least a first meeting. A cold lead who never answered says nothing about fit.
- **How many:** 20 of each gives a real signal. With 5 of each, every value rests on one or two deals: treat the ICP as a first guess and rerun it each quarter.

## The LinkedIn id

The number in `linkedin.com/company/<id>`, or in a Sales Navigator company URL (`/sales/company/<id>`). A company page with a name in the URL (`linkedin.com/company/lemlist`) shows the id in Sales Navigator: open the company there and read the URL.

## What the comparison reads

One Evaboot export row per account carries these company fields: industry, employee range, headquarters, headcount growth over 6 months, 1 year and 2 years, company type, founding year and LinkedIn's revenue estimate. `icp.py` uses the 1-year growth.

Department headcount, technologies and funding are not in the row. Add them by hand to the "Your ICP" list in `ICP.md` when your CRM holds them.

Back to the [README](../README.md).
