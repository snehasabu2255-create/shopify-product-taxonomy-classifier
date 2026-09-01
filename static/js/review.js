/**
 * Focused Rapid Review Queue - Vanilla JavaScript Controller
 */

let reviewQueue = [];
let currentIndex = 0;
let reviewSearchTimeout = null;

document.addEventListener('DOMContentLoaded', () => {
    loadReviewQueue();

    // Keyboard Shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl + Enter to Approve & Next
        if (e.ctrlKey && e.key === 'Enter') {
            e.preventDefault();
            approveCurrentReviewItem();
        }
        // Right arrow for next (only when not in input/textarea)
        else if (e.key === 'ArrowRight' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
            navigateQueue(1);
        }
        // Left arrow for prev (only when not in input/textarea)
        else if (e.key === 'ArrowLeft' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
            navigateQueue(-1);
        }
    });
});

async function loadReviewQueue() {
    const loadingEl = document.getElementById('review-loading');
    const contentEl = document.getElementById('review-content');
    const emptyEl = document.getElementById('review-empty-state');

    loadingEl.classList.remove('hidden');
    contentEl.classList.add('hidden');
    emptyEl.classList.add('hidden');

    try {
        const resp = await fetch('/api/products/?status=REVIEW_NEEDED&page_size=100');
        if (!resp.ok) throw new Error('Failed to load review items');
        const data = await resp.json();

        reviewQueue = data.results || [];
        currentIndex = 0;

        loadingEl.classList.add('hidden');

        if (reviewQueue.length === 0) {
            emptyEl.classList.remove('hidden');
            document.getElementById('review-counter').innerText = '0 items pending review';
        } else {
            contentEl.classList.remove('hidden');
            renderCurrentItem();
        }
    } catch (e) {
        loadingEl.innerHTML = `
            <div class="text-rose-400">
                <i data-lucide="alert-circle" class="w-8 h-8 mx-auto mb-2"></i>
                <p class="text-sm">Failed to load review candidates: ${e.message}</p>
            </div>
        `;
        lucide.createIcons();
    }
}

function renderCurrentItem() {
    if (reviewQueue.length === 0 || currentIndex >= reviewQueue.length) {
        document.getElementById('review-content').classList.add('hidden');
        document.getElementById('review-empty-state').classList.remove('hidden');
        document.getElementById('review-counter').innerText = 'All items reviewed!';
        return;
    }

    const p = reviewQueue[currentIndex];
    const clf = p.classification || {};

    // Update Counter
    document.getElementById('review-counter').innerText = `Item ${currentIndex + 1} of ${reviewQueue.length}`;

    // Navigation button states
    document.getElementById('btn-queue-prev').disabled = (currentIndex === 0);
    document.getElementById('btn-queue-next').disabled = (currentIndex === reviewQueue.length - 1);

    // Left Pane
    document.getElementById('review-sku').innerText = p.product_number;
    document.getElementById('review-title').innerText = p.product_name;
    document.getElementById('review-source-category').innerText = `${p.product_category || ''} > ${p.product_sub_category || ''}`;
    document.getElementById('review-materials').innerText = p.materials || '--';
    document.getElementById('review-dimensions').innerText = p.product_dimensions || '--';
    
    const msrp = p.msrp ? `$${Number(p.msrp).toFixed(2)}` : '--';
    const cost = p.item_cost ? `$${Number(p.item_cost).toFixed(2)}` : '--';
    document.getElementById('review-pricing').innerText = `${msrp} / ${cost}`;
    
    document.getElementById('review-desc').innerText = p.product_description || p.bullets || 'No description provided.';

    // Image
    const imgEl = document.getElementById('review-img');
    const imgFallback = document.getElementById('review-img-fallback');
    if (p.primary_image_url) {
        imgEl.src = p.primary_image_url;
        imgEl.classList.remove('hidden');
        imgFallback.classList.add('hidden');
    } else {
        imgEl.classList.add('hidden');
        imgFallback.classList.remove('hidden');
    }

    // Right Pane - Prediction
    const conf = clf.confidence_score || 0;
    document.getElementById('review-confidence').innerText = `${conf.toFixed(1)}% Confidence`;
    document.getElementById('review-predicted-path').innerText = clf.predicted_category_name || 'Unclassified';

    // Override inputs
    const searchInput = document.getElementById('review-category-search');
    const selectedCatId = document.getElementById('review-selected-category-id');
    searchInput.value = clf.predicted_category_name || '';
    selectedCatId.value = clf.predicted_category ? clf.predicted_category.id : '';

    // Alternatives
    const altsContainer = document.getElementById('review-alternatives-container');
    const alts = clf.alternative_categories || [];
    if (alts.length > 0) {
        let html = '';
        alts.forEach(alt => {
            html += `
                <div class="flex items-center justify-between p-2.5 rounded-lg bg-slate-900 border border-slate-800 hover:border-blue-500/50 transition-all text-xs">
                    <div class="min-w-0 flex-1 mr-2">
                        <div class="font-semibold text-slate-200 truncate">${escapeHtml(alt.full_name || alt.name)}</div>
                        <span class="text-[11px] text-purple-400 font-mono">${alt.confidence}% confidence</span>
                    </div>
                    <button type="button" onclick="selectReviewAlternative('${alt.category_id || ''}', '${escapeHtml(alt.full_name || alt.name)}')" class="px-3 py-1 rounded bg-slate-800 hover:bg-blue-600 text-slate-300 hover:text-white font-semibold text-xs transition-colors">
                        Use
                    </button>
                </div>
            `;
        });
        altsContainer.innerHTML = html;
    } else {
        altsContainer.innerHTML = '<p class="text-xs text-slate-500 italic">No alternative suggestions available.</p>';
    }

    // Attributes
    renderReviewAttributes(clf.extracted_attributes || {});
    lucide.createIcons();
}

