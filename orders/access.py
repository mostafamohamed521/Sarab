def get_order_or_403(request, order):
    """
    Returns True if the current request is allowed to view `order`:
      - the logged-in user who placed it, or
      - a guest who placed it in this browser session (tracked via
        session['last_order_id'], set once at the moment of checkout).

    This exists because order_number/order id appear directly in
    public-looking URLs (success/tracking/invoice pages); without this
    check, anyone who obtains an order number could view another
    customer's name, address, phone, and order contents (IDOR).
    """
    if order.user_id is not None:
        return request.user.is_authenticated and request.user.pk == order.user_id
    return request.session.get('last_order_id') == order.id
