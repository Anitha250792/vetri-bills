from django.dispatch import Signal

# Sent after stock or expiry data changed, once the product's stock has been recalculated.
# Arguments: product (Product), batch (ProductBatch or None).
stock_changed = Signal()