function renderReviewAttributes(attrs) {
    const container = document.getElementById('review-attributes-container');
    container.innerHTML = '';

    const entries = Object.entries(attrs);
    if (entries.length === 0) {
        entries.push(['Color', ''], ['Material', '']);
    }

    entries.forEach(([key, value]) => {
        const div = document.createElement('div');
        div.className = 'flex items-center gap-1.5 review-attr-row';
        div.innerHTML = `
            <input type="text" value="${escapeHtml(key)}" class="review-attr-key w-1/3 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 font-medium">
            <input type="text" value="${escapeHtml(value)}" class="review-attr-val flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200">
        `;
        container.appendChild(div);
    });
}

function navigateQueue(delta) {
    const nextIdx = currentIndex + delta;
    if (nextIdx >= 0 && nextIdx < reviewQueue.length) {
        currentIndex = nextIdx;
        renderCurrentItem();
    }
}

function selectReviewAlternative(id, name) {
    document.getElementById('review-category-search').value = name;
    document.getElementById('review-selected-category-id').value = id;
    showToast(`Category updated to: ${name}`, 'info');
}

function handleReviewCategorySearch(val) {
    clearTimeout(reviewSearchTimeout);
    const dropdown = document.getElementById('review-dropdown');

    if (!val || val.length < 2) {
        dropdown.classList.add('hidden');
        return;
    }

    reviewSearchTimeout = setTimeout(async () => {
        try {
            const resp = await fetch(`/api/taxonomy/search/?q=${encodeURIComponent(val)}`);
            if (!resp.ok) return;
            const categories = await resp.json();

            if (categories.length === 0) {
                dropdown.innerHTML = '<div class="p-3 text-xs text-slate-500 text-center">No categories found</div>';
            } else {
                let html = '';
                categories.forEach(c => {
                    html += `
                        <div class="p-2.5 hover:bg-slate-800 cursor-pointer text-xs transition-colors" onclick="selectReviewCategory(${c.id}, '${escapeHtml(c.full_name)}')">
                            <div class="font-semibold text-slate-200">${escapeHtml(c.full_name)}</div>
                            <div class="text-[10px] text-slate-500 font-mono">${escapeHtml(c.category_gid)}</div>
                        </div>
                    `;
                });
                dropdown.innerHTML = html;
            }
            dropdown.classList.remove('hidden');
        } catch (e) {
            console.error(e);
        }
    }, 250);
}

function selectReviewCategory(id, full_name) {
    document.getElementById('review-category-search').value = full_name;
    document.getElementById('review-selected-category-id').value = id;
    document.getElementById('review-dropdown').classList.add('hidden');
}

async function approveCurrentReviewItem() {
    if (reviewQueue.length === 0 || currentIndex >= reviewQueue.length) return;

    const currentProduct = reviewQueue[currentIndex];
    const btn = document.getElementById('btn-review-approve');
    btn.disabled = true;

    // Gather attributes
    const extractedAttributes = {};
    document.querySelectorAll('.review-attr-row').forEach(row => {
        const k = row.querySelector('.review-attr-key').value.trim();
        const v = row.querySelector('.review-attr-val').value.trim();
        if (k) extractedAttributes[k] = v;
    });

    const categoryId = document.getElementById('review-selected-category-id').value;
    const categoryName = document.getElementById('review-category-search').value.trim();

    const payload = {
        category_id: categoryId ? parseInt(categoryId) : null,
        category_name: categoryName,
        extracted_attributes: extractedAttributes,
        status: 'APPROVED'
    };

    try {
        const resp = await fetch(`/api/products/${currentProduct.id}/review/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!resp.ok) throw new Error('Approval failed');

        showToast(`Approved ${currentProduct.product_number}!`, 'success');

        // Remove item from queue and advance
        reviewQueue.splice(currentIndex, 1);
        if (currentIndex >= reviewQueue.length) {
            currentIndex = Math.max(0, reviewQueue.length - 1);
        }

        renderCurrentItem();
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        btn.disabled = false;
    }
}

// Utility Toast
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast';
    
    let icon = 'info';
    let iconColor = 'text-blue-400';
    if (type === 'success') {
        icon = 'check-circle';
        iconColor = 'text-emerald-400';
    } else if (type === 'warning') {
        icon = 'alert-triangle';
        iconColor = 'text-amber-400';
    } else if (type === 'error') {
        icon = 'x-circle';
        iconColor = 'text-rose-400';
    }

    toast.innerHTML = `
        <i data-lucide="${icon}" class="w-4 h-4 ${iconColor}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);
    lucide.createIcons();

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(50px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
