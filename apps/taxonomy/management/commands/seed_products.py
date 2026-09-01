import os
import time
import pandas as pd
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.taxonomy.models import Product, ClassificationResult

class Command(BaseCommand):
    help = 'Seed products from Product_List.xlsx in the root directory into MariaDB database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='Product_List.xlsx',
            help='Relative or absolute path to Product_List.xlsx'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Batch size for bulk insertion'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        batch_size = options['batch_size']

        if not os.path.isabs(file_path):
            file_path = os.path.join(settings.BASE_DIR, file_path)

        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f"Dataset file not found at: {file_path}"))
            return

        self.stdout.write(self.style.NOTICE(f"Reading dataset from {file_path}..."))
        start_time = time.time()

        try:
            # Read excel using pandas and openpyxl
            df = pd.read_excel(file_path, engine='openpyxl')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to read Excel file: {e}"))
            return

        # Strip whitespace from column headers
        df.columns = [str(c).strip() for c in df.columns]
        total_rows = len(df)
        self.stdout.write(self.style.SUCCESS(f"Loaded {total_rows} rows from Excel. Parsing products..."))

        def clean_val(val, default=''):
            if pd.isna(val) or val is None:
                return default
            s = str(val).strip()
            return '' if s.lower() in ('nan', 'none') else s

        def clean_float(val):
            if pd.isna(val) or val is None:
                return None
            try:
                f = float(val)
                return None if pd.isna(f) else f
            except (ValueError, TypeError):
                return None

        def clean_decimal(val):
            if pd.isna(val) or val is None:
                return None
            try:
                # Remove currency symbols or commas
                cleaned = str(val).replace('$', '').replace(',', '').strip()
                if cleaned.lower() in ('nan', 'none', ''):
                    return None
                return Decimal(f"{float(cleaned):.2f}")
            except Exception:
                return None

        def clean_int(val, default=1):
            if pd.isna(val) or val is None:
                return default
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return default

        products_to_create = []
        product_numbers_seen = set()

        for idx, row in df.iterrows():
            prod_num = clean_val(row.get('Product Number'))
            if not prod_num:
                # Fallback identifier if empty
                prod_num = f"PROD-{idx+1:05d}"

            # Deduplicate if duplicate SKU appears in excel
            if prod_num in product_numbers_seen:
                prod_num = f"{prod_num}_{idx+1}"
            product_numbers_seen.add(prod_num)

            # Collect image URLs 1 through 20
            images = []
            for i in range(1, 21):
                col_name = f"Image {i}"
                img_url = clean_val(row.get(col_name))
                if img_url and img_url.startswith('http'):
                    images.append(img_url)

            primary_img = images[0] if images else ''

            p = Product(
                product_number=prod_num,
                model_number=clean_val(row.get('Model Number')),
                product_category=clean_val(row.get('Product Category')),
                product_sub_category=clean_val(row.get('Product Sub Category')),
                collection_name=clean_val(row.get('Collection Name')),
                color_collection=clean_val(row.get('Color Collection')),
                product_color=clean_val(row.get('Product Color')),
                product_name=clean_val(row.get('Product Name'), default=f"Product {prod_num}"),
                product_description=clean_val(row.get('Product Description')),
                bullets=clean_val(row.get('Bullets')),
                set_includes=clean_val(row.get('Set Includes')),
                product_weight=clean_float(row.get('Product Weight')),
                materials=clean_val(row.get('Materials')),
                product_dimensions=clean_val(row.get('Product Dimensions')),
                assembly_required=clean_val(row.get('Assembly Required')),
                is_set=clean_val(row.get('Is a Set')),
                stackable=clean_val(row.get('Stackable')),
                country_of_origin=clean_val(row.get('Country Of Origin')),
                item_cost=clean_decimal(row.get('Item Cost')),
                map_price=clean_decimal(row.get('MAP')),
                msrp=clean_decimal(row.get('MSRP')),
                primary_image_url=primary_img,
                image_urls=images,
                shipping_method=clean_val(row.get('Shipping Method')),
                total_box_count=clean_int(row.get('Total Box Count'), 1),
                pallet_count=clean_float(row.get('Pallet Count')),
                shipping_weight=clean_float(row.get('Shipping Weight')),
                total_cbm=clean_float(row.get('Total CBM')),
                package_dimensions=clean_val(row.get('Package Dimensions')),
                product_url=clean_val(row.get('Product URL')),
            )
            products_to_create.append(p)

        self.stdout.write(self.style.NOTICE(f"Inserting {len(products_to_create)} products in batches of {batch_size}..."))
        
        # Clear existing or bulk upsert
        Product.objects.all().delete()
        
        created_count = 0
        for i in range(0, len(products_to_create), batch_size):
            chunk = products_to_create[i:i + batch_size]
            Product.objects.bulk_create(chunk, batch_size=batch_size)
            created_count += len(chunk)
            self.stdout.write(f"  Inserted {created_count}/{len(products_to_create)} products...")

        elapsed = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded {created_count} products from {file_path} in {elapsed:.2f} seconds!"
        ))
