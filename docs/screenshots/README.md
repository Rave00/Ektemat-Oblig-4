# Screenshots for the report

Taken with Playwright after `python seed.py` (synthetic data only). From plan 3 on, the browser runs with
Norwegian settings, so date fields look as they do for Ekte Mat's customers (22.10.2026).

| File | Screen | Requirement |
|---|---|---|
| `plan1-food-items.png` | Admin: food items table | A1 |
| `plan1-add-form-with-errors.png` | Admin: add food item, with validation errors | A1 |
| `plan1-edit-food-item.png` | Admin: edit food item with its picture | A1, A2 |
| `plan1-picture-preview.png` | Admin: new picture preview before saving | A2 |
| `plan2-menu.png` | Customer: menu with event and dietary-label filters, first section | C1 |
| `plan2-menu-wedding.png` | Customer: menu filtered on one event (wedding) | C1 |
| `plan2-cart.png` | Customer: cart with three dishes and the estimated total | C2 |
| `plan2-menu-phone.png` | Customer: menu at phone width (390 px), julebord | C1 |
| `plan2-cart-phone.png` | Customer: cart at phone width (390 px) | C2 |
| `plan3-register.png` | Customer: create an account (reached from "Send booking request") | C3 |
| `plan3-order-form.png` | Customer: order form with the cart summary and guest groups | C3 |
| `plan3-order-form-errors.png` | Customer: order form with every kind of mistake marked | C3 |
| `plan3-order-page.png` | Customer: the order page after sending (the receipt) | C3 |
| `plan3-order-form-phone.png` | Customer: order form at phone width (390 px) | C3 |
| `plan3-order-page-phone.png` | Customer: order page at phone width (390 px) | C3 |
| `plan4-my-orders.png` | Customer: My orders with status and payment status | C4 |
| `plan4-my-orders-phone.png` | Customer: My orders at phone width (390 px) | C4 |
| `plan4-order-list.png` | Admin: all orders, status filters with counts, one highlighted after 24 hours | A3 |
| `plan4-order-list-filtered.png` | Admin: orders filtered by event date | A3 |
| `plan4-order-page-admin.png` | Admin: order page with the allowed status changes and the payment status | A3 |
| `plan4-order-page-admin-phone.png` | Admin: order page at phone width (390 px), after approving | A3 |
| `plan4-dashboard.png` | Admin: dashboard with waiting orders and the share answered within 24 hours | A3, NFR-19 |
