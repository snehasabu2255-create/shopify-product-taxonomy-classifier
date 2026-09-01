import re

COMMON_MATERIALS = [
    'Bonded Leather', 'Genuine Leather', 'Faux Leather', 'Leather',
    'Velvet', 'Performance Velvet', 'Boucle', 'Bouclé', 'Linen', 'Polyester', 'Fabric',
    'Solid Wood', 'Rubberwood', 'Walnut Wood', 'Oak Wood', 'Teak Wood', 'Ash Wood', 'Pine Wood', 'Wood',
    'Stainless Steel', 'Brushed Gold', 'Brass', 'Chrome', 'Iron', 'Aluminum', 'Metal',
    'Tempered Glass', 'Glass', 'Marble', 'Rattan', 'Wicker', 'Rope', 'Acrylic', 'Foam'
]

COMMON_COLORS = [
    'White', 'Black', 'Grey', 'Gray', 'Charcoal', 'Beige', 'Cream', 'Ivory', 'Off-White',
    'Brown', 'Cognac', 'Tan', 'Walnut', 'Natural', 'Teak', 'Espresso',
    'Blue', 'Navy', 'Teal', 'Sky Blue', 'Dusty Blue', 'Azure',
    'Green', 'Emerald', 'Olive', 'Sage', 'Mint', 'Forest Green',
    'Pink', 'Dusty Rose', 'Blush', 'Red', 'Burgundy', 'Terracotta', 'Rust',
    'Yellow', 'Mustard', 'Gold', 'Orange', 'Purple', 'Silver'
]

def extract_attributes_for_product(product, shopify_category=None):
    """
    Extract structured attributes & attribute values for a product.
    Matches extracted fields against official Shopify Category attributes when provided.
    """
    attributes = {}

    # 1. Color extraction
    color = ''
    if product.product_color and str(product.product_color).strip().lower() not in ('nan', 'none', ''):
        color = str(product.product_color).strip()
    elif product.color_collection and str(product.color_collection).strip().lower() not in ('nan', 'none', ''):
        color = str(product.color_collection).strip()
    else:
        # Scan title
        for c in COMMON_COLORS:
            if re.search(r'\b' + re.escape(c) + r'\b', product.product_name, re.IGNORECASE):
                color = c
                break
    if color:
        attributes['Color'] = color

    # 2. Material extraction
    material = ''
    if product.materials and str(product.materials).strip().lower() not in ('nan', 'none', ''):
        material = str(product.materials).strip()
    else:
        # Search title and description
        text_corpus = f"{product.product_name} {product.bullets} {product.product_description}"
        found_materials = []
        for m in COMMON_MATERIALS:
            if re.search(r'\b' + re.escape(m) + r'\b', text_corpus, re.IGNORECASE):
                found_materials.append(m)
        if found_materials:
            # Sort by length descending to match most specific first
            found_materials.sort(key=len, reverse=True)
            material = ', '.join(found_materials[:2])

    if material:
        attributes['Material'] = material

    # 3. Assembly Required
    if product.assembly_required:
        val = str(product.assembly_required).strip().upper()
        if val in ('Y', 'YES', 'TRUE', '1'):
            attributes['Assembly Required'] = 'Yes'
        elif val in ('N', 'NO', 'FALSE', '0'):
            attributes['Assembly Required'] = 'No'

    # 4. Is a Set / Count
    if product.is_set:
        val = str(product.is_set).strip().upper()
        if val in ('Y', 'YES', 'TRUE', '1'):
            attributes['Is a Set'] = 'Yes'
        elif val in ('N', 'NO', 'FALSE', '0'):
            attributes['Is a Set'] = 'No'

    # 5. Stackable
    if product.stackable:
        val = str(product.stackable).strip().upper()
        if val in ('Y', 'YES', 'TRUE', '1'):
            attributes['Stackable'] = 'Yes'
        elif val in ('N', 'NO', 'FALSE', '0'):
            attributes['Stackable'] = 'No'

    # 6. Weight
    if product.product_weight and str(product.product_weight).strip().lower() not in ('nan', 'none', ''):
        try:
            w = float(product.product_weight)
            if w > 0:
                attributes['Product Weight'] = f"{w:g} lbs"
        except (ValueError, TypeError):
            pass

    # 7. Dimensions
    if product.product_dimensions and str(product.product_dimensions).strip().lower() not in ('nan', 'none', ''):
        dim_str = str(product.product_dimensions).strip()
        # Find first overall dimension line if multiline
        overall_match = re.search(r'Overall[^:]*:\s*([^\r\n]+)', dim_str, re.IGNORECASE)
        if overall_match:
            attributes['Dimensions'] = overall_match.group(1).strip()
        else:
            # Extract first line
            first_line = dim_str.splitlines()[0].strip()
            if len(first_line) > 5:
                attributes['Dimensions'] = first_line[:120]

    # 8. Room / Location
    if product.product_category and str(product.product_category).strip().lower() not in ('nan', 'none', ''):
        cat = str(product.product_category).strip()
        attributes['Room Type'] = cat

    # 9. Collection
    if product.collection_name and str(product.collection_name).strip().lower() not in ('nan', 'none', ''):
        attributes['Collection'] = str(product.collection_name).strip()

    # 10. Country of Origin
    if product.country_of_origin and str(product.country_of_origin).strip().lower() not in ('nan', 'none', ''):
        attributes['Country of Origin'] = str(product.country_of_origin).strip()

    # 11. Pattern & Special Features
    combined_text = f"{product.product_name} {product.bullets}".lower()
    if 'tufted' in combined_text:
        attributes['Pattern / Detail'] = 'Button Tufted'
    elif 'channel tufted' in combined_text:
        attributes['Pattern / Detail'] = 'Channel Tufted'
    elif 'striped' in combined_text:
        attributes['Pattern / Detail'] = 'Striped'
    elif 'geometric' in combined_text:
        attributes['Pattern / Detail'] = 'Geometric'

    if 'swivel' in combined_text:
        attributes['Special Features'] = '360-Degree Swivel'
    elif 'extendable' in combined_text:
        attributes['Special Features'] = 'Extendable'
    elif 'adjustable height' in combined_text:
        attributes['Special Features'] = 'Adjustable Height'

    return attributes
