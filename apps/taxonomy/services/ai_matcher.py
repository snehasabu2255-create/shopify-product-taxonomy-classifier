import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from apps.taxonomy.models import ShopifyCategory

CATEGORY_HINTS = {
    ('living room', 'sofas and armchairs'): ['sofas', 'armchairs', 'recliners', 'sleeper chairs', 'couches', 'loveseats', 'sectionals'],
    ('living room', 'sofa sectionals'): ['sectional sofas', 'sectionals', 'sofas'],
    ('bar and dining', 'dining chairs'): ['kitchen & dining room chairs', 'dining chairs', 'chairs'],
    ('bar and dining', 'bar and counter stools'): ['table & bar stools', 'bar stools', 'counter stools', 'stools'],
    ('bar and dining', 'bar and dining tables'): ['kitchen & dining room tables', 'dining tables', 'bar tables', 'tables'],
    ('office furniture', 'office chairs'): ['office chairs', 'desk chairs', 'chairs'],
    ('office furniture', 'computer desks'): ['desks', 'office desks', 'computer desks'],
    ('outdoor furniture', 'daybeds and lounges'): ['outdoor chaises & sunloungers', 'outdoor daybeds', 'sun loungers', 'outdoor furniture'],
    ('outdoor furniture', 'sofas and armchairs'): ['outdoor sofas & sectionals', 'outdoor chairs', 'outdoor furniture'],
    ('outdoor furniture', 'tables'): ['outdoor tables', 'outdoor furniture'],
    ('lighting', 'ceiling lamps'): ['chandeliers & ceiling fixture lights', 'pendant lights', 'ceiling lamps', 'lighting'],
    ('lighting', 'table lamps'): ['table lamps', 'lamps', 'lighting'],
    ('lighting', 'floor lamps'): ['floor lamps', 'lamps', 'lighting'],
    ('bedroom', 'benches and stools'): ['benches', 'vanity stools', 'bedroom benches', 'furniture'],
    ('bedroom', 'case goods'): ['nightstands', 'dressers', 'chests', 'bedroom furniture'],
    ('bathroom', 'vanities'): ['bathroom vanities', 'vanities', 'bathroom furniture'],
    ('decor', 'pillow'): ['throw pillows', 'accent pillows', 'cushions', 'decor'],
}

STOPWORDS = {
    'by', 'modway', 'the', 'a', 'an', 'in', 'of', 'and', 'for', 'with',
    'set', 'piece', 'collection', 'series', 'inch', 'inches', 'style'
}

