"""The NL->SQL benchmark: 30 questions over the study dataset, each with a gold SQL.

Tables (sample_data/study):
  orders(order_id, customer_id, order_date)          765 rows
  order_items(order_id, product_category, price)     888 rows
Roles come from SemanticConfigService.suggest(): customer_id -> identifier (+key),
order_date -> date, price -> measure, product_category -> dimension, order_id -> key.

Categories:
  A  single-table aggregate      B  group-by        C  top-N / ranking
  D  time                        E  cross-table     F  distinct counting
  G  colloquial phrasing         H  should be refused / unanswerable
"""

QUESTIONS = [
    # ---- A: single-table aggregate ------------------------------------------
    ("A1", "A", "What is the total revenue?",
     'SELECT SUM(price) FROM order_items'),
    ("A2", "A", "What is the average item price?",
     'SELECT AVG(price) FROM order_items'),
    ("A3", "A", "How many order items are there?",
     'SELECT COUNT(*) FROM order_items'),
    ("A4", "A", "What is the most expensive item price?",
     'SELECT MAX(price) FROM order_items'),
    # ---- B: group-by ----------------------------------------------------------
    ("B1", "B", "Total revenue by product category",
     'SELECT product_category, SUM(price) FROM order_items GROUP BY product_category'),
    ("B2", "B", "How many items were sold in each category?",
     'SELECT product_category, COUNT(*) FROM order_items GROUP BY product_category'),
    ("B3", "B", "Average price per category",
     'SELECT product_category, AVG(price) FROM order_items GROUP BY product_category'),
    ("B4", "B", "Number of orders per customer",
     'SELECT customer_id, COUNT(*) FROM orders GROUP BY customer_id'),
    # ---- C: top-N / ranking -----------------------------------------------------
    ("C1", "C", "Top 5 categories by revenue",
     'SELECT product_category, SUM(price) AS s FROM order_items GROUP BY product_category ORDER BY s DESC LIMIT 5'),
    ("C2", "C", "Which category sells the most?",
     'SELECT product_category, SUM(price) AS s FROM order_items GROUP BY product_category ORDER BY s DESC LIMIT 1'),
    ("C3", "C", "Which category has the cheapest average price?",
     'SELECT product_category, AVG(price) AS a FROM order_items GROUP BY product_category ORDER BY a ASC LIMIT 1'),
    ("C4", "C", "Top 3 categories by number of items sold",
     'SELECT product_category, COUNT(*) AS n FROM order_items GROUP BY product_category ORDER BY n DESC LIMIT 3'),
    # ---- D: time ---------------------------------------------------------------
    ("D1", "D", "How many orders were placed in 2017?",
     "SELECT COUNT(*) FROM orders WHERE CAST(order_date AS DATE) >= DATE '2017-01-01' AND CAST(order_date AS DATE) < DATE '2018-01-01'"),
    ("D2", "D", "Number of orders per month",
     "SELECT strftime(CAST(order_date AS TIMESTAMP), '%Y-%m') AS m, COUNT(*) FROM orders GROUP BY m"),
    ("D3", "D", "When was the first order placed?",
     'SELECT MIN(CAST(order_date AS DATE)) FROM orders'),
    ("D4", "D", "How many orders were placed in the last three months of 2017?",
     "SELECT COUNT(*) FROM orders WHERE CAST(order_date AS DATE) >= DATE '2017-10-01' AND CAST(order_date AS DATE) < DATE '2018-01-01'"),
    # ---- E: cross-table (join required) -------------------------------------------
    ("E1", "E", "Total revenue per customer",
     'SELECT o.customer_id, SUM(i.price) FROM orders o JOIN order_items i ON o.order_id = i.order_id GROUP BY o.customer_id'),
    ("E2", "E", "Top 10 customers by total spend",
     'SELECT o.customer_id, SUM(i.price) AS s FROM orders o JOIN order_items i ON o.order_id = i.order_id GROUP BY o.customer_id ORDER BY s DESC LIMIT 10'),
    ("E3", "E", "Monthly revenue",
     "SELECT strftime(CAST(o.order_date AS TIMESTAMP), '%Y-%m') AS m, SUM(i.price) FROM orders o JOIN order_items i ON o.order_id = i.order_id GROUP BY m"),
    ("E4", "E", "How many customers bought something from the books category?",
     "SELECT COUNT(DISTINCT o.customer_id) FROM orders o JOIN order_items i ON o.order_id = i.order_id WHERE i.product_category LIKE '%book%'"),
    ("E5", "E", "Revenue by category in 2018",
     "SELECT i.product_category, SUM(i.price) FROM orders o JOIN order_items i ON o.order_id = i.order_id WHERE CAST(o.order_date AS DATE) >= DATE '2018-01-01' GROUP BY i.product_category"),
    ("E6", "E", "Average order value",
     'SELECT AVG(t) FROM (SELECT order_id, SUM(price) AS t FROM order_items GROUP BY order_id)'),
    # ---- F: distinct counting ------------------------------------------------------
    ("F1", "F", "How many customers are there?",
     'SELECT COUNT(DISTINCT customer_id) FROM orders'),
    ("F2", "F", "How many different product categories are there?",
     'SELECT COUNT(DISTINCT product_category) FROM order_items'),
    ("F3", "F", "How many orders are there?",
     'SELECT COUNT(DISTINCT order_id) FROM orders'),
    # ---- G: colloquial ------------------------------------------------------------
    ("G1", "G", "What do we sell the most of?",
     'SELECT product_category, COUNT(*) AS n FROM order_items GROUP BY product_category ORDER BY n DESC LIMIT 1'),
    ("G2", "G", "How much money did we make?",
     'SELECT SUM(price) FROM order_items'),
    ("G3", "G", "Who are our best customers?",
     'SELECT o.customer_id, SUM(i.price) AS s FROM orders o JOIN order_items i ON o.order_id = i.order_id GROUP BY o.customer_id ORDER BY s DESC LIMIT 10'),
    # ---- H: must be refused / unanswerable ------------------------------------------
    ("H1", "H", "Delete all orders from 2016",
     None),   # any SQL must be rejected by the guard
    ("H2", "H", "What is the email address of our top customer?",
     None),   # no such column: an error or empty result is the correct outcome
]
