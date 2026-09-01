import threading
import time
import traceback
from django.utils import timezone
from django.db import transaction
from apps.taxonomy.models import Product, ClassificationResult, BatchJob
from apps.taxonomy.services.ai_matcher import TaxonomyMatcher
from apps.taxonomy.services.attribute_extractor import extract_attributes_for_product

_JOB_THREAD = None
_PAUSE_EVENT = threading.Event()
_STOP_EVENT = threading.Event()

def get_or_create_batch_job(job_id='default_job'):
    total_count = Product.objects.count()
    job, created = BatchJob.objects.get_or_create(
        job_id=job_id,
        defaults={'total_items': total_count, 'status': BatchJob.STATUS_IDLE}
    )
    if job.total_items != total_count:
        job.total_items = total_count
        job.save(update_fields=['total_items'])
    return job

def _batch_worker(job_id='default_job', chunk_size=50):
    global _JOB_THREAD
    matcher = TaxonomyMatcher.get_instance()
    matcher.initialize()

    job = get_or_create_batch_job(job_id)
    job.status = BatchJob.STATUS_RUNNING
    if not job.started_at:
        job.started_at = timezone.now()
    job.error_message = ''
    job.save()

    _PAUSE_EVENT.clear()
    _STOP_EVENT.clear()

    try:
        while True:
            if _STOP_EVENT.is_set():
                job.refresh_from_db()
                job.status = BatchJob.STATUS_IDLE
                job.save()
                break

            if _PAUSE_EVENT.is_set():
                job.refresh_from_db()
                job.status = BatchJob.STATUS_PAUSED
                job.save()
                break

            # Fetch next chunk of products with ID > last_processed_product_id
            # Order by id ascending for guaranteed resume logic
            products_chunk = list(
                Product.objects.filter(id__gt=job.last_processed_product_id)
                .order_by('id')[:chunk_size]
            )

            if not products_chunk:
                # All products have been processed!
                job.refresh_from_db()
                job.status = BatchJob.STATUS_COMPLETED
                job.completed_at = timezone.now()
                job.save()
                break

            # Process chunk with graceful error handling
            with transaction.atomic():
                for product in products_chunk:
                    try:
                        # Extract attributes
                        extracted_attrs = extract_attributes_for_product(product)

                        # Match taxonomy category
                        best_cat, cat_name, confidence, status, alternatives = matcher.classify_product(product)

                        # Save or update ClassificationResult
                        ClassificationResult.objects.update_or_create(
                            product=product,
                            defaults={
                                'predicted_category': best_cat,
                                'predicted_category_name': cat_name,
                                'confidence_score': confidence,
                                'status': status,
                                'extracted_attributes': extracted_attrs,
                                'alternative_categories': alternatives,
                                'classified_at': timezone.now(),
                            }
                        )

                        if status == ClassificationResult.STATUS_REQUIRES_REVIEW:
                            job.review_needed_items += 1
                        else:
                            job.success_items += 1

                    except Exception as item_err:
                        # Gracefully record error on item without halting batch job
                        print(f"Warning: Error processing product {product.product_number}: {item_err}")

                    job.processed_items += 1
                    job.current_index += 1
                    job.last_processed_product_id = product.id

                # Update job progress in database
                job.save()

            # Small yield to prevent thread starvation
            time.sleep(0.01)

    except Exception as e:
        job.refresh_from_db()
        job.status = BatchJob.STATUS_FAILED
        job.error_message = f"{str(e)}\n{traceback.format_exc()}"
        job.save()
    finally:
        _JOB_THREAD = None

def start_batch_job(job_id='default_job', chunk_size=50):
    global _JOB_THREAD
    job = get_or_create_batch_job(job_id)

    if _JOB_THREAD is not None and _JOB_THREAD.is_alive():
        return {'status': 'ALREADY_RUNNING', 'job': job}

    _PAUSE_EVENT.clear()
    _STOP_EVENT.clear()

    _JOB_THREAD = threading.Thread(
        target=_batch_worker,
        args=(job_id, chunk_size),
        daemon=True
    )
    _JOB_THREAD.start()

    return {'status': 'STARTED', 'job': job}

def pause_batch_job(job_id='default_job'):
    global _JOB_THREAD
    _PAUSE_EVENT.set()
    job = get_or_create_batch_job(job_id)
    job.status = BatchJob.STATUS_PAUSED
    job.save(update_fields=['status'])
    return {'status': 'PAUSED', 'job': job}

def resume_batch_job(job_id='default_job', chunk_size=50):
    return start_batch_job(job_id, chunk_size)

def reset_batch_job(job_id='default_job'):
    global _JOB_THREAD
    _STOP_EVENT.set()
    time.sleep(0.2)
    job = get_or_create_batch_job(job_id)
    job.status = BatchJob.STATUS_IDLE
    job.processed_items = 0
    job.success_items = 0
    job.review_needed_items = 0
    job.last_processed_product_id = 0
    job.current_index = 0
    job.started_at = None
    job.completed_at = None
    job.error_message = ''
    job.save()
    return {'status': 'RESET', 'job': job}

def get_batch_job_status(job_id='default_job'):
    return get_or_create_batch_job(job_id)
