import os
import json
import gzip
import urllib.request
import time
from django.core.management.base import BaseCommand
from apps.taxonomy.models import ShopifyCategory, ShopifyAttribute
from apps.taxonomy.services.ai_matcher import TaxonomyMatcher

FALLBACK_CATEGORIES = [
    # Furniture Verticals
    ("gid://shopify/TaxonomyCategory/fu", "Furniture", "Furniture", 0, "Furniture", ["Material", "Color", "Room Type"]),
    ("gid://shopify/TaxonomyCategory/fu-1", "Sofas", "Furniture > Sofas", 1, "Furniture", ["Color", "Material", "Seating Capacity", "Pattern"]),
    ("gid://shopify/TaxonomyCategory/fu-1-1", "Sectional Sofas", "Furniture > Sofas > Sectional Sofas", 2, "Furniture", ["Color", "Material", "Orientation", "Shape"]),
    ("gid://shopify/TaxonomyCategory/fu-1-2", "Loveseats", "Furniture > Sofas > Loveseats", 2, "Furniture", ["Color", "Material", "Seating Capacity"]),
    ("gid://shopify/TaxonomyCategory/fu-1-3", "Sleeper Sofas", "Furniture > Sofas > Sleeper Sofas", 2, "Furniture", ["Color", "Material", "Bed Size"]),
    ("gid://shopify/TaxonomyCategory/fu-2", "Chairs", "Furniture > Chairs", 1, "Furniture", ["Color", "Material", "Assembly Required"]),
    ("gid://shopify/TaxonomyCategory/fu-2-1", "Armchairs, Recliners & Sleeper Chairs", "Furniture > Chairs > Armchairs, Recliners & Sleeper Chairs", 2, "Furniture", ["Color", "Material", "Arm Style"]),
    ("gid://shopify/TaxonomyCategory/fu-2-2", "Kitchen & Dining Room Chairs", "Furniture > Chairs > Kitchen & Dining Room Chairs", 2, "Furniture", ["Color", "Material", "Set Count", "Stackable"]),
    ("gid://shopify/TaxonomyCategory/fu-2-3", "Table & Bar Stools", "Furniture > Chairs > Table & Bar Stools", 2, "Furniture", ["Color", "Material", "Seat Height", "Swivel"]),
    ("gid://shopify/TaxonomyCategory/fu-2-4", "Office Chairs", "Furniture > Chairs > Office Chairs", 2, "Furniture", ["Color", "Material", "Ergonomic", "Swivel", "Adjustable Height"]),
    ("gid://shopify/TaxonomyCategory/fu-2-5", "Benches", "Furniture > Chairs > Benches", 2, "Furniture", ["Color", "Material", "Upholstered"]),
    ("gid://shopify/TaxonomyCategory/fu-3", "Tables", "Furniture > Tables", 1, "Furniture", ["Material", "Shape", "Color"]),
    ("gid://shopify/TaxonomyCategory/fu-3-1", "Coffee Tables", "Furniture > Tables > Coffee Tables", 2, "Furniture", ["Material", "Shape", "Dimensions", "Color"]),
    ("gid://shopify/TaxonomyCategory/fu-3-2", "Kitchen & Dining Room Tables", "Furniture > Tables > Kitchen & Dining Room Tables", 2, "Furniture", ["Material", "Shape", "Seating Capacity"]),
    ("gid://shopify/TaxonomyCategory/fu-3-3", "Accent & Side Tables", "Furniture > Tables > Accent & Side Tables", 2, "Furniture", ["Material", "Shape", "Color"]),
    ("gid://shopify/TaxonomyCategory/fu-3-4", "Nightstands", "Furniture > Tables > Nightstands", 2, "Furniture", ["Material", "Drawers", "Color"]),
    ("gid://shopify/TaxonomyCategory/fu-4", "Office Furniture", "Furniture > Office Furniture", 1, "Furniture", ["Material", "Room Type"]),
    ("gid://shopify/TaxonomyCategory/fu-4-1", "Desks", "Furniture > Office Furniture > Desks", 2, "Furniture", ["Material", "Dimensions", "Shape", "Color"]),
    ("gid://shopify/TaxonomyCategory/fu-4-2", "Office Desks", "Furniture > Office Furniture > Office Desks", 2, "Furniture", ["Material", "Storage"]),
    ("gid://shopify/TaxonomyCategory/fu-4-3", "Bookcases & Standing Shelves", "Furniture > Office Furniture > Bookcases & Standing Shelves", 2, "Furniture", ["Material", "Shelves Count"]),
    ("gid://shopify/TaxonomyCategory/fu-5", "Outdoor Furniture", "Furniture > Outdoor Furniture", 1, "Furniture", ["Material", "Weather Resistant", "Color"]),
    ("gid://shopify/TaxonomyCategory/fu-5-1", "Outdoor Sofas & Sectionals", "Furniture > Outdoor Furniture > Outdoor Sofas & Sectionals", 2, "Furniture", ["Material", "Cushion Color", "Weather Resistant"]),
    ("gid://shopify/TaxonomyCategory/fu-5-2", "Outdoor Chairs", "Furniture > Outdoor Furniture > Outdoor Chairs", 2, "Furniture", ["Material", "Stackable", "Weather Resistant"]),
    ("gid://shopify/TaxonomyCategory/fu-5-3", "Outdoor Tables", "Furniture > Outdoor Furniture > Outdoor Tables", 2, "Furniture", ["Material", "Weather Resistant"]),
    ("gid://shopify/TaxonomyCategory/fu-5-4", "Outdoor Chaises & Sunloungers", "Furniture > Outdoor Furniture > Outdoor Chaises & Sunloungers", 2, "Furniture", ["Material", "Reclining", "Weather Resistant"]),
    ("gid://shopify/TaxonomyCategory/fu-5-5", "Outdoor Dining Sets", "Furniture > Outdoor Furniture > Outdoor Dining Sets", 2, "Furniture", ["Material", "Pieces Count"]),
    ("gid://shopify/TaxonomyCategory/fu-6", "Bedroom Furniture", "Furniture > Bedroom Furniture", 1, "Furniture", ["Material", "Color"]),
    ("gid://shopify/TaxonomyCategory/fu-6-1", "Beds & Bed Frames", "Furniture > Bedroom Furniture > Beds & Bed Frames", 2, "Furniture", ["Bed Size", "Headboard Style", "Material", "Color"]),
    ("gid://shopify/TaxonomyCategory/fu-6-2", "Headboards & Footboards", "Furniture > Bedroom Furniture > Headboards & Footboards", 2, "Furniture", ["Bed Size", "Material", "Upholstered"]),
    ("gid://shopify/TaxonomyCategory/fu-6-3", "Dressers", "Furniture > Bedroom Furniture > Dressers", 2, "Furniture", ["Material", "Drawers Count", "Color"]),
    ("gid://shopify/TaxonomyCategory/fu-6-4", "Vanities", "Furniture > Bedroom Furniture > Vanities", 2, "Furniture", ["Material", "Mirror Included", "Color"]),
    ("gid://shopify/TaxonomyCategory/fu-6-5", "Daybeds", "Furniture > Bedroom Furniture > Daybeds", 2, "Furniture", ["Bed Size", "Material", "Trundle Included"]),
    ("gid://shopify/TaxonomyCategory/fu-7", "Cabinets & Storage", "Furniture > Cabinets & Storage", 1, "Furniture", ["Material", "Color"]),
    ("gid://shopify/TaxonomyCategory/fu-7-1", "Buffets & Sideboards", "Furniture > Cabinets & Storage > Buffets & Sideboards", 2, "Furniture", ["Material", "Storage", "Color"]),
    ("gid://shopify/TaxonomyCategory/fu-7-2", "Media Storage & Entertainment Centers", "Furniture > Cabinets & Storage > Media Storage & Entertainment Centers", 2, "Furniture", ["TV Size Compatibility", "Material"]),
    
    # Lighting Verticals
    ("gid://shopify/TaxonomyCategory/hg-1", "Home & Garden > Lighting", "Home & Garden > Lighting", 1, "Home & Garden", ["Lighting Type", "Color", "Material"]),
    ("gid://shopify/TaxonomyCategory/hg-1-1", "Lamps", "Home & Garden > Lighting > Lamps", 2, "Home & Garden", ["Lamp Type", "Color", "Base Material"]),
    ("gid://shopify/TaxonomyCategory/hg-1-2", "Table Lamps", "Home & Garden > Lighting > Lamps > Table Lamps", 3, "Home & Garden", ["Color", "Material", "Bulb Type"]),
    ("gid://shopify/TaxonomyCategory/hg-1-3", "Floor Lamps", "Home & Garden > Lighting > Lamps > Floor Lamps", 3, "Home & Garden", ["Color", "Material", "Height"]),
    ("gid://shopify/TaxonomyCategory/hg-1-4", "Chandeliers & Ceiling Fixture Lights", "Home & Garden > Lighting > Chandeliers & Ceiling Fixture Lights", 2, "Home & Garden", ["Fixture Type", "Material", "Color"]),
    ("gid://shopify/TaxonomyCategory/hg-1-5", "Pendant Lights", "Home & Garden > Lighting > Chandeliers & Ceiling Fixture Lights > Pendant Lights", 3, "Home & Garden", ["Material", "Shade Color"]),
    ("gid://shopify/TaxonomyCategory/hg-1-6", "Wall Lights & Sconces", "Home & Garden > Lighting > Wall Lights & Sconces", 2, "Home & Garden", ["Material", "Color"]),

    # Bathroom Verticals
    ("gid://shopify/TaxonomyCategory/hg-2", "Bathroom Furniture", "Home & Garden > Bathroom Accessories > Bathroom Furniture", 2, "Home & Garden", ["Material", "Color"]),
    ("gid://shopify/TaxonomyCategory/hg-2-1", "Bathroom Vanities", "Home & Garden > Bathroom Accessories > Bathroom Furniture > Bathroom Vanities", 3, "Home & Garden", ["Material", "Sink Count", "Color"]),
    ("gid://shopify/TaxonomyCategory/hg-2-2", "Bathroom Mirrors", "Home & Garden > Bathroom Accessories > Bathroom Mirrors", 2, "Home & Garden", ["Shape", "Frame Material"]),

    # Decor Verticals
    ("gid://shopify/TaxonomyCategory/hg-3", "Decor", "Home & Garden > Decor", 1, "Home & Garden", ["Material", "Color", "Style"]),
    ("gid://shopify/TaxonomyCategory/hg-3-1", "Throw Pillows", "Home & Garden > Decor > Throw Pillows", 2, "Home & Garden", ["Color", "Pattern", "Fabric", "Fill Material"]),
    ("gid://shopify/TaxonomyCategory/hg-3-2", "Rugs", "Home & Garden > Decor > Rugs", 2, "Home & Garden", ["Dimensions", "Material", "Color", "Pattern"]),
    ("gid://shopify/TaxonomyCategory/hg-3-3", "Wall Art", "Home & Garden > Decor > Artwork > Wall Art", 3, "Home & Garden", ["Subject", "Frame Type", "Medium"]),
    ("gid://shopify/TaxonomyCategory/hg-3-4", "Mirrors", "Home & Garden > Decor > Mirrors", 2, "Home & Garden", ["Shape", "Frame Material", "Mount Type"]),
]

