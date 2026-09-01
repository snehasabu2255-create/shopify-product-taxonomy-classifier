# Candidate Questions & Answers

**1. What approach would you use to automatically identify the Shopify category, attributes, and attribute values? Explain your approach and why you selected it.**
**Approach:** I would use a Large Language Model (LLM) combined with Retrieval-Augmented Generation (RAG). By feeding the product title, description, and an embedding-based search of the Shopify taxonomy into an LLM (like GPT-4o or Claude 3.5), we can prompt it to output a structured JSON response containing the category ID, attributes, and values.
**Why:** The Shopify taxonomy is vast and continuously evolving. Traditional rule-based engines or supervised ML models (like Random Forests) require massive labeled datasets and constant retraining. LLMs excel at zero-shot entity extraction and contextual understanding, making them perfect for parsing unstructured product data into structured taxonomies with minimal overhead.

**2. How would you handle a product that has a title but no description and no image?**
I would rely entirely on the product title and pass it to the LLM for zero-shot classification. Since the context is sparse, the confidence score will likely be lower. The system should be configured to flag classifications with low confidence (e.g., < 75%) and assign them a `REQUIRES_REVIEW` status, routing them to an admin dashboard for manual human verification.

**3. How would you use product images to improve classification when an image is available?**
I would integrate a Vision-Language Model (VLM), such as GPT-4V or Claude 3.5 Sonnet. The VLM can analyze the image alongside the text to extract visual attributes that are often missing from descriptions (e.g., color, pattern, material, exact shape). These visual features are then used to refine the category prediction and accurately populate the product attributes.

**4. How would you design the application to process 10,000+ products efficiently? Explain your approach for batch/background processing.**
I would use an asynchronous task queue like **Celery** with **Redis** or RabbitMQ as the message broker. When a batch is uploaded, the web server immediately returns a success response. The system then parses the batch and spawns a Celery task for each product (or in chunks of 50). This ensures the main web thread is never blocked and allows for horizontal scaling by simply adding more Celery worker processes.

**5. How would you store the Shopify taxonomy and its category hierarchy in the database?**
I would use the **Materialized Path** pattern (often implemented via `django-treebeard` or `django-mptt` in Django) in a relational database like MariaDB. While an Adjacency List (a simple `parent_id` foreign key) is easy to set up, the Materialized Path pattern is highly optimized for read-heavy operations, allowing the system to instantly retrieve full category trees, ancestors, or descendants without expensive recursive queries.

**6. How would you calculate or determine the confidence score for a classification?**
When using an LLM, I would design the prompt to explicitly ask the model to evaluate its own certainty and return a confidence score (from 0.0 to 1.0) along with its reasoning in the structured JSON output. If a hybrid approach is used, this LLM score can be combined with a semantic similarity score (cosine similarity) calculated between the product text embeddings and the selected category description embeddings.

**7. What would you do when the system cannot confidently identify a single category?**
If the confidence score falls below a predefined threshold, the system will return the top 3 most probable categories instead of a single definitive one. The product's database status will be marked as `REQUIRES_REVIEW`, and these 3 suggestions will be presented to an admin user in the UI, allowing them to make the final selection with a single click.

**8. How would you handle a broken or inaccessible product image without stopping the complete batch?**
I would implement robust exception handling (`try-except` blocks) around the image fetching logic, coupled with a strict timeout (e.g., 3-5 seconds). If an image fails to download or returns a 404, the system will catch the error, log a warning, gracefully fall back to text-only classification for that specific product, and seamlessly continue processing the rest of the batch.

**9. How would you design the API and database structure for this application?**
*   **Database:**
    *   `Category`: `id`, `shopify_id`, `name`, `path` (Tree structure).
    *   `Product`: `id`, `title`, `description`, `image_url`, `status` (PENDING, PROCESSING, COMPLETED, REQUIRES_REVIEW).
    *   `Classification`: `product_id`, `category_id`, `confidence_score`, `is_approved`.
    *   `ProductAttribute`: `product_id`, `attribute_name`, `attribute_value`.
*   **API (Django REST Framework):**
    *   `POST /api/products/batch/` (Uploads dataset, triggers Celery).
    *   `GET /api/products/` (List with filters for status, confidence).
    *   `PATCH /api/products/{id}/classification/` (Admin approves/overrides category).

**10. If the application needs to process 10,000 products and each external AI/API request takes approximately 2 seconds, how would you optimize the processing time?**
Processing sequentially would take ~5.5 hours. To optimize this, I would heavily utilize concurrency using multiple Celery workers. With 50 concurrent workers, the processing time drops to roughly 6.7 minutes. To support this without hitting API rate limits, I would implement a token-bucket rate limiter. Alternatively, if real-time processing isn't strictly necessary, I would utilize the AI provider's Batch API (e.g., OpenAI Batch API), which processes massive workloads asynchronously at 50% of the cost and with much higher limits.

**11. How would you design the system so that if processing fails after 6,000 products, it can resume from the remaining products instead of starting again?**
This is achieved via state tracking in the database. Initially, all 10,000 products are inserted with a status of `PENDING`. As Celery workers pick them up, the status changes to `PROCESSING`, and finally `COMPLETED` or `FAILED`. If the system crashes, a recovery script simply queries the database for all `PENDING` (and stale `PROCESSING`) products and re-queues them. Idempotent task design ensures no duplicate processing occurs.

**12. What technologies/frameworks would you choose for this application, and why?**
*   **Backend:** Python + Django (Rapid development, robust ORM, excellent ecosystem for data/AI).
*   **API:** Django REST Framework.
*   **Database:** MariaDB (Relational data, ACID compliance) + Redis (Message broker and caching).
*   **Background Tasks:** Celery (Industry standard for Python background processing).
*   **AI Models:** OpenAI GPT-4o-mini for text and GPT-4o for vision (Fast, highly capable, cost-effective).
*   **Frontend:** React (For building a fast, responsive admin dashboard for reviewing classifications).

**13. Provide a high-level architecture/design for the complete application.**
1.  **Client:** React SPA for uploading files and reviewing classifications.
2.  **Web Server & API:** Nginx + Gunicorn running the Django REST backend.
3.  **Task Queue:** Redis acts as the message broker passing tasks from Django to Celery.
4.  **Worker Nodes:** Multiple Celery processes picking up product classification tasks concurrently.
5.  **External Services:** Workers communicate with OpenAI APIs (for classification) and Shopify APIs (to sync taxonomy and push updated products).
6.  **Database:** MariaDB stores the taxonomy tree, product states, and final classifications.

**14. Provide a realistic development effort estimation in hours, including a task-wise breakdown.**
*   **Database Design & Project Setup:** 8h
*   **Shopify Taxonomy Ingestion & Sync:** 12h
*   **AI Integration & Prompt Engineering:** 16h
*   **Batch Processing & Celery Setup:** 16h
*   **API Development (CRUD & Batch Upload):** 16h
*   **Admin UI / Review Dashboard (React):** 24h
*   **Error Handling, Rate Limiting & Optimization:** 16h
*   **Testing & Deployment:** 12h
*   **Total:** ~120 hours (approx. 3 weeks for one developer).
*   **Assumptions:** Clear requirements, API keys provided, standard UI library (e.g., Tailwind/MUI) used.
*   **Risks:** LLM rate limits/costs, handling AI hallucinations requiring prompt tuning, taxonomy API rate limits.

**15. Practical Task: Develop a working prototype that demonstrates the above functionality using the sample product list provided.**
*(Note: The actual prototype code for this task would be developed in the project repository, implementing the core Django models, Celery tasks, and AI integration logic as discussed in the answers above.)*
