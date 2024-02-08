def completely_flatten(nested_list):
    """
    Slaat lijst van lijsten van arbitraire diepte volledigplat
    """
    flat_list = []
    for element in nested_list:
        if isinstance(element, list):
            flat_list.extend(completely_flatten(element))
        else:
            flat_list.append(element)
    return flat_list