class Command(BaseCommand):
    help = 'Seed official Shopify Standard Product Taxonomy categories and attributes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-online',
            action='store_true',
            help='Force download latest taxonomy distribution from GitHub'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initializing Shopify Product Taxonomy seeding..."))
        start_time = time.time()

        downloaded_categories = []
        url = 'https://github.com/Shopify/product-taxonomy/releases/latest/download/categories.en.json.gz'

        try:
            self.stdout.write(f"Attempting to fetch full official taxonomy from {url}...")
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw_data = gzip.decompress(resp.read())
                taxonomy_data = json.loads(raw_data.decode('utf-8'))
                
                for vert in taxonomy_data.get('verticals', []):
                    vert_name = vert.get('name', '')
                    for cat in vert.get('categories', []):
                        gid = cat.get('id')
                        name = cat.get('name')
                        full_name = cat.get('full_name') or name
                        level = cat.get('level', 0)
                        parent_gid = cat.get('parent_id')
                        attrs = cat.get('attributes', [])
                        
                        search_parts = [full_name, name, vert_name]
                        for a in attrs:
                            search_parts.append(a.get('name', ''))
                        
                        downloaded_categories.append(ShopifyCategory(
                            category_gid=gid,
                            name=name,
                            full_name=full_name,
                            level=level,
                            parent_gid=parent_gid,
                            vertical_name=vert_name,
                            attributes_json=attrs,
                            search_text=' '.join(search_parts)
                        ))

            self.stdout.write(self.style.SUCCESS(f"Successfully downloaded {len(downloaded_categories)} official categories!"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Online download skipped/failed ({e}). Seeding comprehensive fallback taxonomy..."))

        categories_to_seed = []
        if downloaded_categories:
            categories_to_seed = downloaded_categories
        else:
            for gid, name, full_name, level, vert, attrs in FALLBACK_CATEGORIES:
                attrs_obj = [{'name': a, 'handle': a.lower().replace(' ', '-')} for a in attrs]
                categories_to_seed.append(ShopifyCategory(
                    category_gid=gid,
                    name=name,
                    full_name=full_name,
                    level=level,
                    parent_gid=None,
                    vertical_name=vert,
                    attributes_json=attrs_obj,
                    search_text=f"{full_name} {name} {vert} {' '.join(attrs)}"
                ))

        self.stdout.write(f"Upserting {len(categories_to_seed)} taxonomy categories into database...")
        
        # Clear & bulk insert
        ShopifyCategory.objects.all().delete()
        
        batch_size = 1000
        for i in range(0, len(categories_to_seed), batch_size):
            chunk = categories_to_seed[i:i + batch_size]
            ShopifyCategory.objects.bulk_create(chunk, batch_size=batch_size)

        # Re-initialize AI Matcher in-memory index
        self.stdout.write("Building AI Semantic Vector Search Index...")
        matcher = TaxonomyMatcher.get_instance()
        matcher.initialize(force=True)

        elapsed = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(
            f"Taxonomy initialized with {len(categories_to_seed)} categories in {elapsed:.2f} seconds!"
        ))