class TaxonomyMatcher:
    _instance = None
    _vectorizer = None
    _tfidf_matrix = None
    _categories = []
    _category_ids = []
    _category_full_names = []
    _category_names = []
    _category_name_lower_list = []
    _is_initialized = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = TaxonomyMatcher()
        return cls._instance

    def initialize(self, force=False):
        """
        Build or refresh in-memory TF-IDF index over all Shopify categories.
        """
        if self._is_initialized and not force:
            return

        qs = list(ShopifyCategory.objects.all())
        if not qs:
            self._is_initialized = False
            return

        self._categories = qs
        self._category_ids = [c.id for c in qs]
        self._category_full_names = [c.full_name for c in qs]
        self._category_names = [c.name for c in qs]
        self._category_name_lower_list = [c.name.lower() for c in qs]

        corpus = []
        for c in qs:
            vertical = c.vertical_name or ''
            name = c.name or ''
            full_name = c.full_name or ''
            search_text = c.search_text or ''
            
            doc = f"{name} {name} {name} {full_name} {full_name} {vertical} {search_text}"
            corpus.append(doc.lower())

        self._vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            sublinear_tf=True,
            token_pattern=r'(?u)\b[a-zA-Z]{2,}\b',
            max_df=0.80
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(corpus)
        self._is_initialized = True

    def extract_core_nouns(self, title, collection=''):
        """
        Extract core product noun phrase by removing brand, collection name, and boilerplate.
        """
        if not title:
            return []
        
        cleaned = re.sub(r'\bby\s+modway\b', '', title, flags=re.IGNORECASE)
        if collection:
            cleaned = re.sub(r'\b' + re.escape(collection) + r'\b', '', cleaned, flags=re.IGNORECASE)

        tokens = [
            w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', cleaned)
            if w.lower() not in STOPWORDS
        ]
        return tokens

    def classify_product(self, product):
        """
        High-speed vectorized classification against Shopify Taxonomy.
        Uses C/BLAS matrix multiplication + top-k candidate scoring.
        """
        if not self._is_initialized or not self._categories:
            self.initialize()

        if not self._is_initialized or not self._categories:
            return None, 'Unclassified', 0.0, 'REQUIRES_REVIEW', []

        prod_name = str(product.product_name or '').strip()
        prod_cat = str(product.product_category or '').strip()
        prod_sub = str(product.product_sub_category or '').strip()
        materials = str(product.materials or '').strip()
        collection = str(product.collection_name or '').strip()
        bullets = str(product.bullets or '')[:200].strip()

        core_tokens = self.extract_core_nouns(prod_name, collection)
        core_phrase = ' '.join(core_tokens)

        # Build weighted search document
        query_text = f"{core_phrase} {core_phrase} {prod_sub} {prod_sub} {prod_name} {prod_cat} {materials} {bullets}".lower()
        
        query_vec = self._vectorizer.transform([query_text])
        similarities = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        # Fast prune: Only evaluate top 60 candidates in Python
        candidate_count = min(60, len(self._categories))
        candidate_indices = np.argpartition(similarities, -candidate_count)[-candidate_count:]

        key_pair = (prod_cat.lower(), prod_sub.lower())
        bonus_keywords = CATEGORY_HINTS.get(key_pair, [])
        is_outdoor = 'outdoor' in prod_cat.lower() or 'outdoor' in prod_name.lower()
        name_lower_full = prod_name.lower()

        candidate_scores = []

        for idx in candidate_indices:
            full_lower = self._category_full_names[idx].lower()
            leaf_name_lower = self._category_name_lower_list[idx]
            cos_score = similarities[idx]

            score = cos_score * 1.6

            # 1. Direct leaf name exact match
            matched_nouns = 0
            for t in core_tokens:
                if t in leaf_name_lower or t.rstrip('s') in leaf_name_lower:
                    matched_nouns += 1
            
            if matched_nouns > 0:
                score += 0.35 * (matched_nouns / max(1, min(len(core_tokens), 3)))

            # If leaf category name matches exact noun (e.g. 'Sofas' for 'Sofa')
            if core_tokens:
                last_noun = core_tokens[-1]
                if leaf_name_lower in (last_noun, last_noun + 's', last_noun.rstrip('s')):
                    score += 0.35

            # Penalty if category has qualifiers NOT in product name (e.g. 'Bed' in 'Sofa Beds' when 'bed' not in title)
            leaf_qualifiers = set(re.findall(r'\b[a-zA-Z]{3,}\b', leaf_name_lower)) - STOPWORDS
            for lq in leaf_qualifiers:
                if lq not in name_lower_full and lq not in prod_sub.lower() and lq not in ('furniture', 'chair', 'chairs', 'table', 'tables', 'sofa', 'sofas'):
                    score -= 0.12

            # 2. Contextual category hint boost
            for kw in bonus_keywords:
                if kw in leaf_name_lower or kw in full_lower:
                    score += 0.20
                    break

            # 3. Outdoor vs Indoor context matching
            if is_outdoor:
                if 'outdoor' in full_lower or 'patio' in full_lower:
                    score += 0.25
                else:
                    score -= 0.20
            else:
                if 'outdoor' in full_lower or 'patio' in full_lower:
                    score -= 0.30

            candidate_scores.append((idx, score))

        # Sort candidate scores descending
        candidate_scores.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidate_scores[:6]

        top_matches = []
        for rank, (idx, raw) in enumerate(top_candidates):
            cat = self._categories[idx]

            # Dynamic calibrated confidence curve
            if raw >= 1.0:
                conf = 88.0 + min(10.5, (raw - 1.0) * 12.0)
            elif raw >= 0.70:
                conf = 75.0 + (raw - 0.70) * 43.0
            elif raw >= 0.45:
                conf = 60.0 + (raw - 0.45) * 60.0
            elif raw >= 0.25:
                conf = 42.0 + (raw - 0.25) * 90.0
            else:
                conf = max(10.0, raw * 160.0)

            conf = min(99.0, max(10.0, conf))

            top_matches.append({
                'category_id': cat.id,
                'category_gid': cat.category_gid,
                'full_name': cat.full_name,
                'name': cat.name,
                'confidence': round(conf, 1),
                'raw_score': raw
            })

        best_match = top_matches[0]
        best_category = self._categories[top_candidates[0][0]]
        best_category_name = best_match['full_name']
        confidence = best_match['confidence']

        # Status determination
        if confidence >= 70.0:
            status = 'CLASSIFIED'
        elif confidence >= 60.0:
            status = 'CLASSIFIED'
        else:
            status = 'REQUIRES_REVIEW'

        # Clean top 3 alternatives
        alternatives = [
            {
                'category_id': m['category_id'],
                'category_gid': m['category_gid'],
                'full_name': m['full_name'],
                'name': m['name'],
                'confidence': m['confidence']
            }
            for m in top_matches[1:4]
        ]

        return best_category, best_category_name, confidence, status, alternatives
