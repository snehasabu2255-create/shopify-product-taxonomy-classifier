from django.test import TransactionTestCase, Client
from apps.taxonomy.models import Product, ShopifyCategory, ClassificationResult, BatchJob
from apps.taxonomy.services.ai_matcher import TaxonomyMatcher
from apps.taxonomy.services.attribute_extractor import extract_attributes_for_product
from apps.taxonomy.services.batch_processor import start_batch_job, pause_batch_job, resume_batch_job, reset_batch_job, get_batch_job_status
import time

class TaxonomyClassificationTests(TransactionTestCase):
    def setUp(self):
        self.client = Client()
        
        # Create test categories
        self.cat_sofa = ShopifyCategory.objects.create(
            category_gid="gid://shopify/TaxonomyCategory/fu-1",
            name="Sofas",
            full_name="Furniture > Sofas",
            level=1,
            vertical_name="Furniture",
            attributes_json=[{"name": "Color"}, {"name": "Material"}],
            search_text="Furniture > Sofas Sofas Furniture"
        )
        self.cat_chair = ShopifyCategory.objects.create(
            category_gid="gid://shopify/TaxonomyCategory/fu-2",
            name="Armchairs, Recliners & Sleeper Chairs",
            full_name="Furniture > Chairs > Armchairs, Recliners & Sleeper Chairs",
            level=2,
            vertical_name="Furniture",
            attributes_json=[{"name": "Color"}, {"name": "Material"}],
            search_text="Furniture > Chairs > Armchairs Armchairs Chairs Furniture"
        )
        self.cat_desk = ShopifyCategory.objects.create(
            category_gid="gid://shopify/TaxonomyCategory/fu-4-1",
            name="Desks",
            full_name="Furniture > Office Furniture > Desks",
            level=2,
            vertical_name="Furniture",
            attributes_json=[{"name": "Material"}, {"name": "Dimensions"}],
            search_text="Furniture > Office Furniture > Desks Desks Office Furniture"
        )

        # Create test products
        self.prod1 = Product.objects.create(
            product_number="TEST-SOFA-01",
            product_name="Empress Bonded Leather Sofa by Modway",
            product_category="Living Room",
            product_sub_category="Sofas and Armchairs",
            product_color="White",
            materials="Bonded Leather",
            assembly_required="Y",
            is_set="N",
            product_weight=105.0,
            product_dimensions='Overall Product Dimensions: 35.5"L x 84"W x 34.5"H',
            bullets="Modern Sofa\nTufted Buttons\nBonded Leather",
            item_cost=500.0,
            msrp=1200.0
        )

        self.prod2 = Product.objects.create(
            product_number="TEST-DESK-01",
            product_name="Transmit Modern Computer Desk by Modway",
            product_category="Office Furniture",
            product_sub_category="Computer Desks",
            product_color="Walnut",
            materials="Wood",
            assembly_required="Y",
            is_set="N",
            product_weight=65.0,
            product_dimensions='Overall Product Dimensions: 24"L x 48"W x 30"H',
            bullets="Office Desk\nStorage Drawers",
            item_cost=200.0,
            msrp=450.0
        )

        # Initialize matcher
        self.matcher = TaxonomyMatcher.get_instance()
        self.matcher.initialize(force=True)

    def test_attribute_extractor(self):
        attrs = extract_attributes_for_product(self.prod1)
        self.assertEqual(attrs.get('Color'), 'White')
        self.assertEqual(attrs.get('Material'), 'Bonded Leather')
        self.assertEqual(attrs.get('Assembly Required'), 'Yes')
        self.assertEqual(attrs.get('Is a Set'), 'No')
        self.assertIn('105', attrs.get('Product Weight', ''))

    def test_ai_classification_prediction(self):
        cat, cat_name, conf, status, alts = self.matcher.classify_product(self.prod1)
        self.assertIsNotNone(cat)
        self.assertIn('Sofa', cat_name)
        self.assertGreaterEqual(conf, 60.0)
        self.assertIn(status, ['CLASSIFIED', 'APPROVED'])

    def test_metrics_api_endpoint(self):
        response = self.client.get('/api/metrics/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['total_products'], 2)
        self.assertIn('average_confidence', data)

    def test_product_list_api_endpoint(self):
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 2)

    def test_product_review_override_api(self):
        payload = {
            "category_id": self.cat_sofa.id,
            "category_name": "Furniture > Sofas",
            "extracted_attributes": {"Color": "Pure White", "Material": "Leather"},
            "review_notes": "Verified by Specialist",
            "status": "APPROVED"
        }
        response = self.client.post(
            f'/api/products/{self.prod1.id}/review/',
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        clf = ClassificationResult.objects.get(product=self.prod1)
        self.assertEqual(clf.status, 'APPROVED')
        self.assertEqual(clf.confidence_score, 100.0)
        self.assertEqual(clf.extracted_attributes.get('Color'), 'Pure White')
        self.assertTrue(clf.is_reviewed)

    def test_batch_processor_and_resume_logic(self):
        # Create 10 items
        for i in range(10):
            Product.objects.create(
                product_number=f"BATCH-SKU-{i+1:03d}",
                product_name=f"Modern Chair Model {i+1} by Modway",
                product_category="Living Room",
                product_sub_category="Sofas and Armchairs",
                product_color="Grey",
                materials="Fabric"
            )

        # Start batch
        start_batch_job(chunk_size=5)
        time.sleep(1.0)

        # Check job progress
        job = get_batch_job_status()
        self.assertGreaterEqual(job.processed_items, 0)

        # Pause
        pause_batch_job()
        time.sleep(0.2)
        job.refresh_from_db()
        last_id = job.last_processed_product_id

        # Resume
        resume_batch_job(chunk_size=5)
        time.sleep(0.5)
        job.refresh_from_db()
        self.assertGreaterEqual(job.last_processed_product_id, last_id)

    def test_taxonomy_search_api(self):
        response = self.client.get('/api/taxonomy/search/?q=Sofa')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 1)

    def test_template_views(self):
        r1 = self.client.get('/')
        self.assertEqual(r1.status_code, 200)
        self.assertContains(r1, 'Executive Taxonomy Dashboard')

        r2 = self.client.get('/review/')
        self.assertEqual(r2.status_code, 200)
        self.assertContains(r2, 'Focused Review Queue')
